"""Gate 3 (first slice): synthetic-only scoped retrieval over the existing ``AdoptionStore``.

Read-only. It never writes, adopts, rolls back, deletes or registers anything, calls no model or
network, and adds no adapter. One call = one deferred SQLite read transaction on the store's own
connection (``BEGIN`` ... ``ROLLBACK``), so the active head, the snapshot, the current policy
(exclusions are part of it), every memory row, receipt and evidence/ancestor row are read from one
consistent view. Other connections cannot change the view mid-call.

Contract decisions
* ``current_snapshot`` / the head is historical metadata. It selects *candidates*; it is never
  permission. Every active member is rechecked under the CURRENT policy before ranking.
* Included only if ALL hold: member state ``active``; memory bytes match the snapshot hash and the
  memory contract; exact scope; memory not expired; ``eligibility_failures`` is empty (registered
  confirmed receipt from the configured verifier, unexpired, bound to memory hash and scope, every
  evidence item and ALL ancestors/roots intact, authorized at the current revision, accepted
  purpose/partition, synthetic, not excluded); every ancestor is in the requested partition;
  the receipt/memory evidence sets agree; the kind/origin rule holds.
  "Verified" means a confirmed registered receipt, not the memory's own ``status`` text.
* Fail closed: missing/corrupt policy, store schema, head, snapshot, memory or journal raise a
  ``StorageError``; nothing partial is returned. An ineligible or expired member is silently
  omitted (counted, never named) and an empty result is a normal result.
* The ``evaluation`` partition (holdout) is never served.
* No tokenizer is accepted, so the budget is an explicit UTF-8 byte budget for the whole
  serialized bundle; nothing is called a token. Records are whole: ranked lower records are dropped
  as a strict prefix cut (never a lower record kept while a higher one is dropped), and a memory's
  scope and evidence references are never truncated. If even the header exceeds the budget the call
  raises instead of returning a stripped bundle.
* Ranking is deterministic lexical overlap: NFKC/casefold words without punctuation, plus
  Japanese character unigrams/bigrams, then ``memory_id``. No query => ``memory_id`` order.
  This is not morphological analysis or a measured retrieval-quality claim.

Not claimed: retrieval quality, authentication of the caller, deletion/cache cleanup (rollback is
a separate writer-side operation, ``AdoptionStore.commit_rollback``; this module never performs it),
production data or live agent integration. The result is reference data, not instructions.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import timezone
from typing import Any

from agent_sleep_lab.adoption_candidates import (
    _memory_document, evidence_origin_failures, parse_canonical,
)
from agent_sleep_lab.adoption_store import AdoptionStore, _check_v3
from agent_sleep_lab.evidence_store import _as_bytes
from agent_sleep_lab.provenance import ContractViolation, StorageError, sha256_hex
from agent_sleep_lab.runtime_store import MAX_CLOSURE_NODES

BUNDLE_SCHEMA = "agent-sleep-reference-bundle/1"
BUDGET_UNIT = "utf8_bytes_of_canonical_bundle_json"
SERVED_PARTITIONS = frozenset({"experience", "development"})
MAX_QUERY_CHARS = 1024
MAX_RECORDS_LIMIT = 256


@dataclass(frozen=True)
class ReferenceBundle:
    document: dict[str, Any]
    bundle_bytes: bytes  # exact serialization that was measured against the byte budget
    bundle_sha256: str
    used_bytes: int


def _serialize(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _check_scope(scope: object) -> dict[str, str]:
    if (type(scope) is not dict or set(scope) != {"project", "task_family"}
            or not all(type(v) is str and v for v in scope.values())):
        raise ValueError("scope must name non-empty project and task_family strings")
    return {"project": scope["project"], "task_family": scope["task_family"]}


_JAPANESE_RUN = re.compile(r"([\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff々ー]+)")


def _terms(text: str) -> frozenset[str]:
    """Dependency-free bilingual baseline; punctuation never becomes part of a word.

    Japanese character unigrams support single-character queries; overlapping bigrams
    add local context without assuming spaces. Common characters can overmatch; no semantic claim.
    """
    terms = set()
    for word in re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold()):
        for part in _JAPANESE_RUN.split(word):
            if not part:
                continue
            if _JAPANESE_RUN.fullmatch(part):
                terms.update(part)
                terms.update(part[i:i + 2] for i in range(len(part) - 1))
            else:
                terms.add(part)
    return frozenset(terms)


def _score(memory: dict[str, Any], terms: frozenset[str]) -> int:
    if not terms:
        return 0
    words = set(_terms(memory["claim"]))
    for tag in memory["tags"]:
        words.update(_terms(tag))
    return len(terms & words)


def _closure(store: AdoptionStore, event_ids: list[str]) -> tuple[set[str], set[str]]:
    """(root origins, evaluation partitions) over every ancestor; bounded, errors propagate."""
    pending, seen = list(event_ids), set()
    origins: set[str] = set()
    partitions: set[str] = set()
    while pending:
        event_id = pending.pop()
        if event_id in seen:
            continue
        if len(seen) >= MAX_CLOSURE_NODES:
            raise StorageError("retrieval.closure_too_large", "evidence ancestry exceeds the bound")
        seen.add(event_id)
        evidence = store.get(event_id)
        origins.add(store.get(evidence.root_id).provenance["origin"])
        partitions.add(evidence.provenance["partition"]["evaluation"])
        pending.extend(r[0] for r in store._parents(event_id))
    return origins, partitions


def _memory_bytes(store: AdoptionStore, member: dict[str, Any]) -> bytes:
    rows = store._rows(
        "SELECT memory_sha256, memory_bytes FROM adoption_memories WHERE memory_id = ?",
        (member["memory_id"],),
    )
    if not rows or rows[0][0] != member["memory_sha256"]:
        raise StorageError("retrieval.memory_corrupt", "active memory is missing or inconsistent")
    data = _as_bytes(rows[0][1])
    if sha256_hex(data) != member["memory_sha256"]:
        raise StorageError("retrieval.memory_corrupt", "active memory fails its hash")
    return data


def _eligible_records(store, scope, partition, snapshot, now, terms, policy):
    """Return (active_count, [(sort_key, record)]) for members that pass every recheck."""
    scope_pair = (scope["project"], scope["task_family"])
    active = [m for m in snapshot["members"] if m["state"] == "active"]
    found = []
    for member in active:
        mid, digest = member["memory_id"], member["memory_sha256"]
        data = _memory_bytes(store, member)
        try:
            memory = _memory_document(mid, digest, data, scope, now)
        except ContractViolation as exc:
            if exc.code == "candidate.memory_expired":
                continue  # legitimately no longer usable
            raise StorageError("retrieval.memory_corrupt", "active memory violates its contract") from None
        if memory["kind"] != member["kind"]:
            raise StorageError("retrieval.memory_corrupt", "snapshot kind differs from memory")
        ref = member["verification_receipt"]
        if store._eligibility_failures_with_policy(
            memory_id=mid, memory_sha256=digest, scope=scope_pair,
            receipt_id=ref["receipt_id"], receipt_sha256=ref["receipt_sha256"],
            verifier=store._verifier, now=now, policy=policy.document,
        ):
            continue
        receipt = store.resolve_receipt("verification", ref["receipt_id"], ref["receipt_sha256"])
        if {e["event_id"] for e in receipt["evidence"]} != {e["event_id"] for e in memory["evidence"]}:
            continue
        origins, partitions = _closure(store, [e["event_id"] for e in receipt["evidence"]])
        if partitions != {partition} or evidence_origin_failures(memory["kind"], origins):
            continue
        record = {
            "memory_id": mid,
            "memory_sha256": digest,
            "kind": memory["kind"],
            "eligibility": "verified",  # current registered receipt, not source self-report
            "score": _score(memory, terms),
            "verification_receipt": {"receipt_id": ref["receipt_id"],
                                     "receipt_sha256": ref["receipt_sha256"]},
            "evidence": [dict(e) for e in receipt["evidence"]],
            "memory": memory,
        }
        found.append(((-record["score"], mid), record))
    found.sort(key=lambda item: item[0])
    return len(active), found


def retrieve_reference_bundle(
    store: AdoptionStore, *, scope: dict[str, str], max_bytes: int,
    partition: str = "experience", query: str | None = None,
    max_records: int = 16,
) -> ReferenceBundle:
    """Bounded reference-data bundle for one exact scope. See the module docstring."""
    if not isinstance(store, AdoptionStore):
        raise TypeError("store must be an AdoptionStore")
    scope = _check_scope(scope)
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_bytes must be a positive int (UTF-8 bytes, not tokens)")
    if type(max_records) is not int or not 1 <= max_records <= MAX_RECORDS_LIMIT:
        raise ValueError("max_records out of range")
    if partition not in SERVED_PARTITIONS:
        raise ContractViolation("retrieval.partition_not_served", "partition is not served")
    if query is not None and (type(query) is not str or len(query) > MAX_QUERY_CHARS):
        raise ValueError("query must be a short string or None")
    terms = _terms(query) if query else frozenset()

    db = store._db()
    if db.in_transaction:
        raise StorageError("retrieval.nested_transaction", "retrieval needs its own read transaction")
    try:
        db.execute("BEGIN")  # deferred: the first read pins one consistent view
    except sqlite3.Error as exc:
        raise StorageError("storage.busy_or_locked", f"cannot start read transaction ({exc})") from None
    try:
        _check_v3(db)
        now = store._now()
        policy = store.current_policy()  # missing/corrupt => StorageError, nothing returned
        if partition not in policy.document["accepted_partitions"]:
            raise ContractViolation("retrieval.partition_not_accepted", "policy does not accept partition")
        digest = store._head(scope)
        active_count, found = 0, []
        if digest is not None:
            snapshot = parse_canonical("candidate_snapshot", store._snapshot(digest, scope))
            active_count, found = _eligible_records(store, scope, partition, snapshot, now, terms, policy)
        total = len(found)  # before either the record cap or byte budget
        found = found[:max_records]

        def build(count: int) -> tuple[dict[str, Any], bytes]:
            records = []
            for rank, (_, record) in enumerate(found[:count], start=1):
                records.append(dict(record, rank=rank))
            doc = {
                "schema_version": BUNDLE_SCHEMA,
                "reference_data_only": True,
                "synthetic_only": True,
                "scope": dict(scope),
                "partition": partition,
                "as_of": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "snapshot_sha256": digest,
                "policy": {"revision": policy.revision, "sha256": policy.sha256},
                "exclusions": {"version": policy.revision, "policy_sha256": policy.sha256},
                "budget": {"unit": BUDGET_UNIT, "max_bytes": max_bytes, "tokenizer": None},
                "counts": {"active_members": active_count, "eligible": total,
                           "returned": count, "dropped": total - count},
                "records": records,
            }
            return doc, _serialize(doc)

        doc, data = build(0)
        if len(data) > max_bytes:
            raise ContractViolation("retrieval.budget_too_small", "budget cannot hold the bundle header")
        for count in range(1, len(found) + 1):
            trial_doc, trial = build(count)
            if len(trial) > max_bytes:
                break  # drop this and every lower-ranked whole record
            doc, data = trial_doc, trial
        return ReferenceBundle(doc, data, sha256_hex(data), len(data))
    except sqlite3.Error as exc:
        raise StorageError("storage.read_failed", f"retrieval read failed ({exc})") from None
    finally:
        try:
            db.execute("ROLLBACK")  # read-only: nothing to commit
        except sqlite3.Error:
            pass
