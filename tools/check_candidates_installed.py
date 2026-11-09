"""Installed-wheel acceptance of pure candidate planning; no database or adoption.

Usage: /installed/python /checkout/tools/check_candidates_installed.py /checkout
All receipts/hashes here are symbolic synthetic references, not registered evidence.
"""

from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
import sys

import agent_sleep_lab
from agent_sleep_lab.adoption_candidates import (
    build_candidate, build_adoption_request, build_committed_receipt, parse_canonical,
)
from agent_sleep_lab.provenance import canonical_json, sha256_hex
from agent_sleep_lab.runtime_artifacts import ARTIFACT_KINDS, encode_artifact


def main():
    checkout = Path(sys.argv[1]).resolve()
    assert not Path(agent_sleep_lab.__file__).resolve().is_relative_to(checkout / "src")
    for _, filename in ARTIFACT_KINDS.values():
        assert resources.files("agent_sleep_lab").joinpath("schemas", filename).read_bytes() == (
            checkout / "schemas" / filename).read_bytes(), filename
    scope = {"project": "wheel", "task_family": "candidate-fixture"}
    now = datetime(2026, 11, 10, tzinfo=timezone.utc)
    receipt = {"receipt_id": "symbolic-vr", "receipt_sha256": "a" * 64}
    evaluation = {"receipt_id": "symbolic-er", "receipt_sha256": "b" * 64}

    def memory(mid, supersedes=()):
        return canonical_json({
            "schema_version": "0.1", "memory_id": mid, "scope": scope,
            "kind": "procedure", "claim": "Synthetic planning fixture only.",
            "status": "candidate", "evidence": [{"event_id": "fixture-event",
                "source_uri": "fixture://candidate", "locator": "line:1"}],
            "observed_at": "2026-11-09T00:00:00Z", "valid_until": None,
            "supersedes": list(supersedes), "tags": [],
            "verification": {"method": "pending fixture", "verifier": None, "result": "pending"},
        })

    def make_plan(mid, blob, parent=None, target=None):
        parent_sha = sha256_hex(parent) if parent is not None else None
        operations = encode_artifact("operation_manifest", {
            "schema_version": "agent-sleep-operation-manifest/1", "scope": scope,
            "expected_parent_snapshot_sha256": parent_sha,
            "operations": [{"op": "supersede" if target else "add", "memory_id": mid,
                "memory_sha256": sha256_hex(blob), "target_id": target, "receipt": receipt}],
        })
        sources = encode_artifact("source_manifest", {
            "schema_version": "agent-sleep-source-manifest/1", "scope": scope,
            "entries": [{"memory_id": mid, "memory_sha256": sha256_hex(blob), "evidence": [{
                "event_id": "fixture-event", "event_sha256": "1" * 64,
                "source_sha256": "2" * 64, "provenance_sha256": "3" * 64}]}],
        })
        return build_candidate(manifest_bytes=operations, source_manifest_bytes=sources,
                               parent_bytes=parent, memory_bytes={mid: blob}, known_ids=(), now=now)

    first = make_plan("m-1", memory("m-1"))
    assert first.active_ids == ("m-1",) and first.changed
    assert first.snapshot_bytes == make_plan("m-1", memory("m-1")).snapshot_bytes
    second = make_plan("m-2", memory("m-2", ["m-1"]), first.snapshot_bytes, "m-1")
    assert second.active_ids == ("m-2",)
    assert second.snapshot_doc["members"][0]["state"] == "superseded"
    assert second.snapshot_doc["members"][0]["superseded_by_id"] == "m-2"
    request, digest = build_adoption_request(operation_id="fixture-op", plan=second,
        expected_policy_revision=1, evaluation_receipt=evaluation)
    formatted_receipt, receipt_sha = build_committed_receipt(request, policy_revision=1, now=now)
    doc = parse_canonical("committed_receipt", formatted_receipt)
    assert doc["request_sha256"] == digest and doc["snapshot_sha256"] == second.snapshot_sha256
    assert receipt_sha == sha256_hex(formatted_receipt)
    print("installed candidate planner: schemas, deterministic add/supersede history, request and receipt-format binding OK; no commit, policy or evidence verification")


if __name__ == "__main__":
    main()
