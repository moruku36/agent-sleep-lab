# Gate 3 first slice: scoped reference retrieval

Date: 2026-11-10 JST. Branch: `feat/gate-3-scoped-retrieval`, based on main `4749b286069c790c9e72780928ef49dcfd2798b5` (PR #12). Implemented and locally checked; not merged. Initial-version progress approximately 40%, not a performance score.

## Delivered

Synthetic-only read-only library `retrieve_reference_bundle` over AdoptionStore. One same-connection deferred read transaction binds active head/snapshot, current policy/exclusions, registered receipts and original evidence/ancestors. Exact project/task family, partition and current eligibility are applied before deterministic ranking. Confirmed registered receipt backs record eligibility; historical immutable source status is not authority. Bundle carries whole records, evidence hashes, scope, snapshot and policy/exclusion versions, as-of, explicit UTF-8 byte budget and no invented token counts. Normal zero eligible results are distinct from corrupt/missing policy or store failures.

Review fixes: counts retain total eligibility before both record and byte caps; record explicitly reports receipt-backed eligibility. Source memory bytes and hashes remain unchanged. No changes to writer semantics or DB format. Documentation-only PR #12 did not implement runtime changes.

## Executed acceptance

macOS arm64, existing Python 3.13.18 environment. One invocation:

```text
.venv/bin/python tests/run_tests.py --limit 4 test_retrieval.RetrievalTests
Ran 4 tests in 0.782s — OK
```

1. Deterministic ranking, whole records with scope/evidence/hash and explicit eligibility, accurate record-cap counters, byte-budget prefix truncation, header-too-small error and transaction cleanup.
2. Exact scope and evaluation-partition separation; never serve evaluation holdout.
3. Current event exclusion blocks original and descendant memories before ranking, then memory exclusion produces normal empty retrieval without changing historical head.
4. Legitimate uninitialized scope returns empty; tampered active-memory bytes and policy chain fail closed, without returning a partial bundle.

Current Gate3 trial: **4 case executions / 1 invocation** of the total cap10. Planned PR CI: 3 selected cases / 1 invocation (projected total7). No CI execution yet, no full-suite, matrix, installed-wheel runtime or old-writer test rerun. Prior writer trial remains historical at19caseexecutions/5invocations, exhausted; this is a different implemented retrieval capability, not a reset of writer acceptance.

## Not demonstrated or implemented

No independent test of concurrent policy update during retrieval, expiry boundary, every corruption path, production/synthetic leakage using real data, or retrieval quality. The four cases are focused checks, not full Gate3/SLP acceptance. Current synthetic-only store prohibits production data. Integrity/ineligibility failures in evidence omit the affected memory, while corrupt policy/schema/head/snapshot/journal/memory rows raise; neither returns the affected memory.

Full Gate2B run registration/broader fault acceptance, rollback, physical deletion/cache cleanup, pinned evaluation-snapshot retrieval, delivered-memory logging, Light/Deep coordinator, A/B runner and live adapter remain pending. No real transcripts, private memory, credentials, model calls from the harness, schedules or production changes.

Development used Claude Code Sonnet5.5 and separate main-agent review. Claude invocation success is not product performance acceptance. Existing PR-only workflow remains one Python3.13 job with three default retrieval cases and a wheel build; only the focused default selection changes.
