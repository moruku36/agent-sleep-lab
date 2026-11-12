"""Explicit file-based runtime commands. No dynamic Python plugins or credentials."""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path

from agent_sleep_lab.strictjson import loads_strict_bytes
from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.provenance import CaptureBoundary
from agent_sleep_lab.runtime_artifacts import VerifierBoundary, EvaluatorBoundary
from agent_sleep_lab.sleep_coordinator import SleepCoordinator, Limits, FakeProvider
from agent_sleep_lab.sleep_evidence import bind_from_store, current_store
from agent_sleep_lab.mimo_provider import OpenClawMimoProvider, MODEL
from agent_sleep_lab.retrieval import retrieve_reference_bundle
from agent_sleep_lab.ab_comparison import ComparisonStore, ArmBudget, SyntheticEvaluator, FakeTaskProvider
from agent_sleep_lab.raw_baseline import RawBaselineComparison


def read_json(path):
    with open(path, "rb") as stream:
        data = stream.read(1048577)
    if len(data) > 1048576:
        raise ValueError("input exceeds 1 MiB")
    return loads_strict_bytes(data)


def open_store(config, *, read_only=False):
    # This is explicit LOCAL boundary configuration, not proof of caller identity.
    if not Path(config["path"]).is_file():
        raise ValueError("existing adoption-store path required; no implicit initialization")
    capture = dict(config["capture"])
    capture["allowed_scopes"] = frozenset(tuple(v) for v in capture["allowed_scopes"])
    capture["allowed_origins"] = frozenset(capture["allowed_origins"])
    verifier, evaluator = dict(config["verifier"]), dict(config["evaluator"])
    verifier["methods"] = frozenset(tuple(v) for v in verifier["methods"])
    evaluator["protocols"] = frozenset(tuple(v) for v in evaluator["protocols"])
    return AdoptionStore(config["path"], CaptureBoundary(**capture),
                         verifier=VerifierBoundary(**verifier), evaluator=EvaluatorBoundary(**evaluator),
                         evaluation_protocol=tuple(config["evaluation_protocol"]), read_only=read_only)


def execute(args):
    if args.command == "sleep-status":
        if not Path(args.journal).is_file():
            raise ValueError("existing journal required")
        c = SleepCoordinator(args.journal)
        try:
            return c.inspect(args.run_id)
        finally:
            c.close()
    manifest = read_json(args.manifest)
    store_config = read_json(args.store_config)
    if hasattr(args, "journal"):
        journal, source = Path(args.journal), Path(store_config["path"])
        if journal.resolve() == source.resolve() or (journal.exists() and source.exists() and journal.samefile(source)):
            raise ValueError("journal must be separate from evidence/adoption store")
    store = open_store(store_config)
    try:
        if args.command == "retrieve":
            return retrieve_reference_bundle(store, **manifest).document
        if args.command == "adopt":
            # Only exact independently prepared artifacts; no receipt registration here.
            # The atomic writer rechecks hashes, parent, policy and registered receipts.
            payload = {k: bytes.fromhex(manifest[k]) for k in
                       ("request_bytes", "manifest_bytes", "source_manifest_bytes")}
            payload["memory_bytes"] = {k: bytes.fromhex(v) for k, v in manifest["memory_bytes"].items()}
            result = store.commit_adoption(**payload)
            return {"status": result.status, "receipt_sha256": result.receipt_sha256}
        if args.command == "sleep":
            c = SleepCoordinator(args.journal)
            try:
                identity = dict(run_id=manifest["run_id"], scope=manifest["scope"],
                                event_ids=manifest["event_ids"],
                                config={"observed_at": manifest["observed_at"],
                                        "caller": manifest.get("config", {})})
                bind_from_store(c, store, **identity, limits=Limits(**manifest.get("limits", {})))
                current = current_store(store, scope=identity["scope"], event_ids=identity["event_ids"])
                if args.provider == "mimo":
                    provider = OpenClawMimoProvider(agent=args.agent, max_calls=2)
                else:
                    from agent_sleep_lab.sleep_coordinator import _encode
                    replies = read_json(args.replies)
                    provider = FakeProvider(_encode(replies["light"]), _encode(replies["deep"]))
                c.advance(identity["run_id"], provider, current=current)
                state = c.advance(identity["run_id"], provider, current=current)
                if state["status"] == "ready":
                    from agent_sleep_lab.sleep_candidates import candidate_memories
                    binding = loads_strict_bytes(c._read(identity["run_id"])[0])
                    generated = candidate_memories(binding, state["deep"],
                                                  observed_at=binding["config"]["observed_at"])
                    state = dict(state, candidate_memories={mid: loads_strict_bytes(blob)
                                                           for mid, blob in generated.items()})
                return state
            finally:
                c.close()
        if args.command == "compare":
            comparison = ComparisonStore(args.journal)
            try:
                baseline = RawBaselineComparison(store, comparison, **manifest["retrieval"])
                identity = manifest["evaluator_identity"]
                # Keys are kept only in the separate local evaluator file, never provider requests.
                key = read_json(args.rubric)
                evaluator = SyntheticEvaluator(identity["name"], identity["version"],
                                               identity["protocol_sha256"],
                                               lambda tid, reply: int(reply.decode("utf-8").strip() == key[tid]))
                from agent_sleep_lab.provenance import sha256_hex
                from agent_sleep_lab.ab_comparison import _encode
                if sha256_hex(_encode(key)) != identity["protocol_sha256"]:
                    raise ValueError("rubric hash differs from bound evaluator protocol")
                if not 1 <= len(manifest["tasks"]) <= 5:
                    raise ValueError("CLI comparison supports at most five paired tasks")
                baseline.plan(plan_id=manifest["plan_id"], tasks=manifest["tasks"],
                              config=manifest.get("config", {}), evaluator_identity=evaluator.identity(),
                              model=MODEL if args.provider == "mimo" else "fake-model-1",
                              budget=ArmBudget(**manifest.get("budget", {})))
                provider = (OpenClawMimoProvider(agent=args.agent, max_calls=10)
                            if args.provider == "mimo" else FakeTaskProvider())
                baseline.run(manifest["plan_id"], provider, evaluator)
                report = baseline.report(manifest["plan_id"])
                report["scoring_limit"] = "local exact-match fixture rubric, not independent paper-quality evaluation"
                return report
            finally:
                comparison.close()
        raise ValueError("unsupported runtime command")
    finally:
        store.close()
