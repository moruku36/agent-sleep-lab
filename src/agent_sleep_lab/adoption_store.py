"""Synthetic-only durable adoption, v3. No retrieval adapter or authentication.

All commit-time decisions, payload writes, journal and scope head share ONE
BEGIN IMMEDIATE transaction. Replay returns historical receipt bytes, not present
permission to use a memory. v2 files require an explicit, atomic upgrade.

``commit_rollback`` (Gate 3, merged PR #14 with focused CI acceptance) adds explicit control recovery to a retained
snapshot using the SAME v3 tables: no schema change, no migration. A rollback journal row stores
the rollback request/receipt bytes with EMPTY manifest/source columns. Adoption request/receipt
v1/v2 bytes and their replay are untouched.

``plan_forget_impact`` / ``commit_forget`` (Gate 3, merged PR #15 with focused CI acceptance) add audited LOGICAL
forgetting on the SAME v3 layout: forget request/receipt rows also keep EMPTY manifest/source
columns and are dispatched by exact schema_version. The writer appends exclusions (never removes
one) as the next policy revision and stores the immutable request/receipt in the SAME BEGIN
IMMEDIATE transaction. This is NOT physical deletion: append-only rows, old SQLite pages, backups
and caller-held bundles keep the bytes. Purge/cache/index/diary cleanup is not implemented.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Callable, Mapping

from agent_sleep_lab.adoption_candidates import (
    _memory_document, build_candidate, build_committed_receipt, build_forget_receipt,
    build_forget_request, build_rollback_receipt, evidence_origin_failures, parse_canonical,
)
from agent_sleep_lab.validation import validate_bytes
from agent_sleep_lab.strictjson import StrictJSONError, loads_strict_bytes
from agent_sleep_lab.evidence_store import (
    APPLICATION_ID, _DDL, _Reader, _as_bytes, _check_path, _connect, _header, _rollback,
)
from agent_sleep_lab.provenance import (
    CaptureBoundary, ConflictError, ContractViolation, StorageError,
    canonical_json, parse_timestamp, sha256_hex,
)
from agent_sleep_lab.runtime_artifacts import (
    ControlBoundary, EvaluatorBoundary, VerifierBoundary, parse_artifact_bytes,
)
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


MAX_IMPACT_EVENTS = 4096
MAX_IMPACT_MEMORIES = 4096
MAX_IMPACT_SNAPSHOTS = 1024
MAX_IMPACT_LINKS = 32768
MAX_IMPACT_REFS = 16384
_TARGET_FIELDS = ("memory_ids", "event_ids", "root_ids")


@dataclass(frozen=True)
class ForgetImpact:
    """Deterministic dry-run plan. IDs, hashes and counts only: never source or memory text.

    ``new_exclusions`` is what a commit would add (targets not already excluded). Affected
    events/memories/snapshot references are DERIVED by ancestry and stay recorded unchanged; the
    current policy hides them. This describes logical exclusion, not physical erasure."""
    scope: dict
    policy_revision: int
    targets: dict
    new_exclusions: dict
    affected_event_ids: tuple
    affected_memory_ids: tuple
    snapshot_refs: tuple  # (snapshot_sha256, memory_id) for every member entry of the scope
    current_head_affected: bool  # the current head holds an ACTIVE affected member
    impact_sha256: str


class AdoptionStore(RuntimeStore):
    """v3 store; boundaries are local simulations, not credentials.

    ``read_only=True`` opens only an existing exact v3 file using SQLite ro and
    query-only controls. The default writer still initializes as before.
    """

    def __init__(
        self, path: str | os.PathLike[str], boundary: CaptureBoundary, *,
        verifier: VerifierBoundary, evaluator: EvaluatorBoundary,
        evaluation_protocol: tuple[str, str, str],
        clock: Callable[[], datetime] | None = None, busy_timeout: float = 5.0,
        read_only: bool = False,
    ):
        if type(read_only) is not bool:
            raise TypeError("read_only must be boolean")
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
        if read_only:
            target = _check_path(path)
            if not target.is_file() or not target.stat().st_size:
                raise StorageError("storage.open_failed", "existing nonempty adoption store required")
        conn = _connect(path, readonly=read_only, timeout=busy_timeout)
        try:
            if read_only:
                app, version, _ = _header(conn)
                if app != APPLICATION_ID or version != 3:
                    raise StorageError("storage.unknown_database", "existing v3 adoption store required")
                _check_v3(conn)
            else:
                _initialize_v3(conn)
        except BaseException:
            conn.close()
            raise
        _Reader.__init__(self, conn, clock)
        self.read_only = read_only
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
        if self._is_rollback(req_data):
            return self._resolve_rollback(
                operation_id, req_sha, req_data, rec_sha, rec_data,
                _as_bytes(manifest_blob), _as_bytes(source_blob),
            )
        if self._is_forget(req_data):
            return self._resolve_forget(
                operation_id, req_sha, req_data, rec_sha, rec_data,
                _as_bytes(manifest_blob), _as_bytes(source_blob),
            )
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
        return req_sha, req_data, AdoptionResult("replayed", rec_data, rec_sha), rec

    @staticmethod
    def _is_rollback(req_data):
        try:
            doc = loads_strict_bytes(req_data)
        except StrictJSONError:
            return False  # the adoption parser then reports it as corrupt
        return isinstance(doc, dict) and doc.get("schema_version") == "agent-sleep-rollback-request/1"

    @staticmethod
    def _is_forget(req_data):
        try:
            doc = loads_strict_bytes(req_data)
        except StrictJSONError:
            return False
        return isinstance(doc, dict) and doc.get("schema_version") == "agent-sleep-forget-request/1"

    def _resolve_forget(self, operation_id, req_sha, req_data, rec_sha, rec_data, manifest, source):
        """Forget rows reuse the v3 journal columns; manifest/source must be empty. The row is bound
        to the exact policy revision it published. Replay never re-applies anything."""
        if manifest != b"" or source != b"":
            raise StorageError("adoption.journal_corrupt", "forget journal carries adoption payloads")
        req = parse_canonical("forget_request", req_data)
        rec = parse_canonical("forget_receipt", rec_data)
        expected = {
            "operation_id": operation_id, "run_id": req["run_id"], "request_sha256": req_sha,
            "scope": req["scope"], "expected_policy_revision": req["expected_policy_revision"],
        }
        if req["operation_id"] != operation_id or any(rec.get(k) != v for k, v in expected.items()):
            raise StorageError("adoption.journal_corrupt", "forget receipt binding mismatch")
        if any(not set(rec["added_exclusions"][f]) <= set(req["targets"][f]) for f in _TARGET_FIELDS):
            raise StorageError("adoption.journal_corrupt", "forget receipt adds untargeted exclusions")
        rows = self._rows(
            "SELECT policy_sha256, policy_bytes FROM policy_revisions WHERE revision = ?",
            (rec["resulting_policy_revision"],),
        )
        if not rows or rows[0][0] != rec["resulting_policy_sha256"]:
            raise StorageError("adoption.journal_corrupt", "forget receipt policy revision mismatch")
        policy_data = _as_bytes(rows[0][1])
        if sha256_hex(policy_data) != rows[0][0]:
            raise StorageError("adoption.journal_corrupt", "forget policy revision fails its hash")
        try:
            policy = parse_artifact_bytes("policy", policy_data)
        except ContractViolation:
            raise StorageError("adoption.journal_corrupt", "forget policy revision is invalid") from None
        previous_rows = self._rows(
            "SELECT policy_sha256, policy_bytes FROM policy_revisions WHERE revision = ?",
            (req["expected_policy_revision"],),
        )
        if not previous_rows:
            raise StorageError("adoption.journal_corrupt", "forget previous policy is absent")
        previous_data = _as_bytes(previous_rows[0][1])
        if sha256_hex(previous_data) != previous_rows[0][0]:
            raise StorageError("adoption.journal_corrupt", "forget previous policy fails its hash")
        try:
            previous = parse_artifact_bytes("policy", previous_data)
        except ContractViolation:
            raise StorageError("adoption.journal_corrupt", "forget previous policy is invalid") from None
        if (policy["revision"] != rec["resulting_policy_revision"]
                or previous["revision"] != req["expected_policy_revision"]
                or any(policy[k] != previous[k] for k in
                       ("authorizations", "accepted_purposes", "accepted_partitions"))):
            raise StorageError("adoption.journal_corrupt", "forget changed an unrelated policy value")
        for field in _TARGET_FIELDS:
            added = [i for i in req["targets"][field] if i not in previous["exclusions"][field]]
            if (rec["added_exclusions"][field] != added
                    or policy["exclusions"][field] != previous["exclusions"][field] + added):
                raise StorageError("adoption.journal_corrupt", "forget policy delta differs from targets")
        return req_sha, req_data, AdoptionResult("replayed", rec_data, rec_sha), rec

    def _resolve_rollback(self, operation_id, req_sha, req_data, rec_sha, rec_data, manifest, source):
        """Rollback rows reuse the v3 journal columns; manifest/source columns must be empty."""
        if manifest != b"" or source != b"":
            raise StorageError("adoption.journal_corrupt", "rollback journal carries adoption payloads")
        req = parse_canonical("rollback_request", req_data)
        rec = parse_canonical("rollback_receipt", rec_data)
        expected = {
            "operation_id": operation_id, "run_id": req["run_id"], "request_sha256": req_sha,
            "scope": req["scope"],
            "parent_snapshot_sha256": req["expected_head_snapshot_sha256"],
            "snapshot_sha256": req["target_snapshot_sha256"],
            "policy_revision": req["expected_policy_revision"],
            "outcome": "rolled_back",
        }
        if req["operation_id"] != operation_id or any(rec.get(k) != v for k, v in expected.items()):
            raise StorageError("adoption.journal_corrupt", "rollback receipt binding mismatch")
        return req_sha, req_data, AdoptionResult("replayed", rec_data, rec_sha), rec

    @contextmanager
    def _read_transaction(self):
        """Consistent metadata read without reserving the SQLite writer lock."""
        db = self._db()
        if db.in_transaction:
            raise StorageError("storage.nested_transaction", "metadata read needs its own transaction")
        try:
            db.execute("BEGIN")
            yield
        except sqlite3.Error as exc:
            raise StorageError("storage.read_failed", f"metadata read failed ({exc})") from None
        finally:
            _rollback(db)

    def resolve_operation(self, operation_id: str) -> AdoptionResult | None:
        """Read-only ACK-loss reconciliation. Never re-applies or grants present eligibility."""
        with self._read_transaction():
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
        receipt = journal[3]  # already parsed and bound by _resolve_operation (adoption or rollback)
        if (receipt["outcome"] not in ("adopted", "rolled_back")
                or receipt["scope"] != scope or receipt["snapshot_sha256"] != digest):
            raise StorageError("adoption.head_corrupt", "head journal binding mismatch")
        self._snapshot(digest, scope)
        return digest

    def current_snapshot(self, scope: dict[str, str]) -> bytes | None:
        """Historical snapshot metadata ONLY; not a currently eligible retrieval result."""
        if type(scope) is not dict or set(scope) != {"project", "task_family"}:
            raise ValueError("scope must name project and task_family")
        with self._read_transaction():
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
        self._check_members(plan.scope, plan.snapshot_doc["members"], entries, memory_bytes, now)

    def _check_members(self, scope, members, entries, memory_bytes, now):
        """Revalidate every ACTIVE member under the CURRENT policy, expiry and exclusions.
        Shared by adoption and rollback so one rule decides eligibility; any failure raises."""
        policy = self.current_policy().document
        for member in members:
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
            memory = _memory_document(mid, digest, data, scope, now)
            if memory["kind"] != member["kind"]:
                raise StorageError("adoption.memory_corrupt", "snapshot kind differs from memory")
            ref = member["verification_receipt"]
            failures = self._eligibility_failures_with_policy(
                memory_id=mid, memory_sha256=digest,
                scope=(scope["project"], scope["task_family"]),
                receipt_id=ref["receipt_id"], receipt_sha256=ref["receipt_sha256"],
                verifier=self._verifier, now=now, policy=policy,
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
        self._require_writable()
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

    def commit_rollback(self, *, request_bytes: object) -> AdoptionResult:
        """Explicitly restore a retained, previously adopted snapshot of the SAME scope.

        Control recovery, not a fresh adoption and not an evaluation claim. In one BEGIN IMMEDIATE
        transaction: replay lookup by operation ID; current policy revision and scope head
        compare-and-swap; every ACTIVE member of the target is revalidated under the CURRENT
        authorization, expiry and exclusions. If any member fails the whole rollback is refused:
        nothing is filtered or rewritten and head and history are unchanged. On success the journal
        row (request digest + receipt) and the head move together. Original snapshots, memories
        and receipts are never modified, and old authorization is never regained.
        """
        self._require_writable()
        req = parse_canonical("rollback_request", request_bytes)
        req_data = bytes(request_bytes)
        req_sha = sha256_hex(req_data)
        scope = req["scope"]
        target = req["target_snapshot_sha256"]
        try:
            with self._immediate():
                _check_v3(self._db())
                prior = self._resolve_operation(req["operation_id"])
                if prior:
                    if prior[0] != req_sha or prior[1] != req_data:
                        raise ConflictError("adoption.operation_conflict", "operation ID already has different content")
                    return prior[2]  # historical receipt; no head write or present-time assertion
                now = self._now()
                policy = self.current_policy()
                if policy.revision != req["expected_policy_revision"]:
                    raise ConflictError("adoption.policy_conflict", "current policy revision differs")
                if self._head(scope) != req["expected_head_snapshot_sha256"]:
                    raise ConflictError("rollback.head_conflict", "current scope head differs")
                rows = self._rows(
                    "SELECT snapshot_bytes FROM adoption_snapshots WHERE snapshot_sha256 = ?", (target,)
                )
                if not rows:
                    raise ContractViolation("rollback.target_unavailable", "target snapshot is not retained")
                data = _as_bytes(rows[0][0])
                if sha256_hex(data) != target:
                    raise StorageError("adoption.snapshot_corrupt", "snapshot hash mismatch")
                snapshot = parse_canonical("candidate_snapshot", data)
                if snapshot["scope"] != scope:
                    raise ContractViolation("rollback.scope_mismatch", "target snapshot belongs to another scope")
                # A retained blob alone is not proof of a committed adoption. Resolve
                # the original, hash-bound adoption receipt in this same transaction.
                adopted = False
                for operation_id, request_blob in self._rows(
                        "SELECT operation_id, request_bytes FROM adoption_journal "
                        "WHERE instr(CAST(request_bytes AS TEXT), ?) > 0", (target,)):
                    # Candidate selection only, never proof. Do not fully resolve unrelated
                    # manifests/receipts or let their corruption disable this scope's recovery.
                    try:
                        candidate = loads_strict_bytes(_as_bytes(request_blob))
                    except StrictJSONError:
                        continue
                    if (not isinstance(candidate, dict)
                            or candidate.get("schema_version") not in (
                                "agent-sleep-adoption-request/1", "agent-sleep-adoption-request/2")
                            or candidate.get("scope") != scope
                            or candidate.get("candidate_snapshot_sha256") != target):
                        continue
                    history = self._resolve_operation(operation_id)
                    receipt = history[3]
                    if (receipt["outcome"] == "adopted" and receipt["scope"] == scope
                            and receipt["snapshot_sha256"] == target):
                        adopted = True
                        break
                if not adopted:
                    raise ContractViolation("rollback.target_not_adopted",
                                            "target has no committed adoption receipt")
                # Whole-or-nothing: any ineligible/expired/missing active member raises here.
                self._check_members(scope, snapshot["members"], {}, {}, now)
                rec_bytes, rec_sha = build_rollback_receipt(
                    req_data, policy_revision=policy.revision, now=now,
                )
                self._db().execute(
                    "INSERT INTO adoption_journal VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (req["operation_id"], req_sha, req_data, b"", b"", rec_sha, rec_bytes),
                )
                self._db().execute(
                    "INSERT INTO adoption_heads VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(project, task_family) DO UPDATE SET "
                    "snapshot_sha256=excluded.snapshot_sha256, operation_id=excluded.operation_id",
                    (scope["project"], scope["task_family"], target, req["operation_id"]),
                )
                result = AdoptionResult("created", rec_bytes, rec_sha)
            return result  # returned only after COMMIT
        except sqlite3.Error as exc:
            raise StorageError("storage.write_failed", f"rollback rolled back ({exc})") from None

    # ---- audited logical forgetting (Gate 3, merged PR #15; focused CI acceptance)

    def _stored_memory(self, memory_id, digest, blob):
        data = _as_bytes(blob)
        try:
            doc = loads_strict_bytes(data)
        except StrictJSONError:
            doc = None
        if (sha256_hex(data) != digest or not isinstance(doc, dict)
                or doc.get("memory_id") != memory_id or not isinstance(doc.get("scope"), dict)
                or not isinstance(doc.get("evidence"), list)
                or not validate_bytes("memory", data).valid):
            raise StorageError("adoption.memory_corrupt", "stored memory fails its binding")
        return doc

    def _check_forget_targets(self, scope, targets):
        """Every target must be a trusted local row of EXACTLY this scope. Unknown and
        other-scope targets are indistinguishable (one code), so a scope cannot probe or revoke
        another scope's IDs."""
        pair = (scope["project"], scope["task_family"])

        def unavailable():
            return ContractViolation("forget.target_unavailable", "a target is not a row of this scope")

        for event_id in targets["event_ids"]:
            rows = self._rows("SELECT project, task_family FROM evidence WHERE event_id = ?", (event_id,))
            if not rows or tuple(rows[0]) != pair:
                raise unavailable()
        for root_id in targets["root_ids"]:
            rows = self._rows(
                "SELECT project, task_family, root_id FROM evidence WHERE event_id = ?", (root_id,))
            if not rows or tuple(rows[0][:2]) != pair or rows[0][2] != root_id:
                raise unavailable()  # must be an existing independent-or-generated ROOT event
        # Expiry must not prevent forgetting, but corrupted target bindings do.
        # This is an integrity check, not an authorization grant.
        for event_id in set(targets["event_ids"]) | set(targets["root_ids"]):
            if set(self.verify(event_id).failures) - {"authorization.expired"}:
                raise StorageError("forget.target_corrupt", "target evidence fails integrity")
        for memory_id in targets["memory_ids"]:
            rows = self._rows(
                "SELECT memory_sha256, memory_bytes FROM adoption_memories WHERE memory_id = ?",
                (memory_id,))
            if not rows or self._stored_memory(memory_id, rows[0][0], rows[0][1])["scope"] != scope:
                raise unavailable()

    def _impact_rows(self, sql, params, limit):
        """Bound materialized rows; refuse excess rather than returning a partial plan."""
        rows = self._rows(sql + " LIMIT ?", params + (limit + 1,))
        if len(rows) > limit:
            raise StorageError("forget.impact_too_large", "impact scan exceeds the synthetic limit")
        return rows

    def _forget_plan(self, scope, targets, policy):
        """Shared by the dry run and the writer, so both see the identical deterministic plan.
        Only the named IDs become exclusions; descendants and dependent memories are hidden by the
        existing ancestor recheck, never by over-broad exclusion of shared or unrelated rows."""
        self._check_forget_targets(scope, targets)
        pair = (scope["project"], scope["task_family"])
        current = policy.document["exclusions"]
        new_exclusions = {f: tuple(i for i in targets[f] if i not in set(current[f]))
                          for f in _TARGET_FIELDS}
        events = self._impact_rows(
            "SELECT event_id, root_id FROM evidence WHERE project = ? AND task_family = ?",
            pair, MAX_IMPACT_EVENTS)
        children = {}
        for child, parent in self._impact_rows(
                "SELECT l.child_id, l.parent_id FROM lineage l JOIN evidence e ON e.event_id = l.child_id "
                "WHERE e.project = ? AND e.task_family = ?", pair, MAX_IMPACT_LINKS):
            children.setdefault(parent, []).append(child)
        wanted_roots = set(targets["root_ids"]) | set(targets["event_ids"])
        pending = list(set(targets["event_ids"]) | set(targets["root_ids"])
                       | {e for e, root in events if root in wanted_roots})
        affected_events = set()
        while pending:
            event_id = pending.pop()
            if event_id in affected_events:
                continue
            affected_events.add(event_id)
            pending.extend(children.get(event_id, ()))
        affected_memories = set(targets["memory_ids"])
        for memory_id, digest, blob in self._impact_rows(
                "SELECT memory_id, memory_sha256, memory_bytes FROM adoption_memories ORDER BY memory_id",
                (), MAX_IMPACT_MEMORIES):
            doc = self._stored_memory(memory_id, digest, blob)
            if doc["scope"] != scope:
                continue
            if any(isinstance(e, dict) and e.get("event_id") in affected_events for e in doc["evidence"]):
                affected_memories.add(memory_id)
        refs, head_affected = [], False
        head = self._head(scope)
        for digest, blob in self._impact_rows(
                "SELECT snapshot_sha256, snapshot_bytes FROM adoption_snapshots ORDER BY snapshot_sha256",
                (), MAX_IMPACT_SNAPSHOTS):
            data = _as_bytes(blob)
            if sha256_hex(data) != digest:
                raise StorageError("adoption.snapshot_corrupt", "snapshot hash mismatch")
            snapshot = parse_canonical("candidate_snapshot", data)
            if snapshot["scope"] != scope:
                continue
            for member in snapshot["members"]:
                if member["memory_id"] in affected_memories:
                    refs.append((digest, member["memory_id"]))
                    if len(refs) > MAX_IMPACT_REFS:
                        raise StorageError("forget.impact_too_large", "too many snapshot references")
                    head_affected = head_affected or (digest == head and member["state"] == "active")
        ordered = {
            "scope": scope, "policy_revision": policy.revision,
            "targets": {f: list(targets[f]) for f in _TARGET_FIELDS},
            "new_exclusions": {f: list(new_exclusions[f]) for f in _TARGET_FIELDS},
            "affected_event_ids": sorted(affected_events),
            "affected_memory_ids": sorted(affected_memories),
            "snapshot_refs": [list(r) for r in sorted(refs)],
            "current_head_snapshot_sha256": head, "current_head_affected": head_affected,
        }
        return ForgetImpact(
            scope=dict(scope), policy_revision=policy.revision,
            targets={f: tuple(targets[f]) for f in _TARGET_FIELDS}, new_exclusions=new_exclusions,
            affected_event_ids=tuple(ordered["affected_event_ids"]),
            affected_memory_ids=tuple(ordered["affected_memory_ids"]),
            snapshot_refs=tuple(sorted(refs)), current_head_affected=head_affected,
            impact_sha256=sha256_hex(canonical_json(ordered)),
        )

    def plan_forget_impact(
        self, *, scope: dict[str, str], memory_ids=(), event_ids=(), root_ids=(),
    ) -> ForgetImpact:
        """Read-only deterministic dry run: one deferred read transaction, no write, no ID consumed.
        Same arguments on the same state give the same ``impact_sha256``."""
        # Reuse the request contract for scope/ID/count validation; the placeholder IDs are discarded.
        data, _ = build_forget_request(
            operation_id="dry-run", run_id="dry-run", scope=scope, expected_policy_revision=1,
            memory_ids=memory_ids, event_ids=event_ids, root_ids=root_ids)
        doc = parse_canonical("forget_request", data)
        db = self._db()
        if db.in_transaction:
            raise StorageError("forget.nested_transaction", "planning needs its own read transaction")
        try:
            db.execute("BEGIN")
        except sqlite3.Error as exc:
            raise StorageError("storage.busy_or_locked", f"cannot start read transaction ({exc})") from None
        try:
            _check_v3(db)
            return self._forget_plan(doc["scope"], doc["targets"], self.current_policy())
        finally:
            _rollback(db)  # read-only: nothing to commit

    def commit_forget(self, *, request_bytes: object, control: ControlBoundary) -> AdoptionResult:
        """Audited LOGICAL forgetting. In ONE BEGIN IMMEDIATE transaction: operation lookup (exact
        replay returns the historical receipt and never re-applies anything) -> policy revision CAS
        -> exact-scope target resolution -> impact plan -> next policy revision that is the current
        one plus the new exclusions (every other value preserved, stamped by the explicitly supplied
        ``control`` boundary) -> immutable request/receipt journal row. Any failure leaves no
        policy revision and no journal row. Head and history are never rewritten; the new
        exclusions apply to retrieval, adoption and rollback at once. NOT physical deletion."""
        self._require_writable()
        if not isinstance(control, ControlBoundary):
            raise TypeError("control must be a ControlBoundary")
        req = parse_canonical("forget_request", request_bytes)
        req_data = bytes(request_bytes)
        req_sha = sha256_hex(req_data)
        try:
            with self._immediate():
                _check_v3(self._db())
                prior = self._resolve_operation(req["operation_id"])
                if prior:
                    if prior[0] != req_sha or prior[1] != req_data:
                        raise ConflictError("adoption.operation_conflict", "operation ID already has different content")
                    return prior[2]  # historical receipt; no policy write or present-time assertion
                now = self._now()
                policy = self.current_policy()
                if policy.revision != req["expected_policy_revision"]:
                    raise ConflictError("adoption.policy_conflict", "current policy revision differs")
                impact = self._forget_plan(req["scope"], req["targets"], policy)
                if not any(impact.new_exclusions.values()):
                    raise ContractViolation("forget.no_new_exclusion", "every target is already excluded")
                body = copy.deepcopy({k: policy.document[k] for k in
                                      ("authorizations", "accepted_purposes", "accepted_partitions")})
                body["exclusions"] = {  # additive: existing entries and order are kept
                    f: list(policy.document["exclusions"][f]) + list(impact.new_exclusions[f])
                    for f in _TARGET_FIELDS
                }
                state = self._set_policy_locked(control, body, policy.revision, now)
                rec_bytes, rec_sha = build_forget_receipt(
                    req_data, resulting_policy_revision=state.revision,
                    resulting_policy_sha256=state.sha256, added_exclusions=impact.new_exclusions,
                    impact_sha256=impact.impact_sha256,
                    affected_event_count=len(impact.affected_event_ids),
                    affected_memory_count=len(impact.affected_memory_ids),
                    affected_snapshot_ref_count=len(impact.snapshot_refs), now=now,
                )
                self._db().execute(
                    "INSERT INTO adoption_journal VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (req["operation_id"], req_sha, req_data, b"", b"", rec_sha, rec_bytes),
                )
                result = AdoptionResult("created", rec_bytes, rec_sha)
            return result  # returned only after COMMIT
        except sqlite3.Error as exc:
            raise StorageError("storage.write_failed", f"forget rolled back ({exc})") from None
