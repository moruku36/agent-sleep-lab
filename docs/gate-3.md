# Gate 3: scoped retrieval library (first slice)

**English** | [日本語](gate-3.ja.md) | [Status](implementation-status.md)

Status: **implemented and locally checked on `feat/gate-3-scoped-retrieval`; not merged.** Four selected synthetic cases passed in one invocation (0.782 s). No CI has run yet; three CI cases are reserved within this trial’s 10-case total. Initial-version progress is about 40%; full Gate 3, rollback/deletion, broader adoption acceptance and live integration remain incomplete.

Contract basis: [contracts section 5–6](contracts-and-acceptance.ja.md). This slice is a read-only library over the existing `AdoptionStore` (`src/agent_sleep_lab/retrieval.py`). It changes no writer or adoption semantics.

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
4. Ranking: number of distinct query words found in claim/tags (lowercased whitespace split), then `memory_id`. No query → `memory_id` order. No model, embedding or network call.
5. Budget: no tokenizer has been accepted, so the unit is **UTF-8 bytes of the canonical serialized bundle** (`budget.unit`, `budget.tokenizer: null`). Nothing is called a token. Whole lower-ranked records are dropped as a strict suffix; a lower record is never kept while a higher one is dropped. Scope, evidence references and hashes of a returned record are never truncated. If the header alone exceeds `max_bytes` the call raises `retrieval.budget_too_small`.

## Bundle fields

`schema_version`, `reference_data_only`, `synthetic_only`, `scope`, `partition`, `as_of`, `snapshot_sha256` (null if no head), `policy {revision, sha256}`, `exclusions {version, policy_sha256}` (the exclusion version is the policy revision), `budget`, `counts {active_members, eligible, returned, dropped}` (eligible is before record/byte caps; dropped includes both caps), `records`. Each record: `eligibility: verified`, `rank`, `score`, `memory_id`, `memory_sha256`, `kind`, `verification_receipt {receipt_id, receipt_sha256}`, `evidence` (event/source/provenance hashes) and the whole `memory` document.

## Limits

- Synthetic-only. Not rollback, deletion/cache cleanup, run registration, an adapter, authentication of the caller, production use or live-agent integration.
- Rank order is a simple deterministic heuristic, not a quality claim. No performance improvement is claimed.
- The query string is not matched against exclusions; exclusions are applied to memories and their evidence ancestry only.
- An evaluation freeze (fixing a snapshot while still applying revocations) and recording of delivered memories are not implemented.
- `eligibility_failures`, `_head` and related helpers are internal store members reused as in the writer; their surface is not a public API promise.

## Selected local acceptance

`.venv/bin/python tests/run_tests.py --limit 4 test_retrieval.RetrievalTests` passed all four cases once in 0.782 s on macOS arm64 / Python 3.13.18. This trial has used 4 executions / 1 invocation; CI is not yet run. No full suite or unchanged writer tests were rerun. The [acceptance record](../reports/gate-3-retrieval-progress.md) details remaining boundaries.

`tests/test_retrieval.py` has exactly four methods: normal bounded retrieval; scope and partition filtering; revocation/ancestor exclusion; corruption fail-closed plus legitimate empty. `tests/run_tests.py` selects three by default (the filtering case is selectable by name). The trial budget is 10 executions in total including CI; see the [testing budget](testing-budget.ja.md).
