"""Offline acceptance of the installed Gate 2A wheel using temporary synthetic data.

Usage: /installed/python /checkout/tools/check_evidence_installed.py /checkout
"""

import copy
from datetime import datetime, timezone
from importlib import resources
import json
from pathlib import Path
import sys
import tempfile

import agent_sleep_lab
from agent_sleep_lab.evidence_store import EvidenceStore, ReadOnlyEvidenceStore
from agent_sleep_lab.provenance import CaptureBoundary, sha256_hex


def fixture(event_id, *, parent=None):
    source = f"synthetic source for {event_id}".encode("ascii")
    event = {
        "schema_version": "0.1", "event_id": event_id, "session_id": "wheel-session",
        "occurred_at": "2026-11-10T00:00:00Z",
        "scope": {"project": "wheel", "task_family": "synthetic-check"},
        "kind": "observation", "summary": "Synthetic installation fixture only.",
        "source_uri": f"fixture://wheel/{event_id}", "synthetic": True,
    }
    event_bytes = (json.dumps(event) + "\n").encode("utf-8")
    claim = {
        "schema_version": "agent-sleep-provenance/1",
        "event": {"event_id": event_id, "sha256": sha256_hex(event_bytes), "scope": copy.deepcopy(event["scope"])},
        "origin": "recall" if parent else "tool_observation",
        "source": {"source_id": f"source-{event_id}", "sha256": sha256_hex(source), "locator": "fixture:1"},
        "observed_at": "2026-11-10T00:00:00Z", "captured_at": "2026-11-10T00:00:01Z",
        "lineage": {"original_root_id": parent or event_id, "derived_from": [parent] if parent else []},
        "authorization": {"ref": "wheel-auth", "revision": 1, "purpose": "regression_fixture",
                          "retention": "until_expiry", "expires_at": "2027-01-01T00:00:00Z"},
        "partition": {"synthetic": True, "evaluation": "development"},
    }
    return dict(event_bytes=event_bytes, source_bytes=source, claim=claim)


def main():
    checkout = Path(sys.argv[1]).resolve()
    assert not Path(agent_sleep_lab.__file__).resolve().is_relative_to(checkout / "src")
    packaged = resources.files("agent_sleep_lab").joinpath("schemas", "provenance.schema.json").read_bytes()
    assert packaged == (checkout / "schemas" / "provenance.schema.json").read_bytes()
    boundary = CaptureBoundary(
        adapter_id="wheel-adapter", adapter_version="1.0.0",
        allowed_origins=frozenset({"tool_observation", "recall"}),
        authorizations={"wheel-auth": 1}, allowed_scopes=frozenset({("wheel", "synthetic-check")}),
    )
    # Fixed synthetic fixture clock, not a current authorization or live operation.
    def clock():
        return datetime(2026, 11, 10, 0, 1, tzinfo=timezone.utc)

    with tempfile.TemporaryDirectory(prefix="asl-wheel-evidence-") as tmp:
        path = Path(tmp) / "evidence.sqlite3"
        root = fixture("wheel-root")
        with EvidenceStore(path, boundary, clock=clock) as store:
            assert store.capture(**root).status == "created"
            assert store.capture(**root).status == "replayed"
            assert store.capture(**fixture("wheel-child", parent="wheel-root")).status == "created"
            assert store.independent_root_count("wheel", "synthetic-check") == 1
        with ReadOnlyEvidenceStore(path, clock=clock) as reader:
            reports = reader.verify_all()
            assert len(reports) == 2 and all(report.ok for report in reports), reports
            assert reader.get("wheel-root").source_bytes == root["source_bytes"]
    print("installed Gate 2A: schema, capture/replay, lineage, root dedupe, restart and read-only verify OK")


if __name__ == "__main__":
    main()
