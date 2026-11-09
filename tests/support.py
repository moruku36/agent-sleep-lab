"""Shared helpers: make ``src`` importable and build small valid records."""

from __future__ import annotations

import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

ZERO_SHA = "0" * 64


def good_event(**override):
    record = {
        "schema_version": "0.1",
        "event_id": "e-1",
        "session_id": "s-1",
        "occurred_at": "2026-11-08T00:00:00Z",
        "scope": {"project": "p", "task_family": "t"},
        "kind": "task",
        "summary": "something happened",
        "source_uri": "fixture://s-1/1",
        "synthetic": True,
    }
    record.update(copy.deepcopy(override))
    return record


def good_memory(**override):
    record = {
        "schema_version": "0.1",
        "memory_id": "m-1",
        "scope": {"project": "p", "task_family": "t"},
        "kind": "procedure",
        "claim": "do the thing",
        "status": "candidate",
        "evidence": [{"event_id": "e-1", "source_uri": "fixture://s-1/1", "locator": "summary"}],
        "observed_at": "2026-11-08T00:03:00+09:00",
        "valid_until": None,
        "supersedes": [],
        "tags": ["x"],
        "verification": {"method": "pending check", "verifier": None, "result": "pending"},
    }
    record.update(copy.deepcopy(override))
    return record


def good_promotion(**override):
    ref = {"id": "unresolvable", "sha256": ZERO_SHA}
    record = {
        "schema_version": "sleep-promotion/1",
        "proposal_only": True,
        "synthetic": True,
        "operation_id": "op-1",
        "run_id": "run-1",
        "scope": {"project": "p", "task_family": "t"},
        "expected_parent_sha256": None,
        "candidate_snapshot": dict(ref),
        "operations_manifest": dict(ref),
        "source_manifest": dict(ref),
        "verification_receipt": dict(ref),
        "evaluation_receipt": dict(ref),
        "authorization_ref": "auth-ref",
        "authorization_revision": 0,
        "exclusion_revision": 0,
    }
    record.update(copy.deepcopy(override))
    return record


def dumps(value) -> bytes:
    return json.dumps(value).encode("utf-8")


def jsonl(*records) -> bytes:
    return b"".join(json.dumps(r).encode("utf-8") + b"\n" for r in records)


def codes(result) -> list[str]:
    return [d.code for d in result.report.diagnostics]
