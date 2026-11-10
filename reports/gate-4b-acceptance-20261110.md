# Gate 4B acceptance and execution-count correction — 2026-11-10

PR19 https://github.com/moruku36/agent-sleep-lab/pull/19 (unmerged).
Sourcehead7902b59bd21fcef83c82f5c6cf086222331428f5;
baseline5e8d201cc0364a9ba600d1765a60ec583fb904fe.

First CI42778158265: five cases once,0.149s,OK,wheelPASS,Ubuntu/Python3.13.18.
Evidence-only head568cccb4c1c27d7b36095ff6a23ef3ec6d86b401 unexpectedly triggered
CI42778493776: SAME five cases repeated,0.168s,OK,wheelPASS.
PR paths filters use aggregate PR changes, not merely the newest docs-only commit.
The earlier claim that documentation-only push could not retrigger CI was incorrect.
Run cancellation was requested but returned alreadycompleted; NOTcancelled.
No cancellation retry or CI rerun was requested.

ACTUAL SAME Gate4B trial:10caseexecutions/2invocations, limit10 EXHAUSTED.
Local0; no fullsuite/matrix. No more tests/CI without specific budget increase.
A third docs-only correction uses the supported skip-ci commit-message marker;
it does not change tested runtime code or its acceptance boundaries.
Historical Gate4A5/1 and Gate323/5 are not part of this new-functionality trial.

Focused accepted synthetic behaviors: shared raw-prefix/additional-memory contexts,
AB/BA order/budgets, evaluator-answer separation, frozen plan/evaluator protocol,
resume without replay, renamed taskset contact reuse, fixed missing/unknown
denominators and policy invalidation. No performance/adoption/savings claim.

Not a model-performance experiment. Fake callbacks and current hashes are trusted local
host inputs, not sandbox/authentication. Paper fixture, frozen-retrieval wiring,
statistics, real parity/costs, one agent integration, unknown-outcome operator resolution
and broader crash/concurrency acceptance remain pending. Initial-version estimate
about40% is based on comparison infrastructure, not file/testcounts or measured gains.
