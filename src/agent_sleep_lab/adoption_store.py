"""Synthetic-only durable adoption, v3. No retrieval adapter or authentication.

All commit-time decisions, payload writes, journal and scope head share ONE
BEGIN IMMEDIATE transaction. Replay returns historical receipt bytes, not present
permission to use a memory. v2 files require an explicit, atomic upgrade.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Callable, Mapping

from agent_sleep_lab.adoption_candidates import (
    _memory_document, build_candidate, build_committed_receipt,
    evidence_origin_failures, parse_canonical,
)
from agent_sleep_lab.evidence_store import (
    APPLICATION_ID, _DDL, _Reader, _as_bytes, _connect, _header, _rollback,
)
from agent_sleep_lab.provenance import (
    CaptureBoundary, ConflictError, ContractViolation, StorageError,
    parse_timestamp, sha256_hex,
)
from agent_sleep_lab.runtime_artifacts import EvaluatorBoundary, VerifierBoundary
from agent_sleep_lab.runtime_store import (
    RuntimeStore, _EXTENSION_DDL, _begin, _check_supported_schema, _schema_rows,
)

ADOPTION_USER_VERSION = 3
_ADOPTION_DDL = (
    """CREATE TABLE adoption_memories (
        memory_id TEXT PRIMARY KEY NOT NULL,
        memory_sha256 TEXT NOT NULL,
        memory_bytes BLOB NOT NULL
    )""",
    """CREATE TABLE adoption_snapshots (
        snapshot_sha256 TEXT PRIMARY KEY NOT NULL,
        snapshot_bytes BLOB NOT NULL
    )""",
    """CREATE TABLE adoption_journal (
        operation_id TEXT PRIMARY KEY NOT NULL,
        request_sha256 TEXT NOT NULL,
        request_bytes BLOB NOT NULL,
        manifest_bytes BLOB NOT NULL,
        source_manifest_bytes BLOB NOT NULL,
        receipt_sha256 TEXT NOT NULL,
        receipt_bytes BLOB NOT NULL
    )""",
    """CREATE TABLE adoption_heads (
        project TEXT NOT NULL,
        task_family TEXT NOT NULL,
        snapshot_sha256 TEXT NOT NULL REFERENCES adoption_snapshots(snapshot_sha256),
        operation_id TEXT NOT NULL REFERENCES adoption_journal(operation_id),
        PRIMARY KEY (project, task_family)
    )""",
) + tuple(
    f"CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table} "
    f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
    for table in ("adoption_memories", "adoption_snapshots", "adoption_journal")
    for op in ("UPDATE", "DELETE")
)


@lru_cache(maxsize=1)
def _expected_v3():
    conn = sqlite3.connect(":memory:")
    try:
        for statement in _DDL + _EXTENSION_DDL + _ADOPTION_DDL:
            conn.execute(statement)
        return _schema_rows(conn)
    finally:
        conn.close()


def _check_v3(conn):
    if _schema_rows(conn) != _expected_v3():
        raise StorageError("storage.unknown_database", "adoption schema differs from v3")


def _initialize_v3(conn):
    _begin(conn)
    try:
        app, version, objects = _header(conn)
        if app == 0 and version == 0 and objects == 0:
            for statement in _DDL + _EXTENSION_DDL + _ADOPTION_DDL:
                conn.execute(statement)
            conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")
            conn.execute("PRAGMA user_version = 3")
        elif app == APPLICATION_ID and version in (1, 2):
            raise StorageError("storage.upgrade_required", "explicit upgrade to v3 is required")
        elif app != APPLICATION_ID or version != 3:
            raise StorageError("storage.unknown_database", "not an adoption store")
        _check_v3(conn)
        conn.execute("COMMIT")
    except BaseException:
        _rollback(conn)
        raise


def upgrade_store_v2_to_v3(path: str | os.PathLike[str], *, busy_timeout=5.0):
    """Only exact v2 is accepted; existing evidence/receipts/policy bytes are untouched."""
    conn = _connect(path, readonly=False, timeout=busy_timeout)
    try:
        _begin(conn)
        try:
            app, version, _ = _header(conn)
            if app != APPLICATION_ID or version != 2:
                raise StorageError("storage.unknown_database", "upgrade requires exact v2")
            _check_supported_schema(conn, 2)
            for statement in _ADOPTION_DDL:
                conn.execute(statement)
            _check_v3(conn)
            conn.execute("PRAGMA user_version = 3")
            conn.execute("COMMIT")
        except BaseException:
            _rollback(conn)
            raise
    finally:
        conn.close()


@dataclass(frozen=True)
class AdoptionResult:
    status: str  # created/replayed; the receipt is historical, not current eligibility
    receipt_bytes: bytes
    receipt_sha256: str


class AdoptionStore(RuntimeStore):
    """v3 extension; configured boundaries are trusted local simulations, not credentials."""

    def __init__(
        self, path: str | os.PathLike[str], boundary: CaptureBoundary, *,
        verifier: VerifierBoundary, evaluator: EvaluatorBoundary,
        evaluation_protocol: tuple[str, str, str],
        clock: Callable[[], datetime] | None = None, busy_timeout: float = 5.0,
    ):
        if not isinstance(boundary, CaptureBoundary):
            raise TypeError("boundary must be a CaptureBoundary")
        if not isinstance(verifier, VerifierBoundary) or not isinstance(evaluator, EvaluatorBoundary):
            raise TypeError("separate verifier/evaluator boundaries are required")
        if (type(evaluation_protocol) is not tuple or len(evaluation_protocol) != 3
                or not all(type(v) is str for v in evaluation_protocol)
                or evaluation_protocol[:2] not in evaluator.protocols
                or len(evaluation_protocol[2]) != 64
                or any(c not in "0123456789abcdef" for c in evaluation_protocol[2])):
            raise ValueError("evaluation_protocol must be an accepted name/version and exact config hash")
        conn = _connect(path, readonly=False, timeout=busy_timeout)
        try:
            _initialize_v3(conn)
        except BaseException:
            conn.close()
            raise
        _Reader.__init__(self, conn, clock)
        self._boundary = boundary
        self._verifier = verifier
        self._evaluator = evaluator
        self._evaluation_protocol = evaluation_protocol

    def _snapshot(self, digest, scope):
        rows = self._rows(
            "SELECT snapshot_bytes FROM adoption_snapshots WHERE snapshot_sha256 = ?", (digest,)
        )
        if not rows:
            raise StorageError("adoption.snapshot_missing", "head/parent snapshot is missing")
        data = _as_bytes(rows[0][0])
        if sha256_hex(data) != digest:
            raise StorageError("adoption.snapshot_corrupt", "snapshot hash mismatch")
        doc = parse_canonical("candidate_snapshot", data)
        if doc["scope"] != scope:
            raise StorageError("adoption.snapshot_corrupt", "snapshot scope mismatch")
        return data

    def _resolve_operation(self, operation_id):
        rows = self._rows(
            "SELECT request_sha256, request_bytes, manifest_bytes, source_manifest_bytes, receipt_sha256, receipt_bytes "
            "FROM adoption_journal WHERE operation_id = ?", (operation_id,)
        )
        if not rows:
            return None
        req_sha, req_blob, manifest_blob, source_blob, rec_sha, rec_blob = rows[0]
        req_data, rec_data = _as_bytes(req_blob), _as_bytes(rec_blob)
        if sha256_hex(req_data) != req_sha or sha256_hex(rec_data) != rec_sha:
            raise StorageError("adoption.journal_corrupt", "journal hash mismatch")
        req = parse_canonical("adoption_request", req_data)
        rec = parse_canonical("committed_receipt", rec_data)
        manifest_data, source_data = _as_bytes(manifest_blob), _as_bytes(source_blob)
        manifest = parse_canonical("operation_manifest", manifest_data)
        source = parse_canonical("source_manifest", source_data)
        if (sha256_hex(manifest_data) != req["operations_sha256"]
                or sha256_hex(source_data) != req["source_manifest_sha256"]
                or manifest["scope"] != req["scope"] or source["scope"] != req["scope"]
                or manifest["expected_parent_snapshot_sha256"] != req["expected_parent_snapshot_sha256"]):
            raise StorageError("adoption.journal_corrupt", "stored payload binding mismatch")
        version = "2" if req["schema_version"] == "agent-sleep-adoption-request/2" else "1"
        expected_rec = {
            "schema_version": "agent-sleep-committed-operation-receipt/" + version,
            "operation_id": operation_id, "request_sha256": req_sha,
            "scope": req["scope"],
            "parent_snapshot_sha256": req["expected_parent_snapshot_sha256"],
            "snapshot_sha256": (req["candidate_snapshot_sha256"]
                               if req["candidate_snapshot_sha256"] is not None
                               else req["expected_parent_snapshot_sha256"]),
            "policy_revision": req["expected_policy_revision"],
            "evaluation_receipt": req["evaluation_receipt"],
            "outcome": "adopted" if req["candidate_snapshot_sha256"] is not None else "audit_only",
        }
        if version == "2":
            expected_rec["run_id"] = req["run_id"]
        if req["operation_id"] != operation_id or any(rec.get(k) != v for k, v in expected_rec.items()):
            raise StorageError("adoption.journal_corrupt", "journal receipt binding mismatch")
        return req_sha, req_data, AdoptionResult("replayed", rec_data, rec_sha)

    def resolve_operation(self, operation_id: str) -> AdoptionResult | None:
        """Read-only ACK-loss reconciliation. Never re-applies or grants present eligibility."""
        with self._immediate():
            _check_v3(self._db())
            row = self._resolve_operation(operation_id)
            return row[2] if row else None

    def _head(self, scope):
        rows = self._rows(
            "SELECT snapshot_sha256, operation_id FROM adoption_heads "
            "WHERE project = ? AND task_family = ?",
            (scope["project"], scope["task_family"]),
        )
        if not rows:
            return None
        digest, operation_id = rows[0]
        journal = self._resolve_operation(operation_id)
        if journal is None:
            raise StorageError("adoption.head_corrupt", "head has no journal entry")
        receipt = parse_canonical("committed_receipt", journal[2].receipt_bytes)
        if receipt["outcome"] != "adopted" or receipt["scope"] != scope or receipt["snapshot_sha256"] != digest:
            raise StorageError("adoption.head_corrupt", "head journal binding mismatch")
        self._snapshot(digest, scope)
        return digest

    def current_snapshot(self, scope: dict[str, str]) -> bytes | None:
        """Historical snapshot metadata ONLY; not a currently eligible retrieval result."""
        if type(scope) is not dict or set(scope) != {"project", "task_family"}:
            raise ValueError("scope must name project and task_family")
        with self._immediate():
            _check_v3(self._db())
            digest = self._head(scope)
            return self._snapshot(digest, scope) if digest else None

    def _evaluation(self, req, plan, now):
        ref = req["evaluation_receipt"]
        doc = self.resolve_receipt("evaluation", ref["receipt_id"], ref["receipt_sha256"])
        expected = {
            "snapshot_sha256": plan.snapshot_sha256, "operations_sha256": plan.operations_sha256,
            "source_manifest_sha256": plan.source_manifest_sha256,
            "expected_parent_sha256": plan.parent_sha256, "scope": plan.scope,
            "boundary": {"boundary_id": self._evaluator.boundary_id,
                         "boundary_version": self._evaluator.boundary_version},
            "protocol": dict(zip(("name", "version", "config_sha256"), self._evaluation_protocol)),
        }
        if any(doc[k] != value for k, value in expected.items()):
            raise ContractViolation("adoption.evaluation_binding", "evaluation does not bind the configured candidate")
        if doc["result"] != "passed" or doc["completeness"]["completed"] != doc["completeness"]["planned"]:
            raise ContractViolation("adoption.evaluation_incomplete", "complete passed evaluation is required")
        if (parse_timestamp(doc["issued_at"]) > now
                or (doc["expires_at"] is not None and now >= parse_timestamp(doc["expires_at"]))):
            raise ContractViolation("adoption.evaluation_expired", "evaluation is not currently valid")

    def _check_active(self, plan, source, memory_bytes, now):
        entries = {entry["memory_id"]: entry for entry in source["entries"]}
        for member in plan.snapshot_doc["members"]:
            if member["state"] != "active":
                continue
            mid, digest = member["memory_id"], member["memory_sha256"]
            if mid in memory_bytes:
                data = memory_bytes[mid]
            else:
                rows = self._rows(
                    "SELECT memory_sha256, memory_bytes FROM adoption_memories WHERE memory_id = ?", (mid,)
                )
                if not rows or rows[0][0] != digest:
                    raise StorageError("adoption.memory_missing", "carried memory is missing or inconsistent")
                data = _as_bytes(rows[0][1])
            memory = _memory_document(mid, digest, data, plan.scope, now)
            if memory["kind"] != member["kind"]:
                raise StorageError("adoption.memory_corrupt", "snapshot kind differs from memory")
            ref = member["verification_receipt"]
            failures = self.eligibility_failures(
                memory_id=mid, memory_sha256=digest,
                scope=(plan.scope["project"], plan.scope["task_family"]),
                receipt_id=ref["receipt_id"], receipt_sha256=ref["receipt_sha256"],
                verifier=self._verifier, now=now,
            )
            if failures:
                raise ContractViolation("adoption.ineligible", ", ".join(failures))
            receipt = self.resolve_receipt("verification", ref["receipt_id"], ref["receipt_sha256"])
            refs = {e["event_id"]: e for e in receipt["evidence"]}
            if set(refs) != {e["event_id"] for e in memory["evidence"]}:
                raise ContractViolation("adoption.evidence_binding", "memory and receipt evidence differ")
            if mid in entries and refs != {e["event_id"]: e for e in entries[mid]["evidence"]}:
                raise ContractViolation("adoption.evidence_binding", "source and receipt evidence hashes differ")
            # Traverse every ancestor, not only the directly named event's original root.
            pending, seen, origins = list(refs), set(), set()
            while pending:
                event_id = pending.pop()
                if event_id in seen:
                    continue
                seen.add(event_id)
                evidence = self.get(event_id)
                root = self.get(evidence.root_id)
                origins.add(root.provenance["origin"])
                pending.extend(r[0] for r in self._parents(event_id))
            failures = evidence_origin_failures(memory["kind"], origins)
            if failures:
                raise ContractViolation("adoption.origin", ", ".join(failures))

    def commit_adoption(
        self, *, request_bytes: object, manifest_bytes: object,
        source_manifest_bytes: object, memory_bytes: Mapping[str, object],
    ) -> AdoptionResult:
        """Commit once, or return original receipt on exact replay. No automatic retry."""
        # Freeze mutable caller bytes before comparing or entering the transaction.
        req = parse_canonical("adoption_request", request_bytes)
        req_data = bytes(request_bytes)
        manifest = parse_canonical("operation_manifest", manifest_bytes)
        source = parse_canonical("source_manifest", source_manifest_bytes)
        manifest_data, source_data = bytes(manifest_bytes), bytes(source_manifest_bytes)
        supplied = {}
        for mid, blob in memory_bytes.items():
            if type(blob) not in (bytes, bytearray):
                raise ContractViolation("candidate.memory_not_bytes", "memory must be bytes")
            supplied[mid] = bytes(blob)
        wanted = {o["memory_id"]: o["memory_sha256"] for o in manifest["operations"]
                  if o["op"] in ("add", "supersede")}
        if (sha256_hex(manifest_data) != req["operations_sha256"]
                or sha256_hex(source_data) != req["source_manifest_sha256"]
                or manifest["scope"] != req["scope"] or source["scope"] != req["scope"]
                or manifest["expected_parent_snapshot_sha256"] != req["expected_parent_snapshot_sha256"]
                or set(wanted) != set(supplied)
                or any(sha256_hex(supplied[mid]) != digest for mid, digest in wanted.items())):
            raise ContractViolation("adoption.payload_mismatch", "request does not bind exact submitted payload")
        req_sha = sha256_hex(req_data)
        try:
            with self._immediate():
                _check_v3(self._db())
                prior = self._resolve_operation(req["operation_id"])
                if prior:
                    if prior[0] != req_sha or prior[1] != req_data:
                        raise ConflictError("adoption.operation_conflict", "operation ID already has different content")
                    return prior[2]  # NO head write or current-policy assertion on historical replay
                if req["schema_version"] != "agent-sleep-adoption-request/2":
                    raise ContractViolation(
                        "adoption.legacy_write", "new operations require request/2 and an explicit run_id"
                    )
                now = self._now()
                policy = self.current_policy()
                if policy.revision != req["expected_policy_revision"]:
                    raise ConflictError("adoption.policy_conflict", "current policy revision differs")
                parent_sha = self._head(req["scope"])
                if parent_sha != req["expected_parent_snapshot_sha256"]:
                    raise ConflictError("adoption.parent_conflict", "current scope head differs")
                parent = self._snapshot(parent_sha, req["scope"]) if parent_sha else None
                known = {r[0] for r in self._rows("SELECT memory_id FROM adoption_memories")}
                plan = build_candidate(
                    manifest_bytes=manifest_data, source_manifest_bytes=source_data,
                    parent_bytes=parent, memory_bytes=supplied, known_ids=known, now=now,
                )
                if plan.snapshot_sha256 != req["candidate_snapshot_sha256"]:
                    raise ContractViolation("adoption.candidate_mismatch", "constructed snapshot differs from request")
                if plan.changed:
                    self._evaluation(req, plan, now)
                    self._check_active(plan, source, supplied, now)
                    for mid, data in supplied.items():
                        self._db().execute(
                            "INSERT INTO adoption_memories VALUES (?, ?, ?)",
                            (mid, sha256_hex(data), data),
                        )
                    self._db().execute(
                        "INSERT INTO adoption_snapshots VALUES (?, ?)",
                        (plan.snapshot_sha256, plan.snapshot_bytes),
                    )
                rec_bytes, rec_sha = build_committed_receipt(
                    req_data, policy_revision=policy.revision, now=now,
                )
                self._db().execute(
                    "INSERT INTO adoption_journal VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (req["operation_id"], req_sha, req_data, manifest_data, source_data, rec_sha, rec_bytes),
                )
                if plan.changed:
                    self._db().execute(
                        "INSERT INTO adoption_heads VALUES (?, ?, ?, ?) "
                        "ON CONFLICT(project, task_family) DO UPDATE SET "
                        "snapshot_sha256=excluded.snapshot_sha256, operation_id=excluded.operation_id",
                        (plan.scope["project"], plan.scope["task_family"],
                         plan.snapshot_sha256, req["operation_id"]),
                    )
                result = AdoptionResult("created", rec_bytes, rec_sha)
            return result  # returned only after COMMIT
        except sqlite3.Error as exc:
            raise StorageError("storage.write_failed", f"adoption rolled back ({exc})") from None
