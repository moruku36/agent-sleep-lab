# Gate 3: audited logical forgetting

**English** | [日本語](gate-3-forgetting.ja.md) | [Status](implementation-status.md)

**Merged via PR #15, focused CI passed** (merge `dd79e234fc2888f99685fb2dcf3961b04645f399`). CI42752368409 passed 3 cases once (0.652 s) and built the wheel. Synthetic logical exclusion, not physical deletion. [Current status](implementation-status.md) / [review issues](review-followup.ja.md).

## API (illustrative; not executed)

```python
from agent_sleep_lab.adoption_candidates import build_forget_request

# store is an existing AdoptionStore, control an explicitly configured ControlBoundary.
scope = {"project": "p", "task_family": "t"}
preview = store.plan_forget_impact(scope=scope, event_ids=["e-2"])
request, request_sha256 = build_forget_request(
    operation_id="forget-1", run_id="synthetic-forget",
    scope=scope, expected_policy_revision=preview.policy_revision,
    event_ids=["e-2"],
)
result = store.commit_forget(request_bytes=request, control=control)
receipt = store.resolve_operation("forget-1")  # reconcile a lost acknowledgement
```

`memory_ids`, `event_ids`, and `root_ids` are optional target collections; at least one ID is required, at most 16 per kind and 32 total. Builders sort/deduplicate; stored requests require unique sorted arrays. IDs are not raw memory/source text. Every target must already exist in the exact project/task-family scope; a root must name a root event. Unknown, wrong-scope and non-root targets share `forget.target_unavailable`. Memory bytes/hash/schema and target-event integrity are checked; authorization expiry alone does not prevent forgetting. Corrupt evidence can refuse the operation; this is not a salvage API.

## Transaction and audit

- Dry run uses one same-connection deferred read transaction and writes nothing. It returns target/new-exclusion IDs, affected event/memory IDs, retained snapshot member references, current-head impact and a deterministic impact hash. An event/root affects its descendants and evidence-dependent memories; a memory target alone does not revoke the shared source or unrelated memories. Snapshot references include active and historical nonactive member entries.
- Preview is informational, **not a locked approval token**. Its hash covers the scope, policy revision, targets, newly added exclusions, affected IDs/references and current head/impact flag. The commit recomputes it against its own transaction; concurrent captures/adoptions can change the impact even without a policy revision change.
- One `BEGIN IMMEDIATE` performs operation-ID resolution, current-policy CAS, exact-scope target resolution and impact recomputation, then inserts the next policy revision **and** immutable request/receipt journal row. Failure leaves neither new row. Existing exclusions and unrelated authorizations/purposes/partitions remain unchanged; the explicit control boundary stamps identity/time.
- A stale expected revision raises `adoption.policy_conflict`. All-already-excluded targets raise `forget.no_new_exclusion`. Refused operations consume no ID. Policy exclusion capacity remains 1,024 IDs per kind; exceeding it refuses the whole operation.
- New `agent-sleep-forget-request/1` and `agent-sleep-forget-receipt/1` artifacts coexist with unchanged adoption v1/v2 and rollback artifacts. The v3 schema is reused, with empty manifest/source journal columns; no database migration. Older readers cannot interpret these new journal kinds (no downgrade guarantee).
- Receipt: exact request hash, scope/run audit label, old/new policy revisions, resulting policy hash, exact added IDs, impact hash/counts, `outcome: logically_forgotten`, `physical_erasure: not_performed`. No raw content is copied into the receipt.
- Exact request replay returns the historical receipt with no policy/head write, even after reopen or a later policy revision. Any different payload under the same ID (including another operation kind) conflicts. Resolution checks both historical policy hashes/revisions, exact exclusion delta and preservation of unrelated policy fields. It does not grant present eligibility.
- Heads, memories, snapshots and old receipts stay byte-for-byte retained. Subsequent retrieval filters using the current policy; adoption/rollback refuse an entire candidate/target if any active member is excluded. A clean retained snapshot can still be restored.

## Bounded synthetic impact scans

Materialized scans refuse excess rather than silently truncating: 4,096 scope events, 32,768 scope lineage links, **4,096 global stored memories / 1,024 global snapshots**, and 16,384 affected snapshot references. Memory/snapshot tables do not index scope, so unrelated scopes count toward those global limits. Existing artifact byte/member bounds still apply. These are conservative materialization bounds, not a constant-time, byte-memory, or whole-database traversal cost guarantee; integrity/ancestry and journal/policy resolution have their existing costs.

## Explicit limits

This is **logical exclusion only**. Source blobs, memory text, SQLite pages, retained history, backups, caller-held reference bundles, external caches/indexes/diaries and delivered outputs are not erased. Already issued bundles cannot be recalled. New content under unrelated new IDs/lineage is not suppressed by content hash. No physical cleanup, secure erasure, content-based re-ingestion tombstone, run authentication/registration, live-user authorization, evaluation-frozen retrieval or delivered-memory log is implemented. Boundaries are trusted synthetic configuration, not credentials. Full Gate 3 and performance improvement are not claimed.

## Acceptance boundary

Three focused PR #15 CI cases passed, not a full-suite, erasure or live-adapter acceptance. SAME Gate 3 trial is exhausted at 13 executions / 4 invocations. Current review fixes are unexecuted; their 5 new + 5 existing cases need an explicit increase. The 1,024-ID policy capacity and adoption refusal while an excluded active member remains in the head are unresolved. See [review disposition](review-followup.ja.md).
