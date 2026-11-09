"""Helpers for Gate 2B runtime-store tests: synthetic boundaries, claims and temporary stores."""

from __future__ import annotations

import support  # noqa: F401  (puts src/ on sys.path)
from evidence_support import StoreCase, make_boundary, make_item  # noqa: F401

from agent_sleep_lab.runtime_artifacts import ControlBoundary, EvaluatorBoundary, VerifierBoundary
from agent_sleep_lab.runtime_store import RuntimeStore

MEMORY_SHA = "a" * 64
OTHER_SHA = "b" * 64
RECEIPT_EXPIRY = "2026-12-01T00:00:00Z"


def make_verifier(**override) -> VerifierBoundary:
    kwargs = dict(
        boundary_id="synthetic-verifier",
        boundary_version="1.0.0",
        methods=frozenset({("manual-check", "1")}),
    )
    kwargs.update(override)
    return VerifierBoundary(**kwargs)


def make_evaluator(**override) -> EvaluatorBoundary:
    kwargs = dict(
        boundary_id="synthetic-evaluator",
        boundary_version="1.0.0",
        protocols=frozenset({("fixture-protocol", "1")}),
    )
    kwargs.update(override)
    return EvaluatorBoundary(**kwargs)


def make_control(**override) -> ControlBoundary:
    kwargs = dict(boundary_id="synthetic-control", boundary_version="1.0.0")
    kwargs.update(override)
    return ControlBoundary(**kwargs)


def policy_body(*, authorization_revision=1, purposes=("offline_consolidation",),
                partitions=("experience",), memory_ids=(), event_ids=(), root_ids=()):
    return {
        "authorizations": [{"ref": "auth-1", "revision": authorization_revision}],
        "accepted_purposes": list(purposes),
        "accepted_partitions": list(partitions),
        "exclusions": {
            "memory_ids": list(memory_ids),
            "event_ids": list(event_ids),
            "root_ids": list(root_ids),
        },
    }


def evidence_ref(store, event_id: str) -> dict:
    stored = store.get(event_id)
    return {
        "event_id": event_id,
        "event_sha256": stored.event_sha256,
        "source_sha256": stored.source_sha256,
        "provenance_sha256": stored.provenance_sha256,
    }


def verification_claim(store, event_ids=("e-1",), **override) -> dict:
    claim = {
        "receipt_id": "vr-1",
        "memory_id": "m-1",
        "memory_sha256": MEMORY_SHA,
        "scope": {"project": "p", "task_family": "t"},
        "evidence": [evidence_ref(store, e) for e in event_ids],
        "method": {"name": "manual-check", "version": "1"},
        "protocol_sha256": OTHER_SHA,
        "outcome": "confirmed",
        "expires_at": RECEIPT_EXPIRY,
        "limits": {"max_evidence": 8, "synthetic_only": True},
    }
    claim.update(override)
    return claim


def evaluation_claim(**override) -> dict:
    claim = {
        "receipt_id": "er-1",
        "snapshot_sha256": MEMORY_SHA,
        "operations_sha256": OTHER_SHA,
        "source_manifest_sha256": "c" * 64,
        "expected_parent_sha256": None,
        "scope": {"project": "p", "task_family": "t"},
        "protocol": {"name": "fixture-protocol", "version": "1", "config_sha256": "d" * 64},
        "result": "passed",
        "completeness": {"planned": 4, "completed": 4},
        "expires_at": RECEIPT_EXPIRY,
        "limits": {"synthetic_only": True},
    }
    claim.update(override)
    return claim


class RuntimeCase(StoreCase):
    """Like StoreCase, but opens the v2 ``RuntimeStore``."""

    def open_runtime(self, boundary=None, **kw) -> RuntimeStore:
        store = RuntimeStore(self.path, boundary or make_boundary(), clock=self.clock, **kw)
        self.addCleanup(store.close)
        return store
