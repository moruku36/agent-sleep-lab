"""Gate 2A provenance contract: strict sidecar schema, capture boundary, record checks.

Scope: a versioned provenance sidecar for one captured event, validated against the
packaged local schema ``provenance.schema.json`` plus cross-field rules the schema
cannot express (origin/root rules, identifier forms, timestamp order, synthetic-only).

Trust limits, stated plainly:

* :class:`CaptureBoundary` is a **local boundary simulation**, not authentication.
  It is configured separately from the data being captured and stamps the adapter
  identity and version onto the record. Nothing proves that the calling code really
  is that adapter; there are no signatures, keys, or OS-level isolation.
* A SHA-256 value is an identity of bytes, not proof of truth, consent, or origin.
* Nothing here reads provenance out of event text. Event bytes are only checked for
  consistency (id, scope, synthetic flag) against the separately supplied claim.
* This module does not touch the filesystem or the network.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from types import MappingProxyType
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from agent_sleep_lab.diagnostics import ascii_safe
from agent_sleep_lab.strictjson import StrictJSONError, loads_strict_bytes
from agent_sleep_lab.validation import (
    SchemaLoadError,
    _describe,
    _pointer,
    build_validator,
    schema_bytes,
    validate_bytes,
)

PROVENANCE_SCHEMA_FILE = "provenance.schema.json"
PROVENANCE_VERSION = "agent-sleep-provenance/1"

MAX_EVENT_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_SCHEMA_PROBLEMS = 10

# Origins that may be an independent root of evidence. These labels are asserted by
# the configured capture boundary; this slice does not authenticate them.
INDEPENDENT_ORIGINS = frozenset({"user_correction", "tool_observation", "external_document"})
# Generated material can help discover candidates but is never an independent root.
GENERATED_ORIGINS = frozenset(
    {"model_derived_summary", "recall", "rem", "diary", "generated_answer"}
)
ORIGINS = INDEPENDENT_ORIGINS | GENERATED_ORIGINS

# Python's ``$`` also matches before a trailing newline, so every pattern is
# re-checked with ``fullmatch`` in code.
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_SHA_RE = re.compile(r"[0-9a-f]{64}")


# --------------------------------------------------------------------------- errors


class EvidenceError(Exception):
    """Base error with a stable machine-readable ``code`` and an ASCII-safe message."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = ascii_safe(message)
        super().__init__(f"{code}: {self.message}")


class ContractViolation(EvidenceError):
    """Input does not satisfy the strict provenance/event contract."""


class BoundaryViolation(EvidenceError):
    """Input is outside what the configured capture boundary permits (incl. non-synthetic)."""


class LineageViolation(EvidenceError):
    """Unknown, cyclic, or inconsistent lineage, or a generated record posing as a root."""


class ConflictError(EvidenceError):
    """An identity (event_id or independent root) is already taken by different content."""


class NotFoundError(EvidenceError):
    """The requested event is not stored."""


class StorageError(EvidenceError):
    """The storage layer failed or the database is not a recognised store."""


@dataclass(frozen=True)
class Problem:
    code: str
    message: str


def violation_for(problem: Problem) -> EvidenceError:
    """Map a problem code prefix to the exception class that reports it."""
    prefix = problem.code.split(".", 1)[0]
    cls: type[EvidenceError] = {
        "synthetic": BoundaryViolation,
        "boundary": BoundaryViolation,
        "lineage": LineageViolation,
    }.get(prefix, ContractViolation)
    return cls(problem.code, problem.message)


# --------------------------------------------------------------------------- helpers


def sha256_hex(data: bytes) -> str:
    """SHA-256 of the exact raw bytes (no normalisation of any kind)."""
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    """Deterministic ASCII JSON used for provenance identity and replay comparison."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def parse_timestamp(text: str) -> datetime:
    """Parse an RFC 3339 timestamp; the offset is mandatory. Raises ``ValueError``."""
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp has no UTC offset")
    return parsed


@lru_cache(maxsize=None)
def _validator() -> tuple[Any, str]:
    try:
        schema = loads_strict_bytes(schema_bytes(PROVENANCE_SCHEMA_FILE))
    except StrictJSONError as exc:
        raise SchemaLoadError("packaged provenance schema is malformed") from exc
    if not isinstance(schema, dict):
        raise SchemaLoadError("packaged provenance schema is not an object")
    version = schema["properties"]["schema_version"]["const"]
    return build_validator(schema, Draft202012Validator), version


# --------------------------------------------------------------------------- boundary


@dataclass(frozen=True, eq=False)
class CaptureBoundary:
    """Separately configured capture boundary (local simulation, not authentication).

    ``adapter_id``/``adapter_version`` are fixed here and stamped onto every record the
    store captures; a submitted claim may not carry its own adapter identity.
    ``authorizations`` maps an authorization reference to its single current revision.
    ``allowed_scopes`` is ``None`` (any scope) or a set of ``(project, task_family)``.
    """

    adapter_id: str
    adapter_version: str
    allowed_origins: frozenset[str]
    authorizations: Mapping[str, int]
    allowed_scopes: frozenset[tuple[str, str]] | None = None

    def __post_init__(self) -> None:
        if not (isinstance(self.adapter_id, str) and _TOKEN_RE.fullmatch(self.adapter_id)):
            raise ValueError("adapter_id must match [a-z0-9][a-z0-9._-]{0,63}")
        if not (
            isinstance(self.adapter_version, str) and _TOKEN_RE.fullmatch(self.adapter_version)
        ):
            raise ValueError("adapter_version must match [a-z0-9][a-z0-9._-]{0,63}")
        origins = frozenset(self.allowed_origins)
        if not origins <= ORIGINS:
            raise ValueError("allowed_origins contains an unknown origin")
        auths = dict(self.authorizations)
        for ref, revision in auths.items():
            if not (isinstance(ref, str) and _ID_RE.fullmatch(ref)):
                raise ValueError("authorization reference has an invalid form")
            if type(revision) is not int or revision < 0:
                raise ValueError("authorization revision must be a non-negative integer")
        scopes = None
        if self.allowed_scopes is not None:
            scopes = frozenset(self.allowed_scopes)
            for item in scopes:
                if not (
                    isinstance(item, tuple)
                    and len(item) == 2
                    and all(isinstance(x, str) and _ID_RE.fullmatch(x) for x in item)
                ):
                    raise ValueError("allowed_scopes entries must be (project, task_family)")
        object.__setattr__(self, "allowed_origins", origins)
        object.__setattr__(self, "authorizations", MappingProxyType(auths))
        object.__setattr__(self, "allowed_scopes", scopes)


def stamp_claim(claim: object, boundary: CaptureBoundary) -> dict[str, Any]:
    """Return the full record: the submitted claim plus the boundary's adapter identity."""
    if not isinstance(claim, dict):
        raise ContractViolation("contract.not_object", "claim must be a JSON object")
    if "adapter" in claim:
        raise ContractViolation(
            "contract.adapter_in_claim",
            "adapter identity comes only from the configured capture boundary",
        )
    try:
        canonical_json(claim)
    except (TypeError, ValueError, RecursionError):
        raise ContractViolation("contract.not_json", "claim is not plain JSON data") from None
    record = copy.deepcopy(claim)
    record["adapter"] = {
        "adapter_id": boundary.adapter_id,
        "adapter_version": boundary.adapter_version,
    }
    return record


# --------------------------------------------------------------------------- checks


def validate_record(record: object) -> list[Problem]:
    """Schema plus cross-field checks for one full provenance record. Pure; no I/O."""
    validator, version = _validator()
    if not isinstance(record, dict):
        return [Problem("contract.not_object", "record must be a JSON object")]
    if "schema_version" in record:
        found = record["schema_version"]
        if not (type(found) is str and found == version):
            return [
                Problem(
                    "contract.unknown_version",
                    f"unsupported schema_version; expected {version!r}",
                )
            ]
    errors = sorted(
        validator.iter_errors(record), key=lambda e: (list(map(str, e.path)), e.validator)
    )
    if errors:
        found_problems = []
        for error in errors[:MAX_SCHEMA_PROBLEMS]:
            code, message = _describe(error)
            found_problems.append(Problem(code, f"{_pointer(error.absolute_path)}: {message}"))
        return found_problems

    problems: list[Problem] = []
    event = record["event"]
    source = record["source"]
    lineage = record["lineage"]
    auth = record["authorization"]
    event_id = event["event_id"]
    derived = lineage["derived_from"]

    named_values = [
        ("event.event_id", event_id, _ID_RE),
        ("event.scope.project", event["scope"]["project"], _ID_RE),
        ("event.scope.task_family", event["scope"]["task_family"], _ID_RE),
        ("event.sha256", event["sha256"], _SHA_RE),
        ("adapter.adapter_id", record["adapter"]["adapter_id"], _TOKEN_RE),
        ("adapter.adapter_version", record["adapter"]["adapter_version"], _TOKEN_RE),
        ("source.source_id", source["source_id"], _ID_RE),
        ("source.sha256", source["sha256"], _SHA_RE),
        ("lineage.original_root_id", lineage["original_root_id"], _ID_RE),
        ("authorization.ref", auth["ref"], _ID_RE),
    ]
    named_values += [(f"lineage.derived_from[{i}]", v, _ID_RE) for i, v in enumerate(derived)]
    for name, value, pattern in named_values:
        if not pattern.fullmatch(value):
            problems.append(Problem("contract.bad_identifier", f"{name} has an invalid form"))
    if not source["locator"].isprintable():
        problems.append(Problem("contract.bad_locator", "source.locator has control characters"))

    if record["partition"]["synthetic"] is not True:
        problems.append(
            Problem("synthetic.required", "only synthetic input is accepted in this slice")
        )

    stamps: dict[str, datetime] = {}
    for name, value in (
        ("observed_at", record["observed_at"]),
        ("captured_at", record["captured_at"]),
        ("authorization.expires_at", auth["expires_at"]),
    ):
        if value is None:
            continue
        try:
            stamps[name] = parse_timestamp(value)
        except ValueError:
            problems.append(Problem("time.unparseable", f"{name} is not a usable timestamp"))
    if "observed_at" in stamps and "captured_at" in stamps:
        if stamps["observed_at"] > stamps["captured_at"]:
            problems.append(Problem("time.order", "observed_at is later than captured_at"))

    if auth["retention"] == "until_expiry" and auth["expires_at"] is None:
        problems.append(
            Problem("authorization.expiry_required", "retention until_expiry needs expires_at")
        )

    origin = record["origin"]
    root = lineage["original_root_id"]
    if event_id in derived:
        problems.append(Problem("lineage.cycle", "an event cannot be derived from itself"))
    if origin in INDEPENDENT_ORIGINS:
        if derived or root != event_id:
            problems.append(
                Problem(
                    "lineage.root_mismatch",
                    "an independent origin must be its own root with empty derived_from",
                )
            )
    elif not derived or root == event_id:
        problems.append(
            Problem(
                "lineage.generated_root",
                "generated origins (summary/recall/REM/diary/answer) cannot be independent "
                "roots; they need derived_from and a different original_root_id",
            )
        )
    return problems


def check_event_bytes(event_bytes: bytes, record: dict[str, Any]) -> list[Problem]:
    """Consistency of raw event bytes with the (already schema-valid) record.

    Reads only ``event_id``, ``scope`` and ``synthetic`` from the event, and only to
    compare them with the separately supplied claim. Nothing in the event text can
    set or raise the origin, adapter, authorization or lineage.
    """
    result = validate_bytes("events", event_bytes)
    if not result.valid or result.records != 1:
        return [
            Problem(
                "event.invalid_contract",
                "event bytes are not exactly one valid Gate 1 event record",
            )
        ]
    try:
        event = loads_strict_bytes(event_bytes)
    except StrictJSONError:
        return [Problem("event.invalid_contract", "event bytes are not strict JSON")]
    if not isinstance(event, dict):
        return [Problem("event.invalid_contract", "event bytes are not a JSON object")]
    problems: list[Problem] = []
    if event.get("event_id") != record["event"]["event_id"]:
        problems.append(Problem("event.id_mismatch", "event_id differs from the claim"))
    if event.get("scope") != record["event"]["scope"]:
        problems.append(Problem("scope.mismatch", "event scope differs from the claim"))
    if event.get("synthetic") is not True:
        problems.append(
            Problem("synthetic.required", "event is not marked synthetic; failing closed")
        )
    return problems
