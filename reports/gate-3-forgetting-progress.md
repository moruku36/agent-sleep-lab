# Gate 3 audited logical forgetting: reviewable, UNTESTED

Date: 2026-11-10 JST. Branch: `feat/gate-3-audited-forgetting`.
Base: merged PR #14, `ab25b0036ca3a04de92a0df665a8731ee59f22a7`.
This is a preparation/review record, **not an acceptance report**.

## Verified preceding milestone

PR #14 merged. Its [CI run 42748316078](https://github.com/moruku36/agent-sleep-lab/actions/runs/42748316078) passed exactly 3 rollback cases once (0.452 s) and built the wheel at head `901ef2df9ebffb6d6c74a1f1d56f34b5c03bc051`. Retrieval PR #13 had 4 local + 3 CI cases. These are dated results, not tests of this branch. Overall initial-version progress stays **about 45%**; no measured performance improvement.

## Implemented, not behavior-verified

- Same-scope ID-only impact preview, including descendants, dependent memories and retained snapshot references, without changing source/history.
- Versioned forget request/receipt contracts mirrored in public and package schema directories.
- One writer transaction: operation lookup, policy CAS, target/integrity resolution, recomputed impact, additive policy revision + immutable journal receipt.
- Exact lost-ACK replay, shared adoption/rollback/forget operation-ID conflicts, historical policy hash/revision and exact-delta binding.
- Conservative materialized-scan caps with refusal rather than truncation; memory/snapshot caps are global because those tables have no scope index.
- Retains adoption v1/v2 formats and the v3 table layout. Refactored the policy setter's transaction-internal publish helper without changing its public contract.
- Three proposed focused test methods (scope/impact/atomicity; descendant non-resurrection; CAS/conflict/reopen replay). No test body executed.

The Sonnet implementation worker reached its turn limit after saving code/schema/test drafts. Main-agent review continued, adding stronger policy-delta bindings, stored-memory schema validation, target-event integrity checking (expiry alone allowed), scan caps and bilingual API/status documentation. Worker termination is not a successful acceptance result.

## Checks and exact budget

The SAME Gate 3 development trial is **10/10 case executions in 3 invocations**, exhausted: retrieval local 4 + retrieval CI 3 + rollback CI 3. The earlier writer trial's 19/5 is historical. A new branch/session does not reset this trial.

Current change: **0 executed test bodies / 0 test invocations**. An attempted `python3 tests/run_tests.py --list --limit 3` stopped at module loading; diagnostic import identified missing `jsonschema` in the system interpreter. Neither command executed test bodies. No dependency installation, local test run, PR or CI was performed. Static review passed: six changed Python files parse; the two public/package schema pairs are byte-identical and valid JSON; exactly three proposed test methods; changed-document local link targets exist; git whitespace check is clean. These checks are separate from runtime acceptance.

Proposed next step requires explicit **+3 case executions**, one PR CI invocation on Python 3.13, bringing the trial to **13 / 4**. No local rerun, matrix or full suite. PR creation triggers this existing CI, so it is deferred until the budget increase. A failed run leaves no spare budget; do not automatically rerun or silently reset.

## Remaining limits

See [English contract](../docs/gate-3-forgetting.md) / [日本語](../docs/gate-3-forgetting.ja.md).
This is **logical exclusion, NOT physical deletion**: original bytes, append-only history, SQLite pages, backups, existing bundles, external caches/indexes/diaries and delivered outputs are retained. Content reintroduced under unrelated new IDs/lineage is not hash-blocked. Preview is not a locked approval token; commit recomputes current impact. Physical purge, run registration/authentication, frozen evaluation retrieval, delivered-memory logging, full Gate 2B/3 acceptance, Light/Deep, comparison evaluation and one agent adapter remain pending.
