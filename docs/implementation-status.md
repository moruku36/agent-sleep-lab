# Implementation status

**English** | [日本語](implementation-status.ja.md) | [Home](../README.md)

2026-11-10: **about 40% of the initial version**. This is the pre-CI Gate 4D
snapshot; subsequent results are in its PR checks. 100% means capture → adoption →
retrieval → Light/Deep → comparison evaluation → one existing-agent integration.
REM, diary and wider rollout are excluded. Counts of files or tests are not progress.

## Current capabilities

| Stage | Verified baseline | Feature branch / remaining boundary |
|---|---|---|
| Evidence, provenance, receipts, policy, adoption | Synthetic libraries merged | Not authentication; broader fault acceptance incomplete |
| Retrieval, rollback, logical forgetting | Merged, review fixes through PR #16 | No physical erasure or delivered-memory logging |
| Light/Deep and run lifecycle | [Gate 4A](gate-4-light-deep.md), PR #17 merged | Offline fake-provider slice; broader faults pending |
| Comparison infrastructure | [Gate 4B](gate-4b-comparison.md), PR #19 merged | Synthetic paired plans/contact tracking, not a performance experiment |
| Retrieval-to-comparison wiring | [Gate 4C](gate-4c-retrieval-comparison.md), PR #20 merged; five new cases once, wheel success | Source-matched context only, not a complete raw baseline |
| Independent raw baseline / input audit | [Gate 4D](gate-4d-raw-baseline.md) saved and reviewed on `feat/gate-4d-raw-baseline` | Pre-CI: untested, unexecuted, unmerged. Bounded ID order, not relevance ranking or live delivery |
| Existing-agent integration | Not implemented | One real adapter remains pending |

## Acceptance evidence and test budget

- **Historical Gate 3:** PR #16 baseline `8e2f871eb1ace6f29378ce44fad8821f36259e18`.
  CI42755593975 passed ten selected cases once; trial total **23 executions / 5
  invocations**, exhausted. Not rerun by this branch.
- **Gate 4A:** PR #17 merged. Source head `a5d64acb294186c840fee7222be5f000661940e2`;
  [CI42772057834](https://github.com/moruku36/agent-sleep-lab/actions/runs/42772057834)
  passed five new cases once, 0.197 s, plus wheel; Ubuntu / Python 3.13.18.
  Trial **5 executions / 1 invocation**, local zero. Dated milestone estimate 35–40%.
- **Gate 4B:** [PR #19](https://github.com/moruku36/agent-sleep-lab/pull/19) merged at
  `acc553050b4437333514d8d534ceebed08609c1a`. Source head
  `7902b59bd21fcef83c82f5c6cf086222331428f5` passed five new cases in
  [CI42778158265](https://github.com/moruku36/agent-sleep-lab/actions/runs/42778158265),
  0.149 s, wheel success. A status-only push unexpectedly repeated those cases in
  [CI42778493776](https://github.com/moruku36/agent-sleep-lab/actions/runs/42778493776),
  head `568cccb4c1c27d7b36095ff6a23ef3ec6d86b401`, 0.168 s, wheel success.
  Cancellation found it already complete, not cancelled. Actual trial **10
  executions / 2 invocations**, local zero, exhausted. Earlier 5/1 observations
  describe the first run only; [dated correction](../reports/gate-4b-acceptance-20261110.md).
- **Gate 4C:** [PR #20](https://github.com/moruku36/agent-sleep-lab/pull/20) merged at
  `bd4d0f6ce898d95c4b0e9afb1372a8f61b8cd81b`. Source head `bfbdcb9508a45149c635f67d25b352c410f013ab`;
  [CI42781526252](https://github.com/moruku36/agent-sleep-lab/actions/runs/42781526252)
  passed five new cases once, 1.308 s, wheel success; Ubuntu / Python3.13.18.
  Historical trial total **5 executions / 1 invocation**, local zero, not rerun.
- **Gate 4D:** five NEW raw-baseline/audit methods in the bounded runner and PR-only
  workflow. **At this pre-CI snapshot: 0 executions, no pass claimed.** Plan: one
  five-case invocation; no local duplicate, push CI, matrix or historical suite.
  Trial cap remains ten including corrections.
  PR path filters use the cumulative diff: do not push an acceptance-only update
  after CI. Subsequent results belong to PR checks and the external local receipt.

## Gate 4D boundary

Raw selection scans the exact scope under current policy, expiry, provenance and
lineage checks, independently of memory citations. The bounded scan fails on excess;
selection cuts record counts/coverage explicitly. Both arms get the same whole raw
prefix; B may add eligible memories. Null adopted head is supported. Frozen eligible
set changes invalidate without revival. Read-only audit binds plan/context/config,
request hash, arm identity and whole prefix to durable statuses, including unknown
outcomes. It never proves delivery/read/use or resends. ID ordering is not relevance
ranking, the fixture is synthetic, and no scientific fairness/performance is claimed.
Separate scan/retrieval/audit reads and recheck-to-dispatch races remain.

## Historical Gate 4C boundary

The read-only adapter freezes exact event/source text and hashes behind currently
eligible retrieved memories, plus whole consolidated records, scope, partition,
retrieval parameters, snapshot and policy. A receives those raw sources; B gets
the same raw prefix plus records within the same cap. It excludes raw evidence
not cited by eligible returned memories, so is a **source-matched representation
fixture, not a fair full raw-baseline evaluation**. All paper data are fictional;
co-authored experience/tasks are not an independent holdout. Fake replies/scores
are not measured quality, savings, performance or an adoption receipt.

Every dispatch/evaluation/report rechecks the current store. Revocation, missing
or mismatching evidence, or a changed context invalidates the plan without revival.
Saved context/replies survive reopen without replay. Context persistence is not
physical erasure. Separate reads and recheck-to-dispatch race remain documented;
local construction/run registration is not authentication. No live provider,
network, CLI, REM, diary, scheduler or extra spend is added to the harness.

## Remaining work

Relevance-ranked raw retrieval and real delivery/use logging; a real
comparison protocol and honest total-cost measurement; broader crash/concurrency
acceptance; physical purge, exclusion capacity and post-forget cleanup; unified
capture/use policy; authenticated provenance/run integration; and one existing-agent
adapter. No measured improvement yet. [Dated review disposition](review-followup.ja.md)
/ [history](../reports/implementation-status-history-20261110.md).
