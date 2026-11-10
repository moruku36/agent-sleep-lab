# Gate 4C — accepted-store retrieval to a frozen source-matched comparison

> Historical gate specification. [日本語要約](gate-4c-retrieval-comparison.ja.md). Current capabilities, merge state and verification evidence live only in [implementation status](implementation-status.md); old test limits and pre-merge labels below are dated history, not current instructions.

[Home](../README.md) | [Status](implementation-status.md) | [状況（日本語）](implementation-status.ja.md) | [Gate 4B](gate-4b-comparison.md)

**Pre-CI snapshot (2026-11-10): saved and reviewed on `feat/gate-4c-paper-retrieval`;
NOT executed, NOT tested, NOT merged at this commit.** No test body has run yet.
Subsequent acceptance results belong to the PR checks; no evidence-only follow-up push. This is a wiring slice over the
accepted Gate 3 retrieval and Gate 4B comparison libraries. It is **not** a
performance experiment and makes no claim of scientific fairness.
日本語の要約は末尾にあります。

- Module: `src/agent_sleep_lab/retrieval_comparison.py` (`RetrievalComparison`)
- Fixture: `tests/paper_fixture.py` (entirely fictional)
- Tests (code only): `tests/test_retrieval_comparison.py`

## What "source-matched representation fixture" means

Arm A receives the exact stored event and source bytes behind the memories that
`retrieve_reference_bundle` currently returns as eligible. Arm B receives the same
whole raw prefix plus the complete consolidated records, under the identical
`ArmBudget`. Raw evidence is restricted to the sources of returned memories.
Therefore arm A is **not the complete raw-retrieval baseline**: it never sees raw
evidence that no eligible memory cites, and it is selected by the consolidation
being evaluated. Reports carry `representation: "source_matched_fixture"`,
`complete_raw_baseline: false` and `scientific_fairness_claim: null`.

## Contract

| Area | Behavior |
|---|---|
| Eligibility | Only records returned by the existing retrieval recheck (`eligibility: "verified"` set by retrieval under the current policy). Caller text is never consulted. |
| Frozen content | Scope, partition, retrieval parameters, bundle hash, `as_of`, snapshot hash, policy hash/revision, evidence references, and the full raw and consolidated item text. Stored in `frozen_contexts` inside the `ComparisonStore` database and bound into the plan through `config.context_sha256`. |
| Evidence check | Each evidence item is fetched with `store.get`, its event and source bytes are re-hashed and compared with the retrieval reference and the stored hashes, scope and partition are compared, and `store.verify` must pass. Missing, unreadable, non-UTF-8 or mismatching evidence raises; nothing is planned. |
| Budget | Unchanged Gate 4B packing: whole items, greedy, raw first. B's raw prefix always equals A's context; consolidated records are added only when whole records fit the same cap. |
| Reopen | An existing `plan_id` reuses the saved context bytes without a new freeze. Different retrieval parameters or plan inputs → `plan binding conflict`. Completed fake work is not rerun (Gate 4B behavior). |
| Live recheck | Before every dispatch/evaluation and on every report, the adapter re-runs retrieval and the evidence checks. Any policy or snapshot difference, any difference in the whole raw/consolidated items, or any failure makes the plan `invalidated` (sticky); restoring the store does not revive it. |
| Writes | None to the accepted store: no receipts, adoption, rollback, forget or head change. |
| Claims | `adoption_receipt`, `performance_claim`, `measured_savings`, `scientific_fairness_claim` are always `null`; `independent_holdout` is always false. |

## Honest limitations

- **Untested at this pre-CI snapshot.** Five new retrieval-integration cases are
  selected explicitly; no historical suite is included. Frozen raw evidence is
  retained in the comparison database, so invalidation is not physical erasure.
- **Non-atomic reads.** Retrieval is one read transaction, but the evidence reads
  and the confirming second retrieval are separate reads. A change in between is
  detected only if it alters snapshot, policy or returned records.
- **Recheck-to-dispatch race.** A policy or head change between a live recheck and
  the fake dispatch that follows it is not excluded. An external policy system
  that does not write to this store is invisible.
- **Context save and plan bind are two steps.** A crash between them leaves a saved
  context without a plan; the next identical `plan` call reuses it.
- **Live recheck failures become invalidation**, with only an error code kept in
  the observation; the plan row stores the generic reason `policy_or_snapshot_changed`.
- Time-based expiry between rechecks follows the store clock; no separate timer.
- Local construction is not authentication. Fake provider and synthetic evaluator only.
- No delivered-memory logging, statistics, repetitions, CLI, live adapter or cost metering.

## Fictional fixture and its split limits

`tests/paper_fixture.py` holds two invented curation notes (experience), two
general consolidated lessons, two development task prompts about other invented
papers, and an evaluator-only key. No real paper, author, venue or user data.
The splits were hand-written together by one author, so the tasks are not an
independent holdout; two items per split support no statistic; there is no final
split. The key encodes fake-provider behavior, not curation quality, and is never
placed in a request or an experience record.

## Five test methods (one explicit PR-only invocation by the main agent)

```
test_retrieval_comparison.RetrievalComparisonTests.test_adopted_store_retrieval_freezes_source_matched_paper_comparison
test_retrieval_comparison.RetrievalComparisonTests.test_corrupt_or_missing_evidence_fails_closed_before_and_after_freeze
test_retrieval_comparison.RetrievalComparisonTests.test_only_exact_scope_and_partition_records_are_frozen
test_retrieval_comparison.RetrievalComparisonTests.test_live_revocation_after_plan_blocks_next_dispatch_and_report
test_retrieval_comparison.RetrievalComparisonTests.test_whole_record_budget_and_frozen_reopen_without_replay
```

`tests/run_tests.py` defaults and the PR-only workflow select these five names explicitly.
Gate 3, Gate 4A and Gate 4B cases are not rerun (Gate 4B's ten-execution budget
is exhausted). Avoid a post-CI source push made only for documentation: PR path
filters use the cumulative diff and would start a duplicate CI run.

## 日本語要約

Gate 4Cは、採用済みstoreの既存取得（`retrieve_reference_bundle`）をGate 4Bの
比較計画へ接続する、信頼するローカルのオフラインadapterです。A群は取得で
現在有効と再確認された記憶の出典（event／source の正確なbyteとhash）、B群は
同じ生参照の先頭部分＋完全な統合記録で、両群の上限は同一です。
**これは出典一致の表現fixtureであり、完全な生取得baselineでも性能比較でも
ありません。科学的公平性は主張しません。** 証拠byteは取得参照と照合し、
欠落・破損・scope／partition不一致・policy撤回は閉じて失敗します。
実行・報告のたびに現行policy／snapshotと文脈全体を再確認し、変化すれば
無効化（復活なし）。同一計画の再openは保存済みbyteを再利用し、完了済みの
偽実行は繰り返しません。storeへの書込み・受領作成・head変更はありません。
取得後の証拠読取りと再確認から送信までの間は非atomicで、外部policyの変化は
検出できません。論文fixtureは完全に架空で、同一作者が同時に書いた2件ずつの
ため独立holdoutではありません。**コードのみ保存、未実行・未テスト・未マージ。**
