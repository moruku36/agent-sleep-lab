"""Five proposed review-fix cases. Bodies unexecuted until an explicit budget increase."""
from __future__ import annotations

from pathlib import Path
from unittest import mock

import support  # noqa: F401
from evidence_support import StoreCase, make_item
from runtime_support import make_control, policy_body
import test_adoption_store as writer_fixtures
import test_retrieval as retrieval_fixtures
from agent_sleep_lab.retrieval import retrieve_reference_bundle
from agent_sleep_lab.validation import read_input, InputError

SCOPE = {"project": "p", "task_family": "t"}


class ReviewFixTests(StoreCase):
    open_adoption = writer_fixtures.AdoptionTests.open_adoption
    setup_store = writer_fixtures.AdoptionTests.setup_store
    adopt = retrieval_fixtures.RetrievalTests.adopt

    def test_bilingual_ranking_normalizes_punctuation_and_keeps_no_query_order(self):
        store = self.setup_store()
        self.put(store, make_item("e-2"))
        first = self.adopt(store, "m-1", "e-1", claim="機械学習の論文を整理する", tags=("研究",))
        self.adopt(store, "m-2", "e-2", claim="Atomic, SAFE rollback.", parent=first, tags=("Café",))
        def records(query):
            return retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000,
                                             query=query).document["records"]
        japanese = records("論文整理")
        self.assertEqual(japanese[0]["memory_id"], "m-1")
        self.assertGreater(japanese[0]["score"], 0)
        english = records("ＡＴＯＭＩＣ! safe,")
        self.assertEqual((english[0]["memory_id"], english[0]["score"]), ("m-2", 2))
        self.assertEqual(records("cafe\u0301")[0]["memory_id"], "m-2")
        self.assertEqual([r["memory_id"] for r in records(None)], ["m-1", "m-2"])
        self.assertEqual([r["memory_id"] for r in records("...")], ["m-1", "m-2"])

    def test_policy_chain_is_once_per_retrieval_and_revocation_is_not_cached(self):
        store = self.setup_store()
        self.put(store, make_item("e-2"))
        first = self.adopt(store, "m-1", "e-1")
        self.adopt(store, "m-2", "e-2", parent=first)
        with mock.patch.object(store, "current_policy", wraps=store.current_policy) as read:
            bundle = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000)
            self.assertEqual(len(bundle.document["records"]), 2)
            self.assertEqual(read.call_count, 1)
        store.set_policy(make_control(), policy_body(memory_ids=("m-1",)), expected_revision=1)
        with mock.patch.object(store, "current_policy", wraps=store.current_policy) as read:
            bundle = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000)
            self.assertEqual([r["memory_id"] for r in bundle.document["records"]], ["m-2"])
            self.assertEqual(bundle.document["policy"]["revision"], 2)
            self.assertEqual(read.call_count, 1)

    def test_metadata_reads_do_not_reserve_writer_and_cleanup_on_failure(self):
        store = self.setup_store()
        snap = self.adopt(store, "m-1", "e-1")
        writer = self.raw()
        writer.execute("BEGIN IMMEDIATE")  # reader must still work, without a reserved lock
        self.addCleanup(writer.rollback)
        store._db().execute("PRAGMA busy_timeout = 0")
        trace = []
        store._db().set_trace_callback(trace.append)
        self.addCleanup(lambda: store._db().set_trace_callback(None))
        self.assertIsNotNone(store.resolve_operation("op-m-1"))
        self.assertEqual(store.current_snapshot(SCOPE), snap)
        self.assertFalse(store.in_transaction)
        self.assertNotIn("BEGIN IMMEDIATE", [s.strip().upper() for s in trace])
        self.assertIn("BEGIN", [s.strip().upper() for s in trace])
        with mock.patch.object(store, "_resolve_operation", side_effect=RuntimeError("injected")):
            with self.assertRaises(RuntimeError):
                store.resolve_operation("op-m-1")
        self.assertFalse(store.in_transaction)

    def test_directory_is_classified_before_open_and_regular_permission_is_preserved(self):
        directory = str(Path(self.path).parent)
        with mock.patch("agent_sleep_lab.validation.os.open",
                        side_effect=PermissionError("Windows directory")) as opened:
            self.assertRaisesCode(InputError, "io.not_regular_file", lambda: read_input(directory))
            opened.assert_not_called()
        regular = Path(directory) / "regular-input.json"
        regular.write_bytes(b"{}")
        with mock.patch("agent_sleep_lab.validation.os.open", side_effect=PermissionError("denied")):
            self.assertRaisesCode(InputError, "io.permission_denied", lambda: read_input(str(regular)))
        self.assertEqual(read_input(str(regular)), b"{}")

    def test_rollback_ignores_unrelated_broken_journal_but_checks_target_proof(self):
        store = self.setup_store()
        self.put(store, make_item("e-2"))
        # Simulate a corrupt unrelated row, restoring append-only trigger DDL afterwards.
        raw = self.raw()
        triggers = raw.execute("SELECT name, sql FROM sqlite_master WHERE type = 'trigger'").fetchall()
        self.drop_triggers(raw)
        raw.execute("INSERT INTO adoption_journal VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("unrelated-corrupt", "0" * 64, b"not-json", b"", b"", "0" * 64, b"bad"))
        for _, ddl in triggers:
            raw.execute(ddl)
        snap1 = self.adopt(store, "m-1", "e-1")
        snap2 = self.adopt(store, "m-2", "e-2", parent=snap1)
        from agent_sleep_lab.adoption_candidates import build_rollback_request
        from agent_sleep_lab.provenance import sha256_hex
        request, _ = build_rollback_request(
            operation_id="rb-review", run_id="fixture-review", scope=SCOPE,
            expected_head_snapshot_sha256=sha256_hex(snap2),
            target_snapshot_sha256=sha256_hex(snap1), expected_policy_revision=1)
        result = store.commit_rollback(request_bytes=request)
        self.assertEqual(result.status, "created")
        self.assertEqual(store.current_snapshot(SCOPE), snap1)
        # Selection is not proof: corrupting the MATCHING adoption receipt must still refuse.
        self.drop_triggers(raw)
        raw.execute("UPDATE adoption_journal SET receipt_sha256 = ? WHERE operation_id = ?",
                    ("0" * 64, "op-m-2"))
        for _, ddl in triggers:
            raw.execute(ddl)
        bad_request, _ = build_rollback_request(
            operation_id="rb-bad-proof", run_id="fixture-review", scope=SCOPE,
            expected_head_snapshot_sha256=sha256_hex(snap1),
            target_snapshot_sha256=sha256_hex(snap2), expected_policy_revision=1)
        from agent_sleep_lab.provenance import StorageError
        self.assertRaisesCode(StorageError, "adoption.journal_corrupt",
                              lambda: store.commit_rollback(request_bytes=bad_request))
        self.assertEqual(store.current_snapshot(SCOPE), snap1)
        self.assertIsNone(store.resolve_operation("rb-bad-proof"))
