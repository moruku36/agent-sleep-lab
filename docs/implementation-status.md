# Implementation status

## Gate 4A acceptance — 2026-11-10

[PR #17](https://github.com/moruku36/agent-sleep-lab/pull/17) is merged.
Head `a5d64acb294186c840fee7222be5f000661940e2`;
[CI42772057834](https://github.com/moruku36/agent-sleep-lab/actions/runs/42772057834)
passed **5 new cases / 1 invocation, 0.197 s**, plus wheel build, Ubuntu / Python 3.13.18.
Local execution: zero. This trial totals 5 case executions / 1 invocation.
Documentation-only follow-up does not trigger duplicate CI.
The accepted synthetic capture→Light→Deep→independent receipts→adoption→retrieval
slice justifies an overall initial-version estimate of **about 40%**.
Production integration, comparison evaluation and broader fault acceptance remain incomplete.


**English** | [日本語](implementation-status.ja.md) | [Home](../README.md)

2026-11-10: **about 40% of the initial version**, after focused Gate 4A acceptance.
The target remains capture → adoption → retrieval → Light/Deep → comparison
evaluation → one existing-agent integration. REM/diary/wider rollout are excluded.

## Current capabilities

| Stage | Verified baseline | Feature branch / remaining boundary |
|---|---|---|
| Evidence, provenance, receipts, policy, adoption | Synthetic libraries merged | Not real authentication; broader fault acceptance incomplete |
| Retrieval, rollback, logical forgetting | Merged, review fixes through PR #16 | No physical erasure, frozen retrieval or delivered-memory logging |
| Light/Deep and run lifecycle | Gate 4A merged (PR #17) | Offline fake-provider slice, focused CI accepted; broader faults pending |
| Comparison evaluation | Not merged | [Gate 4B](gate-4b-comparison.md) offline synthetic paired A/B library and contact tracking saved as code on `feat/gate-4b-offline-comparison`: **five focused CI cases passed, unmerged**. Paper fixture, frozen-retrieval wiring, statistics and live runs pending |
| Existing-agent integration | Not implemented | One real adapter remains pending |

## Evidence and budget

PR #16 baseline: `8e2f871eb1ace6f29378ce44fad8821f36259e18`.
Historical focused CI42755593975 passed ten cases once. Historical Gate 3 total:
23 case executions / 5 invocations, exhausted, not rerun here.

The [new Gate 4A slice](gate-4-light-deep.md) is implemented, merged and
focused-CI-accepted. Five new explicit cases passed in one PR-only CI run;
no local duplicate or historical suite. No runtime pass is claimed in advance.

Gate 4B: CI42778158265 passed five new cases / one invocation, 0.149 s; wheel built.
Local execution zero. PR #19 unmerged. Overall estimate about40%, based on accepted
comparison infrastructure, not a real experiment. No adoption or performance claim.

## Limits

The coordinator binds local run labels to scope/input/config/parent and persists
Light/Deep checkpoints and conservative byte/call reservations. Only explicit adds
are proposed. Trusted local preparation and the unchanged writer enforce independent
receipts/current policy/parent CAS. Local registration is not authentication.
No live provider, REM, diary or schedule is added to the harness.

Physical purge, exclusion capacity and post-forget cleanup, unified capture/use policy,
frozen retrieval, delivered-memory and evaluation-contact logging, broader crash/
concurrency acceptance, A/B evaluation and one real integration remain incomplete.
No measured improvement. [Dated review disposition](review-followup.ja.md) /
[Gate 4A boundaries](gate-4-light-deep.md) /
[history](../reports/implementation-status-history-20261110.md).

## Gate 4B focused acceptance — 2026-11-10

[PR #19](https://github.com/moruku36/agent-sleep-lab/pull/19) remains unmerged.
[CI42778158265](https://github.com/moruku36/agent-sleep-lab/actions/runs/42778158265):
code head `7902b59bd21fcef83c82f5c6cf086222331428f5`, Ubuntu / Python 3.13.18.
**Five new cases / one invocation, 0.149 s, all passed**, wheel succeeded.
Local tests zero, no rerun. Documentation-only evidence update triggers no extra CI.
Overall estimate about40% after focused comparison-infrastructure acceptance, not
performance evaluation. Paper fixture, real retrieval wiring and one agent integration remain pending.
