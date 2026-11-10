"""Three synthetic Gate 3 audited LOGICAL-forgetting cases over the existing AdoptionStore.

Fixtures only: no model, network, real memory or live adapter. Forgetting here is an exclusion
addition plus an immutable receipt, NOT physical deletion/purge. Not an acceptance report; these
cases passed once in PR #15 CI (3 cases, 0.652 s), not full-suite acceptance of later changes.
"""
from __future__ import annotations

from unittest import mock

import support  # noqa: F401
from evidence_support import StoreCase, make_item
from runtime_support import make_control, policy_body
import test_adoption_store as writer_fixtures
import test_retrieval as retrieval_fixtures
from agent_sleep_lab.adoption_candidates import (
    build_forget_request, build_rollback_request, parse_canonical,
)
from agent_sleep_lab.provenance import ConflictError, ContractViolation, sha256_hex
from agent_sleep_lab.retrieval import retrieve_reference_bundle
from agent_sleep_lab.runtime_artifacts import encode_artifact

SCOPE = {"project": "p", "task_family": "t"}
OTHER = {"project": "q", "task_family": "u"}
TABLES = ("adoption_memories", "adoption_snapshots", "adoption_journal", "adoption_heads")


def forget_request(operation_id, *, revision, scope=SCOPE, **targets):
    data, _ = build_forget_request(
        operation_id=operation_id, run_id="fixture-forget", scope=scope,
        expected_policy_revision=revision, **targets,
    )
    return data


def rollback_request(operation_id, head, target, *, revision):
    data, _ = build_rollback_request(
        operation_id=operation_id, run_id="fixture-rollback", scope=SCOPE,
        expected_head_snapshot_sha256=sha256_hex(head),
        target_snapshot_sha256=sha256_hex(target), expected_policy_revision=revision,
    )
    return data


class ForgettingTests(StoreCase):
    # Borrow only fixture helpers; the inherited writer/retrieval test cases are not collected here.
    open_adoption = writer_fixtures.AdoptionTests.open_adoption
    setup_store = writer_fixtures.AdoptionTests.setup_store
    adopt = retrieval_fixtures.RetrievalTests.adopt

    def tables(self):
        conn = self.raw()
        return {t: conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in TABLES}

    def policy_rows(self):
        return self.count("policy_revisions")

    def ids(self, store, scope=SCOPE):
        bundle = retrieve_reference_bundle(store, scope=scope, max_bytes=1_000_000)
        return [r["memory_id"] for r in bundle.document["records"]]

    def test_same_scope_impact_preserves_unrelated_and_commit_is_atomic(self):
        store = self.setup_store()
        self.put(store, retrieval_fixtures.derived("e-2", "e-1"))  # descendant of e-1
        self.put(store, make_item("e-3"))  # unrelated, same scope
        self.put(store, make_item("e-9", scope=("q", "u")))  # another scope
        snap1 = self.adopt(store, "m-1", "e-1")
        snap2 = self.adopt(store, "m-2", "e-2", parent=snap1)
        snap3 = self.adopt(store, "m-3", "e-3", parent=snap2)
        other = self.adopt(store, "m-9", "e-9", scope=OTHER)
        store.set_policy(make_control(), policy_body(root_ids=("r-old",)), expected_revision=1)
        before_policy = store.current_policy()
        # Dry run: deterministic, read-only, IDs and counts only.
        plan = store.plan_forget_impact(scope=SCOPE, event_ids=["e-1"])
        self.assertEqual(plan.affected_event_ids, ("e-1", "e-2"))
        self.assertEqual(plan.affected_memory_ids, ("m-1", "m-2"))  # m-3 and m-9 are unrelated
        self.assertEqual(len(plan.snapshot_refs), 5)  # snap1:1, snap2:2, snap3:2 (other scope excluded)
        self.assertTrue(plan.current_head_affected)
        self.assertEqual(plan.new_exclusions, {"memory_ids": (), "event_ids": ("e-1",), "root_ids": ()})
        self.assertEqual(plan.impact_sha256, store.plan_forget_impact(
            scope=SCOPE, event_ids=["e-1"]).impact_sha256)
        self.assertNotIn("do the thing", repr(plan))  # no memory text in the plan
        only_m3 = store.plan_forget_impact(scope=SCOPE, memory_ids=["m-3"])
        self.assertEqual((only_m3.affected_event_ids, only_m3.affected_memory_ids, len(only_m3.snapshot_refs)),
                         ((), ("m-3",), 1))
        # Unknown, other-scope and non-root targets are one indistinguishable refusal.
        for bad in ({"event_ids": ["e-9"]}, {"memory_ids": ["m-9"]}, {"root_ids": ["e-2"]},
                    {"event_ids": ["nope"]}, {"root_ids": ["e-9"]}):
            self.assertRaisesCode(ContractViolation, "forget.target_unavailable",
                                  lambda b=bad: store.plan_forget_impact(scope=SCOPE, **b))
        before = self.tables()
        self.assertEqual(self.policy_rows(), 2)
        cross = forget_request("fg-cross", revision=2, event_ids=["e-9"])
        self.assertRaisesCode(ContractViolation, "forget.target_unavailable",
                              lambda: store.commit_forget(request_bytes=cross, control=make_control()))
        self.assertEqual((self.tables(), self.policy_rows()), (before, 2))
        # A failure after the policy revision was written leaves neither policy nor journal row.
        req = forget_request("fg-1", revision=2, event_ids=["e-1"])
        with mock.patch("agent_sleep_lab.adoption_store.build_forget_receipt",
                        side_effect=RuntimeError("injected")):
            with self.assertRaises(RuntimeError):
                store.commit_forget(request_bytes=req, control=make_control())
        self.assertFalse(store.in_transaction)
        self.assertEqual((self.tables(), self.policy_rows()), (before, 2))
        self.assertIsNone(store.resolve_operation("fg-1"))
        # The real commit publishes exclusion + receipt together.
        result = store.commit_forget(request_bytes=req, control=make_control())
        self.assertEqual(result.status, "created")
        receipt = parse_canonical("forget_receipt", result.receipt_bytes)
        self.assertEqual(
            (receipt["outcome"], receipt["physical_erasure"], receipt["expected_policy_revision"],
             receipt["resulting_policy_revision"], receipt["added_exclusions"], receipt["committed_at"]),
            ("logically_forgotten", "not_performed", 2, 3,
             {"memory_ids": [], "event_ids": ["e-1"], "root_ids": []}, "2026-11-10T00:00:00Z"))
        self.assertEqual(receipt["impact"], {
            "impact_sha256": plan.impact_sha256, "affected_event_count": 2,
            "affected_memory_count": 2, "affected_snapshot_ref_count": 5})
        self.assertNotIn(b"do the thing", result.receipt_bytes)
        self.assertNotIn(b"raw source", result.receipt_bytes)
        policy = store.current_policy()
        self.assertEqual(receipt["resulting_policy_sha256"], policy.sha256)
        for key in ("authorizations", "accepted_purposes", "accepted_partitions"):
            self.assertEqual(policy.document[key], before_policy.document[key])  # unrelated values kept
        self.assertEqual(policy.document["exclusions"],
                         {"memory_ids": [], "event_ids": ["e-1"], "root_ids": ["r-old"]})  # additive
        self.assertEqual(policy.document["set_by"],
                         {"boundary_id": "synthetic-control", "boundary_version": "1.0.0"})
        after = self.tables()
        for table in ("adoption_memories", "adoption_snapshots", "adoption_heads"):
            self.assertEqual(after[table], before[table])  # no head or history rewrite
        self.assertEqual(len(after["adoption_journal"]), len(before["adoption_journal"]) + 1)
        for row in before["adoption_journal"]:
            self.assertIn(row, after["adoption_journal"])  # earlier rows are byte-identical
        stored = self.raw().execute(
            "SELECT manifest_bytes, source_manifest_bytes FROM adoption_journal WHERE operation_id = 'fg-1'"
        ).fetchone()
        self.assertEqual(tuple(stored), (b"", b""))  # empty adoption payload columns
        self.assertEqual(self.policy_rows(), 3)
        self.assertEqual(store.current_snapshot(SCOPE), snap3)
        self.assertEqual(store.current_snapshot(OTHER), other)
        self.assertEqual(self.ids(store, OTHER), ["m-9"])  # the other scope is untouched

    def test_forgotten_descendant_cannot_resurrect_in_retrieval_adoption_or_rollback(self):
        store = self.setup_store()
        self.put(store, retrieval_fixtures.derived("e-2", "e-1"))
        self.put(store, retrieval_fixtures.derived("e-5", "e-2"))  # grandchild via e-2
        for event_id in ("e-3", "e-4"):
            self.put(store, make_item(event_id))
        snap1 = self.adopt(store, "m-1", "e-1")
        snap2 = self.adopt(store, "m-2", "e-2", parent=snap1)
        snap3 = self.adopt(store, "m-5", "e-5", parent=snap2)
        snap4 = self.adopt(store, "m-3", "e-3", parent=snap3)
        self.assertEqual(self.ids(store), ["m-1", "m-2", "m-3", "m-5"])
        before = self.tables()
        # Name only e-2: its descendant e-5 and the memories on both are hidden; m-1 and m-3 are not.
        plan = store.plan_forget_impact(scope=SCOPE, event_ids=["e-2"])
        self.assertEqual((plan.affected_event_ids, plan.affected_memory_ids),
                         (("e-2", "e-5"), ("m-2", "m-5")))
        store.commit_forget(request_bytes=forget_request("fg-1", revision=1, event_ids=["e-2"]),
                            control=make_control())
        after = self.tables()
        for table in ("adoption_memories", "adoption_snapshots", "adoption_heads"):
            self.assertEqual(after[table], before[table])
        self.assertEqual(store.current_snapshot(SCOPE), snap4)  # head is historical metadata only
        # Retrieval: the very next call honors the new exclusion; unrelated memories remain.
        bundle = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000)
        self.assertEqual([r["memory_id"] for r in bundle.document["records"]], ["m-1", "m-3"])
        self.assertEqual((bundle.document["policy"]["revision"], bundle.document["counts"]["active_members"]),
                         (2, 4))
        # Adoption: the head still carries forgotten active members, so a fresh adoption is refused.
        self.assertRaisesCode(ContractViolation, "adoption.ineligible",
                              lambda: self.adopt(store, "m-4", "e-4", parent=snap4, revision=2))
        self.assertEqual(store.current_snapshot(SCOPE), snap4)
        # Rollback: a target with forgotten members is refused whole, even though m-1 is fine.
        self.assertRaisesCode(ContractViolation, "adoption.ineligible", lambda: store.commit_rollback(
            request_bytes=rollback_request("rb-bad", snap4, snap3, revision=2)))
        self.assertEqual(store.current_snapshot(SCOPE), snap4)
        self.assertIsNone(store.resolve_operation("rb-bad"))
        # A fully eligible earlier snapshot is still restorable and ordinary adoption continues.
        restored = store.commit_rollback(request_bytes=rollback_request("rb-1", snap4, snap1, revision=2))
        self.assertEqual(restored.status, "created")
        self.assertEqual(self.ids(store), ["m-1"])
        # (a new memory ID: the refused m-4 attempt already registered its own receipts)
        snap5 = self.adopt(store, "m-6", "e-4", parent=snap1, revision=2)
        self.assertEqual(self.ids(store), ["m-1", "m-6"])
        # Restoring or advancing history never revives the forgotten descendants.
        self.assertRaisesCode(ContractViolation, "adoption.ineligible", lambda: store.commit_rollback(
            request_bytes=rollback_request("rb-2", snap5, snap2, revision=2)))
        self.assertEqual(store.current_snapshot(SCOPE), snap5)
        self.assertEqual(self.ids(store), ["m-1", "m-6"])

    def test_policy_cas_id_conflict_and_ack_replay_survive_reopen(self):
        store = self.setup_store()
        self.put(store, make_item("e-2"))
        snap1 = self.adopt(store, "m-1", "e-1")
        snap2 = self.adopt(store, "m-2", "e-2", parent=snap1)
        stale = forget_request("fg-stale", revision=2, event_ids=["e-2"])
        before = (self.tables(), self.policy_rows())
        self.assertRaisesCode(ConflictError, "adoption.policy_conflict",
                              lambda: store.commit_forget(request_bytes=stale, control=make_control()))
        self.assertEqual((self.tables(), self.policy_rows()), before)
        self.assertIsNone(store.resolve_operation("fg-stale"))  # a refusal consumes no operation ID
        req = forget_request("fg-1", revision=1, event_ids=["e-2"])
        first = store.commit_forget(request_bytes=req, control=make_control())
        # ACK loss: the caller resolves the outcome by operation ID alone.
        self.assertEqual(store.resolve_operation("fg-1").receipt_bytes, first.receipt_bytes)
        # Original adoption-proof scans coexist with the forget row: m-1 is still eligible.
        restored = store.commit_rollback(request_bytes=rollback_request("rb-1", snap2, snap1, revision=2))
        self.assertEqual(restored.status, "created")
        self.assertEqual(store.current_snapshot(SCOPE), snap1)
        store.close()
        reopened = self.open_adoption()
        self.assertEqual(reopened.resolve_operation("fg-1").receipt_bytes, first.receipt_bytes)
        committed = (self.tables(), self.policy_rows())
        replay = reopened.commit_forget(request_bytes=req, control=make_control())
        self.assertEqual((replay.status, replay.receipt_bytes), ("replayed", first.receipt_bytes))
        self.assertEqual((self.tables(), self.policy_rows()), committed)  # exclusions not re-applied
        # A later, unrelated policy revision does not change what replay returns.
        reopened.set_policy(make_control(), policy_body(event_ids=("e-2",), root_ids=("r-x",)),
                            expected_revision=2)
        again = reopened.commit_forget(request_bytes=req, control=make_control())
        self.assertEqual((again.status, again.receipt_bytes), ("replayed", first.receipt_bytes))
        self.assertEqual(self.policy_rows(), 3)
        # Same ID with different content is a conflict, whatever kind of request carries it.
        changed = parse_canonical("forget_request", req)
        changed["run_id"] = "another-run"
        retargeted = forget_request("fg-1", revision=1, memory_ids=["m-1"])
        crossed = rollback_request("fg-1", snap2, snap1, revision=3)
        for call in (
            lambda: reopened.commit_forget(
                request_bytes=encode_artifact("forget_request", changed), control=make_control()),
            lambda: reopened.commit_forget(request_bytes=retargeted, control=make_control()),
            lambda: reopened.commit_rollback(request_bytes=crossed),
        ):
            self.assertRaisesCode(ConflictError, "adoption.operation_conflict", call)
        # Re-forgetting an already excluded target adds nothing, so it is refused and not recorded.
        noop = forget_request("fg-2", revision=3, event_ids=["e-2"])
        self.assertRaisesCode(ContractViolation, "forget.no_new_exclusion",
                              lambda: reopened.commit_forget(request_bytes=noop, control=make_control()))
        self.assertIsNone(reopened.resolve_operation("fg-2"))
        # The exclusion union is additive: a revision that drops it is refused.
        self.assertRaisesCode(ContractViolation, "policy.exclusion_removed",
                              lambda: reopened.set_policy(make_control(), policy_body(), expected_revision=3))
        self.assertEqual(self.policy_rows(), 3)
