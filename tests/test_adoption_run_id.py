"""Three selected versioned audit-label cases; synthetic manually seeded v1 history.

Historical fixtures reproduce the frozen v1 wire/DDL contract, not an execution
of a previously installed binary. No live run registry/authentication is claimed.
"""
from evidence_support import StoreCase
from runtime_support import make_control, policy_body
from test_adoption_candidates import manifest, op
from test_adoption_store import AdoptionTests, SCOPE
from agent_sleep_lab.adoption_candidates import (
    build_adoption_request, build_candidate, build_committed_receipt, parse_canonical,
)
from agent_sleep_lab.provenance import ConflictError, ContractViolation, sha256_hex
from agent_sleep_lab.runtime_artifacts import encode_artifact


class RunIdTests(StoreCase):
    open_adoption = AdoptionTests.open_adoption
    setup_store = AdoptionTests.setup_store
    proposal = AdoptionTests.proposal

    def audit_payload(self, operation_id):
        ops = manifest([op("defer", "pending-1", sha="a" * 64)])
        source = encode_artifact("source_manifest", {
            "schema_version": "agent-sleep-source-manifest/1", "scope": SCOPE, "entries": [],
        })
        plan = build_candidate(manifest_bytes=ops, source_manifest_bytes=source,
                               parent_bytes=None, memory_bytes={}, known_ids=(), now=self.clock())
        req, _ = build_adoption_request(operation_id=operation_id, run_id="audit-run",
                                       plan=plan, expected_policy_revision=1, evaluation_receipt=None)
        return dict(request_bytes=req, manifest_bytes=ops, source_manifest_bytes=source, memory_bytes={})

    def legacy_payload(self, payload):
        doc = parse_canonical("adoption_request", payload["request_bytes"])
        doc["schema_version"] = "agent-sleep-adoption-request/1"
        del doc["run_id"]
        return dict(payload, request_bytes=encode_artifact("adoption_request", doc))

    def seed_v1(self, payload):
        """Seed historical rows directly: do not weaken the new writer's v1 gate."""
        req = parse_canonical("adoption_request", payload["request_bytes"])
        assert req["schema_version"] == "agent-sleep-adoption-request/1"
        plan = build_candidate(
            manifest_bytes=payload["manifest_bytes"], source_manifest_bytes=payload["source_manifest_bytes"],
            parent_bytes=None, memory_bytes=payload["memory_bytes"], known_ids=(), now=self.clock(),
        )
        receipt, receipt_sha = build_committed_receipt(
            payload["request_bytes"], policy_revision=1, now=self.clock(),
        )
        conn = self.raw()
        conn.execute("BEGIN IMMEDIATE")
        try:
            for mid, data in payload["memory_bytes"].items():
                conn.execute("INSERT INTO adoption_memories VALUES (?, ?, ?)", (mid, sha256_hex(data), data))
            if plan.changed:
                conn.execute("INSERT INTO adoption_snapshots VALUES (?, ?)", (plan.snapshot_sha256, plan.snapshot_bytes))
            conn.execute("INSERT INTO adoption_journal VALUES (?, ?, ?, ?, ?, ?, ?)", (
                req["operation_id"], sha256_hex(payload["request_bytes"]), payload["request_bytes"],
                payload["manifest_bytes"], payload["source_manifest_bytes"], receipt_sha, receipt,
            ))
            if plan.changed:
                conn.execute("INSERT INTO adoption_heads VALUES (?, ?, ?, ?)", (
                    SCOPE["project"], SCOPE["task_family"], plan.snapshot_sha256, req["operation_id"],
                ))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        return receipt, receipt_sha, plan.snapshot_bytes

    def test_legacy_journal_replay_preserves_original_bytes_after_exclusion(self):
        store = self.setup_store()
        payload = self.legacy_payload(self.proposal(store))
        original, original_sha, snapshot = self.seed_v1(payload)
        stored_before = self.raw().execute("SELECT * FROM adoption_journal").fetchall()
        store.set_policy(make_control(), policy_body(memory_ids=("m-1",)), expected_revision=1)
        store.close()
        reopened = self.open_adoption()
        result = reopened.commit_adoption(**payload)
        self.assertEqual((result.status, result.receipt_bytes, result.receipt_sha256),
                         ("replayed", original, original_sha))
        self.assertEqual(reopened.resolve_operation("op-1"), result)
        self.assertEqual(reopened.current_snapshot(SCOPE), snapshot)
        self.assertEqual(reopened.current_policy().revision, 2)
        self.assertEqual(self.raw().execute("SELECT * FROM adoption_journal").fetchall(), stored_before)
        doc = parse_canonical("committed_receipt", result.receipt_bytes)
        self.assertEqual(doc["schema_version"], "agent-sleep-committed-operation-receipt/1")
        self.assertNotIn("run_id", doc)
        self.assertEqual(self.raw().execute("PRAGMA user_version").fetchone()[0], 3)

    def test_v2_run_label_is_bound_and_different_run_same_operation_conflicts(self):
        store = self.setup_store()
        payload = self.proposal(store, run_id="run-A")
        first = store.commit_adoption(**payload)
        request = parse_canonical("adoption_request", payload["request_bytes"])
        receipt = parse_canonical("committed_receipt", first.receipt_bytes)
        self.assertEqual((request["schema_version"], receipt["schema_version"]),
                         ("agent-sleep-adoption-request/2", "agent-sleep-committed-operation-receipt/2"))
        self.assertEqual((request["run_id"], receipt["run_id"]), ("run-A", "run-A"))
        self.assertEqual(receipt["request_sha256"], sha256_hex(payload["request_bytes"]))
        snapshot = store.current_snapshot(SCOPE)
        request["run_id"] = "run-B"
        changed = dict(payload, request_bytes=encode_artifact("adoption_request", request))
        self.assertRaisesCode(ConflictError, "adoption.operation_conflict",
                              lambda: store.commit_adoption(**changed))
        self.assertEqual(store.current_snapshot(SCOPE), snapshot)
        self.assertEqual(store.resolve_operation("op-1").receipt_bytes, first.receipt_bytes)
        self.assertEqual(self.count("adoption_journal"), 1)
        self.assertEqual(self.count("adoption_memories"), 1)

    def test_new_v1_rejected_and_v2_audit_only_coexists_with_v1_history(self):
        store = self.setup_store()
        legacy = self.legacy_payload(self.audit_payload("legacy-audit"))
        self.assertRaisesCode(ContractViolation, "adoption.legacy_write",
                              lambda: store.commit_adoption(**legacy))
        self.assertEqual(self.count("adoption_journal"), 0)
        old_receipt, _, _ = self.seed_v1(legacy)
        result = store.commit_adoption(**self.audit_payload("v2-audit"))
        receipt = parse_canonical("committed_receipt", result.receipt_bytes)
        self.assertEqual((receipt["run_id"], receipt["outcome"]), ("audit-run", "audit_only"))
        self.assertIsNone(receipt["evaluation_receipt"])
        self.assertIsNone(store.current_snapshot(SCOPE))
        self.assertEqual(self.count("adoption_heads"), 0)
        self.assertEqual(self.count("adoption_snapshots"), 0)
        self.assertEqual(self.count("adoption_memories"), 0)
        self.assertEqual(self.count("adoption_journal"), 2)
        store.close()
        reopened = self.open_adoption()
        self.assertEqual(reopened.resolve_operation("legacy-audit").receipt_bytes, old_receipt)
        self.assertEqual(reopened.resolve_operation("v2-audit").receipt_bytes, result.receipt_bytes)
        self.assertEqual(reopened.commit_adoption(**legacy).receipt_bytes, old_receipt)
