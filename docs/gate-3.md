# Gate 3: scoped retrieval library (first slice)

**English** | [日本語](gate-3.ja.md) | [Status](implementation-status.md)

Status: scoped retrieval (PR #13) and safe rollback (PR #14) are merged. Rollback merge: `ab25b0036ca3a04de92a0df665a8731ee59f22a7`; [CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42748316078) passed 3 cases once (0.452 s) and built the wheel at head `901ef2d`. Overall progress corrected to about 30–35%. [Logical forgetting](gate-3-forgetting.md) is also merged via PR #15 with focused CI acceptance. The current [review fixes](review-followup.ja.md) are untested. Full Gate 3 is incomplete.

Contract basis: [contracts section 5–6](contracts-and-acceptance.ja.md). The retrieval slice is a read-only library over the existing `AdoptionStore` (`src/agent_sleep_lab/retrieval.py`). It changes no writer or adoption semantics.

## API

```python
from agent_sleep_lab.retrieval import retrieve_reference_bundle

bundle = retrieve_reference_bundle(
    store,                      # AdoptionStore (its own connection and verifier boundary)
    scope={"project": "p", "task_family": "t"},   # exact match, both non-empty strings
    max_bytes=8192,             # required; UTF-8 bytes of the whole serialized bundle
    partition="experience",     # "experience" | "development"; "evaluation" is never served
    query=None,                 # optional short string, used only for ranking
    max_records=16,             # 1..256
)
bundle.document      # dict (reference data, not instructions)
bundle.bundle_bytes  # the exact bytes measured against the budget
bundle.bundle_sha256, bundle.used_bytes
```

## Behavior

1. One deferred read transaction on the store's connection (`BEGIN` … `ROLLBACK`) pins the head, snapshot, current policy (exclusions are part of the policy chain), memories, receipts and evidence for the whole call. It never writes.
2. The head and its snapshot are historical metadata. They only select candidates. Each `active` member is rechecked under the **current** policy before ranking:
   - memory bytes match the snapshot hash and the memory contract; exact scope; `valid_until` not passed;
   - `eligibility_failures` is empty: registered, confirmed, unexpired receipt from the configured verifier bound to the memory hash and scope; every evidence item and **all ancestors/roots** intact, authorized at the current revision, accepted purpose/partition, synthetic, not excluded (memory, event or root);
   - receipt and memory name the same evidence; all ancestors are in the requested partition; the kind/origin rule holds (e.g. preference needs user-correction roots).
   "Verified" means a confirmed registered receipt, not the memory's own `status` text. Unadopted candidates and `stale`/`superseded` snapshot members are never returned. Immutable source bytes may retain `status: candidate`; the bundle record’s `eligibility: verified` is backed by the registered receipt, never by that historical self-report.
3. **Fail closed:** missing or corrupt policy, schema, head, snapshot, journal or active memory raises `StorageError`; no partial bundle is returned. An ineligible or expired member is omitted (counted, not named). **Zero eligible records is a normal result** (including a never-initialized scope).
4. Ranking: lexical overlap in claim/tags (review branch: NFKC/casefold, punctuation-separated words and Japanese character unigrams/bigrams; quality unmeasured), then `memory_id`. No query → `memory_id` order. No model, embedding or network call.
5. Budget: no tokenizer has been accepted, so the unit is **UTF-8 bytes of the canonical serialized bundle** (`budget.unit`, `budget.tokenizer: null`). Nothing is called a token. Whole lower-ranked records are dropped as a strict suffix; a lower record is never kept while a higher one is dropped. Scope, evidence references and hashes of a returned record are never truncated. If the header alone exceeds `max_bytes` the call raises `retrieval.budget_too_small`.

## Bundle fields

`schema_version`, `reference_data_only`, `synthetic_only`, `scope`, `partition`, `as_of`, `snapshot_sha256` (null if no head), `policy {revision, sha256}`, `exclusions {version, policy_sha256}` (the exclusion version is the policy revision), `budget`, `counts {active_members, eligible, returned, dropped}` (eligible is before record/byte caps; dropped includes both caps), `records`. Each record: `eligibility: verified`, `rank`, `score`, `memory_id`, `memory_sha256`, `kind`, `verification_receipt {receipt_id, receipt_sha256}`, `evidence` (event/source/provenance hashes) and the whole `memory` document.

## Safe rollback

Explicit **control recovery**: restore a retained, previously adopted snapshot of the same exact scope. It is **not** a fresh model-candidate adoption, needs no evaluation receipt, and is **not** a performance or evaluation claim.

```python
from agent_sleep_lab.adoption_candidates import build_rollback_request

request_bytes, request_sha256 = build_rollback_request(
    operation_id="rb-1",            # NEW id; never reused from any adoption or rollback
    run_id="my-audit-label",        # caller-supplied audit label, not an authenticated run
    scope={"project": "p", "task_family": "t"},
    expected_head_snapshot_sha256=head_hash,    # compare-and-swap on the current head
    target_snapshot_sha256=target_hash,         # retained snapshot of the same scope
    expected_policy_revision=policy_revision,   # compare-and-swap on the current policy
)
result = store.commit_rollback(request_bytes=request_bytes)   # AdoptionResult
store.resolve_operation("rb-1")  # ACK-loss lookup; returns the historical receipt bytes
```

Contract decisions:

1. **Versioned, additive artifacts.** `agent-sleep-rollback-request/1` and `agent-sleep-rollback-receipt/1` (`outcome: rolled_back`) are new kinds with their own schemas. Adoption request/receipt v1/v2 schemas and bytes are untouched, so existing journals replay unchanged. No storage migration: the v3 tables are reused and a rollback journal row keeps the rollback request/receipt bytes with **empty** manifest/source columns (any other content in such a row is reported as `adoption.journal_corrupt`). Older code cannot read a rollback row; this is forward-only, with no downgrade claim.
2. **One writer transaction (`BEGIN IMMEDIATE`).** Operation lookup → current policy revision CAS (`adoption.policy_conflict`) → scope head CAS (`rollback.head_conflict`) → target lookup (`rollback.target_unavailable`, `rollback.scope_mismatch`) → revalidation of **every active target member** → journal row (request digest + receipt) and head move together. A non-null head is required; rolling back to an uninitialized scope is not supported. The target must differ from the expected head (contract check).
3. **Whole-or-nothing revalidation.** Each active target member is rechecked with the same rule the adoption writer uses: memory bytes/hash/contract, expiry, registered confirmed verification receipt, evidence and **all ancestors/roots**, current authorization revision, accepted purpose/partition, exclusions, kind/origin rule. Any failure refuses the entire rollback (`adoption.ineligible`, `candidate.memory_expired`, `adoption.memory_missing` …). Nothing is filtered, rewritten or partially restored; head and history are unchanged. `stale`/`superseded` members are carried as recorded.
4. **No regained authority.** Restoring the head never restores old authorization: retrieval and later adoption keep rechecking under the current policy, and an excluded memory stays excluded. Original snapshots, memories, receipts, evidence and earlier journal rows are never modified (append-only triggers remain).
5. **Idempotency.** Exact replay of the same bytes returns the historical receipt (`status: replayed`) without a head write or present-time assertion, even after a later revocation or reopen. The same operation ID with different bytes raises `adoption.operation_conflict`. A refused rollback consumes no operation ID.
6. **Adoption after rollback.** The new head is the restored snapshot; the next adoption names that snapshot as its expected parent and works as before. Retrieval reads the head through the same path.
7. "Previously adopted" requires both retained snapshot bytes and a hash-bound, same-scope original `adopted` journal receipt, resolved in the same transaction. An orphan blob is refused (`rollback.target_not_adopted`); no new evaluation is inferred. The synthetic implementation scans the local journal to find this receipt.

Not implemented: physical deletion/purge/cache cleanup, evaluation-frozen retrieval, logging of delivered memories, run authentication/registration. Three focused cases in `tests/test_rollback.py` passed once in PR #14 CI (3 cases, 0.452 s). This is dated synthetic acceptance, not full Gate 3 or later-code verification.

## Not implemented

Deletion/physical purge/cache cleanup, evaluation-frozen retrieval, delivered-memory logging, full Gate 2B acceptance, Light/Deep generation, comparison evaluation and the adapter integration are all pending. Nothing here is a full Gate 3 or performance claim.

## Limits

- Synthetic-only. Not deletion/cache cleanup, run registration, an adapter, authentication of the caller, production use or live-agent integration. (Rollback is described above and is unexecuted.)
- Rank order is a simple deterministic heuristic, not a quality claim. No performance improvement is claimed.
- The query string is not matched against exclusions; exclusions are applied to memories and their evidence ancestry only.
- An evaluation freeze (fixing a snapshot while still applying revocations) and recording of delivered memories are not implemented.
- `eligibility_failures`, `_head` and related helpers are internal store members reused as in the writer; their surface is not a public API promise.

## Selected local acceptance

Historical (dated 2026-11-10, retrieval slice): `.venv/bin/python tests/run_tests.py --limit 4 test_retrieval.RetrievalTests` passed all four cases once in 0.782 s on macOS arm64 / Python 3.13.18, then 3 PR CI cases passed at head `90b3d9e`; PR #13 is merged. The [acceptance record](../reports/gate-3-retrieval-progress.md) details remaining boundaries. The earlier writer trial (**19 executions / 5 invocations**) is historical and exhausted.

Current SAME Gate 3 accounting: **13 executions / 4 invocations**, approved budget exhausted (retrieval local4 + CI3 + rollback CI3 + forgetting CI3). Review fixes have 0 executions; proposed +10 once in PR CI needs explicit approval before PR creation.

`tests/test_retrieval.py` has four methods and `tests/test_rollback.py` three, retained without rerunning. The current review runner proposes 5 new + 5 existing regression methods, unexecuted pending an explicit +10 increase. See the [testing budget](testing-budget.ja.md).
