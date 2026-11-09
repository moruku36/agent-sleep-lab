"""Gate 2B (first slice) explicit store extension: registered receipts and persisted policy.

Design (see docs/decisions/0005-runtime-store-extension.md and docs/gate-2b.md):

* The Gate 2A evidence store is ``user_version=1``. This module defines ``user_version=2``:
  the *same* tables, triggers and bytes plus two append-only extension tables
  (``receipts``, ``policy_revisions``). A v2 file is created fresh by ``RuntimeStore`` or by the
  explicit ``upgrade_store_v1_to_v2`` call. ``RuntimeStore`` refuses a v1 file
  (``storage.upgrade_required``); the v1 classes refuse a v2 file (``storage.unknown_database``).
  Nothing is migrated implicitly and no provenance is ever created or rewritten.
* Everything that adoption will need lives on ONE SQLite connection: evidence recheck
  (``verify`` and ancestry reads), receipt resolution, current policy and exclusions. They only
  use ``self._conn``, so the future adoption writer can run them inside its single
  ``BEGIN IMMEDIATE`` transaction (``EvidenceStore._immediate``). A second connection or a read-only
  store is *not* part of that transaction and must never be described as atomic with it.
* Receipts are registered through boundary-specific methods and are resolved later only by
  ``(receipt_id, exact sha256)``. A proposal-supplied receipt object or identity is never trusted.
* The policy has its own expected-current compare-and-swap. Revisions are monotonic (enforced in
  Python and by a SQL trigger), persisted in the file, and never reset by constructing or
  reopening a store. A missing or malformed policy fails closed.

PENDING (not implemented here): operation manifests, candidate construction, active pointer,
committed-operation receipts, the adoption transaction, concurrency/process-crash fixtures.
All boundaries are local simulations; this is not authentication.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Callable

from agent_sleep_lab.diagnostics import ascii_safe
from agent_sleep_lab.evidence_store import (
    APPLICATION_ID,
    _DDL,
    EvidenceStore,
    _as_bytes,
    _connect,
    _header,
    _Reader,
    _rollback,
)
from agent_sleep_lab.provenance import (
    CaptureBoundary,
    ConflictError,
    ContractViolation,
    NotFoundError,
    StorageError,
    parse_timestamp,
    sha256_hex,
)
from agent_sleep_lab.runtime_artifacts import (
    ControlBoundary,
    EvaluatorBoundary,
    VerifierBoundary,
    encode_artifact,
    parse_artifact_bytes,
)

RUNTIME_USER_VERSION = 2
MAX_CLOSURE_NODES = 1024

_EXTENSION_DDL: tuple[str, ...] = (
    """CREATE TABLE receipts (
        kind TEXT NOT NULL CHECK (kind IN ('verification', 'evaluation')),
        receipt_id TEXT NOT NULL,
        receipt_sha256 TEXT NOT NULL,
        receipt_bytes BLOB NOT NULL,
        boundary_id TEXT NOT NULL,
        boundary_version TEXT NOT NULL,
        PRIMARY KEY (kind, receipt_id)
    )""",
    """CREATE TABLE policy_revisions (
        revision INTEGER PRIMARY KEY NOT NULL CHECK (revision >= 1),
        policy_sha256 TEXT NOT NULL,
        policy_bytes BLOB NOT NULL
    )""",
    # Monotonic by construction: an insert must be exactly current + 1 (no gaps, no rewind).
    "CREATE TRIGGER policy_revisions_monotonic BEFORE INSERT ON policy_revisions "
    "WHEN NEW.revision != (SELECT COALESCE(MAX(revision), 0) + 1 FROM policy_revisions) "
    "BEGIN SELECT RAISE(ABORT, 'policy revision must follow the current revision'); END",
) + tuple(
    f"CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table} "
    f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
    for table in ("receipts", "policy_revisions")
    for op in ("UPDATE", "DELETE")
)


@dataclass(frozen=True)
class RegisteredReceipt:
    status: str  # "created" or "replayed"
    kind: str
    receipt_id: str
    receipt_sha256: str


@dataclass(frozen=True)
class PolicyState:
    revision: int
    sha256: str
    document: dict[str, Any]


# --------------------------------------------------------------------------- header / schema


def _schema_rows(conn: sqlite3.Connection) -> tuple[tuple, ...]:
    return tuple(conn.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE name NOT GLOB 'sqlite_*' ORDER BY type, name"
    ).fetchall())


@lru_cache(maxsize=2)
def _expected_schema(version: int) -> tuple[tuple, ...]:
    # Schema reference only: this temporary connection never reads runtime data or
    # participates in policy/evidence decisions. Those use the store connection.
    conn = sqlite3.connect(":memory:")
    try:
        for statement in _DDL + (_EXTENSION_DDL if version == 2 else ()):
            conn.execute(statement)
        return _schema_rows(conn)
    finally:
        conn.close()


def _check_supported_schema(conn: sqlite3.Connection, version: int) -> None:
    if _schema_rows(conn) != _expected_schema(version):
        raise StorageError(
            "storage.unknown_database", "store schema differs from the supported definition"
        )


def _begin(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as exc:
        raise StorageError("storage.busy_or_locked", f"cannot start transaction ({exc})") from None


def _initialize_v2(conn: sqlite3.Connection) -> None:
    _begin(conn)
    try:
        app_id, version, objects = _header(conn)
        if app_id == 0 and version == 0 and objects == 0:
            for statement in _DDL + _EXTENSION_DDL:
                conn.execute(statement)
            conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")
            conn.execute(f"PRAGMA user_version = {RUNTIME_USER_VERSION}")
        elif app_id == APPLICATION_ID and version == 1:
            raise StorageError(
                "storage.upgrade_required",
                "evidence store is version 1; call upgrade_store_v1_to_v2 explicitly",
            )
        elif app_id != APPLICATION_ID or version != RUNTIME_USER_VERSION:
            raise StorageError(
                "storage.unknown_database", "not a runtime store of a supported version"
            )
        _check_supported_schema(conn, 2)
        conn.execute("COMMIT")
    except sqlite3.Error as exc:
        _rollback(conn)
        raise StorageError("storage.init_failed", f"cannot initialise store ({exc})") from None
    except BaseException:
        _rollback(conn)
        raise


def upgrade_store_v1_to_v2(path: str | os.PathLike[str], *, busy_timeout: float = 5.0) -> None:
    """Explicit, atomic v1 -> v2 extension. Adds empty extension tables only.

    Refuses anything that is not a recognisable Gate 2A store, and an already-upgraded file.
    Evidence rows and bytes are not read, rewritten or reinterpreted.
    """
    conn = _connect(path, readonly=False, timeout=busy_timeout)
    try:
        _begin(conn)
        try:
            app_id, version, objects = _header(conn)
            if app_id != APPLICATION_ID or version != 1:
                raise StorageError(
                    "storage.unknown_database", "only a version 1 evidence store can be upgraded"
                )
            _check_supported_schema(conn, 1)
            for statement in _EXTENSION_DDL:
                conn.execute(statement)
            _check_supported_schema(conn, 2)
            conn.execute(f"PRAGMA user_version = {RUNTIME_USER_VERSION}")
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            _rollback(conn)
            raise StorageError("storage.init_failed", f"cannot upgrade store ({exc})") from None
        except BaseException:
            _rollback(conn)
            raise
    finally:
        conn.close()


def _without_issue_time(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k != "issued_at"}


# --------------------------------------------------------------------------- store


class RuntimeStore(EvidenceStore):
    """Evidence store (v2 format) plus registered receipts and the persisted control policy.

    Inherits ``capture``/``get``/``verify`` unchanged. One connection per instance.
    """

    def __init__(
        self,
        path: str | os.PathLike[str],
        boundary: CaptureBoundary,
        *,
        clock: Callable[[], datetime] | None = None,
        busy_timeout: float = 5.0,
    ) -> None:
        if not isinstance(boundary, CaptureBoundary):
            raise TypeError("boundary must be a CaptureBoundary")
        conn = _connect(path, readonly=False, timeout=busy_timeout)
        try:
            _initialize_v2(conn)
        except BaseException:
            conn.close()
            raise
        _Reader.__init__(self, conn, clock)  # deliberately not EvidenceStore.__init__ (v1 guard)
        self._boundary = boundary

    @property
    def in_transaction(self) -> bool:
        """True while this store's single connection has an open transaction."""
        return self._db().in_transaction

    # ---- receipts

    def register_verification(self, boundary: VerifierBoundary, claim: object) -> RegisteredReceipt:
        """Register a verification receipt issued through ``boundary``.

        The boundary stamps identity/time; the receipt's evidence hashes and scope are rechecked
        against the stored evidence in the registering transaction.
        """
        if not isinstance(boundary, VerifierBoundary):
            raise TypeError("boundary must be a VerifierBoundary")
        now = self._now()
        doc = boundary.stamp(claim, now)
        data = encode_artifact("verification", doc)
        try:
            with self._immediate():
                self._bind_evidence_locked(doc, now)
                return self._insert_receipt_locked("verification", doc, data)
        except sqlite3.Error as exc:
            raise StorageError("storage.write_failed", f"write failed, rolled back ({exc})") from None

    def register_evaluation(self, boundary: EvaluatorBoundary, claim: object) -> RegisteredReceipt:
        """Register an evaluation receipt issued through ``boundary`` (immutable fixture record).

        Binding to a candidate snapshot is checked by the (pending) adoption writer.
        """
        if not isinstance(boundary, EvaluatorBoundary):
            raise TypeError("boundary must be an EvaluatorBoundary")
        now = self._now()
        doc = boundary.stamp(claim, now)
        data = encode_artifact("evaluation", doc)
        try:
            with self._immediate():
                return self._insert_receipt_locked("evaluation", doc, data)
        except sqlite3.Error as exc:
            raise StorageError("storage.write_failed", f"write failed, rolled back ({exc})") from None

    def _bind_evidence_locked(self, doc: dict[str, Any], now: datetime) -> None:
        scope = (doc["scope"]["project"], doc["scope"]["task_family"])
        for ref in doc["evidence"]:
            event_id = ref["event_id"]
            raw = self._load_raw(event_id)
            if raw is None:
                raise NotFoundError(
                    "receipt.evidence_unknown", f"unknown evidence {ascii_safe(event_id, 80)}"
                )
            report = self.verify(event_id, now=now)
            if not report.ok:
                raise StorageError(
                    "receipt.evidence_integrity",
                    f"evidence {ascii_safe(event_id, 80)} fails integrity: "
                    + ", ".join(report.failures),
                )
            if (
                raw["event_sha256"] != ref["event_sha256"]
                or raw["source_sha256"] != ref["source_sha256"]
                or raw["provenance_sha256"] != ref["provenance_sha256"]
            ):
                raise ContractViolation(
                    "receipt.evidence_hash_mismatch", "receipt hashes differ from stored evidence"
                )
            if (raw["project"], raw["task_family"]) != scope:
                raise ContractViolation(
                    "receipt.scope_mismatch", "receipt scope differs from the evidence scope"
                )
            if self.get(event_id).provenance["partition"]["synthetic"] is not True:
                raise ContractViolation("receipt.not_synthetic", "evidence is not synthetic")

    def _insert_receipt_locked(
        self, kind: str, doc: dict[str, Any], data: bytes
    ) -> RegisteredReceipt:
        receipt_id = doc["receipt_id"]
        rows = self._rows(
            "SELECT receipt_sha256, receipt_bytes, boundary_id, boundary_version "
            "FROM receipts WHERE kind = ? AND receipt_id = ?",
            (kind, receipt_id),
        )
        if rows:
            stored = _as_bytes(rows[0][1])
            if sha256_hex(stored) != rows[0][0]:
                raise StorageError("receipt.stored_corrupt", "stored receipt fails its hash")
            try:
                existing = parse_artifact_bytes(kind, stored)
            except ContractViolation:
                raise StorageError("receipt.stored_corrupt", "stored receipt is invalid") from None
            if existing["receipt_id"] != receipt_id or existing["boundary"] != {
                "boundary_id": rows[0][2], "boundary_version": rows[0][3],
            }:
                raise StorageError("receipt.stored_corrupt", "stored receipt columns disagree")
            if _without_issue_time(existing) == _without_issue_time(doc):
                return RegisteredReceipt("replayed", kind, receipt_id, rows[0][0])
            raise ConflictError(
                "receipt.id_conflict", "a different receipt is already registered under this id"
            )
        digest = sha256_hex(data)
        self._db().execute(
            "INSERT INTO receipts (kind, receipt_id, receipt_sha256, receipt_bytes, "
            "boundary_id, boundary_version) VALUES (?, ?, ?, ?, ?, ?)",
            (
                kind,
                receipt_id,
                digest,
                data,
                doc["boundary"]["boundary_id"],
                doc["boundary"]["boundary_version"],
            ),
        )
        return RegisteredReceipt("created", kind, receipt_id, digest)

    def resolve_receipt(self, kind: str, receipt_id: object, receipt_sha256: object) -> dict[str, Any]:
        """Resolve a registered receipt by ID and exact hash. Reads only; no proposal object is used."""
        if kind not in ("verification", "evaluation"):
            raise ContractViolation("receipt.unknown_kind", "unknown receipt kind")
        if type(receipt_id) is not str or type(receipt_sha256) is not str:
            raise ContractViolation("receipt.bad_reference", "receipt reference must be strings")
        rows = self._rows(
            "SELECT receipt_sha256, receipt_bytes, boundary_id, boundary_version "
            "FROM receipts WHERE kind = ? AND receipt_id = ?",
            (kind, receipt_id),
        )
        if not rows:
            raise NotFoundError("receipt.not_found", "no such registered receipt")
        stored_sha, stored_bytes, boundary_id, boundary_version = rows[0]
        if stored_sha != receipt_sha256:
            raise ContractViolation(
                "receipt.hash_mismatch", "referenced hash differs from the registered receipt"
            )
        data = _as_bytes(stored_bytes)
        if sha256_hex(data) != stored_sha:
            raise StorageError("receipt.stored_corrupt", "stored receipt fails its hash")
        try:
            doc = parse_artifact_bytes(kind, data)
        except ContractViolation:
            raise StorageError("receipt.stored_corrupt", "stored receipt is invalid") from None
        if doc["receipt_id"] != receipt_id or doc["boundary"] != {
            "boundary_id": boundary_id,
            "boundary_version": boundary_version,
        }:
            raise StorageError("receipt.stored_corrupt", "stored receipt columns disagree")
        return doc

    # ---- policy

    def current_policy(self) -> PolicyState:
        """The latest policy after verifying the whole revision chain. Fails closed."""
        rows = self._rows(
            "SELECT revision, policy_sha256, policy_bytes FROM policy_revisions ORDER BY revision"
        )
        if not rows:
            raise StorageError("policy.missing", "no control policy has been set")
        previous: dict[str, Any] | None = None
        state: PolicyState | None = None
        for index, (revision, digest, blob) in enumerate(rows, start=1):
            data = _as_bytes(blob)
            if revision != index or sha256_hex(data) != digest:
                raise StorageError("policy.corrupt", "policy revision chain fails verification")
            try:
                doc = parse_artifact_bytes("policy", data)
            except ContractViolation:
                raise StorageError("policy.corrupt", "stored policy is invalid") from None
            if doc["revision"] != revision:
                raise StorageError("policy.corrupt", "policy revision disagrees with its row")
            if previous is not None and _exclusion_removed(previous, doc):
                raise StorageError("policy.corrupt", "an exclusion was removed between revisions")
            previous = doc
            state = PolicyState(revision, digest, doc)
        assert state is not None
        return state

    def set_policy(
        self, boundary: ControlBoundary, body: object, *, expected_revision: int
    ) -> PolicyState:
        """Publish the next policy revision iff the current revision equals ``expected_revision``.

        ``0`` means "no policy yet". The store, not the caller, assigns ``expected + 1``. Exclusions
        can only grow (non-resurrection); a revision that drops one is refused.
        """
        if not isinstance(boundary, ControlBoundary):
            raise TypeError("boundary must be a ControlBoundary")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ContractViolation("policy.bad_expected_revision", "expected_revision must be >= 0")
        now = self._now()
        try:
            with self._immediate():
                current = int(self._rows("SELECT COALESCE(MAX(revision), 0) FROM policy_revisions")[0][0])
                if current != expected_revision:
                    raise ConflictError(
                        "policy.revision_conflict",
                        f"current policy revision is {current}, expected {expected_revision}",
                    )
                previous = self.current_policy().document if current else None
                doc = boundary.build_policy(body, revision=current + 1, now=now)
                data = encode_artifact("policy", doc)
                if previous is not None and _exclusion_removed(previous, doc):
                    raise ContractViolation(
                        "policy.exclusion_removed", "a policy revision may not drop an exclusion"
                    )
                digest = sha256_hex(data)
                self._db().execute(
                    "INSERT INTO policy_revisions (revision, policy_sha256, policy_bytes) "
                    "VALUES (?, ?, ?)",
                    (current + 1, digest, data),
                )
                return PolicyState(current + 1, digest, doc)
        except sqlite3.Error as exc:
            raise StorageError("storage.write_failed", f"write failed, rolled back ({exc})") from None

    # ---- eligibility (reads only; designed to run inside the future adoption transaction)

    def eligibility_failures(
        self,
        *,
        memory_id: str,
        memory_sha256: str,
        scope: tuple[str, str],
        receipt_id: str,
        receipt_sha256: str,
        verifier: VerifierBoundary,
        now: datetime | None = None,
    ) -> tuple[str, ...]:
        """Sorted failure codes; an empty tuple means the memory is currently eligible.

        Rechecks, on this one connection: the current policy (missing/corrupt raises), the
        registered receipt (by ID + exact hash, from the configured verifier, confirmed, unexpired,
        bound to this memory hash and scope), and for every receipt evidence item plus all of its
        ancestors and root: full integrity, exact hashes, current authorization revision, accepted
        purpose/partition and the exclusion ledger. Store read errors raise instead of passing.
        """
        if not isinstance(verifier, VerifierBoundary):
            raise TypeError("verifier must be a VerifierBoundary")
        current = self._now(now)
        policy = self.current_policy().document
        failures: set[str] = set()
        try:
            receipt = self.resolve_receipt("verification", receipt_id, receipt_sha256)
        except (NotFoundError, ContractViolation) as exc:
            return (f"receipt.unresolved.{exc.code}",)  # type: ignore[attr-defined]

        if receipt["boundary"] != {
            "boundary_id": verifier.boundary_id,
            "boundary_version": verifier.boundary_version,
        } or (receipt["method"]["name"], receipt["method"]["version"]) not in verifier.methods:
            failures.add("receipt.untrusted_boundary")
        if receipt["outcome"] != "confirmed":
            failures.add("receipt.outcome_not_confirmed")
        if receipt["expires_at"] is not None and current >= parse_timestamp(receipt["expires_at"]):
            failures.add("receipt.expired")
        if parse_timestamp(receipt["issued_at"]) > current:
            failures.add("receipt.issued_in_future")
        if receipt["memory_id"] != memory_id or receipt["memory_sha256"] != memory_sha256:
            failures.add("receipt.memory_mismatch")
        if (receipt["scope"]["project"], receipt["scope"]["task_family"]) != tuple(scope):
            failures.add("receipt.scope_mismatch")
        if memory_id in policy["exclusions"]["memory_ids"]:
            failures.add("policy.memory_excluded")

        for ref in receipt["evidence"]:
            self._evidence_failures(ref, policy, current, failures)
        return tuple(sorted(failures))

    def _evidence_failures(
        self, ref: dict[str, str], policy: dict[str, Any], current: datetime, failures: set[str]
    ) -> None:
        raw = self._load_raw(ref["event_id"])
        if raw is None:
            failures.add("evidence.unknown")
            return
        if (
            raw["event_sha256"] != ref["event_sha256"]
            or raw["source_sha256"] != ref["source_sha256"]
            or raw["provenance_sha256"] != ref["provenance_sha256"]
        ):
            failures.add("evidence.receipt_hash_mismatch")
        authorizations = {a["ref"]: a["revision"] for a in policy["authorizations"]}
        excluded = policy["exclusions"]
        pending = [ref["event_id"], raw["root_id"]]
        seen: set[str] = set()
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            if len(seen) >= MAX_CLOSURE_NODES:
                failures.add("evidence.closure_too_large")
                return
            seen.add(node)
            row = self._load_raw(node)
            if row is None:
                failures.add("evidence.unknown_ancestor")
                continue
            if node in excluded["event_ids"]:
                failures.add("policy.event_excluded")
            if row["root_id"] in excluded["root_ids"] or node in excluded["root_ids"]:
                failures.add("policy.root_excluded")
            report = self.verify(node, now=current)
            failures.update(f"evidence.{code}" for code in report.failures)
            if not report.ok:
                pending.extend(r[0] for r in self._parents(node))
                continue
            provenance = self.get(node).provenance
            auth = provenance["authorization"]
            if auth["ref"] not in authorizations:
                failures.add("policy.authorization_unknown")
            elif authorizations[auth["ref"]] != auth["revision"]:
                failures.add("policy.authorization_stale")
            if auth["purpose"] not in policy["accepted_purposes"]:
                failures.add("policy.purpose_not_accepted")
            if provenance["partition"]["evaluation"] not in policy["accepted_partitions"]:
                failures.add("policy.partition_not_accepted")
            if provenance["partition"]["synthetic"] is not True:
                failures.add("evidence.not_synthetic")
            pending.extend(r[0] for r in self._parents(node))


def _exclusion_removed(previous: dict[str, Any], new: dict[str, Any]) -> bool:
    return any(
        not set(previous["exclusions"][field]) <= set(new["exclusions"][field])
        for field in ("memory_ids", "event_ids", "root_ids")
    )
