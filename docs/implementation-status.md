# Implementation status

**English** | [日本語](implementation-status.ja.md) | [Home](../README.md) | [History](../reports/implementation-status-history-20261110.md)

As of 2026-11-10 JST: **about 30–35%** of the initial version, correcting the earlier optimistic 45%.
The unchanged target is capture → adoption → retrieval → Light/Deep → comparison evaluation → one existing-agent integration. REM/diary/wider rollout are excluded. This is not a file/test-count calculation or measured performance.

## Current capabilities

| Stage | Merged main | Remaining boundary |
|---|---|---|
| Contract CLI | Implemented | Offline structural validation, not truth/authentication |
| Evidence / provenance / lineage | Implemented | Synthetic SQLite; replay, scope, ancestry checks |
| Receipts / policy / atomic adoption | Core implemented | Full Gate 2B, run registration and broader fault acceptance incomplete |
| Scoped retrieval | PR #13 merged | Current policy and UTF-8 byte budget; frozen retrieval/delivered-memory logging absent |
| Rollback | PR #14 merged | Whole-target current revalidation, not an evaluation claim |
| Audited logical forgetting | **PR #15 merged, focused CI passed** | Additive exclusions + receipt, not physical erasure; ledger capacity and post-forget cleanup unresolved |
| Physical purge / content re-ingestion suppression | Incomplete | Existing source, backups, caches and issued bundles retained |
| Light/Deep / coordinator / run lifecycle | **Not implemented** | Next: fake-provider end-to-end slice with run registration/state/budgets |
| Paper fixture / A/B runner | **Not implemented, no comparison run** | SLP-12 evaluation-contact logging absent |
| Existing-agent integration | **Not implemented** | Writers are library-only; run_id is an audit label |

## Latest verified evidence

- [PR #15](https://github.com/moruku36/agent-sleep-lab/pull/15) merged at 2026-11-10T03:56:07Z, commit `dd79e234fc2888f99685fb2dcf3961b04645f399`.
- [CI42752368409](https://github.com/moruku36/agent-sleep-lab/actions/runs/42752368409), head `ea28c71bf32dd0625f0c886dcc15bc65060df29b`: 3 cases once, 0.652 s, OK; wheel built.
- SAME Gate 3 trial: **13 case executions / 4 invocations, approved budget exhausted**. Older writer 19/5 is a dated separate record.
- The current [review-fix branch](review-followup.ja.md) is **UNTESTED / unmerged**. Proposed acceptance: 5 new + 5 historical regression cases once in PR CI; needs explicit +10 extension (23 total / 5 invocations) before PR creation. No full suite or permanent full-suite CI enabled.
- Owner-supplied external Windows 11 / Python 3.15.2 report: 211 cases, 207 pass / 4 failures. Logs and exact SHA were not independently verified here; do not add it to our acceptance counts. Windows-native acceptance of this patch remains pending.
- POSIX SIGKILL tests will explicitly skip where unavailable; Windows crash recovery is not thereby verified.

## Limits and next milestone

No real-user authentication, live adapter, measured retrieval quality, running sleep engine or demonstrated improvement.
[Review disposition](review-followup.ja.md) separates fixed, partially mitigated and unresolved findings. Ledger migration, exclusion-only cleanup, capture/use authorization integration and journal indexing require separate contracts; do not silently weaken adoption evaluation or remove safety bounds.

After focused review-fix acceptance, build one fake-provider path: fixed input → Light → Deep → existing verification/adoption → next retrieval, with run lifecycle and failure/budget behavior. Then paper-curation A/B and one adapter.
[Roadmap](roadmap.ja.md) / [contracts](contracts-and-acceptance.md). Historical acceptance and corrections moved to [history](../reports/implementation-status-history-20261110.md).
