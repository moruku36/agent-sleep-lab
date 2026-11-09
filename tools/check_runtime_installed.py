"""Offline installed-wheel acceptance of the first Gate 2B receipt/policy slice.

Usage: /installed/python /checkout/tools/check_runtime_installed.py /checkout
This checks fixture bindings, not truth, authentication or active memory adoption.
"""

from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
import sys
import tempfile

import agent_sleep_lab
from agent_sleep_lab.evidence_store import EvidenceStore
from agent_sleep_lab.provenance import CaptureBoundary, sha256_hex
from agent_sleep_lab.runtime_artifacts import (
    ARTIFACT_KINDS, ControlBoundary, EvaluatorBoundary, VerifierBoundary,
)
from agent_sleep_lab.runtime_store import RuntimeStore, upgrade_store_v1_to_v2
from check_evidence_installed import fixture


def main():
    checkout = Path(sys.argv[1]).resolve()
    assert not Path(agent_sleep_lab.__file__).resolve().is_relative_to(checkout / "src")
    for _, filename in ARTIFACT_KINDS.values():
        packaged = resources.files("agent_sleep_lab").joinpath("schemas", filename).read_bytes()
        assert packaged == (checkout / "schemas" / filename).read_bytes(), filename
    capture = CaptureBoundary(
        adapter_id="wheel-adapter", adapter_version="1.0.0",
        allowed_origins=frozenset({"tool_observation", "recall"}),
        authorizations={"wheel-auth": 1},
    )
    verifier = VerifierBoundary("wheel-verifier", "1", frozenset({("fixture-check", "1")}))
    evaluator = EvaluatorBoundary("wheel-evaluator", "1", frozenset({("fixture-protocol", "1")}))
    control = ControlBoundary("wheel-control", "1")
    scope = {"project": "wheel", "task_family": "synthetic-check"}
    digest = sha256_hex(b"synthetic memory binding only")
    clock = lambda: datetime(2026, 11, 10, 0, 1, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory(prefix="asl-wheel-runtime-") as tmp:
        path = Path(tmp) / "runtime.sqlite3"
        with EvidenceStore(path, capture, clock=clock) as old:
            old.capture(**fixture("wheel-root"))
            original = old.get("wheel-root")
        upgrade_store_v1_to_v2(path)
        with RuntimeStore(path, capture, clock=clock) as store:
            assert store.get("wheel-root") == original
            store.capture(**fixture("wheel-child", parent="wheel-root"))
            child = store.get("wheel-child")
            receipt = store.register_verification(verifier, {
                "receipt_id": "wheel-vr", "memory_id": "wheel-memory",
                "memory_sha256": digest, "scope": scope,
                "evidence": [{"event_id": child.event_id, "event_sha256": child.event_sha256,
                              "source_sha256": child.source_sha256,
                              "provenance_sha256": child.provenance_sha256}],
                "method": {"name": "fixture-check", "version": "1"},
                "protocol_sha256": digest, "outcome": "confirmed",
                "expires_at": "2027-01-01T00:00:00Z",
                "limits": {"max_evidence": 8, "synthetic_only": True},
            })
            evaluation = store.register_evaluation(evaluator, {
                "receipt_id": "wheel-er", "snapshot_sha256": digest,
                "operations_sha256": digest, "source_manifest_sha256": digest,
                "expected_parent_sha256": None, "scope": scope,
                "protocol": {"name": "fixture-protocol", "version": "1", "config_sha256": digest},
                "result": "passed", "completeness": {"planned": 1, "completed": 1},
                "expires_at": "2027-01-01T00:00:00Z", "limits": {"synthetic_only": True},
            })
            assert store.resolve_receipt("evaluation", "wheel-er", evaluation.receipt_sha256)["result"] == "passed"
            policy = {
                "authorizations": [{"ref": "wheel-auth", "revision": 1}],
                "accepted_purposes": ["regression_fixture"], "accepted_partitions": ["development"],
                "exclusions": {"memory_ids": [], "event_ids": [], "root_ids": []},
            }
            assert store.set_policy(control, policy, expected_revision=0).revision == 1
            args = dict(memory_id="wheel-memory", memory_sha256=digest,
                        scope=("wheel", "synthetic-check"), receipt_id="wheel-vr",
                        receipt_sha256=receipt.receipt_sha256, verifier=verifier)
            with store._immediate():
                assert store.eligibility_failures(**args) == ()
            policy["exclusions"]["root_ids"] = ["wheel-root"]
            assert store.set_policy(control, policy, expected_revision=1).revision == 2
            assert "policy.root_excluded" in store.eligibility_failures(**args)
        with RuntimeStore(path, capture, clock=clock) as reopened:
            assert reopened.current_policy().revision == 2
            assert "policy.root_excluded" in reopened.eligibility_failures(**args)
            assert reopened.resolve_receipt("verification", "wheel-vr", receipt.receipt_sha256)["memory_id"] == "wheel-memory"
    print("installed Gate 2B first slice: schemas, explicit upgrade, evidence, receipts, policy CAS, ancestry exclusion and reopen OK; no adoption")


if __name__ == "__main__":
    main()
