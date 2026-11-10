"""Four synthetic Gate 3 scoped-retrieval cases over the existing AdoptionStore.

Fixtures only: no model, network, real memory or live adapter. Not an acceptance report.
"""
from __future__ import annotations

import support
from evidence_support import StoreCase, make_item
from runtime_support import (
    evidence_ref, make_control, make_evaluator, make_verifier, policy_body, verification_claim,
    evaluation_claim,
)
from test_adoption_candidates import manifest, op
import test_adoption_store as writer_fixtures
from agent_sleep_lab.adoption_candidates import build_adoption_request, build_candidate
from agent_sleep_lab.provenance import ContractViolation, StorageError, sha256_hex
from agent_sleep_lab.retrieval import retrieve_reference_bundle
from agent_sleep_lab.runtime_artifacts import encode_artifact

SCOPE = {"project": "p", "task_family": "t"}
OTHER = {"project": "q", "task_family": "u"}


def derived(event_id, parent):
    return make_item(event_id, derived_from=[parent], origin="recall", root="e-1")


class RetrievalTests(StoreCase):
    # Borrow only the store fixtures; the inherited writer cases are not collected here.
    open_adoption = writer_fixtures.AdoptionTests.open_adoption
    setup_store = writer_fixtures.AdoptionTests.setup_store

    def tamper(self, sql, params=()):
        """Simulate out-of-band corruption, then restore the exact trigger DDL (schema stays valid)."""
        conn = self.raw()
        triggers = conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'trigger'").fetchall()
        self.drop_triggers(conn)
        conn.execute(sql, params)
        for _, ddl in triggers:
            conn.execute(ddl)

    def adopt(self, store, mid, event_id, *, scope=SCOPE, claim="do the thing", parent=None,
              revision=1, tags=("x",)):
        """Commit one active memory whose evidence is ``event_id`` (already captured)."""
        op_id = "op-" + mid
        blob = support.dumps(support.good_memory(
            memory_id=mid, scope=scope, claim=claim, tags=list(tags),
            evidence=[{"event_id": event_id, "source_uri": "fixture://s-1/1", "locator": "summary"}],
        ))
        vr = store.register_verification(make_verifier(), verification_claim(
            store, event_ids=(event_id,), receipt_id="vr-" + mid, memory_id=mid,
            memory_sha256=sha256_hex(blob), scope=scope,
        ))
        ops = manifest([op("add", mid, blob, receipt={
            "receipt_id": vr.receipt_id, "receipt_sha256": vr.receipt_sha256,
        })], sha256_hex(parent) if parent else None, scope=scope)
        src = encode_artifact("source_manifest", {
            "schema_version": "agent-sleep-source-manifest/1", "scope": scope,
            "entries": [{"memory_id": mid, "memory_sha256": sha256_hex(blob),
                         "evidence": [evidence_ref(store, event_id)]}],
        })
        plan = build_candidate(manifest_bytes=ops, source_manifest_bytes=src, parent_bytes=parent,
                               memory_bytes={mid: blob}, known_ids=(), now=self.clock())
        er = store.register_evaluation(make_evaluator(), evaluation_claim(
            receipt_id="er-" + mid, snapshot_sha256=plan.snapshot_sha256,
            operations_sha256=plan.operations_sha256,
            source_manifest_sha256=plan.source_manifest_sha256,
            expected_parent_sha256=plan.parent_sha256, scope=scope,
        ))
        req, _ = build_adoption_request(
            operation_id=op_id, run_id="fixture-run", plan=plan, expected_policy_revision=revision,
            evaluation_receipt={"receipt_id": er.receipt_id, "receipt_sha256": er.receipt_sha256},
        )
        store.commit_adoption(request_bytes=req, manifest_bytes=ops, source_manifest_bytes=src,
                              memory_bytes={mid: blob})
        return store.current_snapshot(scope)

    def ids(self, bundle):
        return [r["memory_id"] for r in bundle.document["records"]]

    def test_normal_bounded_retrieval_returns_whole_ranked_records(self):
        store = self.setup_store()  # policy revision 1, e-1 captured
        self.put(store, make_item("e-2"))
        self.put(store, make_item("e-3"))
        snap = self.adopt(store, "m-1", "e-1", claim="alpha beta")
        snap = self.adopt(store, "m-2", "e-2", claim="beta gamma", parent=snap)
        self.adopt(store, "m-3", "e-3", claim="beta alpha delta", parent=snap)
        full = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000, query="alpha delta")
        doc = full.document
        self.assertEqual(self.ids(full), ["m-3", "m-1"])  # exclude zero-score records
        self.assertEqual((doc["scope"], doc["policy"]["revision"], doc["exclusions"]["version"]),
                         (SCOPE, 1, 1))
        self.assertEqual(doc["snapshot_sha256"], sha256_hex(store.current_snapshot(SCOPE)))
        self.assertEqual((doc["as_of"], doc["budget"]["tokenizer"]), ("2026-11-10T00:00:00Z", None))
        first = doc["records"][0]
        self.assertEqual(first["eligibility"], "verified")
        self.assertEqual(first["memory"]["claim"], "beta alpha delta")  # whole memory record
        self.assertEqual(first["evidence"][0]["event_id"], "e-3")
        stored = self.raw().execute(
            "SELECT memory_sha256 FROM adoption_memories WHERE memory_id = 'm-3'").fetchone()[0]
        self.assertEqual(first["memory_sha256"], stored)  # integrity hash is the stored one
        self.assertEqual(full.used_bytes, len(full.bundle_bytes))
        self.assertEqual(full.bundle_bytes, retrieve_reference_bundle(
            store, scope=SCOPE, max_bytes=1_000_000, query="alpha delta").bundle_bytes)  # deterministic
        # A budget between one and two records keeps only a whole top-ranked prefix, with scope kept.
        capped = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000,
                                           query="alpha delta", max_records=1)
        self.assertEqual(capped.document["counts"],
                         {"active_members": 3, "eligible": 2, "returned": 1, "dropped": 1})
        one_size = len(capped.bundle_bytes)
        small = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=one_size + 10, query="alpha delta")
        self.assertEqual(self.ids(small), ["m-3"])
        self.assertLessEqual(small.used_bytes, one_size + 10)
        self.assertEqual((small.document["scope"], small.document["counts"]["dropped"]), (SCOPE, 1))
        self.assertEqual(small.document["records"][0], dict(first, rank=1))
        self.assertRaisesCode(ContractViolation, "retrieval.budget_too_small",
                              lambda: retrieve_reference_bundle(store, scope=SCOPE, max_bytes=50))
        self.assertFalse(store.in_transaction)

    def test_scope_and_partition_filtering(self):
        store = self.setup_store()
        store.set_policy(make_control(), policy_body(partitions=("experience", "development")),
                         expected_revision=1)
        self.put(store, make_item("e-2", evaluation="development"))
        self.put(store, make_item("e-9", scope=("q", "u")))
        snap = self.adopt(store, "m-1", "e-1", revision=2)
        self.adopt(store, "m-2", "e-2", parent=snap, revision=2)
        self.adopt(store, "m-9", "e-9", scope=OTHER, revision=2)
        self.assertEqual(self.ids(retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000)),
                         ["m-1"])  # development evidence is not in the experience partition
        dev = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000, partition="development")
        self.assertEqual(self.ids(dev), ["m-2"])
        other = retrieve_reference_bundle(store, scope=OTHER, max_bytes=1_000_000)
        self.assertEqual((self.ids(other), other.document["scope"]), (["m-9"], OTHER))
        for bad in ({"project": "p"}, {"project": "p", "task_family": ""}, "p"):
            with self.assertRaises(ValueError):
                retrieve_reference_bundle(store, scope=bad, max_bytes=100)
        self.assertRaisesCode(ContractViolation, "retrieval.partition_not_served",
                              lambda: retrieve_reference_bundle(
                                  store, scope=SCOPE, max_bytes=1_000_000, partition="evaluation"))

    def test_revocation_and_ancestor_exclusion_apply_before_ranking(self):
        store = self.setup_store()
        self.put(store, derived("e-2", "e-1"))  # descendant of e-1
        self.put(store, make_item("e-3"))
        snap = self.adopt(store, "m-1", "e-1")
        snap = self.adopt(store, "m-2", "e-2", parent=snap)
        self.adopt(store, "m-3", "e-3", parent=snap)
        historical = store.current_snapshot(SCOPE)
        before = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000)
        self.assertEqual(self.ids(before), ["m-1", "m-2", "m-3"])
        store.set_policy(make_control(), policy_body(event_ids=("e-1",)), expected_revision=1)
        after = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000)
        self.assertEqual(self.ids(after), ["m-3"])  # e-1 and its descendant e-2 revoked
        self.assertEqual((after.document["policy"]["revision"], after.document["counts"]["active_members"]), (2, 3))
        self.assertEqual(after.document["snapshot_sha256"], sha256_hex(historical))  # head unchanged
        self.assertEqual([r["evidence"][0]["event_id"] for r in after.document["records"]], ["e-3"])
        store.set_policy(make_control(), policy_body(event_ids=("e-1",), memory_ids=("m-3",)),
                         expected_revision=2)
        empty = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000)
        self.assertEqual((self.ids(empty), empty.document["policy"]["revision"]), ([], 3))
        self.assertEqual(store.current_snapshot(SCOPE), historical)  # historical metadata is not permission

    def test_corruption_fails_closed_and_legitimate_empty_is_normal(self):
        store = self.setup_store()
        empty = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000)  # never initialized
        self.assertEqual((self.ids(empty), empty.document["snapshot_sha256"]), ([], None))
        self.assertEqual(empty.document["counts"]["eligible"], 0)
        self.adopt(store, "m-1", "e-1")
        self.assertEqual(self.ids(retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000)),
                         ["m-1"])
        self.tamper("UPDATE adoption_memories SET memory_bytes = ? WHERE memory_id = 'm-1'", (b"{}",))
        self.assertRaisesCode(StorageError, "retrieval.memory_corrupt",
                              lambda: retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000))
        self.assertFalse(store.in_transaction)  # the read transaction was ended
        self.tamper("UPDATE policy_revisions SET policy_bytes = ? WHERE revision = 1", (b"{}",))
        self.assertRaisesCode(StorageError, "policy.corrupt",
                              lambda: retrieve_reference_bundle(store, scope=SCOPE, max_bytes=1_000_000))
        self.assertRaisesCode(StorageError, "policy.corrupt",
                              lambda: retrieve_reference_bundle(store, scope=OTHER, max_bytes=1_000_000))
