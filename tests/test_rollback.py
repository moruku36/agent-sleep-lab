"""Three synthetic Gate 3 rollback cases over the existing AdoptionStore.

Fixtures only: no model, network, real memory or live adapter. Rollback is explicit control
recovery, not a fresh adoption and not a performance evaluation. Not an acceptance report.
"""
from __future__ import annotations

import support  # noqa: F401
from evidence_support import StoreCase, make_item
from runtime_support import make_control, policy_body
import test_adoption_store as writer_fixtures
import test_retrieval as retrieval_fixtures
from agent_sleep_lab.adoption_candidates import build_rollback_request, parse_canonical
from agent_sleep_lab.provenance import ConflictError, ContractViolation, sha256_hex
from agent_sleep_lab.retrieval import retrieve_reference_bundle
from agent_sleep_lab.runtime_artifacts import encode_artifact

SCOPE = {"project": "p", "task_family": "t"}
OTHER = {"project": "q", "task_family": "u"}
TABLES = ("adoption_memories", "adoption_snapshots", "adoption_journal", "adoption_heads")


class RollbackTests(StoreCase):
    # Borrow only fixture helpers; the inherited writer/retrieval test cases are not collected here.
    open_adoption = writer_fixtures.AdoptionTests.open_adoption
    setup_store = writer_fixtures.AdoptionTests.setup_store
    adopt = retrieval_fixtures.RetrievalTests.adopt

    def request(self, operation_id, head, target, *, revision=1, scope=SCOPE, run_id="fixture-rollback"):
        data, _ = build_rollback_request(
            operation_id=operation_id, run_id=run_id, scope=scope,
            expected_head_snapshot_sha256=sha256_hex(head), target_snapshot_sha256=sha256_hex(target),
            expected_policy_revision=revision,
        )
        return data

    def tables(self):
        conn = self.raw()
        return {t: conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in TABLES}

    def ids(self, store, scope=SCOPE):
        bundle = retrieve_reference_bundle(store, scope=scope, max_bytes=1_000_000)
        return [r["memory_id"] for r in bundle.document["records"]]

    def test_scope_bound_rollback_then_normal_adoption(self):
        store = self.setup_store()
        for event_id in ("e-2", "e-3"):
            self.put(store, make_item(event_id))
        self.put(store, make_item("e-9", scope=("q", "u")))
        snap1 = self.adopt(store, "m-1", "e-1")
        snap2 = self.adopt(store, "m-2", "e-2", parent=snap1)
        other = self.adopt(store, "m-9", "e-9", scope=OTHER)
        self.assertEqual(self.ids(store), ["m-1", "m-2"])
        before = self.tables()
        # A target retained for a DIFFERENT scope is refused and changes nothing.
        cross = self.request("rb-cross", other, snap1, scope=OTHER)
        self.assertRaisesCode(ContractViolation, "rollback.scope_mismatch",
                              lambda: store.commit_rollback(request_bytes=cross))
        self.assertEqual(self.tables(), before)
        # A valid retained blob without an adoption receipt is not restorable.
        orphan = parse_canonical("candidate_snapshot", snap1)
        orphan["parent_snapshot_sha256"] = "f" * 64
        orphan_bytes = encode_artifact("candidate_snapshot", orphan)
        self.raw().execute("INSERT INTO adoption_snapshots VALUES (?, ?)",
                           (sha256_hex(orphan_bytes), orphan_bytes))
        before = self.tables()
        self.assertRaisesCode(ContractViolation, "rollback.target_not_adopted",
                              lambda: store.commit_rollback(request_bytes=self.request(
                                  "rb-orphan", snap2, orphan_bytes)))
        self.assertEqual(self.tables(), before)
        req = self.request("rb-1", snap2, snap1)
        result = store.commit_rollback(request_bytes=req)
        self.assertEqual(result.status, "created")
        receipt = parse_canonical("rollback_receipt", result.receipt_bytes)
        self.assertEqual(
            (receipt["outcome"], receipt["scope"], receipt["parent_snapshot_sha256"],
             receipt["snapshot_sha256"], receipt["policy_revision"], receipt["run_id"],
             receipt["committed_at"]),
            ("rolled_back", SCOPE, sha256_hex(snap2), sha256_hex(snap1), 1, "fixture-rollback",
             "2026-11-10T00:00:00Z"))
        self.assertEqual(receipt["request_sha256"], sha256_hex(req))
        self.assertEqual(store.current_snapshot(SCOPE), snap1)
        self.assertEqual(store.current_snapshot(OTHER), other)  # other scope is untouched
        self.assertEqual(self.ids(store), ["m-1"])  # restored head is served only after rechecks
        after = self.tables()
        for table in ("adoption_memories", "adoption_snapshots"):
            self.assertEqual(after[table], before[table])  # originals are never rewritten
        self.assertEqual(after["adoption_journal"][:len(before["adoption_journal"])],
                         before["adoption_journal"])  # earlier history is byte-identical
        self.assertEqual(len(after["adoption_journal"]), len(before["adoption_journal"]) + 1)
        # An existing adoption-v2 replay must return its original bytes, not undo rollback.
        old = self.raw().execute(
            "SELECT request_bytes, manifest_bytes, source_manifest_bytes, receipt_bytes "
            "FROM adoption_journal WHERE operation_id = ?", ("op-m-2",)).fetchone()
        memory = self.raw().execute(
            "SELECT memory_bytes FROM adoption_memories WHERE memory_id = ?", ("m-2",)).fetchone()[0]
        replay = store.commit_adoption(request_bytes=old[0], manifest_bytes=old[1],
                                       source_manifest_bytes=old[2], memory_bytes={"m-2": memory})
        self.assertEqual((replay.status, replay.receipt_bytes), ("replayed", old[3]))
        self.assertEqual(store.current_snapshot(SCOPE), snap1)
        # Ordinary adoption still works from the restored head; m-2 stays a retained, unused id.
        snap3 = self.adopt(store, "m-3", "e-3", parent=snap1)
        self.assertEqual(parse_canonical("candidate_snapshot", snap3)["parent_snapshot_sha256"],
                         sha256_hex(snap1))
        self.assertEqual(self.ids(store), ["m-1", "m-3"])

    def test_current_revocation_refuses_whole_rollback_and_leaves_history(self):
        store = self.setup_store()
        for event_id in ("e-2", "e-3"):
            self.put(store, make_item(event_id))
        snap1 = self.adopt(store, "m-1", "e-1")
        snap2 = self.adopt(store, "m-2", "e-2", parent=snap1)
        snap3 = self.adopt(store, "m-3", "e-3", parent=snap2)
        # Revoke only m-2: m-1 stays eligible, but the target {m-1, m-2} must not be filtered.
        store.set_policy(make_control(), policy_body(memory_ids=("m-2",)), expected_revision=1)
        before = self.tables()
        refused = self.request("rb-1", snap3, snap2, revision=2)
        self.assertRaisesCode(ContractViolation, "adoption.ineligible",
                              lambda: store.commit_rollback(request_bytes=refused))
        self.assertEqual(self.tables(), before)  # head, journal, snapshots, memories unchanged
        self.assertEqual(store.current_snapshot(SCOPE), snap3)
        self.assertIsNone(store.resolve_operation("rb-1"))
        # The refusal consumed nothing: a fully eligible target is still restorable explicitly.
        ok = store.commit_rollback(request_bytes=self.request("rb-2", snap3, snap1, revision=2))
        self.assertEqual(ok.status, "created")
        self.assertEqual(store.current_snapshot(SCOPE), snap1)
        self.assertEqual(self.ids(store), ["m-1"])
        # Restoring history never regains old authorization for the revoked member.
        again = self.request("rb-3", snap1, snap2, revision=2)
        self.assertRaisesCode(ContractViolation, "adoption.ineligible",
                              lambda: store.commit_rollback(request_bytes=again))
        self.assertEqual(store.current_snapshot(SCOPE), snap1)

    def test_stale_head_conflict_and_exact_replay_survive_reopen(self):
        store = self.setup_store()
        self.put(store, make_item("e-2"))
        snap1 = self.adopt(store, "m-1", "e-1")
        snap2 = self.adopt(store, "m-2", "e-2", parent=snap1)
        before = self.tables()
        stale = self.request("rb-stale", snap1, snap2)  # claims head snap1, actual head is snap2
        self.assertRaisesCode(ConflictError, "rollback.head_conflict",
                              lambda: store.commit_rollback(request_bytes=stale))
        wrong_policy = self.request("rb-policy", snap2, snap1, revision=2)
        self.assertRaisesCode(ConflictError, "adoption.policy_conflict",
                              lambda: store.commit_rollback(request_bytes=wrong_policy))
        self.assertEqual(self.tables(), before)
        self.assertIsNone(store.resolve_operation("rb-stale"))
        req = self.request("rb-1", snap2, snap1)
        first = store.commit_rollback(request_bytes=req)
        # ACK loss: the caller resolves the outcome by operation ID alone.
        self.assertEqual(store.resolve_operation("rb-1").receipt_bytes, first.receipt_bytes)
        # A later successful update must not be undone by an old rollback replay.
        self.put(store, make_item("e-3"))
        latest = self.adopt(store, "m-3", "e-3", parent=snap1)
        store.close()
        reopened = self.open_adoption()
        self.assertEqual(reopened.resolve_operation("rb-1").receipt_bytes, first.receipt_bytes)
        replay = reopened.commit_rollback(request_bytes=req)
        self.assertEqual((replay.status, replay.receipt_bytes), ("replayed", first.receipt_bytes))
        committed = self.tables()
        # A later revocation does not rewrite or re-judge the historical receipt.
        reopened.set_policy(make_control(), policy_body(memory_ids=("m-1",)), expected_revision=1)
        again = reopened.commit_rollback(request_bytes=req)
        self.assertEqual((again.status, again.receipt_bytes), ("replayed", first.receipt_bytes))
        self.assertEqual(self.tables(), committed)
        self.assertEqual(reopened.current_snapshot(SCOPE), latest)
        # Same operation ID with a different payload is a conflict, not a replay.
        changed = parse_canonical("rollback_request", req)
        changed["run_id"] = "another-run"
        self.assertRaisesCode(
            ConflictError, "adoption.operation_conflict",
            lambda: reopened.commit_rollback(request_bytes=encode_artifact("rollback_request", changed)))
        self.assertEqual(self.tables(), committed)
