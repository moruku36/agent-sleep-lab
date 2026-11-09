"""Gate 2B candidate-slice tests: contracts and parent-based candidate
construction. Pure and synthetic: no database, no files, no network."""

from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone

import support

from agent_sleep_lab import adoption_candidates as ac
from agent_sleep_lab import runtime_artifacts as ra
from agent_sleep_lab.provenance import ContractViolation, sha256_hex

NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)
SCOPE = {"project": "p", "task_family": "t"}
OTHER_SCOPE = {"project": "p", "task_family": "other"}
RECEIPT = {"receipt_id": "vr-1", "receipt_sha256": "a" * 64}
EVAL = {"receipt_id": "er-1", "receipt_sha256": "b" * 64}


def mem(memory_id, **override):
    override.setdefault(
        "evidence", [{"event_id": f"e-{memory_id}", "source_uri": "fixture://s-1/1", "locator": "summary"}]
    )
    return support.dumps(support.good_memory(memory_id=memory_id, **override))


def op(kind, memory_id=None, blob=None, target=None, receipt=None, sha=None):
    return {
        "op": kind,
        "memory_id": memory_id,
        "memory_sha256": sha if sha is not None else (sha256_hex(blob) if blob is not None else None),
        "target_id": target,
        "receipt": receipt,
    }


def add(memory_id, blob):
    return op("add", memory_id, blob, receipt=dict(RECEIPT))


def manifest(ops, parent_sha=None, scope=SCOPE):
    doc = {
        "schema_version": "agent-sleep-operation-manifest/1",
        "scope": dict(scope),
        "expected_parent_snapshot_sha256": parent_sha,
        "operations": sorted(ops, key=ra.operation_sort_key),
    }
    return ra.encode_artifact("operation_manifest", doc)


def evidence_ref(event_id):
    return {"event_id": event_id, "event_sha256": "1" * 64, "source_sha256": "2" * 64,
            "provenance_sha256": "3" * 64}


def source(blobs, scope=SCOPE, events=None):
    entries = []
    for memory_id in sorted(blobs):
        entries.append({
            "memory_id": memory_id,
            "memory_sha256": sha256_hex(blobs[memory_id]),
            "evidence": [evidence_ref(e) for e in (events or {}).get(memory_id, [f"e-{memory_id}"])],
        })
    doc = {"schema_version": "agent-sleep-source-manifest/1", "scope": dict(scope), "entries": entries}
    return ra.encode_artifact("source_manifest", doc)


def plan_for(ops, blobs=None, parent=None, known=(), scope=SCOPE, memory_bytes=None,
             source_bytes=None, manifest_bytes=None, now=NOW, **kw):
    blobs = blobs or {}
    parent_sha = sha256_hex(parent) if parent is not None else None
    return ac.build_candidate(
        manifest_bytes=manifest_bytes if manifest_bytes is not None else manifest(ops, parent_sha, scope),
        source_manifest_bytes=source_bytes if source_bytes is not None else source(blobs, scope),
        parent_bytes=parent,
        memory_bytes=blobs if memory_bytes is None else memory_bytes,
        known_ids=known,
        now=now,
        **kw,
    )


B1 = mem("m-1", kind="procedure")
B2 = mem("m-2", kind="fact")


def initial_plan():
    return plan_for([add("m-1", B1), add("m-2", B2)], {"m-1": B1, "m-2": B2})


class Base(unittest.TestCase):
    def assertCode(self, code, fn, exc=ContractViolation):
        with self.assertRaises(exc) as cm:
            fn()
        self.assertEqual(cm.exception.code, code)

    def parent(self):
        return initial_plan().snapshot_bytes


class InitializationTests(Base):
    def test_first_snapshot_is_deterministic_sorted_and_active(self):
        plan = initial_plan()
        self.assertTrue(plan.changed)
        self.assertIsNone(plan.parent_sha256)
        self.assertEqual([m["memory_id"] for m in plan.snapshot_doc["members"]], ["m-1", "m-2"])
        self.assertTrue(all(m["state"] == "active" and m["superseded_by_id"] is None
                            for m in plan.snapshot_doc["members"]))
        self.assertEqual(plan.snapshot_sha256, sha256_hex(plan.snapshot_bytes))
        self.assertEqual(plan.active_ids, ("m-1", "m-2"))
        self.assertEqual((plan.carried_forward, plan.added), ((), ("m-1", "m-2")))
        again = initial_plan()
        self.assertEqual((again.snapshot_bytes, again.operations_sha256, again.source_manifest_sha256),
                         (plan.snapshot_bytes, plan.operations_sha256, plan.source_manifest_sha256))
        self.assertEqual(ac.parse_canonical("candidate_snapshot", plan.snapshot_bytes), plan.snapshot_doc)
        self.assertEqual(plan.memories["m-1"]["kind"], "procedure")

    def test_null_parent_only_for_an_uninitialized_scope(self):
        parent = self.parent()
        self.assertCode("candidate.parent_unexpected", lambda: ac.build_candidate(
            manifest_bytes=manifest([add("m-3", mem("m-3"))], None),
            source_manifest_bytes=source({"m-3": mem("m-3")}),
            parent_bytes=parent, memory_bytes={"m-3": mem("m-3")}, known_ids=(), now=NOW))
        self.assertCode("candidate.parent_missing", lambda: ac.build_candidate(
            manifest_bytes=manifest([add("m-3", mem("m-3"))], sha256_hex(parent)),
            source_manifest_bytes=source({"m-3": mem("m-3")}),
            parent_bytes=None, memory_bytes={"m-3": mem("m-3")}, known_ids=(), now=NOW))
        # nothing can be staled or superseded in an uninitialized scope
        self.assertCode("candidate.unknown_target",
                        lambda: plan_for([op("mark_stale", target="m-1")]))
        self.assertCode("candidate.unknown_target", lambda: plan_for(
            [op("supersede", "m-3", mem("m-3", supersedes=["m-1"]), "m-1", dict(RECEIPT))],
            {"m-3": mem("m-3", supersedes=["m-1"])}))

    def test_parent_hash_scope_and_canonical_bytes_are_checked(self):
        parent = self.parent()
        wrong = parent + b" "
        self.assertCode("candidate.parent_hash_mismatch", lambda: ac.build_candidate(
            manifest_bytes=manifest([op("reject", "m-9", mem("m-9"))], sha256_hex(parent)),
            source_manifest_bytes=source({}), parent_bytes=wrong, memory_bytes={}, known_ids=(), now=NOW))
        other_blob = mem("m-1", scope=OTHER_SCOPE)
        other = plan_for([add("m-1", other_blob)], {"m-1": other_blob}, scope=OTHER_SCOPE).snapshot_bytes
        self.assertCode("candidate.scope_mismatch", lambda: ac.build_candidate(
            manifest_bytes=manifest([op("reject", "m-9", mem("m-9"))], sha256_hex(other)),
            source_manifest_bytes=source({}), parent_bytes=other, memory_bytes={}, known_ids=(), now=NOW))
        self.assertCode("candidate.scope_mismatch", lambda: plan_for(
            [add("m-1", B1)], {"m-1": B1}, source_bytes=source({"m-1": B1}, OTHER_SCOPE)))
        pretty = json.dumps(json.loads(manifest([add("m-1", B1)])), indent=2).encode()
        self.assertCode("candidate.not_canonical_bytes", lambda: plan_for(
            [], {"m-1": B1}, manifest_bytes=pretty))


class FollowUpTests(Base):
    def test_supersede_and_add_preserve_unrelated_members_and_history(self):
        parent = self.parent()
        b3, b4 = mem("m-3", supersedes=["m-1"]), mem("m-4")
        plan = plan_for(
            [op("supersede", "m-3", b3, "m-1", dict(RECEIPT)), add("m-4", b4)],
            {"m-3": b3, "m-4": b4}, parent=parent)
        members = {m["memory_id"]: m for m in plan.snapshot_doc["members"]}
        old = {m["memory_id"]: m for m in ac.parse_canonical("candidate_snapshot", parent)["members"]}
        self.assertEqual(plan.parent_sha256, sha256_hex(parent))
        self.assertEqual(plan.snapshot_doc["parent_snapshot_sha256"], sha256_hex(parent))
        self.assertEqual(members["m-1"]["state"], "superseded")
        self.assertEqual(members["m-1"]["superseded_by_id"], "m-3")
        self.assertEqual(members["m-1"]["memory_sha256"], old["m-1"]["memory_sha256"])  # history kept
        self.assertEqual(members["m-2"], old["m-2"])  # unrelated member byte-identical
        self.assertEqual({k: members[k]["state"] for k in ("m-3", "m-4")}, {"m-3": "active", "m-4": "active"})
        self.assertEqual(plan.carried_forward, ("m-2",))
        self.assertEqual(plan.active_ids, ("m-2", "m-3", "m-4"))  # carried-forward is revalidated too
        self.assertEqual((plan.superseded, plan.added), ((("m-1", "m-3"),), ("m-4",)))

    def test_mark_stale_removes_eligibility_without_deleting(self):
        plan = plan_for([op("mark_stale", target="m-2")], parent=self.parent())
        members = {m["memory_id"]: m for m in plan.snapshot_doc["members"]}
        self.assertEqual((members["m-1"]["state"], members["m-2"]["state"]), ("active", "stale"))
        self.assertEqual((plan.active_ids, plan.staled), (("m-1",), ("m-2",)))
        self.assertEqual(len(members), 2)
        # a stale or superseded member can no longer be a target
        stale_parent = plan.snapshot_bytes
        self.assertCode("candidate.target_not_active",
                        lambda: plan_for([op("mark_stale", target="m-2")], parent=stale_parent))
        b5 = mem("m-5", supersedes=["m-2"])
        self.assertCode("candidate.target_not_active", lambda: plan_for(
            [op("supersede", "m-5", b5, "m-2", dict(RECEIPT))], {"m-5": b5}, parent=stale_parent))

    def test_reject_and_defer_are_audit_only_and_never_remove_members(self):
        parent = self.parent()
        plan = plan_for([op("reject", "m-8", mem("m-8")), op("defer", "m-9", mem("m-9"))], parent=parent)
        self.assertFalse(plan.changed)
        self.assertEqual((plan.snapshot_bytes, plan.snapshot_sha256, plan.snapshot_doc), (None, None, None))
        self.assertEqual([a[:2] for a in plan.audit], [("defer", "m-9"), ("reject", "m-8")])
        self.assertEqual(plan.carried_forward, ("m-1", "m-2"))
        # in an uninitialized scope an audit-only run does not initialize anything
        empty = plan_for([op("defer", "m-9", mem("m-9"))])
        self.assertFalse(empty.changed)
        self.assertIsNone(empty.parent_sha256)
        # mixed with a real change, audit entries still leave every member alone
        b4 = mem("m-4")
        mixed = plan_for([add("m-4", b4), op("reject", "m-8", mem("m-8"))], {"m-4": b4}, parent=parent)
        self.assertEqual([m["memory_id"] for m in mixed.snapshot_doc["members"]], ["m-1", "m-2", "m-4"])
        self.assertEqual(mixed.audit[0][:2], ("reject", "m-8"))

    def test_reject_and_defer_cannot_name_an_existing_member(self):
        for kind in ("reject", "defer"):
            with self.subTest(kind):
                self.assertCode("candidate.ambiguous_reject_target", lambda kind=kind: plan_for(
                    [op(kind, "m-1", B1)], parent=self.parent()))


class RejectionTests(Base):
    def test_unknown_duplicate_and_reused_ids(self):
        parent = self.parent()
        self.assertCode("candidate.unknown_target",
                        lambda: plan_for([op("mark_stale", target="m-404")], parent=parent))
        b3 = mem("m-3", supersedes=["m-1"])
        # the same member touched twice through different operations
        self.assertCode("candidate.duplicate_target", lambda: plan_for(
            [op("mark_stale", target="m-1"), op("supersede", "m-3", b3, "m-1", dict(RECEIPT))],
            {"m-3": b3}, parent=parent))
        self.assertCode("candidate.duplicate_target", lambda: plan_for(
            [add("m-3", mem("m-3")), op("reject", "m-3", mem("m-3"))], {"m-3": mem("m-3")}, parent=parent))
        # global id reuse: current member, historical id, and a superseded id
        self.assertCode("candidate.id_reused", lambda: plan_for([add("m-1", B1)], {"m-1": B1}, parent=parent))
        b7 = mem("m-7")
        self.assertCode("candidate.id_reused",
                        lambda: plan_for([add("m-7", b7)], {"m-7": b7}, parent=parent, known={"m-7"}))
        self.assertCode("candidate.id_reused", lambda: plan_for(
            [op("supersede", "m-2", mem("m-2", supersedes=["m-1"]), "m-1", dict(RECEIPT))],
            {"m-2": mem("m-2", supersedes=["m-1"])}, parent=parent))

    def test_memory_bytes_must_match_exactly(self):
        b3 = mem("m-3")
        base = dict(parent=self.parent())
        self.assertCode("candidate.memory_hash_mismatch", lambda: plan_for(
            [op("add", "m-3", receipt=dict(RECEIPT), sha="c" * 64)], {"m-3": b3}, **base))
        self.assertCode("candidate.memory_missing", lambda: plan_for(
            [add("m-3", b3)], {"m-3": b3}, memory_bytes={}, **base))
        self.assertCode("candidate.unrequested_memory", lambda: plan_for(
            [add("m-3", b3)], {"m-3": b3}, memory_bytes={"m-3": b3, "m-5": mem("m-5")}, **base))
        wrong_id = mem("m-other")
        self.assertCode("candidate.memory_id_mismatch", lambda: plan_for(
            [op("add", "m-3", receipt=dict(RECEIPT), sha=sha256_hex(wrong_id))], {"m-3": wrong_id},
            source_bytes=source({"m-3": wrong_id}), **base))
        self.assertCode("candidate.memory_not_bytes", lambda: plan_for(
            [add("m-3", b3)], {"m-3": b3}, memory_bytes={"m-3": b3.decode()}, **base))
        array = b"[1]"
        self.assertCode("candidate.memory_not_object", lambda: plan_for(
            [op("add", "m-3", receipt=dict(RECEIPT), sha=sha256_hex(array))], {"m-3": array},
            source_bytes=source({"m-3": array}), **base))

    def test_memory_content_rules(self):
        base = dict(parent=self.parent())

        def attempt(blob, code, kind="add", target=None):
            ops = [op(kind, "m-3", blob, target, dict(RECEIPT))]
            self.assertCode(code, lambda: plan_for(ops, {"m-3": blob}, **base))

        attempt(mem("m-3", kind="hypothesis"), "candidate.hypothesis_not_activatable")
        attempt(mem("m-3", valid_until="2026-11-09T00:00:00Z"), "candidate.memory_expired")
        attempt(mem("m-3", status="rejected"), "candidate.memory_status")
        attempt(mem("m-3", supersedes=["m-1"]), "candidate.supersedes_mismatch")
        attempt(mem("m-3", supersedes=[]), "candidate.supersedes_mismatch", "supersede", "m-1")
        attempt(mem("m-3", scope=OTHER_SCOPE), "candidate.scope_mismatch")
        broken = json.loads(mem("m-3"))
        del broken["claim"]
        attempt(json.dumps(broken).encode(), "candidate.memory_invalid")
        attempt(b"{not json", "candidate.memory_invalid")
        ok = plan_for([add("m-3", mem("m-3", valid_until="2027-01-01T00:00:00Z"))],
                      {"m-3": mem("m-3", valid_until="2027-01-01T00:00:00Z")}, **base)
        self.assertEqual(ok.added, ("m-3",))

    def test_duplicate_memory_evidence_is_rejected(self):
        doc = json.loads(mem("m-3"))
        doc["evidence"].append(dict(doc["evidence"][0]))
        blob = support.dumps(doc)
        self.assertCode("candidate.duplicate_evidence", lambda: plan_for(
            [add("m-3", blob)], {"m-3": blob}))

    def test_source_manifest_must_cover_exactly_the_proposed_memories(self):
        parent = self.parent()
        b3, b4 = mem("m-3"), mem("m-4")
        ops = [add("m-3", b3)]
        self.assertCode("candidate.source_manifest_mismatch", lambda: plan_for(
            ops, {"m-3": b3}, parent=parent, source_bytes=source({})))
        self.assertCode("candidate.source_manifest_mismatch", lambda: plan_for(
            ops, {"m-3": b3}, parent=parent, source_bytes=source({"m-3": b3, "m-4": b4})))
        self.assertCode("candidate.evidence_mismatch", lambda: plan_for(
            ops, {"m-3": b3}, parent=parent, source_bytes=source({"m-3": b3}, events={"m-3": ["e-other"]})))
        entry_other_bytes = source({"m-3": mem("m-3", claim="different")})
        self.assertCode("candidate.source_manifest_mismatch", lambda: plan_for(
            ops, {"m-3": b3}, parent=parent, source_bytes=entry_other_bytes))

    def test_oversized_candidates_fail_without_eviction(self):
        parent = self.parent()
        b3 = mem("m-3")
        self.assertCode("candidate.too_large", lambda: plan_for(
            [add("m-3", b3)], {"m-3": b3}, parent=parent, max_members=2))
        self.assertEqual(plan_for([add("m-3", b3)], {"m-3": b3}, parent=parent, max_members=3).active_ids,
                         ("m-1", "m-2", "m-3"))
        self.assertRaises(ValueError, lambda: plan_for([], max_members=0, manifest_bytes=manifest([add("m-3", b3)])))

    def test_argument_hygiene(self):
        b3 = mem("m-3")
        self.assertRaises(TypeError, lambda: plan_for([add("m-3", b3)], {"m-3": b3}, known="m-1"))
        self.assertRaises(ValueError, lambda: plan_for([add("m-3", b3)], {"m-3": b3}, now=datetime(2026, 11, 10)))
        blobs = {"m-3": b3}
        before = copy.deepcopy(blobs)
        plan_for([add("m-3", b3)], blobs)
        self.assertEqual(blobs, before)


class ContractCrossFieldTests(Base):
    def codes(self, kind, doc):
        return {p.code for p in ra.validate_artifact(kind, doc)}

    def test_manifest_shapes_and_order(self):
        good = json.loads(manifest([add("m-1", B1), op("mark_stale", target="m-2")], "d" * 64))
        self.assertEqual(self.codes("operation_manifest", good), set())
        unsorted = copy.deepcopy(good)
        unsorted["operations"].reverse()
        self.assertIn("contract.operations_not_canonical", self.codes("operation_manifest", unsorted))
        for index, field, value in ((0, "receipt", None), (1, "memory_id", "m-9"), (0, "target_id", "m-1")):
            broken = copy.deepcopy(good)
            broken["operations"][index][field] = value
            self.assertTrue(
                {"contract.operation_shape", "contract.operation_self_target"}
                & self.codes("operation_manifest", broken), (index, field))
        extra = copy.deepcopy(good)
        extra["operations"][0]["surprise"] = 1
        self.assertIn("contract.schema", self.codes("operation_manifest", extra))
        self.assertIn("contract.bad_format", self.codes("operation_manifest", dict(
            good, expected_parent_snapshot_sha256="d" * 64 + "\n")))

    def test_snapshot_invariants(self):
        good = copy.deepcopy(initial_plan().snapshot_doc)
        self.assertEqual(self.codes("candidate_snapshot", good), set())
        unsorted = copy.deepcopy(good)
        unsorted["members"].reverse()
        self.assertIn("contract.members_not_canonical", self.codes("candidate_snapshot", unsorted))
        dangling = copy.deepcopy(good)
        dangling["members"][0].update(state="superseded", superseded_by_id="m-404")
        self.assertIn("contract.supersession_target", self.codes("candidate_snapshot", dangling))
        half = copy.deepcopy(good)
        half["members"][0]["state"] = "superseded"
        self.assertIn("contract.supersession_state", self.codes("candidate_snapshot", half))
        cycle = copy.deepcopy(good)
        cycle["members"][0].update(state="superseded", superseded_by_id="m-2")
        cycle["members"][1].update(state="superseded", superseded_by_id="m-1")
        self.assertIn("contract.supersession_cycle", self.codes("candidate_snapshot", cycle))
        hypothesis = copy.deepcopy(good)
        hypothesis["members"][0]["kind"] = "hypothesis"
        self.assertIn("contract.schema", self.codes("candidate_snapshot", hypothesis))
        too_many = copy.deepcopy(good)
        too_many["members"] = [dict(good["members"][0], memory_id=f"m-{i:04d}") for i in range(257)]
        self.assertIn("contract.schema", self.codes("candidate_snapshot", too_many))

    def test_source_manifest_request_and_receipt_rules(self):
        src = json.loads(source({"m-1": B1, "m-2": B2}))
        self.assertEqual(self.codes("source_manifest", src), set())
        src["entries"].reverse()
        self.assertIn("contract.entries_not_canonical", self.codes("source_manifest", src))
        dup = json.loads(source({"m-1": B1}))
        dup["entries"][0]["evidence"].append(dict(dup["entries"][0]["evidence"][0]))
        self.assertIn("contract.duplicate_evidence", self.codes("source_manifest", dup))

        plan = initial_plan()
        data, _ = ac.build_adoption_request(
            operation_id="op-1", plan=plan, expected_policy_revision=1, evaluation_receipt=dict(EVAL))
        request = json.loads(data)
        self.assertEqual(self.codes("adoption_request", request), set())
        self.assertIn("contract.evaluation_required",
                      self.codes("adoption_request", dict(request, evaluation_receipt=None)))
        self.assertIn("contract.unexpected_evaluation", self.codes(
            "adoption_request", dict(request, candidate_snapshot_sha256=None)))
        self.assertIn("contract.schema", self.codes("adoption_request", dict(request, expected_policy_revision=0)))
        self.assertIn("contract.schema", self.codes("adoption_request", dict(request, authorization_revision=0)))

        receipt = json.loads(ac.build_committed_receipt(data, policy_revision=1, now=NOW)[0])
        self.assertEqual(self.codes("committed_receipt", receipt), set())
        self.assertIn("contract.adopted_snapshot", self.codes(
            "committed_receipt", dict(receipt, snapshot_sha256=receipt["parent_snapshot_sha256"])))
        self.assertIn("contract.audit_only_changed", self.codes(
            "committed_receipt", dict(receipt, outcome="audit_only")))


class RequestAndReceiptBuilderTests(Base):
    def test_request_names_the_constructed_snapshot_and_is_deterministic(self):
        plan = initial_plan()
        data, digest = ac.build_adoption_request(
            operation_id="op-1", plan=plan, expected_policy_revision=3, evaluation_receipt=dict(EVAL))
        again, digest2 = ac.build_adoption_request(
            operation_id="op-1", plan=plan, expected_policy_revision=3, evaluation_receipt=dict(EVAL))
        self.assertEqual((data, digest), (again, digest2))
        self.assertEqual(digest, sha256_hex(data))
        request = ac.parse_canonical("adoption_request", data)
        self.assertEqual(request["candidate_snapshot_sha256"], plan.snapshot_sha256)
        self.assertEqual(request["operations_sha256"], plan.operations_sha256)
        self.assertEqual(request["expected_policy_revision"], 3)
        self.assertNotIn("authorization_revision", request)  # one combined policy revision
        self.assertNotIn("exclusion_revision", request)
        other, other_digest = ac.build_adoption_request(
            operation_id="op-2", plan=plan, expected_policy_revision=3, evaluation_receipt=dict(EVAL))
        self.assertNotEqual(digest, other_digest)

    def test_active_change_requires_evaluation_and_audit_only_forbids_it(self):
        plan = initial_plan()
        self.assertCode("contract.evaluation_required", lambda: ac.build_adoption_request(
            operation_id="op-1", plan=plan, expected_policy_revision=1, evaluation_receipt=None))
        audit = plan_for([op("reject", "m-9", mem("m-9"))], parent=self.parent())
        self.assertCode("contract.unexpected_evaluation", lambda: ac.build_adoption_request(
            operation_id="op-1", plan=audit, expected_policy_revision=1, evaluation_receipt=dict(EVAL)))
        data, _ = ac.build_adoption_request(
            operation_id="op-1", plan=audit, expected_policy_revision=1, evaluation_receipt=None)
        request = ac.parse_canonical("adoption_request", data)
        self.assertIsNone(request["candidate_snapshot_sha256"])
        self.assertEqual(request["expected_parent_snapshot_sha256"], audit.parent_sha256)

    def test_receipt_builder_rejects_naive_time_and_policy_drift(self):
        data, _ = ac.build_adoption_request(
            operation_id="op-1", plan=initial_plan(), expected_policy_revision=3,
            evaluation_receipt=dict(EVAL))
        for revision in (2, 4, True, "3", 3.0):
            with self.subTest(revision=revision):
                self.assertCode("candidate.policy_revision_mismatch", lambda: ac.build_committed_receipt(
                    data, policy_revision=revision, now=NOW))
        self.assertRaises(ValueError, lambda: ac.build_committed_receipt(
            data, policy_revision=3, now=datetime(2026, 11, 10)))

    def test_committed_receipt_builder(self):
        plan = initial_plan()
        data, _ = ac.build_adoption_request(
            operation_id="op-1", plan=plan, expected_policy_revision=3, evaluation_receipt=dict(EVAL))
        receipt_bytes, receipt_sha = ac.build_committed_receipt(data, policy_revision=3, now=NOW)
        receipt = ac.parse_canonical("committed_receipt", receipt_bytes)
        self.assertEqual((receipt["outcome"], receipt["snapshot_sha256"], receipt["parent_snapshot_sha256"]),
                         ("adopted", plan.snapshot_sha256, None))
        self.assertEqual(receipt["request_sha256"], sha256_hex(data))
        self.assertEqual(receipt["committed_at"], "2026-11-10T00:00:00Z")
        self.assertEqual(receipt_sha, sha256_hex(receipt_bytes))

        audit = plan_for([op("defer", "m-9", mem("m-9"))])
        audit_request, _ = ac.build_adoption_request(
            operation_id="op-2", plan=audit, expected_policy_revision=3, evaluation_receipt=None)
        audit_receipt = ac.parse_canonical(
            "committed_receipt", ac.build_committed_receipt(audit_request, policy_revision=3, now=NOW)[0])
        self.assertEqual((audit_receipt["outcome"], audit_receipt["snapshot_sha256"]), ("audit_only", None))
        self.assertCode("candidate.not_canonical_bytes", lambda: ac.build_committed_receipt(
            json.dumps(json.loads(data), indent=1).encode(), policy_revision=3, now=NOW))


class OriginRuleTests(unittest.TestCase):
    def test_kind_rules_over_evidence_root_origins(self):
        f = ac.evidence_origin_failures
        self.assertEqual(f("hypothesis", ["user_correction"]), ["candidate.hypothesis_not_activatable"])
        self.assertEqual(f("preference", ["user_correction"]), [])
        self.assertEqual(f("preference", ["user_correction", "external_document"]),
                         ["candidate.preference_needs_user_correction"])
        self.assertEqual(f("preference", ["external_document"]), ["candidate.preference_needs_user_correction"])
        self.assertEqual(f("preference", []), ["candidate.preference_needs_user_correction"])
        self.assertEqual(f("fact", ["tool_observation"]), [])
        self.assertEqual(f("procedure", ["external_document"]), [])
        self.assertEqual(f("mystery", ["tool_observation"]), ["candidate.unknown_kind"])


if __name__ == "__main__":
    unittest.main()
