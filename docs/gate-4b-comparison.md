# Gate 4B — offline synthetic paired comparison

> Historical gate specification. [日本語要約](gate-4b-comparison.ja.md). Current capabilities, merge state and verification evidence live only in [implementation status](implementation-status.md); old test limits and pre-merge labels below are dated history, not current instructions.

[Home](../README.md) | [Current status](implementation-status.md)

Implemented on feature branch; **five focused CI cases passed, unmerged**.
PR #19, code head7902b59bd21fcef83c82f5c6cf086222331428f5,
CI42778158265:5cases/1invocation/0.149s/OK, wheel success, Python3.13.18 on Ubuntu.
Local0; no retry or duplicate CI. See reports/gate-4b-acceptance-20261110.md.
No real model comparison, adoption receipt, measured savings or performance claim.
The harness supports only FakeTaskProvider plus a separate SyntheticEvaluator.

## Frozen plan

Bind exact canonical task requests, config/model labels, scope, snapshot/policy
hashes, raw/consolidated source hashes, shared ArmBudget and evaluator name/version/
protocol hash. Reject changed bytes under the same plan ID; verify plan integrity
when reopening. Evaluation answers stay inside the trusted local evaluator callback,
not task/provider requests. This is structural separation, not a detector of answers
hidden in prompt prose or reference text.

A packs whole raw reference items. B keeps that same raw prefix first, then packs
additional consolidated items within the SAME total request-byte cap. If raw items
consume the cap, B may receive no added memory; included/dropped counts are recorded.
This simple order is a baseline, not evidence of optimal retrieval. Calls are capped
per arm by task count. Fixed per-task order alternates AB/BA, no cross-arm output is
passed in requests. The fake callback can have Python state; this is not a sandbox
or enforced model/session isolation for arbitrary host code.

## Contact, execution and reporting

- Record contact conservatively when binding a plan, before dispatch.
- Contact identity hashes the sorted prompt-content multiset, excluding task IDs
  and ordering. Renaming or reordering the same exact prompts cannot create a fresh
  final set. Translations, semantic overlaps and cross-database leakage still need
  trusted dataset grouping review. Plans live in one private SQLite database.
- Reused declared-final sets become development. A first final contact is recorded
  as such, but reports never claim an independent scientific holdout.
- Persist dispatch intent before fake execution. Completed terminal arms do not
  repeat on reopen. A saved reply may be scored locally again by the SAME evaluator
  identity after scoring failure, but is not sent to the provider again.
- Unknown dispatch outcomes become sticky incomplete, no automatic retry. There is
  no operator resolution path yet. Single-process restart is covered, not a claim
  of concurrent-worker/crash durability acceptance.
- Keep fixed denominators and outcome counts for complete AND incomplete runs.
  Timeout/missing/invalid are explicit non-pass outcomes; unknown and not-started
  arms are shown separately, never dropped or treated as success.
- Complete dispatch means the protocol finished even if replies timed out.
  all_outcomes_scored is false on missing/timeout/invalid/unknown data; fake score
  summaries are not a general performance or adoption decision.
- Trusted current() checks current policy/snapshot before dispatch, before evaluation,
  and on report. Mismatch invalidates the comparison. This does not atomically lease
  remote policy; it is not frozen retrieval or authenticated authorization.

## Costs and limits

Capture, consolidation, verification, retrieval, task_execution, task_input,
task_output, maintenance and evaluation all carry synthetic_zero or unavailable
labels. Currency is unavailable and units are synthetic; task_input/task_output are
subcomponent labels, not measured additive expenses. B consolidation defaults to
unavailable, which keeps its total unavailable. No real metering or cost conclusion.

Not yet wired to AdoptionStore/retrieve_reference_bundle: a trusted caller supplies
contexts and current hash observations. No paper-curation dataset, statistical
confidence intervals, repetitions, CLI, live adapter, delivered-memory log or real
model/temperature/tool parity enforcement. Existing physical purge/exclusion capacity/
capture-use policy limitations remain. Runtime DBs and evaluator answers stay private.

## Five focused acceptance cases

One PR-only CI invocation, five new ComparisonTests methods; no local duplicate,
Gate4A rerun, old Gate3 regression or full discovery. Exact names are fixed in
tests/run_tests.py and the PR workflow. Cases cover paired context/order/report;
reopen/binding/evaluator identity; renamed final-set reuse; timeout/unknown fixed
denominators without replay; current-policy invalidation.

## 日本語要約

Gate 4Bは偽providerと独立したローカル採点器による合成A/B比較です。
Aは原ログ、Bは同じ原ログ＋予算内の追加記憶。課題・設定・scope・snapshot・
policy・採点器ID／版／protocolを固定し、完了済み群は再送しません。
同一課題本文の改名・並べ替えでも最終集合の再利用履歴は残り、開発扱いになります。
欠落・timeout・結果不明は固定分母と明示状態に残します。全費用項目は合成ゼロ／
計測不能を区別し、実費節約・性能改善・採用合格とは表示しません。
**重点CI5項目合格・未マージ。** 実際の取得固定、論文課題セット、実agent接続、統計評価は未完です。

## Gate 4B execution-count correction

The evidence-only push unexpectedly triggered CI42778493776 at head568cccb.
It repeated the SAME five cases, 0.168s, all passed, wheel success.
**Actual cumulative trial count:10 case executions / 2 invocations, budget exhausted.**
Local0. Cancellation was attempted but the run had already completed; it was not cancelled.
Earlier5/1 statements describe the first observation only. No more tests.
This correction is docs-only and uses GitHub's commit-message skip-ci support to avoid a third run.
