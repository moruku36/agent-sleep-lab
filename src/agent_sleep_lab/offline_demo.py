"""Built-in synthetic wiring demo. No caller data, provider selection or saved state.

Fixture receipt registration is deliberately local and separate from scripted
proposals. It exercises the normal writer; it is not real-model verification,
an existing-agent integration, an independent holdout or a performance study.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_sleep_lab.ab_comparison import (
    ArmBudget, ComparisonStore, FakeTaskProvider, SyntheticEvaluator,
)
from agent_sleep_lab.adoption_candidates import (
    build_adoption_request, build_candidate, parse_canonical,
)
from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.provenance import CaptureBoundary, canonical_json, sha256_hex
from agent_sleep_lab.raw_baseline import RawBaselineComparison
from agent_sleep_lab.retrieval import retrieve_reference_bundle
from agent_sleep_lab.runtime_artifacts import (
    ControlBoundary, EvaluatorBoundary, VerifierBoundary, encode_artifact,
)
from agent_sleep_lab.sleep_candidates import candidate_memories
from agent_sleep_lab.sleep_coordinator import FakeProvider, Limits, SleepCoordinator
from agent_sleep_lab.sleep_evidence import bind_from_store, current_store, observe
from agent_sleep_lab.strictjson import loads_strict_bytes

_AT = "2026-11-12T00:00:00Z"
_EXPIRES = "2026-11-13T00:00:00Z"  # After the fixed fixture clock, never wall-clock permission.
_SCOPE = {"project": "synthetic-demo", "task_family": "catalog"}
_RUN = "synthetic-demo-sleep"
_PLAN = "synthetic-demo-pair"
_MEMORY = "synthetic-demo-memory"
_EXPERIENCE = (
    ("synthetic-demo-1", "Synthetic catalog practice: record the source locator before filing a note."),
    ("synthetic-demo-2", "Synthetic catalog observation: the archive contains a blue folder."),
)
_METHOD = {"name": "synthetic-source-equality", "version": "1"}
_CHECKS = ("one_added_memory", "no_parent", "exact_generated_claim", "exact_experience_binding")
_PROTOCOL = {"name": "synthetic-candidate-checks", "version": "1",
             "config_sha256": sha256_hex(canonical_json(_CHECKS))}
_SLEEP_LIMITS = Limits(calls=2, input_bytes=32768, output_bytes=4096,
                       stage_output_bytes=2048, candidates=2)
_ARM_BUDGET = ArmBudget(calls=2, request_bytes=16384, reply_bytes=128)
_RETRIEVAL_BYTES = 16384


def _clock():
    return datetime(2026, 11, 12, tzinfo=timezone.utc)


def _require(condition, message):
    if not condition:
        raise ValueError("synthetic demo: " + message)


def _capture(store):
    results = []
    for event_id, text in _EXPERIENCE:
        event = canonical_json({
            "schema_version": "0.1", "event_id": event_id,
            "session_id": "synthetic-demo-session", "occurred_at": _AT,
            "scope": _SCOPE, "kind": "observation", "summary": text,
            "source_uri": "fixture://synthetic-demo/" + event_id, "synthetic": True,
        })
        source = text.encode("utf-8")
        claim = {
            "schema_version": "agent-sleep-provenance/1",
            "event": {"event_id": event_id, "sha256": sha256_hex(event), "scope": _SCOPE},
            "origin": "tool_observation",
            "source": {"source_id": "source-" + event_id, "sha256": sha256_hex(source),
                       "locator": "source"},
            "observed_at": _AT, "captured_at": _AT,
            "lineage": {"original_root_id": event_id, "derived_from": []},
            "authorization": {"ref": "synthetic-demo-auth", "revision": 1,
                              "purpose": "offline_consolidation", "retention": "until_expiry",
                              "expires_at": _EXPIRES},
            "partition": {"synthetic": True, "evaluation": "experience"},
        }
        result = store.capture(event_bytes=event, source_bytes=source, claim=claim)
        _require(result.status == "created" and store.verify(event_id).ok,
                 "experience capture failed")
        results.append(asdict(result))
    return results


def _prepare(store, verifier, evaluator, operation_id, run_id, binding, deep):
    """Trusted synthetic fixture check/registration, never a provider callback."""
    memories = candidate_memories(binding, deep, observed_at=_AT)
    _require(set(memories) == {_MEMORY}, "unexpected materialized candidates")
    memory = loads_strict_bytes(memories[_MEMORY])
    stored = store.get(_EXPERIENCE[0][0])
    reference = {"event_id": stored.event_id, "event_sha256": stored.event_sha256,
                 "source_sha256": stored.source_sha256,
                 "provenance_sha256": stored.provenance_sha256}
    _require(memory["status"] == "candidate"
             and memory["verification"]["result"] == "pending"
             and memory["claim"] == stored.source_bytes.decode("utf-8") == _EXPERIENCE[0][1]
             and [e["event_id"] for e in memory["evidence"]] == [stored.event_id]
             and store.verify(stored.event_id).ok, "synthetic source equality check failed")
    digest = sha256_hex(memories[_MEMORY])
    verification = store.register_verification(verifier, {
        "receipt_id": "synthetic-demo-verification", "memory_id": _MEMORY,
        "memory_sha256": digest, "scope": _SCOPE, "evidence": [reference],
        "method": _METHOD, "protocol_sha256": sha256_hex(canonical_json(_METHOD)),
        "outcome": "confirmed", "expires_at": None,
        "limits": {"max_evidence": 1, "synthetic_only": True},
    })
    manifest = encode_artifact("operation_manifest", {
        "schema_version": "agent-sleep-operation-manifest/1", "scope": _SCOPE,
        "expected_parent_snapshot_sha256": binding["parent_sha256"],
        "operations": [{"op": "add", "memory_id": _MEMORY, "memory_sha256": digest,
                        "target_id": None, "receipt": {
                            "receipt_id": verification.receipt_id,
                            "receipt_sha256": verification.receipt_sha256}}],
    })
    source = encode_artifact("source_manifest", {
        "schema_version": "agent-sleep-source-manifest/1", "scope": _SCOPE,
        "entries": [{"memory_id": _MEMORY, "memory_sha256": digest, "evidence": [reference]}],
    })
    plan = build_candidate(manifest_bytes=manifest, source_manifest_bytes=source,
                           parent_bytes=store.current_snapshot(_SCOPE), memory_bytes=memories,
                           known_ids=(), now=_clock())
    checks = dict(zip(_CHECKS, (
        plan.changed and plan.added == (_MEMORY,) and plan.active_ids == (_MEMORY,),
        plan.parent_sha256 is None,
        plan.memories[_MEMORY]["claim"] == deep["operations"][0]["claim"],
        binding["store_binding"] == observe(
            store, scope=_SCOPE, event_ids=[e[0] for e in _EXPERIENCE])[1],
    )))
    _require(all(checks.values()), "synthetic candidate checks failed")
    evaluation = store.register_evaluation(evaluator, {
        "receipt_id": "synthetic-demo-evaluation", "snapshot_sha256": plan.snapshot_sha256,
        "operations_sha256": plan.operations_sha256,
        "source_manifest_sha256": plan.source_manifest_sha256,
        "expected_parent_sha256": plan.parent_sha256, "scope": _SCOPE, "protocol": _PROTOCOL,
        "result": "passed", "completeness": {"planned": len(checks),
                                                "completed": sum(checks.values())},
        "expires_at": None, "limits": {"synthetic_only": True},
    })
    request, _ = build_adoption_request(
        operation_id=operation_id, run_id=run_id, plan=plan,
        expected_policy_revision=store.current_policy().revision,
        evaluation_receipt={"receipt_id": evaluation.receipt_id,
                            "receipt_sha256": evaluation.receipt_sha256})
    details = {
        "candidates": [{"memory_id": _MEMORY, "memory_sha256": digest,
                        "status": memory["status"], "verification": memory["verification"]}],
        "fixture_registration": {"synthetic_only": True, "checks": checks,
                                 "verification": asdict(verification),
                                 "evaluation": asdict(evaluation),
                                 "verifier_boundary_id": verifier.boundary_id,
                                 "evaluator_boundary_id": evaluator.boundary_id,
                                 "protocol": _PROTOCOL},
        "bindings": {"parent_snapshot_sha256": plan.parent_sha256,
                     "snapshot_sha256": plan.snapshot_sha256,
                     "operations_sha256": plan.operations_sha256,
                     "source_manifest_sha256": plan.source_manifest_sha256,
                     "evidence": [reference]},
    }
    return dict(request_bytes=request, manifest_bytes=manifest,
                source_manifest_bytes=source, memory_bytes=memories), details


def _compare(store, comparisons):
    tasks = [{"task_id": "synthetic-demo-task-1",
              "prompt": "Describe the synthetic catalog practice using the reference data."},
             {"task_id": "synthetic-demo-task-2",
              "prompt": "Describe the synthetic archive observation using the reference data."}]
    # Evaluator-only answer key. Neither this mapping nor expected reply text is
    # included in sleep bindings, tasks, caller config, raw evidence or memories.
    key = {task["task_id"]: "synthetic-scripted-reply" for task in tasks}
    scores = []

    def score(task_id, reply):
        value = int(reply.decode("utf-8") == key[task_id])
        scores.append(value)
        return value

    evaluator = SyntheticEvaluator("synthetic-demo-exact-match", "1",
                                   sha256_hex(canonical_json(key)), score)
    baseline = RawBaselineComparison(store, comparisons, scope=_SCOPE,
                                     max_bytes=_RETRIEVAL_BYTES, max_records=1,
                                     scan_limit=2, max_raw=2)
    baseline.plan(plan_id=_PLAN, tasks=tasks, config={"synthetic_only": True},
                  model="synthetic-scripted-demo-1", evaluator_identity=evaluator.identity(),
                  budget=_ARM_BUDGET)
    frozen = baseline.frozen(_PLAN)
    before = baseline.audit(_PLAN)
    for index in range(len(tasks)):
        a, b = before["arms"][2 * index:2 * index + 2]
        _require(a["request_sha256"] != b["request_sha256"]
                 and a["raw_present"] == b["raw_present"] == frozen["events"]
                 and not a["memories_present"] and b["memories_present"] == frozen["memories"]
                 and not any(arm[k] for arm in (a, b)
                             for k in ("raw_dropped", "memories_dropped")),
                 "paired contexts are not distinct complete comparable fixture arms")
    provider = FakeTaskProvider(default=b"synthetic-scripted-reply")
    baseline.run(_PLAN, provider, evaluator)
    report, audit = baseline.report(_PLAN), baseline.audit(_PLAN)
    _require(report["status"] == "complete" and report["comparable"]
             and report["all_outcomes_scored"] and len(scores) == 2 * len(tasks)
             and len(provider.requests) == 2 * len(tasks), "paired comparison did not complete")
    _require(all(len(request) <= _ARM_BUDGET.request_bytes
                 and b"synthetic-scripted-reply" not in request
                 for request in provider.requests), "request cap or answer separation failed")
    # Preserve the production report, including unavailable costs and its explicit
    # absence of scientific claims. Top-level demo claims are always false.
    return {"report": report, "audit": audit, "frozen_context": frozen,
            "frozen_evidence": frozen["events"], "frozen_memories": frozen["memories"],
            "budget": asdict(_ARM_BUDGET), "calls": len(provider.requests),
            "input_bytes": sum(map(len, provider.requests)), "evaluator_calls": len(scores),
            "script": "same built-in fixed reply for both arms; scores are wiring fixtures"}


def run_demo():
    """Run only built-in data in disposable stores; errors propagate to CLI handling."""
    with TemporaryDirectory(prefix="agent-sleep-lab-demo-") as directory:
        with ExitStack() as stack:
            capture = CaptureBoundary(
                "synthetic-demo-capture", "1", frozenset({"tool_observation"}),
                {"synthetic-demo-auth": 1}, frozenset({tuple(_SCOPE.values())}))
            verifier = VerifierBoundary("synthetic-demo-verifier", "1",
                                        frozenset({tuple(_METHOD.values())}))
            evaluator = EvaluatorBoundary("synthetic-demo-evaluator", "1",
                                          frozenset({(_PROTOCOL["name"], _PROTOCOL["version"])}))
            store = stack.enter_context(AdoptionStore(
                Path(directory) / "adoption.sqlite", capture, verifier=verifier,
                evaluator=evaluator, evaluation_protocol=tuple(_PROTOCOL.values()), clock=_clock))
            sleep = SleepCoordinator(Path(directory) / "sleep.sqlite")
            stack.callback(sleep.close)
            comparisons = ComparisonStore(Path(directory) / "comparison.sqlite")
            stack.callback(comparisons.close)
            captured = _capture(store)
            policy = store.set_policy(ControlBoundary("synthetic-demo-control", "1"), {
                "authorizations": [{"ref": "synthetic-demo-auth", "revision": 1}],
                "accepted_purposes": ["offline_consolidation"],
                "accepted_partitions": ["experience"],
                "exclusions": {"memory_ids": [], "event_ids": [], "root_ids": []},
            }, expected_revision=0)
            event_ids = [e[0] for e in _EXPERIENCE]
            binding_sha = bind_from_store(sleep, store, run_id=_RUN, scope=_SCOPE,
                                         event_ids=event_ids, config={"observed_at": _AT},
                                         limits=_SLEEP_LIMITS)
            provider = FakeProvider(canonical_json({"event_ids": event_ids[:1]}), canonical_json({
                "operations": [{"op": "add", "memory_id": _MEMORY,
                                "event_ids": event_ids[:1], "claim": _EXPERIENCE[0][1]}]}))
            current = current_store(store, scope=_SCOPE, event_ids=event_ids)
            light = sleep.advance(_RUN, provider, current=current)
            _require(light["status"] == "deep", "Light did not select evidence")
            deep = sleep.advance(_RUN, provider, current=current)
            _require(deep["status"] == "ready", "Deep did not produce a candidate")
            preparation = {}

            def prepare(operation_id, run_id, binding, proposal):
                payload, details = _prepare(store, verifier, evaluator, operation_id,
                                            run_id, binding, proposal)
                preparation.update(details)
                return payload

            handoff = sleep.prepare(_RUN, prepare)
            _require(handoff["status"] == "handoff", "preparation did not complete")
            adopted = sleep.adopt(_RUN, store)
            _require(adopted["status"] == "adopted", "atomic adoption did not complete")
            committed = store.resolve_operation(adopted["operation_id"])
            _require(committed is not None, "adoption journal receipt missing")
            receipt = parse_canonical("committed_receipt", committed.receipt_bytes)
            snapshot = store.current_snapshot(_SCOPE)
            _require(snapshot is not None and sha256_hex(snapshot)
                     == receipt["snapshot_sha256"] == preparation["bindings"]["snapshot_sha256"],
                     "adopted snapshot binding differs")
            bundle = retrieve_reference_bundle(store, scope=_SCOPE, max_bytes=_RETRIEVAL_BYTES,
                                               max_records=1)
            _require([r["memory_id"] for r in bundle.document["records"]] == [_MEMORY]
                     and bundle.document["records"][0]["eligibility"] == "verified",
                     "adopted memory was not retrieved")
            comparison = _compare(store, comparisons)
            result = {
                "schema_version": "agent-sleep-offline-demo/1", "status": "completed",
                "synthetic_only": True, "live_provider_verified": False,
                "existing_agent_integration_verified": False, "performance_claim": False,
                "clock": _AT, "scope": dict(_SCOPE), "run_id": _RUN,
                "state_storage": "TemporaryDirectory; three separate disposable SQLite stores",
                "capture": {"count": len(captured), "results": captured,
                            "boundary_id": capture.adapter_id},
                "policy": {"revision": policy.revision, "sha256": policy.sha256},
                "sleep": {"binding_sha256": binding_sha, "light": light, "deep": deep,
                          "calls": len(provider.calls), "stages_called": provider.calls,
                          "limits": asdict(_SLEEP_LIMITS)},
                **preparation,
                "adoption": {"status": adopted["status"], "receipt": receipt,
                             "receipt_sha256": committed.receipt_sha256},
                "retrieval": {"bundle": bundle.document, "bundle_sha256": bundle.bundle_sha256,
                              "used_bytes": bundle.used_bytes},
                "comparison": comparison,
                "calls": {"scripted_sleep": len(provider.calls),
                          "scripted_task": comparison["calls"],
                          "paired_evaluator": comparison["evaluator_calls"]},
            }
    # Report cleanup only after all connections closed and directory removal ran.
    _require(not Path(directory).exists(), "temporary state was not removed")
    result["temporary_state_removed"] = True
    return result
