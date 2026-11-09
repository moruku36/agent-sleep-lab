"""Gate 2B adoption slice: deterministic, parent-based candidate construction (pure, no I/O).

A candidate snapshot is *constructed* from an immutable parent snapshot plus a validated
operation manifest. A caller can never supply a replacement snapshot: the constructed
snapshot hash is what the evaluation receipt and the adoption request must name.

Semantics (all enforced here, all covered by tests/test_adoption_candidates.py):

* ``add``        new ``memory_id`` (never used before, globally) becomes an ``active`` member.
* ``supersede``  an ``active`` target becomes ``superseded`` (``superseded_by_id`` = new id) and the
                 new memory becomes ``active``. The new memory's own ``supersedes`` must be exactly
                 ``[target_id]``; an ``add`` must have ``supersedes == []``. History is retained.
* ``mark_stale`` an ``active`` target becomes ``stale`` (kept, not eligible, not declared false).
* ``reject`` / ``defer``  audit only, about a *proposed* ``memory_id`` that is not a member. They never
                 touch members. An operation set with only these changes nothing ("audit-only"):
                 ``changed`` is false and no snapshot is produced, so an uninitialized scope stays
                 uninitialized and no evaluation is required.
* Every id an operation touches must appear once. Unknown/inactive targets, id reuse (checked against
  parent members and the caller-supplied global ``known_ids``), scope changes, unrequested or missing
  memory bytes, source-manifest mismatches and oversized results are rejected. Nothing is evicted.
* ``expected_parent_snapshot_sha256`` is ``null`` only for a never-initialized scope; a non-null
  parent must hash (raw bytes) to the expected value. Untouched members are copied byte-for-byte
  (as canonical JSON values), so unrelated members cannot be dropped silently.
* Encoding: ``canonical_json`` (sorted keys, compact, ASCII; this project's internal encoding, NOT
  RFC 8785). Members are sorted by ``memory_id``; operations are required in canonical order.
  Artifact bytes handed to this module must already be the canonical encoding (one byte form).

What passing construction does not establish: receipts, evidence integrity, policy, exclusions,
preference/hypothesis origin rules against stored evidence and the transaction itself are the
writer's job (pending). ``evidence_origin_failures`` is the pure rule the writer will call.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Collection, Mapping

from agent_sleep_lab.provenance import ContractViolation, parse_timestamp, sha256_hex
from agent_sleep_lab.runtime_artifacts import encode_artifact, parse_artifact_bytes
from agent_sleep_lab.strictjson import StrictJSONError, loads_strict_bytes
from agent_sleep_lab.validation import validate_bytes

MAX_MEMBERS = 256
ACTIVATABLE_KINDS = frozenset({"preference", "procedure", "fact"})
ADOPTABLE_MEMORY_STATUS = frozenset({"candidate", "verified"})
CHANGING_OPS = frozenset({"add", "supersede", "mark_stale"})


def _fail(code: str, message: str) -> ContractViolation:
    return ContractViolation(code, message)


@dataclass(frozen=True)
class CandidatePlan:
    scope: dict[str, str]
    parent_sha256: str | None
    changed: bool
    snapshot_doc: dict[str, Any] | None
    snapshot_bytes: bytes | None
    snapshot_sha256: str | None  # None exactly when ``changed`` is False (audit-only)
    operations_sha256: str
    source_manifest_sha256: str
    added: tuple[str, ...]
    superseded: tuple[tuple[str, str], ...]  # (old_id, new_id)
    staled: tuple[str, ...]
    audit: tuple[tuple[str, str, str], ...]  # (op, memory_id, memory_sha256) for reject/defer
    carried_forward: tuple[str, ...]  # parent members copied unchanged
    active_ids: tuple[str, ...]  # every active member of the candidate, carried ones included
    memories: Mapping[str, dict[str, Any]]  # parsed memory documents for add/supersede


def parse_canonical(kind: str, data: object) -> dict[str, Any]:
    """Parse artifact bytes and require them to be the one canonical byte form."""
    doc = parse_artifact_bytes(kind, data)
    if encode_artifact(kind, doc) != bytes(data):  # type: ignore[arg-type]
        raise _fail("candidate.not_canonical_bytes", f"{kind} bytes are not the canonical encoding")
    return doc


def artifact_sha256(kind: str, doc: dict[str, Any]) -> str:
    """Raw-byte identity of an artifact's canonical encoding."""
    return sha256_hex(encode_artifact(kind, doc))


def evidence_origin_failures(kind: str, root_origins: Collection[str]) -> list[str]:
    """Pure kind rule over the origins of a memory's evidence *roots* (the writer supplies them)."""
    if kind == "hypothesis":
        return ["candidate.hypothesis_not_activatable"]
    if kind == "preference":
        origins = set(root_origins)
        if not origins or origins != {"user_correction"}:
            return ["candidate.preference_needs_user_correction"]
        return []
    if kind in ("fact", "procedure"):
        return []
    return ["candidate.unknown_kind"]


def _memory_document(memory_id: str, sha: str, data: object, scope: dict[str, str], now: datetime) -> dict[str, Any]:
    if type(data) not in (bytes, bytearray):
        raise _fail("candidate.memory_not_bytes", "memory bytes must be bytes")
    raw = bytes(data)  # type: ignore[arg-type]
    if sha256_hex(raw) != sha:
        raise _fail("candidate.memory_hash_mismatch", "memory bytes differ from the operation's hash")
    try:
        doc = loads_strict_bytes(raw)
    except StrictJSONError:
        raise _fail("candidate.memory_invalid", "memory is not strict JSON") from None
    if not isinstance(doc, dict):
        raise _fail("candidate.memory_not_object", "memory bytes must be one JSON object")
    if not validate_bytes("memory", raw).valid:
        raise _fail("candidate.memory_invalid", "memory fails the legacy memory contract")
    if doc["memory_id"] != memory_id:
        raise _fail("candidate.memory_id_mismatch", "memory_id inside the bytes differs from the operation")
    if doc["scope"] != scope:
        raise _fail("candidate.scope_mismatch", "memory scope differs from the manifest scope")
    evidence_ids = [entry["event_id"] for entry in doc["evidence"]]
    if len(set(evidence_ids)) != len(evidence_ids):
        raise _fail("candidate.duplicate_evidence", "memory repeats an evidence event_id")
    if doc["status"] not in ADOPTABLE_MEMORY_STATUS:
        raise _fail("candidate.memory_status", "memory status is not adoptable")
    if doc["kind"] == "hypothesis":
        raise _fail("candidate.hypothesis_not_activatable", "a hypothesis cannot become active")
    if doc["kind"] not in ACTIVATABLE_KINDS:
        raise _fail("candidate.unknown_kind", "memory kind cannot be activated")
    if doc["valid_until"] is not None and parse_timestamp(doc["valid_until"]) <= now:
        raise _fail("candidate.memory_expired", "memory is expired")
    return doc


def build_candidate(
    *,
    manifest_bytes: object,
    source_manifest_bytes: object,
    parent_bytes: object,
    memory_bytes: Mapping[str, object],
    known_ids: Collection[str],
    now: datetime,
    max_members: int = MAX_MEMBERS,
) -> CandidatePlan:
    """Construct the candidate from the immutable parent. Raises ``ContractViolation`` on any defect."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    if isinstance(known_ids, (str, bytes)) or not all(isinstance(i, str) for i in known_ids):
        raise TypeError("known_ids must be a collection of memory id strings")
    if type(max_members) is not int or not 1 <= max_members <= MAX_MEMBERS:
        raise ValueError("max_members out of range")

    manifest = parse_canonical("operation_manifest", manifest_bytes)
    source = parse_canonical("source_manifest", source_manifest_bytes)
    scope = manifest["scope"]
    if source["scope"] != scope:
        raise _fail("candidate.scope_mismatch", "source manifest scope differs from the manifest scope")

    expected_parent = manifest["expected_parent_snapshot_sha256"]
    if parent_bytes is None:
        if expected_parent is not None:
            raise _fail("candidate.parent_missing", "the manifest expects a parent that was not supplied")
        members: dict[str, dict[str, Any]] = {}
    else:
        if expected_parent is None:
            raise _fail(
                "candidate.parent_unexpected",
                "a null expected parent is only for a never-initialized scope",
            )
        if type(parent_bytes) not in (bytes, bytearray) or sha256_hex(bytes(parent_bytes)) != expected_parent:  # type: ignore[arg-type]
            raise _fail("candidate.parent_hash_mismatch", "parent bytes differ from the expected hash")
        parent = parse_canonical("candidate_snapshot", parent_bytes)
        if parent["scope"] != scope:
            raise _fail("candidate.scope_mismatch", "parent scope differs from the manifest scope")
        members = {m["memory_id"]: copy.deepcopy(m) for m in parent["members"]}
    known = set(known_ids) | set(members)

    ops = manifest["operations"]
    touched: list[str] = []
    for o in ops:
        if o["op"] in ("add", "reject", "defer"):
            touched.append(o["memory_id"])
        elif o["op"] == "supersede":
            touched.extend((o["memory_id"], o["target_id"]))
        else:
            touched.append(o["target_id"])
    if len(set(touched)) != len(touched):
        raise _fail("candidate.duplicate_target", "an id is touched by more than one operation")

    for o in ops:
        op = o["op"]
        if op in ("add", "supersede") and o["memory_id"] in known:
            raise _fail("candidate.id_reused", "a memory id may never be reused")
        if op in ("supersede", "mark_stale"):
            target = members.get(o["target_id"])
            if target is None:
                raise _fail("candidate.unknown_target", "operation targets a memory that is not a member")
            if target["state"] != "active":
                raise _fail("candidate.target_not_active", "operation targets a member that is not active")
        if op in ("reject", "defer") and o["memory_id"] in members:
            raise _fail(
                "candidate.ambiguous_reject_target",
                "reject/defer cannot name a member; use mark_stale or supersede",
            )

    needed = {o["memory_id"]: o for o in ops if o["op"] in ("add", "supersede")}
    provided = set(memory_bytes)
    if provided - set(needed):
        raise _fail("candidate.unrequested_memory", "memory bytes were supplied for no add/supersede")
    if set(needed) - provided:
        raise _fail("candidate.memory_missing", "add/supersede memory bytes were not supplied")
    sources = {e["memory_id"]: e for e in source["entries"]}
    if set(sources) != set(needed):
        raise _fail("candidate.source_manifest_mismatch", "source manifest must cover exactly the add/supersede memories")

    memories: dict[str, dict[str, Any]] = {}
    for mid, o in needed.items():
        doc = _memory_document(mid, o["memory_sha256"], memory_bytes[mid], scope, now)
        expected_supersedes = [o["target_id"]] if o["op"] == "supersede" else []
        if doc["supersedes"] != expected_supersedes:
            raise _fail("candidate.supersedes_mismatch", "memory supersedes does not match its operation")
        entry = sources[mid]
        if entry["memory_sha256"] != o["memory_sha256"]:
            raise _fail("candidate.source_manifest_mismatch", "source manifest names different memory bytes")
        if {e["event_id"] for e in entry["evidence"]} != {e["event_id"] for e in doc["evidence"]}:
            raise _fail("candidate.evidence_mismatch", "memory evidence differs from the source manifest")
        memories[mid] = doc

    untouched = [i for i in members if i not in touched]
    new = {i: copy.deepcopy(m) for i, m in members.items()}
    added: list[str] = []
    superseded: list[tuple[str, str]] = []
    staled: list[str] = []
    audit: list[tuple[str, str, str]] = []
    for o in ops:  # canonical order
        op = o["op"]
        if op in ("add", "supersede"):
            mid = o["memory_id"]
            if op == "supersede":
                new[o["target_id"]].update(state="superseded", superseded_by_id=mid)
                superseded.append((o["target_id"], mid))
            else:
                added.append(mid)
            new[mid] = {
                "memory_id": mid,
                "memory_sha256": o["memory_sha256"],
                "kind": memories[mid]["kind"],
                "state": "active",
                "superseded_by_id": None,
                "verification_receipt": dict(o["receipt"]),
            }
        elif op == "mark_stale":
            new[o["target_id"]]["state"] = "stale"
            staled.append(o["target_id"])
        else:
            audit.append((op, o["memory_id"], o["memory_sha256"]))
    if len(new) > max_members:
        raise _fail("candidate.too_large", "the candidate would exceed the member limit; nothing is evicted")
    assert set(members) <= set(new)  # no unrequested omission is possible

    operations_sha = artifact_sha256("operation_manifest", manifest)
    source_sha = artifact_sha256("source_manifest", source)
    changed = any(o["op"] in CHANGING_OPS for o in ops)
    snapshot_doc = snapshot_bytes = snapshot_sha = None
    if changed:
        snapshot_doc = {
            "schema_version": "agent-sleep-candidate-snapshot/1",
            "scope": dict(scope),
            "parent_snapshot_sha256": expected_parent,
            "members": [new[i] for i in sorted(new)],
        }
        snapshot_bytes = encode_artifact("candidate_snapshot", snapshot_doc)
        snapshot_sha = sha256_hex(snapshot_bytes)
    active = tuple(sorted(i for i, m in new.items() if m["state"] == "active")) if changed else ()
    return CandidatePlan(
        scope=dict(scope),
        parent_sha256=expected_parent,
        changed=changed,
        snapshot_doc=snapshot_doc,
        snapshot_bytes=snapshot_bytes,
        snapshot_sha256=snapshot_sha,
        operations_sha256=operations_sha,
        source_manifest_sha256=source_sha,
        added=tuple(added),
        superseded=tuple(superseded),
        staled=tuple(staled),
        audit=tuple(audit),
        carried_forward=tuple(sorted(untouched)),
        active_ids=active,
        memories=memories,
    )


def build_adoption_request(
    *,
    operation_id: str,
    run_id: str,
    plan: CandidatePlan,
    expected_policy_revision: int,
    evaluation_receipt: dict[str, str] | None,
) -> tuple[bytes, str]:
    """Canonical request bytes and their digest (the durable operation digest). The request names
    the *constructed* snapshot hash, never a caller-chosen one; ``expected_policy_revision`` is the
    single control-policy chain revision, not the legacy authorization/exclusion integer pair.
    run_id is a caller-supplied audit label, not a registered/authenticated run."""
    doc = {
        "schema_version": "agent-sleep-adoption-request/2",
        "operation_id": operation_id,
        "run_id": run_id,
        "scope": dict(plan.scope),
        "expected_parent_snapshot_sha256": plan.parent_sha256,
        "expected_policy_revision": expected_policy_revision,
        "operations_sha256": plan.operations_sha256,
        "source_manifest_sha256": plan.source_manifest_sha256,
        "candidate_snapshot_sha256": plan.snapshot_sha256,
        "evaluation_receipt": dict(evaluation_receipt) if evaluation_receipt else None,
    }
    data = encode_artifact("adoption_request", doc)
    return data, sha256_hex(data)


def build_committed_receipt(
    request_bytes: object, *, policy_revision: int, now: datetime
) -> tuple[bytes, str]:
    """Pure builder for the receipt the writer will persist in the same transaction as the pointer."""
    request = parse_canonical("adoption_request", request_bytes)
    if type(policy_revision) is not int or policy_revision != request["expected_policy_revision"]:
        raise _fail("candidate.policy_revision_mismatch", "receipt policy revision differs from the request")
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    adopted = request["candidate_snapshot_sha256"] is not None
    parent = request["expected_parent_snapshot_sha256"]
    version = "2" if request["schema_version"] == "agent-sleep-adoption-request/2" else "1"
    doc = {
        "schema_version": "agent-sleep-committed-operation-receipt/" + version,
        "operation_id": request["operation_id"],
        "request_sha256": sha256_hex(bytes(request_bytes)),  # type: ignore[arg-type]
        "scope": request["scope"],
        "parent_snapshot_sha256": parent,
        "snapshot_sha256": request["candidate_snapshot_sha256"] if adopted else parent,
        "policy_revision": policy_revision,
        "evaluation_receipt": request["evaluation_receipt"],
        "outcome": "adopted" if adopted else "audit_only",
        "committed_at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if version == "2":
        doc["run_id"] = request["run_id"]
    data = encode_artifact("committed_receipt", doc)
    return data, sha256_hex(data)
