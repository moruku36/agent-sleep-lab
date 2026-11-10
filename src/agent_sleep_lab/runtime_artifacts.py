"""Gate 2B runtime artifact contracts and simulated verifier/evaluator/control boundaries.

What it is: strict, versioned, locally packaged contracts for verification receipts,
evaluation receipts and the current control policy, plus three *separately configured*
boundary objects that stamp a fixed identity/version onto the artifacts they issue.

What it is not: authentication. A boundary is a local simulation (like ``CaptureBoundary``).
Anyone who can construct a boundary object or write the database file can forge a receipt
or a policy; hashes detect inconsistent edits, not coordinated forgery. A proposal can never
carry its own boundary identity, receipt object or policy: it may only *reference* a
registered receipt by ID and exact hash (see ``runtime_store``).

Also includes pure operation/source/candidate/request/receipt-format contracts for the
candidate-planning slice (docs/gate-2b-candidates.md). Formatting a receipt does not commit
anything. The separate synthetic adoption writer implements transactional journal/head updates.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator

from agent_sleep_lab.provenance import (
    BoundaryViolation,
    ContractViolation,
    Problem,
    canonical_json,
    parse_timestamp,
    sha256_hex,
)
from agent_sleep_lab.strictjson import StrictJSONError, loads_strict_bytes
from agent_sleep_lab.validation import SchemaLoadError, build_validator, schema_bytes

VERIFICATION_VERSION = "agent-sleep-verification-receipt/1"
EVALUATION_VERSION = "agent-sleep-evaluation-receipt/1"
POLICY_VERSION = "agent-sleep-control-policy/1"

# kind -> (schema_version, packaged schema file)
ARTIFACT_KINDS: dict[str, tuple[str, str]] = {
    "verification": (VERIFICATION_VERSION, "verification-receipt.schema.json"),
    "evaluation": (EVALUATION_VERSION, "evaluation-receipt.schema.json"),
    "policy": (POLICY_VERSION, "control-policy.schema.json"),
    "operation_manifest": ("agent-sleep-operation-manifest/1", "operation-manifest.schema.json"),
    "source_manifest": ("agent-sleep-source-manifest/1", "source-manifest.schema.json"),
    "candidate_snapshot": ("agent-sleep-candidate-snapshot/1", "candidate-snapshot.schema.json"),
    "adoption_request": ("agent-sleep-adoption-request/1", "adoption-request.schema.json"),
    "committed_receipt": (
        "agent-sleep-committed-operation-receipt/1",
        "committed-operation-receipt.schema.json",
    ),
    # Gate 3 control recovery. Separate kinds: adoption v1/v2 artifacts are untouched.
    "rollback_request": ("agent-sleep-rollback-request/1", "rollback-request.schema.json"),
    "rollback_receipt": ("agent-sleep-rollback-receipt/1", "rollback-receipt.schema.json"),
    # Gate 3 audited LOGICAL forgetting (exclusion additions only; not physical erasure).
    "forget_request": ("agent-sleep-forget-request/1", "forget-request.schema.json"),
    "forget_receipt": ("agent-sleep-forget-receipt/1", "forget-receipt.schema.json"),
}

# Fixed allowlist: artifact identifiers never become caller-selected paths or URLs.
_VERSIONED_ADOPTION = {
    "adoption_request": {
        "agent-sleep-adoption-request/1": "adoption-request.schema.json",
        "agent-sleep-adoption-request/2": "adoption-request-v2.schema.json",
    },
    "committed_receipt": {
        "agent-sleep-committed-operation-receipt/1": "committed-operation-receipt.schema.json",
        "agent-sleep-committed-operation-receipt/2": "committed-operation-receipt-v2.schema.json",
    },
}

# operation -> which of (memory_id, memory_sha256, target_id, receipt) must be present
_OPERATION_SHAPES: dict[str, tuple[bool, bool, bool, bool]] = {
    "add": (True, True, False, True),
    "supersede": (True, True, True, True),
    "mark_stale": (False, False, True, False),
    "reject": (True, True, False, False),
    "defer": (True, True, False, False),
}


def operation_sort_key(op: dict[str, Any]) -> tuple[str, str, str]:
    """Canonical operation order. The manifest must already be listed in this order."""
    return (op["op"], op["memory_id"] or "", op["target_id"] or "")


def _adoption_problems(kind: str, doc: dict[str, Any], problems: list[Problem]) -> None:
    def bad(code: str, message: str) -> None:
        problems.append(Problem(code, message))

    if kind == "operation_manifest":
        ops = doc["operations"]
        keys = [operation_sort_key(o) for o in ops]
        if keys != sorted(keys) or len(set(keys)) != len(keys):
            bad("contract.operations_not_canonical", "operations must be unique and in canonical order")
        for o in ops:
            present = (
                o["memory_id"] is not None,
                o["memory_sha256"] is not None,
                o["target_id"] is not None,
                o["receipt"] is not None,
            )
            if present != _OPERATION_SHAPES[o["op"]]:
                bad("contract.operation_shape", f"{o['op']} operation has the wrong fields")
            if o["target_id"] is not None and o["target_id"] == o["memory_id"]:
                bad("contract.operation_self_target", "an operation may not target its own memory")
    elif kind == "source_manifest":
        ids = [e["memory_id"] for e in doc["entries"]]
        if ids != sorted(ids) or len(set(ids)) != len(ids):
            bad("contract.entries_not_canonical", "entries must be unique and sorted by memory_id")
        for entry in doc["entries"]:
            events = [e["event_id"] for e in entry["evidence"]]
            if len(set(events)) != len(events):
                bad("contract.duplicate_evidence", "an entry repeats an evidence event_id")
    elif kind == "candidate_snapshot":
        members = doc["members"]
        ids = [m["memory_id"] for m in members]
        if ids != sorted(ids) or len(set(ids)) != len(ids):
            bad("contract.members_not_canonical", "members must be unique and sorted by memory_id")
            return
        by = {m["memory_id"]: m for m in members}
        for m in members:
            successor = m["superseded_by_id"]
            if (m["state"] == "superseded") != (successor is not None):
                bad("contract.supersession_state", "superseded_by_id is set exactly when superseded")
            elif successor is not None and (successor == m["memory_id"] or successor not in by):
                bad("contract.supersession_target", "superseded_by_id must name another member")
        for start in by:
            seen = {start}
            current = by[start]["superseded_by_id"]
            while current is not None and current in by:
                if current in seen:
                    bad("contract.supersession_cycle", "supersession forms a cycle")
                    break
                seen.add(current)
                current = by[current]["superseded_by_id"]
    elif kind == "adoption_request":
        has_candidate = doc["candidate_snapshot_sha256"] is not None
        if has_candidate and doc["evaluation_receipt"] is None:
            bad("contract.evaluation_required", "an active change needs an evaluation receipt")
        if not has_candidate and doc["evaluation_receipt"] is not None:
            bad("contract.unexpected_evaluation", "an audit-only request carries no evaluation receipt")
    elif kind == "committed_receipt":
        parent, snapshot = doc["parent_snapshot_sha256"], doc["snapshot_sha256"]
        if doc["outcome"] == "adopted":
            if snapshot is None or snapshot == parent:
                bad("contract.adopted_snapshot", "an adopted outcome needs a new snapshot")
            if doc["evaluation_receipt"] is None:
                bad("contract.evaluation_required", "an adopted outcome needs an evaluation receipt")
        elif snapshot != parent or doc["evaluation_receipt"] is not None:
            bad("contract.audit_only_changed", "an audit-only outcome leaves the snapshot unchanged")
    elif kind == "rollback_request":
        if doc["target_snapshot_sha256"] == doc["expected_head_snapshot_sha256"]:
            bad("contract.rollback_noop", "rollback target must differ from the expected head")
    elif kind == "rollback_receipt":
        if doc["snapshot_sha256"] == doc["parent_snapshot_sha256"]:
            bad("contract.rollback_noop", "a rollback receipt must restore a different snapshot")
    elif kind in ("forget_request", "forget_receipt"):
        lists = doc["targets"] if kind == "forget_request" else doc["added_exclusions"]
        total = 0
        for field in ("memory_ids", "event_ids", "root_ids"):
            if lists[field] != sorted(lists[field]):
                bad("contract.forget_not_canonical", f"{field} must be sorted")
            total += len(lists[field])
        if total < 1 or total > 32:
            bad("contract.forget_target_count", "between 1 and 32 explicit targets are required")
        if (kind == "forget_receipt"
                and doc["resulting_policy_revision"] != doc["expected_policy_revision"] + 1):
            bad("contract.forget_revision", "a forget receipt advances the policy by exactly one")

MAX_ARTIFACT_BYTES = 256 * 1024

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_SHA_RE = re.compile(r"[0-9a-f]{64}")
_TS_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_PURPOSE_RE = re.compile(r"[a-z][a-z0-9_]{0,63}")
_PARTITION_RE = re.compile(r"[a-z][a-z0-9_]{0,31}")
_BOUNDARY_TOKEN_KEYS = frozenset({"boundary_id", "boundary_version"})


@lru_cache(maxsize=None)
def _validator(kind: str, version: str | None = None) -> Any:
    if kind not in ARTIFACT_KINDS:
        raise ContractViolation("artifact.unknown_kind", "unknown artifact kind")
    expected_version, filename = ARTIFACT_KINDS[kind]
    if kind in _VERSIONED_ADOPTION and version is not None:
        if version not in _VERSIONED_ADOPTION[kind]:
            raise ContractViolation("artifact.unsupported_version", "unsupported adoption artifact version")
        expected_version, filename = version, _VERSIONED_ADOPTION[kind][version]
    try:
        schema = loads_strict_bytes(schema_bytes(filename))
    except StrictJSONError as exc:
        raise SchemaLoadError("packaged artifact schema is malformed") from exc
    if not isinstance(schema, dict):
        raise SchemaLoadError("packaged artifact schema is not an object")
    if schema["properties"]["schema_version"]["const"] != expected_version:
        raise SchemaLoadError("packaged artifact schema version disagrees with code")
    return build_validator(schema, Draft202012Validator)


_TOKEN_KEYS = _BOUNDARY_TOKEN_KEYS | {"name", "version"}
_ID_NAMED_KEYS = frozenset({"ref", "project", "task_family"})


def _string_ok(key: str, item: str) -> bool:
    if key == "accepted_purposes":
        return bool(_PURPOSE_RE.fullmatch(item))
    if key == "accepted_partitions":
        return bool(_PARTITION_RE.fullmatch(item))
    if key in _TOKEN_KEYS:
        return bool(_TOKEN_RE.fullmatch(item))
    if key.endswith("_id") or key.endswith("_ids") or key in _ID_NAMED_KEYS:
        return bool(_ID_RE.fullmatch(item))
    if key.endswith("_sha256"):
        return bool(_SHA_RE.fullmatch(item))
    if key.endswith("_at"):
        if not _TS_RE.fullmatch(item):
            return False
        try:
            parse_timestamp(item)
        except ValueError:
            return False
    return True


def _format_walk(value: Any, path: str, problems: list[Problem], key: str = "") -> None:
    """``fullmatch`` guard: JSON-schema ``pattern`` is a search and ``$`` admits a trailing
    newline, so identifier/hash/time forms are re-checked exactly in code."""
    if isinstance(value, dict):
        for name, item in value.items():
            _format_walk(item, f"{path}/{name}", problems, name)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _format_walk(item, f"{path}/{index}", problems, key)
    elif isinstance(value, str) and not _string_ok(key, value):
        problems.append(Problem("contract.bad_format", f"{path} has an invalid form"))


def validate_artifact(kind: str, doc: object) -> list[Problem]:
    """Schema plus cross-field checks for one full artifact. Pure; no I/O."""
    if kind not in ARTIFACT_KINDS:
        raise ContractViolation("artifact.unknown_kind", "unknown artifact kind")
    if not isinstance(doc, dict):
        return [Problem("contract.not_object", "artifact must be a JSON object")]
    version = None
    if kind in _VERSIONED_ADOPTION:
        version = doc.get("schema_version")
        if type(version) is not str or version not in _VERSIONED_ADOPTION[kind]:
            return [Problem("artifact.unsupported_version", "unsupported adoption artifact version")]
    validator = _validator(kind, version)
    problems: list[Problem] = []
    for error in sorted(validator.iter_errors(doc), key=lambda e: list(map(str, e.path)))[:10]:
        where = "/" + "/".join(str(p) for p in error.absolute_path)
        problems.append(Problem("contract.schema", f"{where or '/'}: {error.message[:120]}"))
    if problems:
        return problems
    _format_walk(doc, "", problems)
    if problems:
        return problems
    if kind == "verification":
        ids = [e["event_id"] for e in doc["evidence"]]
        if len(set(ids)) != len(ids):
            problems.append(Problem("contract.duplicate_evidence", "evidence event_ids repeat"))
        if len(ids) > doc["limits"]["max_evidence"]:
            problems.append(Problem("contract.limit_exceeded", "evidence exceeds receipt limit"))
    elif kind == "evaluation":
        done = doc["completeness"]
        if done["completed"] > done["planned"]:
            problems.append(Problem("contract.completeness", "completed exceeds planned"))
        if doc["result"] == "passed" and done["completed"] != done["planned"]:
            problems.append(Problem("contract.completeness", "a passed result must be complete"))
    elif kind == "policy":
        refs = [a["ref"] for a in doc["authorizations"]]
        if len(set(refs)) != len(refs):
            problems.append(Problem("contract.duplicate_authorization", "authorization refs repeat"))
        for field in ("accepted_purposes", "accepted_partitions"):
            if len(set(doc[field])) != len(doc[field]):
                problems.append(Problem("contract.duplicate_entry", f"{field} has duplicates"))
        for field, values in doc["exclusions"].items():
            if len(set(values)) != len(values):
                problems.append(Problem("contract.duplicate_entry", f"exclusions.{field} repeats"))
    _adoption_problems(kind, doc, problems)
    if kind in ("verification", "evaluation") and doc["expires_at"] is not None:
        if parse_timestamp(doc["expires_at"]) <= parse_timestamp(doc["issued_at"]):
            problems.append(Problem("contract.expiry_order", "expires_at must follow issued_at"))
    return problems


def parse_artifact_bytes(kind: str, data: object) -> dict[str, Any]:
    """Strictly parse stored/registered bytes. Raises ``ContractViolation``."""
    if type(data) not in (bytes, bytearray):
        raise ContractViolation("artifact.not_bytes", "artifact bytes must be bytes")
    raw = bytes(data)
    if not raw or len(raw) > MAX_ARTIFACT_BYTES:
        raise ContractViolation("artifact.size", "artifact size is out of bounds")
    try:
        doc = loads_strict_bytes(raw)
    except StrictJSONError as exc:
        raise ContractViolation("artifact.unparseable", "artifact is not strict JSON") from exc
    problems = validate_artifact(kind, doc)
    if problems:
        raise ContractViolation(problems[0].code, problems[0].message)
    return doc  # type: ignore[return-value]


def encode_artifact(kind: str, doc: dict[str, Any]) -> bytes:
    """Validate and return the canonical (internal, NOT RFC 8785) bytes of an artifact."""
    problems = validate_artifact(kind, doc)
    if problems:
        raise ContractViolation(problems[0].code, problems[0].message)
    data = canonical_json(doc)
    if len(data) > MAX_ARTIFACT_BYTES:
        raise ContractViolation("artifact.size", "artifact size is out of bounds")
    return data


def _iso(moment: datetime) -> str:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_token(name: str, value: object) -> str:
    if not (isinstance(value, str) and _TOKEN_RE.fullmatch(value)):
        raise ValueError(f"{name} must match [a-z0-9][a-z0-9._-]{{0,63}}")
    return value


def _reject_keys(claim: object, forbidden: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(claim, dict):
        raise ContractViolation("contract.not_object", "claim must be a JSON object")
    for key in forbidden:
        if key in claim:
            raise ContractViolation(
                "contract.boundary_field_in_claim",
                f"{key} is stamped by the configured boundary and may not be supplied",
            )
    try:
        canonical_json(claim)
    except (TypeError, ValueError, RecursionError):
        raise ContractViolation("contract.not_json", "claim is not plain JSON data") from None
    return copy.deepcopy(claim)


@dataclass(frozen=True, eq=False)
class VerifierBoundary:
    """Separately configured verifier (local simulation, not authentication).

    ``boundary_id``/``boundary_version`` and the permitted ``(method, version)`` pairs are fixed
    here. A claim may not carry ``boundary``, ``schema_version`` or ``issued_at``.
    """

    boundary_id: str
    boundary_version: str
    methods: frozenset[tuple[str, str]]

    def __post_init__(self) -> None:
        _check_token("boundary_id", self.boundary_id)
        _check_token("boundary_version", self.boundary_version)
        methods = frozenset(self.methods)
        for item in methods:
            if not (isinstance(item, tuple) and len(item) == 2):
                raise ValueError("methods entries must be (name, version)")
            _check_token("method name", item[0])
            _check_token("method version", item[1])
        if not methods:
            raise ValueError("a verifier boundary needs at least one method")
        object.__setattr__(self, "methods", methods)

    def stamp(self, claim: object, now: datetime) -> dict[str, Any]:
        doc = _reject_keys(claim, ("boundary", "schema_version", "issued_at"))
        method = doc.get("method")
        if not (
            isinstance(method, dict)
            and type(method.get("name")) is str
            and type(method.get("version")) is str
            and (method["name"], method["version"]) in self.methods
        ):
            raise BoundaryViolation(
                "boundary.method_not_allowed", "method is not permitted by this verifier boundary"
            )
        doc["schema_version"] = VERIFICATION_VERSION
        doc["issued_at"] = _iso(now)
        doc["boundary"] = {
            "boundary_id": self.boundary_id,
            "boundary_version": self.boundary_version,
        }
        return doc


@dataclass(frozen=True, eq=False)
class EvaluatorBoundary:
    """Separately configured evaluator (local simulation). Permits fixed (protocol, version)
    pairs; it is a fixture boundary, not an evaluation runner, and says nothing about quality."""

    boundary_id: str
    boundary_version: str
    protocols: frozenset[tuple[str, str]]

    def __post_init__(self) -> None:
        _check_token("boundary_id", self.boundary_id)
        _check_token("boundary_version", self.boundary_version)
        protocols = frozenset(self.protocols)
        for item in protocols:
            if not (isinstance(item, tuple) and len(item) == 2):
                raise ValueError("protocols entries must be (name, version)")
            _check_token("protocol name", item[0])
            _check_token("protocol version", item[1])
        if not protocols:
            raise ValueError("an evaluator boundary needs at least one protocol")
        object.__setattr__(self, "protocols", protocols)

    def stamp(self, claim: object, now: datetime) -> dict[str, Any]:
        doc = _reject_keys(claim, ("boundary", "schema_version", "issued_at"))
        protocol = doc.get("protocol")
        if not (
            isinstance(protocol, dict)
            and type(protocol.get("name")) is str
            and type(protocol.get("version")) is str
            and (protocol["name"], protocol["version"]) in self.protocols
        ):
            raise BoundaryViolation(
                "boundary.protocol_not_allowed", "protocol is not permitted by this evaluator"
            )
        doc["schema_version"] = EVALUATION_VERSION
        doc["issued_at"] = _iso(now)
        doc["boundary"] = {
            "boundary_id": self.boundary_id,
            "boundary_version": self.boundary_version,
        }
        return doc


@dataclass(frozen=True, eq=False)
class ControlBoundary:
    """Separately configured control plane (local simulation). Only this object can build a
    policy document; the store assigns the revision (expected-current CAS), never the caller."""

    boundary_id: str
    boundary_version: str

    def __post_init__(self) -> None:
        _check_token("boundary_id", self.boundary_id)
        _check_token("boundary_version", self.boundary_version)

    def build_policy(self, body: object, *, revision: int, now: datetime) -> dict[str, Any]:
        doc = _reject_keys(body, ("schema_version", "revision", "set_by", "set_at"))
        doc["schema_version"] = POLICY_VERSION
        doc["revision"] = revision
        doc["set_by"] = {
            "boundary_id": self.boundary_id,
            "boundary_version": self.boundary_version,
        }
        doc["set_at"] = _iso(now)
        return doc
