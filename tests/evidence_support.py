"""Helpers for Gate 2A evidence-store tests: synthetic items and temporary stores only."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone

import support  # noqa: F401  (puts src/ on sys.path)

from agent_sleep_lab.evidence_store import EvidenceStore, ReadOnlyEvidenceStore
from agent_sleep_lab.provenance import ORIGINS, CaptureBoundary, sha256_hex

NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)
LATER = datetime(2027, 6, 1, tzinfo=timezone.utc)  # after the default expiry below


class Clock:
    def __init__(self, now: datetime = NOW) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_boundary(revision: int = 1, **override) -> CaptureBoundary:
    kwargs = dict(
        adapter_id="synthetic-adapter",
        adapter_version="1.0.0",
        allowed_origins=frozenset(ORIGINS),
        authorizations={"auth-1": revision},
    )
    kwargs.update(override)
    return CaptureBoundary(**kwargs)


def make_item(
    event_id: str,
    *,
    origin: str = "tool_observation",
    derived_from=(),
    root: str | None = None,
    text: str | None = None,
    scope=("p", "t"),
    claim_scope=None,
    synthetic: bool = True,
    event_synthetic: bool | None = None,
    evaluation: str = "experience",
    revision: int = 1,
    expires: str | None = "2027-01-01T00:00:00Z",
    summary: str = "something happened",
    **top,
):
    """Return (event_bytes, source_bytes, claim). ``top`` overrides top-level claim keys."""
    event = support.good_event(
        event_id=event_id,
        scope={"project": scope[0], "task_family": scope[1]},
        synthetic=synthetic if event_synthetic is None else event_synthetic,
        summary=summary,
    )
    event_bytes = (json.dumps(event, sort_keys=True) + "\n").encode("utf-8")
    source_bytes = (text if text is not None else f"raw source for {event_id}").encode("utf-8")
    cs = claim_scope or scope
    claim = {
        "schema_version": "agent-sleep-provenance/1",
        "event": {
            "event_id": event_id,
            "sha256": sha256_hex(event_bytes),
            "scope": {"project": cs[0], "task_family": cs[1]},
        },
        "origin": origin,
        "source": {
            "source_id": f"src-{event_id}",
            "sha256": sha256_hex(source_bytes),
            "locator": "line:1",
        },
        "observed_at": "2026-11-08T00:00:00Z",
        "captured_at": "2026-11-09T00:00:00Z",
        "lineage": {"original_root_id": root or event_id, "derived_from": list(derived_from)},
        "authorization": {
            "ref": "auth-1",
            "revision": revision,
            "purpose": "offline_consolidation",
            "retention": "until_expiry",
            "expires_at": expires,
        },
        "partition": {"synthetic": synthetic, "evaluation": evaluation},
    }
    claim.update(top)
    return event_bytes, source_bytes, claim


class StoreCase(unittest.TestCase):
    """Each test gets a fresh temporary directory outside the repository."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="asl-gate2a-")
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.path = os.path.join(self.dir, "evidence.sqlite3")
        self.clock = Clock()

    def open(self, boundary=None, **kw) -> EvidenceStore:
        store = EvidenceStore(self.path, boundary or make_boundary(), clock=self.clock, **kw)
        self.addCleanup(store.close)
        return store

    def open_ro(self) -> ReadOnlyEvidenceStore:
        store = ReadOnlyEvidenceStore(self.path, clock=self.clock)
        self.addCleanup(store.close)
        return store

    def put(self, store, item):
        event_bytes, source_bytes, claim = item
        return store.capture(event_bytes=event_bytes, source_bytes=source_bytes, claim=claim)

    def raw(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, isolation_level=None)
        self.addCleanup(conn.close)
        return conn

    def drop_triggers(self, conn) -> None:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")]
        for name in names:
            conn.execute(f'DROP TRIGGER "{name}"')

    def count(self, table: str) -> int:
        return self.raw().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def assertRaisesCode(self, exc_type, code, fn):
        with self.assertRaises(exc_type) as cm:
            fn()
        self.assertEqual(cm.exception.code, code)
        return cm.exception
