"""Selected synthetic v3 writer acceptance cases. No model/network/real memory."""
from __future__ import annotations

import sqlite3

import support
from evidence_support import StoreCase, make_boundary, make_item
from runtime_support import (
    RuntimeStore, evidence_ref, evaluation_claim, make_control, make_evaluator,
    make_verifier, policy_body, verification_claim,
)
from test_adoption_candidates import manifest, op
from agent_sleep_lab.adoption_candidates import build_adoption_request, build_candidate, parse_canonical
from agent_sleep_lab.adoption_store import AdoptionStore, upgrade_store_v2_to_v3
from agent_sleep_lab.provenance import ConflictError, ContractViolation, StorageError, sha256_hex
from agent_sleep_lab.runtime_artifacts import encode_artifact

SCOPE = {"project": "p", "task_family": "t"}


class AdoptionTests(StoreCase):
    def open_adoption(self):
        store = AdoptionStore(
            self.path, make_boundary(), verifier=make_verifier(), evaluator=make_evaluator(),
            evaluation_protocol=("fixture-protocol", "1", "d" * 64), clock=self.clock,
        )
        self.addCleanup(store.close)
        return store

    def setup_store(self):
        store = self.open_adoption()
        self.put(store, make_item("e-1"))
        store.set_policy(make_control(), policy_body(), expected_revision=0)
        return store

    def proposal(self, store, operation_id="op-1", mid="m-1", parent=None, revision=1,
                 kind="procedure", evaluation_override=None):
        blob = support.dumps(support.good_memory(memory_id=mid, kind=kind))
        vr = store.register_verification(
            make_verifier(), verification_claim(store, receipt_id="vr-" + operation_id,
                                                memory_id=mid, memory_sha256=sha256_hex(blob)),
        )
        ops = manifest([op("add", mid, blob, receipt={
            "receipt_id": vr.receipt_id, "receipt_sha256": vr.receipt_sha256,
        })], sha256_hex(parent) if parent else None)
        src = encode_artifact("source_manifest", {
            "schema_version": "agent-sleep-source-manifest/1", "scope": SCOPE,
            "entries": [{"memory_id": mid, "memory_sha256": sha256_hex(blob),
                         "evidence": [evidence_ref(store, "e-1")]}],
        })
        plan = build_candidate(
            manifest_bytes=ops, source_manifest_bytes=src, parent_bytes=parent,
            memory_bytes={mid: blob}, known_ids=(), now=self.clock(),
        )
        claim = evaluation_claim(
            receipt_id="er-" + operation_id, snapshot_sha256=plan.snapshot_sha256,
            operations_sha256=plan.operations_sha256,
            source_manifest_sha256=plan.source_manifest_sha256,
            expected_parent_sha256=plan.parent_sha256,
        )
        claim.update(evaluation_override or {})
        er = store.register_evaluation(make_evaluator(), claim)
        req, _ = build_adoption_request(
            operation_id=operation_id, plan=plan, expected_policy_revision=revision,
            evaluation_receipt={"receipt_id": er.receipt_id, "receipt_sha256": er.receipt_sha256},
        )
        return dict(request_bytes=req, manifest_bytes=ops, source_manifest_bytes=src,
                    memory_bytes={mid: blob})

    def test_commit_reopen_replay_after_exclusion(self):
        store = self.setup_store()
        payload = self.proposal(store)
        first = store.commit_adoption(**payload)
        self.assertEqual(first.status, "created")
        snapshot = store.current_snapshot(SCOPE)
        self.assertEqual(parse_canonical("candidate_snapshot", snapshot)["members"][0]["memory_id"], "m-1")
        self.assertEqual(self.count("adoption_journal"), 1)
        store.set_policy(make_control(), policy_body(memory_ids=("m-1",)), expected_revision=1)
        store.close()
        reopened = self.open_adoption()
        replay = reopened.commit_adoption(**payload)
        self.assertEqual((replay.status, replay.receipt_bytes), ("replayed", first.receipt_bytes))
        self.assertEqual(reopened.resolve_operation("op-1").receipt_bytes, first.receipt_bytes)
        self.assertEqual(reopened.current_snapshot(SCOPE), snapshot)
        # Historical replay does NOT override present exclusion or rewrite policy.
        self.assertEqual(reopened.current_policy().revision, 2)
        self.assertEqual(self.count("adoption_journal"), 1)
        changed = parse_canonical("adoption_request", payload["request_bytes"])
        changed["expected_policy_revision"] = 2
        changed_payload = dict(payload, request_bytes=encode_artifact("adoption_request", changed))
        self.assertRaisesCode(ConflictError, "adoption.operation_conflict",
                              lambda: reopened.commit_adoption(**changed_payload))

    def test_audit_only_does_not_initialize_scope(self):
        store = self.setup_store()
        ops = manifest([op("defer", "pending-1", sha="a" * 64)])
        src = encode_artifact("source_manifest", {
            "schema_version": "agent-sleep-source-manifest/1", "scope": SCOPE, "entries": [],
        })
        plan = build_candidate(manifest_bytes=ops, source_manifest_bytes=src, parent_bytes=None,
                               memory_bytes={}, known_ids=(), now=self.clock())
        req, _ = build_adoption_request(operation_id="audit-1", plan=plan,
                                       expected_policy_revision=1, evaluation_receipt=None)
        result = store.commit_adoption(request_bytes=req, manifest_bytes=ops,
                                       source_manifest_bytes=src, memory_bytes={})
        self.assertEqual(parse_canonical("committed_receipt", result.receipt_bytes)["outcome"], "audit_only")
        self.assertIsNone(store.current_snapshot(SCOPE))
        self.assertEqual((self.count("adoption_journal"), self.count("adoption_snapshots")), (1, 0))

    def test_two_connections_reject_stale_parent(self):
        store = self.setup_store()
        first = self.proposal(store, "winner", "m-1")
        other = self.open_adoption()
        stale = self.proposal(other, "loser", "m-2")
        store.commit_adoption(**first)
        self.assertRaisesCode(ConflictError, "adoption.parent_conflict",
                              lambda: other.commit_adoption(**stale))
        self.assertIsNone(other.resolve_operation("loser"))
        self.assertEqual((self.count("adoption_journal"), self.count("adoption_memories")), (1, 1))

    def test_carried_member_is_rechecked_under_current_policy(self):
        store = self.setup_store()
        store.commit_adoption(**self.proposal(store))
        parent = store.current_snapshot(SCOPE)
        store.set_policy(make_control(), policy_body(memory_ids=("m-1",)), expected_revision=1)
        payload = self.proposal(store, "next", "m-2", parent=parent, revision=2)
        self.assertRaisesCode(ContractViolation, "adoption.ineligible",
                              lambda: store.commit_adoption(**payload))
        self.assertEqual(store.current_snapshot(SCOPE), parent)
        self.assertIsNone(store.resolve_operation("next"))
        self.assertEqual(self.count("adoption_memories"), 1)

    def test_registered_evaluation_must_bind_exact_protocol_config(self):
        store = self.setup_store()
        payload = self.proposal(
            store, evaluation_override={
                "protocol": {"name": "fixture-protocol", "version": "1", "config_sha256": "e" * 64},
            },
        )
        self.assertRaisesCode(ContractViolation, "adoption.evaluation_binding",
                              lambda: store.commit_adoption(**payload))
        self.assertEqual(self.count("adoption_journal"), 0)
        self.assertIsNone(store.current_snapshot(SCOPE))

    def test_late_write_failure_rolls_back_payloads_and_head(self):
        store = self.setup_store()
        payload = self.proposal(store)
        # Inject a failure after memory, snapshot and journal inserts, at the final head write.
        original = store._db().set_authorizer
        def deny_head_insert(action, table, column, database, source):
            if action == sqlite3.SQLITE_INSERT and table == "adoption_heads":
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        original(deny_head_insert)
        try:
            self.assertRaisesCode(StorageError, "storage.write_failed",
                                  lambda: store.commit_adoption(**payload))
        finally:
            original(None)
        self.assertEqual(tuple(self.count(t) for t in (
            "adoption_memories", "adoption_snapshots", "adoption_journal", "adoption_heads",
        )), (0, 0, 0, 0))
        self.assertEqual(store.current_policy().revision, 1)

    def test_explicit_upgrade_preserves_evidence_and_policy(self):
        old = RuntimeStore(self.path, make_boundary(), clock=self.clock)
        self.addCleanup(old.close)
        self.put(old, make_item("e-1"))
        old.set_policy(make_control(), policy_body(), expected_revision=0)
        before = old.get("e-1")
        old.close()
        self.assertRaisesCode(StorageError, "storage.upgrade_required", self.open_adoption)
        upgrade_store_v2_to_v3(self.path)
        store = self.open_adoption()
        self.assertEqual(store.get("e-1"), before)
        self.assertEqual(store.current_policy().revision, 1)
        self.assertEqual(self.count("adoption_journal"), 0)
