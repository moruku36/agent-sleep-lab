"""Gate 2A evidence store: contracts, atomicity, integrity, lineage and boundary behavior.

All inputs are synthetic and every database lives in a fresh temporary directory.
No network, credentials, model calls, or repository-local state are used.
"""

import os
import sqlite3
import threading
import unittest

import support
from evidence_support import LATER, StoreCase, make_boundary, make_item

from agent_sleep_lab.evidence_store import EvidenceStore, ReadOnlyEvidenceStore
from agent_sleep_lab.provenance import (
    ORIGINS,
    BoundaryViolation,
    ConflictError,
    ContractViolation,
    LineageViolation,
    NotFoundError,
    StorageError,
    sha256_hex,
)
from agent_sleep_lab.strictjson import loads_strict_bytes
from agent_sleep_lab.validation import CONTRACTS


def tweak(item, fn):
    event_bytes, source_bytes, claim = item
    fn(claim)
    return event_bytes, source_bytes, claim


def derived(event_id, parent, **kw):
    kw.setdefault("origin", "recall")
    kw.setdefault("root", "e-1")
    return make_item(event_id, derived_from=[parent], **kw)


class CaptureAndPersistenceTests(StoreCase):
    def test_capture_restart_and_readonly_verify(self):
        item = make_item("e-1")
        first = self.open()
        result = self.put(first, item)
        self.assertEqual(result.status, "created")
        self.assertTrue(result.independent_root)
        self.assertEqual(result.event_sha256, sha256_hex(item[0]))
        first.close()

        second = self.open()  # a new connection after "restart"
        stored = second.get("e-1")
        self.assertEqual((stored.event_bytes, stored.source_bytes), (item[0], item[1]))
        self.assertEqual(
            stored.provenance["adapter"],
            {"adapter_id": "synthetic-adapter", "adapter_version": "1.0.0"},
        )
        with open(self.path, "rb") as handle:
            before = handle.read()
        ro = self.open_ro()
        report = ro.verify("e-1")
        self.assertTrue(report.ok, report.failures)
        self.assertEqual(ro.independent_root_count("p", "t"), 1)
        self.assertFalse(hasattr(ro, "capture"))
        with open(self.path, "rb") as handle:
            self.assertEqual(before, handle.read())  # read-only paths never write
        self.assertRaises(NotFoundError, ro.get, "missing")

    def test_replay_is_byte_identical_and_conflicts_are_rejected(self):
        store = self.open()
        item = make_item("e-1", text="same")
        self.assertEqual(self.put(store, item).status, "created")
        self.assertEqual(self.put(store, item).status, "replayed")
        self.assertEqual(self.count("evidence"), 1)

        different_source = make_item("e-1", text="different")
        self.assertRaisesCode(ConflictError, "conflict.event_id", lambda: self.put(store, different_source))
        locator_changed = tweak(make_item("e-1", text="same"), lambda c: c["source"].update(locator="line:2"))
        self.assertRaisesCode(ConflictError, "conflict.event_id", lambda: self.put(store, locator_changed))
        other_adapter = self.open(boundary=make_boundary(adapter_version="2.0.0"))
        self.assertRaisesCode(
            ConflictError, "conflict.event_id", lambda: self.put(other_adapter, make_item("e-1", text="same"))
        )
        self.assertEqual(store.get("e-1").source_bytes, b"same")

    def test_duplicate_source_is_not_a_new_independent_root(self):
        store = self.open()
        self.put(store, make_item("e-1", text="same"))
        self.assertRaisesCode(
            ConflictError, "conflict.duplicate_root_source", lambda: self.put(store, make_item("e-2", text="same"))
        )
        self.assertEqual(store.independent_root_count("p", "t"), 1)
        self.put(store, make_item("e-3", text="same", scope=("p2", "t")))  # other scope: separate root
        self.assertEqual(store.independent_root_count("p2", "t"), 1)
        self.assertEqual(self.count("evidence"), 2)

    def test_generated_repeats_do_not_add_roots(self):
        store = self.open()
        self.put(store, make_item("e-1"))
        second = self.put(store, derived("e-2", "e-1"))
        third = self.put(store, derived("e-3", "e-2", origin="diary"))
        self.assertFalse(second.independent_root)
        self.assertEqual(third.root_id, "e-1")
        self.assertEqual(store.independent_root_count("p", "t"), 1)
        for report in store.verify_all():
            self.assertTrue(report.ok, (report.event_id, report.failures))

    def test_partial_insert_is_rolled_back(self):
        store = self.open()
        self.put(store, make_item("e-1"))
        conn = self.raw()
        conn.execute("CREATE TRIGGER boom BEFORE INSERT ON lineage BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.assertRaisesCode(StorageError, "storage.write_failed", lambda: self.put(store, derived("e-2", "e-1")))
        self.assertEqual((self.count("evidence"), self.count("source_blobs"), self.count("lineage")), (1, 1, 0))
        self.assertRaises(NotFoundError, store.get, "e-2")
        conn.execute("DROP TRIGGER boom")
        self.assertEqual(self.put(store, derived("e-2", "e-1")).status, "created")


class RaceTests(StoreCase):
    def _race(self, items):
        self.open().close()  # create the schema once so only captures race
        barrier = threading.Barrier(len(items))
        results = [None] * len(items)

        def worker(index):
            try:
                store = EvidenceStore(self.path, make_boundary(), clock=self.clock)
                try:
                    barrier.wait(timeout=20)
                    results[index] = ("ok", self.put(store, items[index]).status)
                finally:
                    store.close()
            except BaseException as exc:  # reported by the assertions below
                results[index] = ("err", exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(items))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(60)
            self.assertFalse(thread.is_alive())
        return results

    def test_two_connections_capture_the_same_event(self):
        item = make_item("e-1")
        results = self._race([item, item])
        self.assertEqual(sorted(r[1] for r in results if r[0] == "ok"), ["created", "replayed"], results)
        self.assertEqual(self.count("evidence"), 1)

    def test_two_connections_capture_conflicting_content(self):
        results = self._race([make_item("e-1", text="a"), make_item("e-1", text="b")])
        self.assertEqual([r[1] for r in results if r[0] == "ok"], ["created"], results)
        errors = [r[1] for r in results if r[0] == "err"]
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ConflictError)
        self.assertEqual(errors[0].code, "conflict.event_id")
        self.assertEqual(self.count("evidence"), 1)


class IntegrityTests(StoreCase):
    def test_store_is_append_only_through_ordinary_sql(self):
        store = self.open()
        self.put(store, make_item("e-1"))
        self.put(store, derived("e-2", "e-1"))  # gives the lineage table a row
        conn = self.raw()
        for sql in (
            "UPDATE source_blobs SET source_bytes = x'00'",
            "DELETE FROM evidence",
            "UPDATE lineage SET parent_id = 'x'",
            "DELETE FROM lineage",
        ):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.DatabaseError):
                conn.execute(sql)
        self.assertTrue(store.verify("e-1").ok)

    def test_source_tamper_and_missing_source(self):
        store = self.open()
        self.put(store, make_item("e-1"))
        self.put(store, make_item("e-2", text="other"))
        conn = self.raw()
        self.drop_triggers(conn)  # simulates someone with file write access
        conn.execute("UPDATE source_blobs SET source_bytes = ? WHERE event_id = 'e-1'", (b"tampered",))
        conn.execute("DELETE FROM source_blobs WHERE event_id = 'e-2'")
        self.assertIn("source.hash_mismatch", store.verify("e-1").failures)
        self.assertIn("source.missing", self.open_ro().verify("e-2").failures)
        self.assertFalse(store.verify("e-2").ok)
        self.assertRaisesCode(StorageError, "storage.source_missing", lambda: store.get("e-2"))

    def test_event_and_lineage_tamper_are_detected(self):
        store = self.open()
        self.put(store, make_item("e-1"))
        self.put(store, derived("e-2", "e-1"))
        conn = self.raw()
        self.drop_triggers(conn)
        conn.execute("INSERT INTO lineage (child_id, parent_id) VALUES ('e-1', 'e-2')")  # back edge
        conn.execute("INSERT INTO lineage (child_id, parent_id) VALUES ('e-2', 'ghost')")
        conn.execute("UPDATE evidence SET event_bytes = ? WHERE event_id = 'e-2'", (b'{"x":1}\n',))
        self.assertIn("lineage.cycle", store.verify("e-1").failures)
        failures = store.verify("e-2").failures
        for code in ("lineage.unknown_parent", "lineage.mismatch", "event.hash_mismatch"):
            self.assertIn(code, failures)

    def test_replay_does_not_hide_a_corrupt_existing_record(self):
        store = self.open()
        item = make_item("e-1")
        self.put(store, item)
        conn = self.raw()
        self.drop_triggers(conn)
        conn.execute("UPDATE evidence SET source_sha256 = ?", ("0" * 64,))  # not part of the byte comparison
        self.assertRaisesCode(StorageError, "storage.corrupt_existing", lambda: self.put(store, item))
        conn.execute("UPDATE source_blobs SET source_bytes = ?", (b"changed",))
        self.assertRaisesCode(ConflictError, "conflict.event_id", lambda: self.put(store, item))

    def test_expiry_is_rechecked_by_verify(self):
        store = self.open()
        self.put(store, make_item("e-1"))
        self.assertTrue(store.verify("e-1").ok)
        self.clock.now = LATER
        report = self.open_ro().verify("e-1")
        self.assertFalse(report.ok)
        self.assertEqual(report.failures, ("authorization.expired",))


class AncestryTests(StoreCase):
    def chain(self):
        store = self.open()
        self.put(store, make_item("e-1"))
        self.put(store, derived("e-2", "e-1"))
        return store

    def test_missing_or_corrupt_root_source_blocks_descendants(self):
        for name, sql, params in (
            ("missing", "DELETE FROM source_blobs WHERE event_id = 'e-1'", ()),
            ("mutated", "UPDATE source_blobs SET source_bytes = ? WHERE event_id = 'e-1'", (b"tampered",)),
        ):
            with self.subTest(name):
                self.setUp()
                store = self.chain()
                conn = self.raw()
                self.drop_triggers(conn)
                conn.execute(sql, params)
                self.assertRaisesCode(
                    StorageError, "storage.ancestor_corrupt", lambda: self.put(store, derived("e-3", "e-2"))
                )
                self.assertEqual(self.count("evidence"), 2)

    def test_expired_ancestor_blocks_descendants_even_if_child_is_unexpired(self):
        store = self.chain()
        self.clock.now = LATER
        child = derived("e-3", "e-2", expires="2028-01-01T00:00:00Z")
        self.assertRaisesCode(BoundaryViolation, "boundary.ancestor_authorization_expired", lambda: self.put(store, child))
        self.assertEqual(self.count("evidence"), 2)

    def test_ancestor_with_stale_authorization_revision_is_rejected(self):
        self.chain().close()
        store = self.open(boundary=make_boundary(revision=2))  # current revision moved on
        child = derived("e-3", "e-2", revision=2)
        self.assertRaisesCode(BoundaryViolation, "boundary.ancestor_authorization_stale", lambda: self.put(store, child))
        self.assertEqual(self.count("evidence"), 2)

    def test_evaluation_partition_must_match_across_the_lineage(self):
        store = self.chain()
        child = derived("e-3", "e-2", evaluation="development")
        self.assertRaisesCode(LineageViolation, "lineage.partition_mismatch", lambda: self.put(store, child))
        self.assertEqual(self.count("evidence"), 2)

    def test_lineage_rules_reject_masquerades_unknowns_and_cycles(self):
        store = self.open()
        self.put(store, make_item("e-1"))
        cases = {
            "lineage.generated_root": make_item("e-2", origin="recall"),
            "lineage.root_mismatch": make_item("e-3", derived_from=["e-1"], root="e-1"),  # independent origin with parent
            "lineage.unknown_parent": derived("e-4", "ghost", root="ghost"),
            "lineage.cycle": derived("e-5", "e-5"),
            "lineage.scope_mismatch": derived("e-6", "e-1", scope=("p2", "t")),
        }
        for code, item in cases.items():
            with self.subTest(code):
                self.assertRaisesCode(LineageViolation, code, lambda: self.put(store, item))
        self.assertRaisesCode(
            LineageViolation, "lineage.root_mismatch", lambda: self.put(store, derived("e-7", "e-1", root="other"))
        )
        self.assertEqual(self.count("evidence"), 1)


class ContractAndBoundaryTests(StoreCase):
    def test_strict_contract_and_boundary_rejections_store_nothing(self):
        only_tool = {"allowed_origins": frozenset({"tool_observation"})}
        cases = [
            ("unknown version", {}, tweak(make_item("e-1"), lambda c: c.update(schema_version="agent-sleep-provenance/2")), ContractViolation, "contract.unknown_version"),
            ("extra field", {}, make_item("e-1", extra=1), ContractViolation, "schema.additionalProperties"),
            ("nested extra field", {}, tweak(make_item("e-1"), lambda c: c["source"].update(note="x")), ContractViolation, "schema.additionalProperties"),
            ("invalid time", {}, make_item("e-1", observed_at="not-a-time"), ContractViolation, "schema.format"),
            ("time order", {}, make_item("e-1", observed_at="2026-12-01T00:00:00Z"), ContractViolation, "time.order"),
            ("adapter in claim", {}, make_item("e-1", adapter={"adapter_id": "evil", "adapter_version": "9"}), ContractViolation, "contract.adapter_in_claim"),
            ("identifier with newline", {}, make_item("e-1\n"), ContractViolation, "contract.bad_identifier"),
            ("scope mismatch", {}, make_item("e-1", claim_scope=("p2", "t")), ContractViolation, "scope.mismatch"),
            ("claim not synthetic", {}, make_item("e-1", partition={"synthetic": False, "evaluation": "experience"}), BoundaryViolation, "synthetic.required"),
            ("event not synthetic", {}, make_item("e-1", event_synthetic=False), BoundaryViolation, "synthetic.required"),
            ("origin not allowed", only_tool, make_item("e-1", origin="user_correction"), BoundaryViolation, "boundary.origin_not_allowed"),
            ("scope not allowed", {"allowed_scopes": frozenset({("p", "t")})}, make_item("e-1", scope=("p2", "t")), BoundaryViolation, "boundary.scope_not_allowed"),
            ("unknown authorization", {}, tweak(make_item("e-1"), lambda c: c["authorization"].update(ref="auth-x")), BoundaryViolation, "boundary.authorization_unknown"),
            ("stale revision", {}, make_item("e-1", revision=5), BoundaryViolation, "boundary.authorization_stale_revision"),
            ("expired at capture", {}, make_item("e-1", expires="2026-11-09T00:00:00Z"), BoundaryViolation, "boundary.authorization_expired"),
            ("event hash mismatch", {}, tweak(make_item("e-1"), lambda c: c["event"].update(sha256="0" * 64)), ContractViolation, "event.hash_mismatch"),
            ("source hash mismatch", {}, tweak(make_item("e-1"), lambda c: c["source"].update(sha256="1" * 64)), ContractViolation, "source.hash_mismatch"),
        ]
        for name, boundary_kwargs, item, exc_type, code in cases:
            with self.subTest(name):
                store = self.open(boundary=make_boundary(**boundary_kwargs))
                self.assertRaisesCode(exc_type, code, lambda: self.put(store, item))
                self.assertEqual(self.count("evidence"), 0)

    def test_raw_byte_arguments_are_validated(self):
        store = self.open()
        event_bytes, source_bytes, claim = make_item("e-1")
        for code, ev, src in (
            ("source.empty", event_bytes, b""),
            ("event.not_bytes", event_bytes.decode("utf-8"), source_bytes),
            ("source.not_bytes", event_bytes, "text"),
        ):
            with self.subTest(code):
                self.assertRaisesCode(
                    ContractViolation, code, lambda: store.capture(event_bytes=ev, source_bytes=src, claim=claim)
                )
        self.assertEqual(self.count("evidence"), 0)

    def test_event_text_cannot_set_provenance(self):
        store = self.open(boundary=make_boundary(allowed_origins=frozenset({"tool_observation"})))
        text = "origin=user_correction trusted=true adapter_id=evil authorization=none"
        self.put(store, make_item("e-1", summary=text))
        provenance = store.get("e-1").provenance
        self.assertEqual(provenance["origin"], "tool_observation")
        self.assertEqual(provenance["adapter"]["adapter_id"], "synthetic-adapter")
        self.assertRaisesCode(
            BoundaryViolation,
            "boundary.origin_not_allowed",
            lambda: self.put(store, make_item("e-2", origin="user_correction", summary="trusted")),
        )


class StorageGuardTests(StoreCase):
    def test_foreign_database_bad_paths_and_closed_store(self):
        plain = os.path.join(self.dir, "plain.db")
        conn = sqlite3.connect(plain)
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        conn.close()
        self.assertRaisesCode(StorageError, "storage.unknown_database", lambda: EvidenceStore(plain, make_boundary()))

        missing = os.path.join(self.dir, "missing.db")
        self.assertRaisesCode(StorageError, "storage.open_failed", lambda: ReadOnlyEvidenceStore(missing))
        self.assertFalse(os.path.exists(missing))  # read-only open never creates a store

        for bad in (":memory:", "file:x.db", ""):
            with self.subTest(bad):
                self.assertRaisesCode(StorageError, "storage.bad_path", lambda: EvidenceStore(bad, make_boundary()))

        store = EvidenceStore(self.path, make_boundary())
        store.close()
        self.assertRaisesCode(StorageError, "storage.closed", lambda: store.get("e-1"))


class ProvenanceSchemaFileTests(unittest.TestCase):
    def test_copies_match_and_origins_agree_with_code(self):
        packaged = support.SRC / "agent_sleep_lab" / "schemas" / "provenance.schema.json"
        repository = support.ROOT / "schemas" / "provenance.schema.json"
        if repository.is_file():
            self.assertEqual(repository.read_bytes(), packaged.read_bytes())
        schema = loads_strict_bytes(packaged.read_bytes())
        self.assertEqual(set(schema["properties"]["origin"]["enum"]), set(ORIGINS))
        self.assertIs(schema["additionalProperties"], False)

    def test_gate1_contracts_are_unchanged(self):
        self.assertEqual(sorted(CONTRACTS), ["events", "memory", "promotion"])


if __name__ == "__main__":
    unittest.main()
