"""Gate 2A local, append-only evidence store on standard-library SQLite.

What it is: a small library for atomically capturing one event (raw bytes), its
original source (raw bytes) and a validated provenance record, with replay
idempotency, conflicting-id rejection, independent-root deduplication and a
read-only integrity recheck. See docs/decisions/0004-local-evidence-store.md for the
durability and trust limits.

What it is not: no memory promotion, active pointer, retrieval, verifier or
evaluation integration, scheduling, model calls, CLI, or migration. A stored record
is evidence of what a *simulated* capture boundary accepted, not authenticated
truth. Anyone who can write the database file can rewrite rows and hashes together;
the recheck detects inconsistent edits, not a coordinated forgery.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from agent_sleep_lab.diagnostics import ascii_safe
from agent_sleep_lab.provenance import (
    INDEPENDENT_ORIGINS,
    MAX_EVENT_BYTES,
    MAX_SOURCE_BYTES,
    BoundaryViolation,
    CaptureBoundary,
    ConflictError,
    ContractViolation,
    LineageViolation,
    NotFoundError,
    StorageError,
    canonical_json,
    check_event_bytes,
    parse_timestamp,
    sha256_hex,
    stamp_claim,
    validate_record,
    violation_for,
)
from agent_sleep_lab.strictjson import StrictJSONError, loads_strict_bytes

APPLICATION_ID = 0x41534C47  # "ASLG": refuse to adopt arbitrary SQLite files
STORE_USER_VERSION = 1

_DDL: tuple[str, ...] = (
    """CREATE TABLE evidence (
        event_id TEXT PRIMARY KEY NOT NULL,
        project TEXT NOT NULL,
        task_family TEXT NOT NULL,
        event_sha256 TEXT NOT NULL,
        event_bytes BLOB NOT NULL,
        provenance_sha256 TEXT NOT NULL,
        provenance_bytes BLOB NOT NULL,
        source_sha256 TEXT NOT NULL,
        root_id TEXT NOT NULL,
        independent_root INTEGER NOT NULL CHECK (independent_root IN (0, 1))
    )""",
    # One independent root per (scope, raw source bytes): a repeat is not new evidence.
    "CREATE UNIQUE INDEX evidence_one_root_per_source "
    "ON evidence (project, task_family, source_sha256) WHERE independent_root = 1",
    """CREATE TABLE source_blobs (
        event_id TEXT PRIMARY KEY NOT NULL REFERENCES evidence (event_id),
        source_bytes BLOB NOT NULL
    )""",
    """CREATE TABLE lineage (
        child_id TEXT NOT NULL REFERENCES evidence (event_id),
        parent_id TEXT NOT NULL REFERENCES evidence (event_id),
        PRIMARY KEY (child_id, parent_id)
    )""",
) + tuple(
    f"CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table} "
    f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
    for table in ("evidence", "source_blobs", "lineage")
    for op in ("UPDATE", "DELETE")
)


@dataclass(frozen=True)
class CaptureResult:
    status: str  # "created" or "replayed"
    event_id: str
    event_sha256: str
    source_sha256: str
    provenance_sha256: str
    root_id: str
    independent_root: bool


@dataclass(frozen=True)
class StoredEvidence:
    """What the store holds. ``get`` does not verify; call ``verify`` for that."""

    event_id: str
    project: str
    task_family: str
    event_bytes: bytes
    source_bytes: bytes
    provenance: dict[str, Any]
    event_sha256: str
    source_sha256: str
    provenance_sha256: str
    root_id: str
    independent_root: bool


@dataclass(frozen=True)
class IntegrityReport:
    event_id: str
    ok: bool
    failures: tuple[str, ...]


# --------------------------------------------------------------------------- plumbing


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_bytes(value: object) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    return str(value).encode("utf-8", "replace")  # tampered column type: will not hash-match


def _require_bytes(prefix: str, value: object, limit: int) -> bytes:
    if type(value) not in (bytes, bytearray):
        raise ContractViolation(f"{prefix}.not_bytes", f"{prefix}_bytes must be bytes")
    data = bytes(value)  # type: ignore[arg-type]
    if not data:
        raise ContractViolation(f"{prefix}.empty", f"{prefix}_bytes must not be empty")
    if len(data) > limit:
        raise ContractViolation(f"{prefix}.too_large", f"{prefix}_bytes exceeds {limit} bytes")
    return data


def _check_path(path: object) -> Path:
    try:
        text = os.fspath(path)  # type: ignore[arg-type]
    except TypeError:
        raise StorageError("storage.bad_path", "path must be a str or PathLike") from None
    if isinstance(text, bytes):
        text = os.fsdecode(text)
    if not text or "\x00" in text or text == ":memory:" or text.startswith("file:"):
        raise StorageError("storage.bad_path", "path must name a file location")
    return Path(text)


def _connect(path: object, *, readonly: bool, timeout: float) -> sqlite3.Connection:
    target = _check_path(path)
    try:
        if readonly:
            uri = target.resolve().as_uri() + "?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=timeout, isolation_level=None)
        else:
            conn = sqlite3.connect(str(target), timeout=timeout, isolation_level=None)
    except sqlite3.Error as exc:
        raise StorageError("storage.open_failed", f"cannot open database ({exc})") from None
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        if readonly:
            conn.execute("PRAGMA query_only = ON")
        else:
            conn.execute("PRAGMA synchronous = FULL")
            conn.execute("PRAGMA fullfsync = ON")  # macOS: flush the drive cache; no-op elsewhere
    except sqlite3.Error as exc:
        conn.close()
        raise StorageError("storage.open_failed", f"cannot configure database ({exc})") from None
    return conn


def _header(conn: sqlite3.Connection) -> tuple[int, int, int]:
    app_id = conn.execute("PRAGMA application_id").fetchall()[0][0]
    version = conn.execute("PRAGMA user_version").fetchall()[0][0]
    objects = conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchall()[0][0]
    return app_id, version, objects


def _check_header(conn: sqlite3.Connection) -> None:
    try:
        app_id, version, _ = _header(conn)
    except sqlite3.Error as exc:
        raise StorageError("storage.open_failed", f"cannot read database ({exc})") from None
    if app_id != APPLICATION_ID or version != STORE_USER_VERSION:
        raise StorageError(
            "storage.unknown_database", "not an evidence store of a supported version"
        )


def _initialize(conn: sqlite3.Connection) -> None:
    """Create the schema in one IMMEDIATE transaction, or verify an existing store."""
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as exc:
        raise StorageError("storage.busy_or_locked", f"cannot start transaction ({exc})") from None
    try:
        app_id, version, objects = _header(conn)
        if app_id == 0 and version == 0 and objects == 0:
            for statement in _DDL:
                conn.execute(statement)
            conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")
            conn.execute(f"PRAGMA user_version = {STORE_USER_VERSION}")
        elif app_id != APPLICATION_ID or version != STORE_USER_VERSION:
            raise StorageError(
                "storage.unknown_database", "not an evidence store of a supported version"
            )
        conn.execute("COMMIT")
    except sqlite3.Error as exc:
        _rollback(conn)
        raise StorageError("storage.init_failed", f"cannot initialise store ({exc})") from None
    except BaseException:
        _rollback(conn)
        raise


def _rollback(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("ROLLBACK")
    except sqlite3.Error:
        pass


# --------------------------------------------------------------------------- reading


class _Reader:
    """Read-only lookup and integrity recheck shared by both store classes."""

    def __init__(self, conn: sqlite3.Connection, clock: Callable[[], datetime] | None) -> None:
        self._conn: sqlite3.Connection | None = conn
        self._clock = clock or _utc_now

    def close(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            conn.close()

    def __enter__(self) -> "_Reader":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            raise StorageError("storage.closed", "store is closed")
        return self._conn

    def _rows(self, sql: str, params: tuple = ()) -> list[tuple]:
        # fetchall() always runs the statement to completion so no read lock lingers.
        db = self._db()
        try:
            return db.execute(sql, params).fetchall()
        except sqlite3.Error as exc:
            raise StorageError("storage.read_failed", f"read failed ({exc})") from None

    def _now(self, override: datetime | None = None) -> datetime:
        value = override if override is not None else self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("clock must provide a timezone-aware datetime")
        return value

    def _load_raw(self, event_id: object) -> dict[str, Any] | None:
        if type(event_id) is not str:
            raise ContractViolation("lookup.bad_id", "event_id must be a string")
        rows = self._rows(
            "SELECT project, task_family, event_sha256, event_bytes, provenance_sha256, "
            "provenance_bytes, source_sha256, root_id, independent_root "
            "FROM evidence WHERE event_id = ?",
            (event_id,),
        )
        if not rows:
            return None
        row = rows[0]
        blobs = self._rows("SELECT source_bytes FROM source_blobs WHERE event_id = ?", (event_id,))
        return {
            "project": row[0],
            "task_family": row[1],
            "event_sha256": row[2],
            "event_bytes": _as_bytes(row[3]),
            "provenance_sha256": row[4],
            "provenance_bytes": _as_bytes(row[5]),
            "source_sha256": row[6],
            "root_id": row[7],
            "independent_root": bool(row[8]),
            "source_bytes": _as_bytes(blobs[0][0]) if blobs else None,
        }

    def get(self, event_id: str) -> StoredEvidence:
        raw = self._load_raw(event_id)
        if raw is None:
            raise NotFoundError(
                "lookup.not_found", f"no evidence stored for {ascii_safe(event_id, 80)}"
            )
        if raw["source_bytes"] is None:
            raise StorageError("storage.source_missing", "original source bytes are missing")
        try:
            provenance = loads_strict_bytes(raw["provenance_bytes"])
        except StrictJSONError:
            raise StorageError("storage.corrupt_provenance", "stored provenance is unreadable") from None
        if not isinstance(provenance, dict):
            raise StorageError("storage.corrupt_provenance", "stored provenance is not an object")
        return StoredEvidence(
            event_id=event_id,
            project=raw["project"],
            task_family=raw["task_family"],
            event_bytes=raw["event_bytes"],
            source_bytes=raw["source_bytes"],
            provenance=provenance,
            event_sha256=raw["event_sha256"],
            source_sha256=raw["source_sha256"],
            provenance_sha256=raw["provenance_sha256"],
            root_id=raw["root_id"],
            independent_root=raw["independent_root"],
        )

    def list_event_ids(self) -> list[str]:
        return [row[0] for row in self._rows("SELECT event_id FROM evidence ORDER BY event_id")]

    def independent_root_count(self, project: str, task_family: str) -> int:
        """Distinct independent roots in a scope. Generated repeats never add to this."""
        rows = self._rows(
            "SELECT COUNT(*) FROM evidence "
            "WHERE independent_root = 1 AND project = ? AND task_family = ?",
            (project, task_family),
        )
        return int(rows[0][0])

    def verify(self, event_id: str, *, now: datetime | None = None) -> IntegrityReport:
        """Recheck hashes, contracts, scope, lineage and expiry. Never writes."""
        raw = self._load_raw(event_id)
        if raw is None:
            raise NotFoundError(
                "lookup.not_found", f"no evidence stored for {ascii_safe(event_id, 80)}"
            )
        current = self._now(now)
        failures: set[str] = set()
        if sha256_hex(raw["event_bytes"]) != raw["event_sha256"]:
            failures.add("event.hash_mismatch")
        if sha256_hex(raw["provenance_bytes"]) != raw["provenance_sha256"]:
            failures.add("provenance.hash_mismatch")
        if raw["source_bytes"] is None:
            failures.add("source.missing")
        elif sha256_hex(raw["source_bytes"]) != raw["source_sha256"]:
            failures.add("source.hash_mismatch")
        record: Any
        try:
            record = loads_strict_bytes(raw["provenance_bytes"])
        except StrictJSONError:
            failures.add("provenance.unparseable")
            record = None
        if record is not None:
            problems = validate_record(record)
            if problems:
                failures.update(f"provenance.{p.code}" for p in problems)
            else:
                self._verify_record(event_id, raw, record, current, failures)
        return IntegrityReport(event_id, not failures, tuple(sorted(failures)))

    def verify_all(self, *, now: datetime | None = None) -> list[IntegrityReport]:
        return [self.verify(event_id, now=now) for event_id in self.list_event_ids()]

    def _verify_record(
        self,
        event_id: str,
        raw: dict[str, Any],
        record: dict[str, Any],
        current: datetime,
        failures: set[str],
    ) -> None:
        if record["event"]["event_id"] != event_id:
            failures.add("provenance.event_id_mismatch")
        if record["event"]["sha256"] != raw["event_sha256"] or record["event"][
            "sha256"
        ] != sha256_hex(raw["event_bytes"]):
            failures.add("event.hash_mismatch")
        declared = record["source"]["sha256"]
        if declared != raw["source_sha256"] or (
            raw["source_bytes"] is not None and declared != sha256_hex(raw["source_bytes"])
        ):
            failures.add("source.hash_mismatch")
        failures.update(p.code for p in check_event_bytes(raw["event_bytes"], record))

        scope = record["event"]["scope"]
        if (raw["project"], raw["task_family"]) != (scope["project"], scope["task_family"]):
            failures.add("scope.mismatch")
        lineage = record["lineage"]
        independent = record["origin"] in INDEPENDENT_ORIGINS
        if raw["root_id"] != lineage["original_root_id"] or raw["independent_root"] != independent:
            failures.add("lineage.root_mismatch")
        expires = record["authorization"]["expires_at"]
        if expires is not None and current >= parse_timestamp(expires):
            failures.add("authorization.expired")

        declared_parents = set(lineage["derived_from"])
        stored_parents = {r[0] for r in self._parents(event_id)}
        if stored_parents != declared_parents:
            failures.add("lineage.mismatch")
        for parent in stored_parents | declared_parents:
            rows = self._rows(
                "SELECT root_id, project, task_family FROM evidence WHERE event_id = ?",
                (parent,),
            )
            if not rows:
                failures.add("lineage.unknown_parent")
                continue
            if rows[0][0] != lineage["original_root_id"]:
                failures.add("lineage.root_mismatch")
            if (rows[0][1], rows[0][2]) != (raw["project"], raw["task_family"]):
                failures.add("lineage.scope_mismatch")
        if self._has_cycle(event_id):
            failures.add("lineage.cycle")

    def _parents(self, event_id: str) -> list[tuple]:
        return self._rows(
            "SELECT parent_id FROM lineage WHERE child_id = ? ORDER BY parent_id", (event_id,)
        )

    def _has_cycle(self, start: str) -> bool:
        """Iterative DFS over parent edges; True if a cycle is reachable from ``start``."""
        state: dict[str, int] = {start: 1}  # 1 = on current path, 2 = fully explored
        stack: list[tuple[str, Iterator[tuple]]] = [(start, iter(self._parents(start)))]
        while stack:
            node, parents = stack[-1]
            descended = False
            for (parent,) in parents:
                seen = state.get(parent, 0)
                if seen == 1:
                    return True
                if seen == 0:
                    state[parent] = 1
                    stack.append((parent, iter(self._parents(parent))))
                    descended = True
                    break
            if not descended:
                state[node] = 2
                stack.pop()
        return False


class ReadOnlyEvidenceStore(_Reader):
    """Opens an existing store with SQLite ``mode=ro`` and ``query_only``; no capture API."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        clock: Callable[[], datetime] | None = None,
        busy_timeout: float = 5.0,
    ) -> None:
        conn = _connect(path, readonly=True, timeout=busy_timeout)
        try:
            _check_header(conn)
        except BaseException:
            conn.close()
            raise
        super().__init__(conn, clock)


# --------------------------------------------------------------------------- writing


class EvidenceStore(_Reader):
    """Writer. Create one per thread/process; connections are never shared."""

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
            _initialize(conn)
        except BaseException:
            conn.close()
            raise
        super().__init__(conn, clock)
        self._boundary = boundary

    def _require_writable(self) -> None:
        if getattr(self, "read_only", False):
            raise StorageError("storage.read_only", "store opened read-only")

    @contextmanager
    def _immediate(self) -> Iterator[None]:
        self._require_writable()
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
        except sqlite3.Error as exc:
            raise StorageError("storage.busy_or_locked", f"cannot start transaction ({exc})") from None
        try:
            yield
        except BaseException:
            _rollback(db)
            raise
        else:
            try:
                db.execute("COMMIT")
            except sqlite3.Error as exc:
                _rollback(db)
                raise StorageError("storage.commit_failed", f"commit failed ({exc})") from None

    def capture(
        self, *, event_bytes: bytes, source_bytes: bytes, claim: dict[str, Any]
    ) -> CaptureResult:
        """Atomically store event, source and provenance, or change nothing.

        Returns ``created`` for new evidence or ``replayed`` when byte-identical
        content (including the boundary's adapter identity) is already stored.
        """
        self._require_writable()
        self._db()
        event_data = _require_bytes("event", event_bytes, MAX_EVENT_BYTES)
        source_data = _require_bytes("source", source_bytes, MAX_SOURCE_BYTES)
        record = stamp_claim(claim, self._boundary)
        problems = validate_record(record)
        if problems:
            raise violation_for(problems[0])
        now = self._now()
        self._check_boundary(record, now)
        problems = check_event_bytes(event_data, record)
        if problems:
            raise violation_for(problems[0])
        if sha256_hex(event_data) != record["event"]["sha256"]:
            raise ContractViolation("event.hash_mismatch", "declared event sha256 differs from bytes")
        if sha256_hex(source_data) != record["source"]["sha256"]:
            raise ContractViolation(
                "source.hash_mismatch", "declared source sha256 differs from bytes"
            )
        provenance_bytes = canonical_json(record)
        try:
            with self._immediate():
                return self._capture_locked(record, event_data, source_data, provenance_bytes, now)
        except sqlite3.Error as exc:
            raise StorageError("storage.write_failed", f"write failed, rolled back ({exc})") from None

    def _check_boundary(self, record: dict[str, Any], now: datetime) -> None:
        boundary = self._boundary
        if record["origin"] not in boundary.allowed_origins:
            raise BoundaryViolation(
                "boundary.origin_not_allowed", "origin is not permitted by this capture boundary"
            )
        scope = record["event"]["scope"]
        if boundary.allowed_scopes is not None and (
            scope["project"],
            scope["task_family"],
        ) not in boundary.allowed_scopes:
            raise BoundaryViolation(
                "boundary.scope_not_allowed", "scope is not permitted by this capture boundary"
            )
        auth = record["authorization"]
        current = boundary.authorizations.get(auth["ref"])
        if current is None:
            raise BoundaryViolation("boundary.authorization_unknown", "authorization is unknown")
        if auth["revision"] != current:
            raise BoundaryViolation(
                "boundary.authorization_stale_revision",
                "authorization revision is not the current one",
            )
        if auth["expires_at"] is not None and now >= parse_timestamp(auth["expires_at"]):
            raise BoundaryViolation("boundary.authorization_expired", "authorization has expired")

    def _check_ancestry(self, record: dict[str, Any], now: datetime) -> None:
        """Inside the capture transaction: every transitive ancestor, including the
        original root, must pass the full integrity recheck (hashes, source bytes
        present, unexpired), carry the boundary's *current* authorization revision,
        and sit in the same evaluation partition. Otherwise nothing is added."""
        lineage = record["lineage"]
        if not lineage["derived_from"]:
            return
        pending = list(lineage["derived_from"]) + [lineage["original_root_id"]]
        seen: set[str] = set()
        while pending:
            ancestor = pending.pop()
            if ancestor in seen:
                continue
            seen.add(ancestor)
            if self._load_raw(ancestor) is None:
                raise LineageViolation(
                    "lineage.unknown_parent", f"unknown ancestor {ascii_safe(ancestor, 80)}"
                )
            report = self.verify(ancestor, now=now)
            if not report.ok:
                if report.failures == ("authorization.expired",):
                    raise BoundaryViolation(
                        "boundary.ancestor_authorization_expired",
                        f"ancestor {ascii_safe(ancestor, 80)} authorization has expired",
                    )
                raise StorageError(
                    "storage.ancestor_corrupt",
                    f"ancestor {ascii_safe(ancestor, 80)} fails integrity: "
                    + ", ".join(report.failures),
                )
            ancestor_record = self.get(ancestor).provenance
            auth = ancestor_record["authorization"]
            if self._boundary.authorizations.get(auth["ref"]) != auth["revision"]:
                raise BoundaryViolation(
                    "boundary.ancestor_authorization_stale",
                    f"ancestor {ascii_safe(ancestor, 80)} authorization revision is not current",
                )
            if ancestor_record["partition"]["evaluation"] != record["partition"]["evaluation"]:
                raise LineageViolation(
                    "lineage.partition_mismatch",
                    "ancestor is in a different evaluation partition",
                )
            pending.extend(row[0] for row in self._parents(ancestor))

    def _capture_locked(
        self,
        record: dict[str, Any],
        event_bytes: bytes,
        source_bytes: bytes,
        provenance_bytes: bytes,
        now: datetime,
    ) -> CaptureResult:
        db = self._db()
        event = record["event"]
        lineage = record["lineage"]
        event_id = event["event_id"]
        project = event["scope"]["project"]
        family = event["scope"]["task_family"]
        independent = record["origin"] in INDEPENDENT_ORIGINS
        base: dict[str, Any] = {
            "event_id": event_id,
            "event_sha256": event["sha256"],
            "source_sha256": record["source"]["sha256"],
            "provenance_sha256": sha256_hex(provenance_bytes),
            "root_id": lineage["original_root_id"],
            "independent_root": independent,
        }

        existing = self._rows(
            "SELECT event_bytes, provenance_bytes FROM evidence WHERE event_id = ?", (event_id,)
        )
        if existing:
            blobs = self._rows(
                "SELECT source_bytes FROM source_blobs WHERE event_id = ?", (event_id,)
            )
            differing = []
            if _as_bytes(existing[0][0]) != event_bytes:
                differing.append("event")
            if _as_bytes(existing[0][1]) != provenance_bytes:
                differing.append("provenance")
            if not blobs or _as_bytes(blobs[0][0]) != source_bytes:
                differing.append("source")
            if differing:
                raise ConflictError(
                    "conflict.event_id",
                    "event_id is already stored with different " + "/".join(differing) + " content",
                )
            # Byte-identical is not enough: a corrupt existing record must not look successful.
            report = self.verify(event_id, now=now)
            if not report.ok:
                raise StorageError(
                    "storage.corrupt_existing",
                    "existing record fails integrity: " + ", ".join(report.failures),
                )
            return CaptureResult("replayed", **base)

        if independent:
            duplicate = self._rows(
                "SELECT event_id FROM evidence WHERE independent_root = 1 "
                "AND project = ? AND task_family = ? AND source_sha256 = ?",
                (project, family, base["source_sha256"]),
            )
            if duplicate:
                raise ConflictError(
                    "conflict.duplicate_root_source",
                    "these source bytes already back independent root "
                    f"{ascii_safe(duplicate[0][0], 80)} in this scope; a repeat is not a new root",
                )

        for parent in lineage["derived_from"]:
            rows = self._rows(
                "SELECT project, task_family, root_id, provenance_bytes "
                "FROM evidence WHERE event_id = ?",
                (parent,),
            )
            if not rows:
                raise LineageViolation(
                    "lineage.unknown_parent", f"unknown parent {ascii_safe(parent, 80)}"
                )
            parent_project, parent_family, parent_root, parent_prov = rows[0]
            if (parent_project, parent_family) != (project, family):
                raise LineageViolation("lineage.scope_mismatch", "parent is in a different scope")
            if parent_root != lineage["original_root_id"]:
                raise LineageViolation(
                    "lineage.root_mismatch", "original_root_id is not the parent's root"
                )
        self._check_ancestry(record, now)

        db.execute(
            "INSERT INTO evidence (event_id, project, task_family, event_sha256, event_bytes, "
            "provenance_sha256, provenance_bytes, source_sha256, root_id, independent_root) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                project,
                family,
                base["event_sha256"],
                event_bytes,
                base["provenance_sha256"],
                provenance_bytes,
                base["source_sha256"],
                base["root_id"],
                1 if independent else 0,
            ),
        )
        db.execute(
            "INSERT INTO source_blobs (event_id, source_bytes) VALUES (?, ?)",
            (event_id, source_bytes),
        )
        for parent in sorted(lineage["derived_from"]):
            db.execute(
                "INSERT INTO lineage (child_id, parent_id) VALUES (?, ?)", (event_id, parent)
            )
        return CaptureResult("created", **base)


__all__ = [
    "APPLICATION_ID",
    "STORE_USER_VERSION",
    "CaptureResult",
    "EvidenceStore",
    "IntegrityReport",
    "ReadOnlyEvidenceStore",
    "StoredEvidence",
]
