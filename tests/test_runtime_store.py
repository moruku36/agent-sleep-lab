"""Gate 2B runtime-store behavior tests: v2 extension, registered receipts,
persisted policy CAS, and current eligibility rechecks on one connection. Synthetic data only."""

from __future__ import annotations

import os
import sqlite3
import unittest

import support  # noqa: F401
from evidence_support import LATER, NOW, make_boundary, make_item
from runtime_support import (
    MEMORY_SHA,
    OTHER_SHA,
    RuntimeCase,
    evaluation_claim,
    make_control,
    make_evaluator,
    make_verifier,
    policy_body,
    verification_claim,
)

from agent_sleep_lab.evidence_store import EvidenceStore, ReadOnlyEvidenceStore
from agent_sleep_lab.provenance import (
    BoundaryViolation,
    ConflictError,
    ContractViolation,
    NotFoundError,
    StorageError,
)
from agent_sleep_lab.runtime_store import RuntimeStore, upgrade_store_v1_to_v2

SCOPE = ("p", "t")


def derived(event_id, parent, **kw):
    kw.setdefault("origin", "recall")
    kw.setdefault("root", "e-1")
    return make_item(event_id, derived_from=[parent], **kw)


class ExtensionFormatTests(RuntimeCase):
    def user_version(self):
        return self.raw().execute("PRAGMA user_version").fetchone()[0]

    def test_fresh_store_is_v2_and_v1_classes_refuse_it(self):
        store = self.open_runtime()
        store.close()
        self.assertEqual(self.user_version(), 2)
        self.assertRaisesCode(StorageError, "storage.unknown_database",
                              lambda: EvidenceStore(self.path, make_boundary()))
        self.assertRaisesCode(StorageError, "storage.unknown_database",
                              lambda: ReadOnlyEvidenceStore(self.path))

    def test_v1_file_needs_an_explicit_upgrade_and_evidence_is_untouched(self):
        v1 = self.open()
        self.put(v1, make_item("e-1"))
        self.put(v1, derived("e-2", "e-1"))
        v1.close()
        before = self.raw().execute("SELECT * FROM evidence ORDER BY event_id").fetchall()
        blobs = self.raw().execute("SELECT * FROM source_blobs ORDER BY event_id").fetchall()
        edges = self.raw().execute("SELECT * FROM lineage ORDER BY child_id, parent_id").fetchall()

        self.assertRaisesCode(StorageError, "storage.upgrade_required",
                              lambda: RuntimeStore(self.path, make_boundary()))
        self.assertEqual(self.user_version(), 1)  # refusing did not change the file

        upgrade_store_v1_to_v2(self.path)
        self.assertEqual(self.user_version(), 2)
        self.assertEqual(self.raw().execute("SELECT * FROM evidence ORDER BY event_id").fetchall(), before)
        self.assertEqual(self.raw().execute("SELECT * FROM source_blobs ORDER BY event_id").fetchall(), blobs)
        self.assertEqual(
            self.raw().execute("SELECT * FROM lineage ORDER BY child_id, parent_id").fetchall(), edges)
        self.assertEqual(self.count("receipts"), 0)
        self.assertEqual(self.count("policy_revisions"), 0)

        store = self.open_runtime()
        self.assertEqual([self.assertTrue(store.verify(e).ok) for e in ("e-1", "e-2")], [None, None])
        self.assertRaisesCode(StorageError, "storage.unknown_database",
                              lambda: upgrade_store_v1_to_v2(self.path))  # not twice

    def test_upgrade_refuses_foreign_missing_and_tampered_files(self):
        plain = os.path.join(self.dir, "plain.db")
        conn = sqlite3.connect(plain)
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        conn.close()
        self.assertRaisesCode(StorageError, "storage.unknown_database",
                              lambda: upgrade_store_v1_to_v2(plain))
        self.assertRaisesCode(StorageError, "storage.unknown_database",
                              lambda: RuntimeStore(plain, make_boundary()))
        # A v1-labelled file that lacks the evidence schema must not be blessed.
        fake = os.path.join(self.dir, "fake.db")
        conn = sqlite3.connect(fake)
        conn.execute("CREATE TABLE evidence (x)")
        conn.execute("PRAGMA application_id = %d" % 0x41534C47)
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
        conn.close()
        self.assertRaisesCode(StorageError, "storage.unknown_database",
                              lambda: upgrade_store_v1_to_v2(fake))
        self.assertRaisesCode(StorageError, "storage.bad_path",
                              lambda: upgrade_store_v1_to_v2(":memory:"))

    def test_v2_store_with_a_dropped_extension_table_is_refused(self):
        self.open_runtime().close()
        conn = self.raw()
        self.drop_triggers(conn)
        conn.execute("DROP TABLE receipts")
        self.assertRaisesCode(StorageError, "storage.unknown_database",
                              lambda: RuntimeStore(self.path, make_boundary()))

    def test_upgrade_rejects_replaced_trigger_without_mutation(self):
        self.open().close()
        conn = self.raw()
        conn.execute("DROP TRIGGER evidence_no_delete")
        conn.execute("CREATE TRIGGER evidence_no_delete BEFORE DELETE ON evidence "
                     "BEGIN SELECT 1; END")
        before = conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall()
        self.assertRaisesCode(StorageError, "storage.unknown_database",
                              lambda: upgrade_store_v1_to_v2(self.path))
        self.assertEqual(self.user_version(), 1)
        self.assertEqual(conn.execute(
            "SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall(), before)

    def test_v2_rejects_missing_trigger_and_column_drift(self):
        for number, sql in enumerate(("DROP TRIGGER receipts_no_delete",
                                     "ALTER TABLE receipts ADD COLUMN surprise TEXT")):
            path = os.path.join(self.dir, f"drift-{number}.sqlite3")
            RuntimeStore(path, make_boundary(), clock=self.clock).close()
            conn = sqlite3.connect(path)
            try:
                conn.execute(sql)
                conn.commit()
            finally:
                conn.close()
            with self.subTest(sql):
                self.assertRaisesCode(StorageError, "storage.unknown_database",
                                      lambda: RuntimeStore(path, make_boundary()))

    def test_failed_upgrade_rolls_back_partial_extension(self):
        from unittest.mock import patch
        from agent_sleep_lab import runtime_store as runtime

        original = self.open()
        self.put(original, make_item("e-1"))
        original.close()
        before = self.raw().execute("SELECT * FROM evidence").fetchall()
        with patch.object(runtime, "_EXTENSION_DDL", runtime._EXTENSION_DDL + ("INVALID SQL",)):
            self.assertRaisesCode(StorageError, "storage.init_failed",
                                  lambda: upgrade_store_v1_to_v2(self.path))
        self.assertEqual(self.user_version(), 1)
        tables = {r[0] for r in self.raw().execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertNotIn("receipts", tables)
        self.assertNotIn("policy_revisions", tables)
        self.assertEqual(self.raw().execute("SELECT * FROM evidence").fetchall(), before)
        upgrade_store_v1_to_v2(self.path)
        self.assertTrue(self.open_runtime().verify("e-1").ok)

    def test_gate2a_capture_replay_and_verify_still_work_on_v2(self):
        store = self.open_runtime()
        self.assertEqual(self.put(store, make_item("e-1")).status, "created")
        self.assertEqual(self.put(store, make_item("e-1")).status, "replayed")
        self.put(store, derived("e-2", "e-1"))
        self.assertTrue(store.verify("e-2").ok)
        self.assertEqual(store.independent_root_count("p", "t"), 1)
        self.assertEqual(store.verify("e-1", now=LATER).failures, ("authorization.expired",))
        self.assertRaisesCode(BoundaryViolation, "boundary.authorization_stale_revision",
                              lambda: self.put(self.open_runtime(make_boundary(revision=2)),
                                               make_item("e-9", revision=1)))

    def test_extension_tables_are_append_only_and_policy_revisions_cannot_skip(self):
        store = self.open_runtime()
        self.put(store, make_item("e-1"))
        store.register_verification(make_verifier(), verification_claim(store))
        store.set_policy(make_control(), policy_body(), expected_revision=0)
        conn = self.raw()
        for sql in ("UPDATE receipts SET receipt_id = 'x'", "DELETE FROM receipts",
                    "UPDATE policy_revisions SET policy_sha256 = 'x'", "DELETE FROM policy_revisions"):
            with self.subTest(sql), self.assertRaises(sqlite3.DatabaseError):
                conn.execute(sql)
        for revision in (1, 3, 99):  # duplicate, gap, jump
            with self.subTest(revision), self.assertRaises(sqlite3.DatabaseError):
                conn.execute("INSERT INTO policy_revisions VALUES (?, ?, ?)", (revision, "x", b"x"))
        self.assertEqual(self.count("policy_revisions"), 1)


class ReceiptTests(RuntimeCase):
    def setUp(self):
        super().setUp()
        self.store = self.open_runtime()
        self.put(self.store, make_item("e-1"))
        self.verifier = make_verifier()

    def register(self, **override):
        return self.store.register_verification(
            self.verifier, verification_claim(self.store, **override))

    def test_register_resolve_replay_and_conflict(self):
        created = self.register()
        self.assertEqual((created.status, created.kind, created.receipt_id), ("created", "verification", "vr-1"))
        doc = self.store.resolve_receipt("verification", "vr-1", created.receipt_sha256)
        self.assertEqual(doc["boundary"], {"boundary_id": "synthetic-verifier", "boundary_version": "1.0.0"})
        self.assertEqual(doc["outcome"], "confirmed")

        from datetime import timedelta

        self.clock.now = self.clock.now + timedelta(hours=1)  # new issued_at, same claim
        again = self.register()
        self.assertEqual((again.status, again.receipt_sha256), ("replayed", created.receipt_sha256))
        self.assertEqual(self.count("receipts"), 1)

        self.assertRaisesCode(ConflictError, "receipt.id_conflict",
                              lambda: self.register(outcome="rejected"))
        self.assertEqual(self.count("receipts"), 1)

        # survives reopen
        self.store.close()
        reopened = self.open_runtime()
        self.assertEqual(
            reopened.resolve_receipt("verification", "vr-1", created.receipt_sha256)["receipt_id"], "vr-1")

    def test_a_claim_cannot_supply_identity_or_unlisted_methods(self):
        for key in ("boundary", "schema_version", "issued_at"):
            with self.subTest(key):
                self.assertRaisesCode(
                    ContractViolation, "contract.boundary_field_in_claim",
                    lambda key=key: self.register(**{key: "forged"}))
        self.assertRaisesCode(BoundaryViolation, "boundary.method_not_allowed",
                              lambda: self.register(method={"name": "other", "version": "1"}))
        self.assertRaises(TypeError, lambda: self.store.register_verification(object(), {}))
        self.assertRaises(TypeError, lambda: self.store.register_verification(make_evaluator(), {}))
        self.assertEqual(self.count("receipts"), 0)

    def test_evidence_binding_failures_store_nothing(self):
        good = verification_claim(self.store)["evidence"][0]
        cases = {
            "receipt.evidence_hash_mismatch": dict(good, source_sha256="0" * 64),
            "receipt.evidence_hash_mismatch ": dict(good, provenance_sha256="0" * 64),
            "receipt.evidence_unknown": dict(good, event_id="e-404"),
        }
        for code, ref in cases.items():
            with self.subTest(code):
                exc = NotFoundError if code.endswith("unknown") else ContractViolation
                self.assertRaisesCode(exc, code.strip(), lambda ref=ref: self.register(evidence=[ref]))
        self.assertRaisesCode(ContractViolation, "receipt.scope_mismatch",
                              lambda: self.register(scope={"project": "other", "task_family": "t"}))
        self.assertEqual(self.count("receipts"), 0)

    def test_corrupt_or_expired_evidence_cannot_be_certified(self):
        self.put(self.store, make_item("e-2"))
        claim = verification_claim(self.store, event_ids=("e-2",), receipt_id="vr-2")
        conn = self.raw()
        self.drop_triggers(conn)
        conn.execute("UPDATE source_blobs SET source_bytes = ? WHERE event_id = 'e-2'", (b"tampered",))
        with self.assertRaises(StorageError) as cm:
            self.store.register_verification(self.verifier, claim)
        self.assertEqual(cm.exception.code, "receipt.evidence_integrity")
        self.clock.now = LATER
        with self.assertRaises(StorageError) as cm:
            self.register(expires_at=None)  # e-1's authorization has expired by LATER
        self.assertEqual(cm.exception.code, "receipt.evidence_integrity")
        self.assertEqual(self.count("receipts"), 0)

    def test_resolution_is_by_exact_hash_and_detects_tampering(self):
        sha = self.register().receipt_sha256
        self.assertRaisesCode(ContractViolation, "receipt.hash_mismatch",
                              lambda: self.store.resolve_receipt("verification", "vr-1", OTHER_SHA))
        self.assertRaisesCode(NotFoundError, "receipt.not_found",
                              lambda: self.store.resolve_receipt("verification", "vr-9", sha))
        self.assertRaisesCode(NotFoundError, "receipt.not_found",
                              lambda: self.store.resolve_receipt("evaluation", "vr-1", sha))
        self.assertRaisesCode(ContractViolation, "receipt.unknown_kind",
                              lambda: self.store.resolve_receipt("policy", "vr-1", sha))
        self.assertRaisesCode(ContractViolation, "receipt.bad_reference",
                              lambda: self.store.resolve_receipt("verification", {"id": "vr-1"}, sha))
        conn = self.raw()
        self.drop_triggers(conn)
        conn.execute("UPDATE receipts SET receipt_bytes = ? WHERE receipt_id = 'vr-1'", (b"{}",))
        self.assertRaisesCode(StorageError, "receipt.stored_corrupt",
                              lambda: self.store.resolve_receipt("verification", "vr-1", sha))

    def test_receipt_replay_rejects_inconsistent_boundary_columns(self):
        self.register()
        conn = self.raw()
        self.drop_triggers(conn)
        conn.execute("UPDATE receipts SET boundary_id = 'changed'")
        self.assertRaisesCode(StorageError, "receipt.stored_corrupt", self.register)
        self.assertEqual(self.count("receipts"), 1)

    def test_evaluation_receipts_register_independently(self):
        evaluator = make_evaluator()
        created = self.store.register_evaluation(evaluator, evaluation_claim())
        doc = self.store.resolve_receipt("evaluation", "er-1", created.receipt_sha256)
        self.assertEqual(doc["boundary"]["boundary_id"], "synthetic-evaluator")
        self.assertEqual(self.store.register_evaluation(evaluator, evaluation_claim()).status, "replayed")
        self.assertRaisesCode(
            ConflictError, "receipt.id_conflict",
            lambda: self.store.register_evaluation(
                evaluator, evaluation_claim(snapshot_sha256=OTHER_SHA)))
        self.assertRaisesCode(
            ContractViolation, "contract.completeness",
            lambda: self.store.register_evaluation(
                evaluator, evaluation_claim(receipt_id="er-2", completeness={"planned": 3, "completed": 1})))
        self.assertRaises(TypeError, lambda: self.store.register_evaluation(make_verifier(), {}))
        # verification and evaluation namespaces do not collide
        self.register(receipt_id="er-1")
        self.assertEqual(self.count("receipts"), 2)


class PolicyTests(RuntimeCase):
    def test_missing_policy_fails_closed_and_first_revision_needs_expected_zero(self):
        store = self.open_runtime()
        self.assertRaisesCode(StorageError, "policy.missing", store.current_policy)
        self.assertRaisesCode(ConflictError, "policy.revision_conflict",
                              lambda: store.set_policy(make_control(), policy_body(), expected_revision=1))
        state = store.set_policy(make_control(), policy_body(), expected_revision=0)
        self.assertEqual(state.revision, 1)
        self.assertEqual(state.document["set_by"]["boundary_id"], "synthetic-control")
        self.assertEqual(self.count("policy_revisions"), 1)

    def test_cas_is_monotonic_and_never_resets_on_reopen(self):
        store = self.open_runtime()
        store.set_policy(make_control(), policy_body(), expected_revision=0)
        store.set_policy(make_control(), policy_body(memory_ids=["m-1"]), expected_revision=1)
        self.assertRaisesCode(ConflictError, "policy.revision_conflict",
                              lambda: store.set_policy(make_control(), policy_body(), expected_revision=1))
        self.assertRaisesCode(ConflictError, "policy.revision_conflict",
                              lambda: store.set_policy(make_control(), policy_body(), expected_revision=0))
        store.close()
        for _ in range(2):  # constructing/reopening does not reset or bump the revision
            reopened = self.open_runtime()
            self.assertEqual(reopened.current_policy().revision, 2)
            reopened.close()
        again = self.open_runtime()
        self.assertEqual(again.set_policy(make_control(), policy_body(memory_ids=["m-1"]), expected_revision=2).revision, 3)

    def test_two_writers_one_wins_the_same_expected_revision(self):
        first = self.open_runtime()
        first.set_policy(make_control(), policy_body(), expected_revision=0)
        second = self.open_runtime()
        first.set_policy(make_control(), policy_body(memory_ids=["m-a"]), expected_revision=1)
        self.assertRaisesCode(
            ConflictError, "policy.revision_conflict",
            lambda: second.set_policy(make_control(), policy_body(memory_ids=["m-b"]), expected_revision=1))
        self.assertEqual(second.current_policy().document["exclusions"]["memory_ids"], ["m-a"])

    def test_exclusions_only_grow_and_bad_input_is_rejected(self):
        store = self.open_runtime()
        store.set_policy(make_control(), policy_body(memory_ids=["m-1"], root_ids=["e-1"]), expected_revision=0)
        self.assertRaisesCode(
            ContractViolation, "policy.exclusion_removed",
            lambda: store.set_policy(make_control(), policy_body(root_ids=["e-1"]), expected_revision=1))
        grown = store.set_policy(
            make_control(), policy_body(memory_ids=["m-1", "m-2"], root_ids=["e-1"]), expected_revision=1)
        self.assertEqual(grown.revision, 2)
        for bad in (-1, "1", True, None):
            with self.subTest(bad), self.assertRaises(ContractViolation):
                store.set_policy(make_control(), policy_body(), expected_revision=bad)
        self.assertRaises(TypeError, lambda: store.set_policy(object(), policy_body(), expected_revision=2))
        self.assertRaisesCode(ContractViolation, "contract.boundary_field_in_claim",
                              lambda: store.set_policy(make_control(), dict(policy_body(), revision=9), expected_revision=2))
        self.assertEqual(store.current_policy().revision, 2)

    def test_corrupt_policy_chain_fails_closed(self):
        store = self.open_runtime()
        store.set_policy(make_control(), policy_body(), expected_revision=0)
        conn = self.raw()
        self.drop_triggers(conn)
        conn.execute("UPDATE policy_revisions SET policy_bytes = ?", (b'{"revision":1}',))
        self.assertRaisesCode(StorageError, "policy.corrupt", store.current_policy)
        self.assertRaisesCode(StorageError, "policy.corrupt",
                              lambda: store.set_policy(make_control(), policy_body(), expected_revision=1))


class EligibilityTests(RuntimeCase):
    """Reads only; each check runs on the store's own connection."""

    def setUp(self):
        super().setUp()
        self.store = self.open_runtime()
        self.put(self.store, make_item("e-1"))
        self.verifier = make_verifier()
        self.sha = self.store.register_verification(self.verifier, verification_claim(self.store)).receipt_sha256
        self.store.set_policy(make_control(), policy_body(), expected_revision=0)

    def failures(self, **override):
        kwargs = dict(memory_id="m-1", memory_sha256=MEMORY_SHA, scope=SCOPE, receipt_id="vr-1",
                      receipt_sha256=self.sha, verifier=self.verifier)
        kwargs.update(override)
        return self.store.eligibility_failures(**kwargs)

    def test_happy_path_is_eligible(self):
        self.assertEqual(self.failures(), ())

    def test_receipt_binding_and_outcome_failures(self):
        self.assertIn("receipt.memory_mismatch", self.failures(memory_sha256=OTHER_SHA))
        self.assertIn("receipt.memory_mismatch", self.failures(memory_id="m-2"))
        self.assertIn("receipt.scope_mismatch", self.failures(scope=("p", "other")))
        self.assertIn("receipt.untrusted_boundary", self.failures(verifier=make_verifier(boundary_id="other-verifier")))
        self.assertIn("receipt.untrusted_boundary", self.failures(
            verifier=make_verifier(methods=frozenset({("manual-check", "2")}))))
        self.assertEqual(self.failures(receipt_sha256=OTHER_SHA), ("receipt.unresolved.receipt.hash_mismatch",))
        self.assertEqual(self.failures(receipt_id="vr-404"), ("receipt.unresolved.receipt.not_found",))
        self.assertRaises(TypeError, lambda: self.failures(verifier=object()))
        for outcome in ("pending", "rejected"):
            sha = self.store.register_verification(
                self.verifier, verification_claim(self.store, receipt_id=f"vr-{outcome}", outcome=outcome)
            ).receipt_sha256
            self.assertEqual(self.failures(receipt_id=f"vr-{outcome}", receipt_sha256=sha),
                             ("receipt.outcome_not_confirmed",))

    def test_receipt_expiry_is_checked_at_use_time(self):
        from datetime import datetime, timezone

        later = datetime(2026, 12, 15, tzinfo=timezone.utc)  # receipt expired, evidence still valid
        self.assertEqual(self.failures(now=later), ("receipt.expired",))
        past = datetime(2026, 11, 1, tzinfo=timezone.utc)
        self.assertIn("receipt.issued_in_future", self.failures(now=past))

    def test_evidence_changes_after_registration_are_caught(self):
        conn = self.raw()
        self.drop_triggers(conn)
        conn.execute("UPDATE source_blobs SET source_bytes = ? WHERE event_id = 'e-1'", (b"changed",))
        self.assertIn("evidence.source.hash_mismatch", self.failures())
        conn.execute("DELETE FROM source_blobs WHERE event_id = 'e-1'")
        self.assertIn("evidence.source.missing", self.failures())

    def test_authorization_expiry_and_policy_mismatches(self):
        self.clock.now = LATER
        self.assertIn("evidence.authorization.expired", self.failures())
        self.clock.now = NOW
        self.store.set_policy(make_control(), policy_body(authorization_revision=2), expected_revision=1)
        self.assertIn("policy.authorization_stale", self.failures())
        self.store.set_policy(make_control(), dict(policy_body(), authorizations=[{"ref": "other-auth", "revision": 1}]),
                              expected_revision=2)
        self.assertIn("policy.authorization_unknown", self.failures())
        self.store.set_policy(make_control(), policy_body(purposes=("other_purpose",), partitions=("held_out",)),
                              expected_revision=3)
        self.assertTrue({"policy.purpose_not_accepted", "policy.partition_not_accepted"} <= set(self.failures()))

    def test_exclusions_added_after_registration_apply_to_memory_event_and_root(self):
        self.assertEqual(self.failures(), ())
        self.store.set_policy(make_control(), policy_body(memory_ids=["m-1"]), expected_revision=1)
        self.assertEqual(self.failures(), ("policy.memory_excluded",))
        self.store.set_policy(make_control(), policy_body(memory_ids=["m-1"], event_ids=["e-1"]), expected_revision=2)
        self.assertIn("policy.event_excluded", self.failures())

    def test_excluded_root_blocks_descendant_evidence(self):
        self.put(self.store, derived("e-2", "e-1"))
        sha = self.store.register_verification(
            self.verifier, verification_claim(self.store, event_ids=("e-2",), receipt_id="vr-2")).receipt_sha256
        self.assertEqual(self.failures(receipt_id="vr-2", receipt_sha256=sha), ())
        self.store.set_policy(make_control(), policy_body(root_ids=["e-1"]), expected_revision=1)
        self.assertIn("policy.root_excluded", self.failures(receipt_id="vr-2", receipt_sha256=sha))

    def test_corrupt_ancestor_and_unreadable_policy_do_not_pass(self):
        self.put(self.store, derived("e-2", "e-1"))
        sha = self.store.register_verification(
            self.verifier, verification_claim(self.store, event_ids=("e-2",), receipt_id="vr-2")).receipt_sha256
        conn = self.raw()
        self.drop_triggers(conn)
        conn.execute("UPDATE source_blobs SET source_bytes = ? WHERE event_id = 'e-1'", (b"changed",))
        self.assertIn("evidence.source.hash_mismatch", self.failures(receipt_id="vr-2", receipt_sha256=sha))
        conn.execute("DELETE FROM policy_revisions")
        self.assertRaisesCode(StorageError, "policy.missing", self.failures)

    def test_all_checks_run_in_one_immediate_transaction_on_one_connection(self):
        self.assertFalse(self.store.in_transaction)
        other = RuntimeStore(self.path, make_boundary(), clock=self.clock, busy_timeout=0.05)
        self.addCleanup(other.close)
        with self.store._immediate():
            self.assertTrue(self.store.in_transaction)
            self.assertEqual(self.failures(), ())
            self.assertEqual(self.store.current_policy().revision, 1)
            # a different connection cannot change the policy while the transaction is open
            self.assertRaisesCode(
                StorageError, "storage.busy_or_locked",
                lambda: other.set_policy(make_control(), policy_body(memory_ids=["m-1"]), expected_revision=1))
            self.assertEqual(self.failures(), ())
        self.assertFalse(self.store.in_transaction)
        other.set_policy(make_control(), policy_body(memory_ids=["m-1"]), expected_revision=1)
        self.assertEqual(self.failures(), ("policy.memory_excluded",))  # the next check sees it


if __name__ == "__main__":
    unittest.main()
