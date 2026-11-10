# Gate 4D — independent raw-evidence baseline and per-arm request audit

> Historical gate specification. [日本語要約](gate-4d-raw-baseline.ja.md). Current capabilities, merge state and verification evidence live only in [implementation status](implementation-status.md); old test limits and pre-merge labels below are dated history, not current instructions.

[Home](../README.md) | [Status](implementation-status.md) | [Gate 4C](gate-4c-retrieval-comparison.md) | [Gate 4B](gate-4b-comparison.md)

**Pre-CI snapshot (2026-11-10): saved and reviewed on `feat/gate-4d-raw-baseline`;
NOT executed, NOT tested, NOT merged at this commit.** Zero of the trial's ten case
executions are used. Subsequent results are in PR checks, not an extra status-only push.
Synthetic wiring only: no fairness, retrieval-quality or performance claim.
The overall initial-version estimate stays at about 40% until reviewed evidence
exists. 日本語の要約は末尾にあります。

- Module: `src/agent_sleep_lab/raw_baseline.py` (`RawBaselineComparison`, subclass of the Gate 4C adapter)
- Tests (code only): `tests/test_raw_baseline.py`
- Gate 4C `source_matched_fixture`, `ab_comparison.py` and `retrieval.py` are unchanged.

## Why

Gate 4C chooses arm A's raw evidence from the sources of eligible consolidated
memories, so the baseline is shaped by the consolidation under comparison.
Gate 4D selects raw evidence from the accepted evidence store without looking at
memories, and adds an audit of what each arm's request actually contains.

## Raw selection contract

| Area | Behavior |
|---|---|
| Source | Bounded scan of `evidence` rows for the exact scope, in one read transaction with the current policy and head. |
| Bound | `scan_limit` (default 256). More rows than the limit raises `comparison.raw_scan_exceeds_cap`; no tail is silently skipped. |
| Partition | `experience` or `development` only, accepted by the current policy. `evaluation` is never served. Items of another partition are counted, not selected. |
| Origin | The item's own origin and every root origin must be in `INDEPENDENT_ORIGINS`. Summaries, recall, REM, diary and generated answers are counted and rejected. |
| Policy / expiry / lineage | Existing `RuntimeStore._evidence_failures` over the item, its ancestors and root: integrity, expiry, authorization revision, purpose, partition acceptance, exclusions, synthetic flag. `retrieval._closure` checks ancestor partitions. Caller text is never consulted. |
| Fail closed | Missing or unreadable evidence, hash mismatch, non-UTF-8 bytes, missing/corrupt policy or head raise; nothing is planned. Excluded or otherwise ineligible items are omitted and counted. |
| Order / cap | `event_id` ascending, then `max_raw` (default 16, at most 64). Counts record scanned / eligible / selected / dropped-by-cap, and `raw_coverage` is `truncated_by_max_raw` whenever the cap cut anything. |
| No memories | A scope with no adopted head still freezes a raw baseline (`snapshot_sha256: null`); a fixed label hash stands in for the plan's snapshot binding. |
| Arms | A and B get the same frozen whole raw prefix under the same `ArmBudget` (unchanged Gate 4B packing). B may add consolidated records that the existing retrieval currently returns as eligible. |

## Freeze and live recheck

The frozen context stores selected event IDs with event/source/provenance hashes
and exact bytes, selected memory IDs/hashes and records, rules/caps/order, counts
and coverage, caller configuration, policy hash/revision, snapshot hash, and an `eligible_set_sha256`
over **all** eligible raw references (including those cut by the cap) and
memories. It is bound into the plan through `config.context_sha256`.

- An identical reopen reuses the saved bytes with no new scan; changed rules,
  caps or plan inputs raise `plan binding conflict`.
- Every dispatch, evaluation and report re-runs the scan and retrieval. A policy
  or head change, a changed eligible set, changed bytes, or any failure
  (revoked, corrupt, expired, missing) makes the plan `invalidated` (sticky).
- Nothing is written to the accepted store; no receipt is created or changed.

## Per-arm audit (`audit(plan_id)`, read-only)

Built from the immutable packed request in the plan plus the durable arm row.
Arms are identified by `plan_id` + `task_index` + `arm`; A and B may share a
request hash when no memory fits.

| Field | Meaning |
|---|---|
| `status` | `planned_not_dispatched`, `dispatch_intent_outcome_unknown`, `replied`, `completed`, `timeout`, `missing`, `invalid` |
| `raw_present` / `memories_present` | Exact IDs and hashes found in that arm's request |
| `raw_dropped` / `memories_dropped` | Whole records offered to that arm but cut by the byte budget |
| `delivery_confirmed` | Always `null`: the harness cannot observe delivery, reading or use |

The audit checks the plan digest, scope/configuration/frozen-context binding, each
request hash, arm identity/status/order, byte cap and exact allowed whole prefix.
It never dispatches or resends; an unknown outcome stays unknown. This is a
historical input/status audit, not a present-eligibility check; use `report` for the
live recheck. Audit reads of plan/status are not an atomic cross-connection snapshot.

## Honest limitations

- **Untested at this pre-CI snapshot.** Five new cases are selected explicitly;
  no historical suite is included. Frozen context is retained privately, not erased.
- **Not a fairness or completeness claim.** Reports keep `complete_raw_baseline: false`
  and `scientific_fairness_claim: null`. Order is `event_id`, not relevance; the
  raw arm has no query ranking while memories use the existing lexical ranking.
- **Multiple reads.** The raw scan is one transaction; the memory retrieval and
  each later recheck are separate reads. A change between scan and retrieval is
  detected only through head or policy hash.
- **Recheck-to-dispatch race.** A change between a live recheck and the fake
  dispatch that follows is not excluded. External policy systems are invisible.
- **Strict integrity classification.** Only policy ineligibility, expiry and
  non-synthetic flags may be omitted; every other integrity/lineage failure raises.
  A corrupt row in the scanned scope can stop the scan even in another partition.
- **Audit shows plan membership, not delivery.** `completed` means a fake reply was
  stored and scored, nothing more.
- The audit reads `ComparisonStore._plan` and the `comparison_arms` table directly;
  no public accessor was added.
- Local construction is not authentication. No CLI, live adapter, cost metering or statistics.

## Review boundary

Existing verification, lineage and transaction APIs were inspected. Runtime acceptance
remains pending at this pre-CI snapshot; the five cases exercise never-cited evidence,
null-head plans, generated-origin exclusion, corruption, freeze/reopen, exact audit
membership and durable unknown outcomes. They do not establish scientific fairness.

## Five test methods

```
test_raw_baseline.RawBaselineTests.test_uncited_raw_is_selected_independently_and_without_adopted_memory
test_raw_baseline.RawBaselineTests.test_exact_scope_partition_policy_and_integrity_fail_closed
test_raw_baseline.RawBaselineTests.test_frozen_reopen_binding_and_eligible_set_invalidation
test_raw_baseline.RawBaselineTests.test_equal_whole_record_budgets_have_exact_audit_membership
test_raw_baseline.RawBaselineTests.test_partial_and_unknown_outcomes_are_audited_without_replay
```

`tests/run_tests.py` defaults and the PR-only workflow select exactly these five
NEW methods. Gate 3 (23/5), Gate 4A (5/1), Gate 4B (10/2, exhausted) and Gate 4C
(5/1) are historical, not rerun or reset.

## 日本語要約

Gate 4Dは、統合記憶がどの証拠を引用しているかに依存せず、採用済み証拠storeから
生の証拠を選ぶ独立baselineと、各群の要求内容を読み取り専用で監査する機能です。
scopeとpartition（experience／developmentのみ）は厳密一致、現行policy・期限・
完全性・合成・系譜は既存の信頼済み検査を再利用し、生成・回想由来は拒否します。
走査は上限付きで、超過時は黙って切らずに失敗します。件数上限で切った場合は
`truncated_by_max_raw`と記録し、完全取得とは表示しません。両群は同じ生参照の
先頭部分と同じ予算を使い、B群だけが現在有効な統合記録を追加できます。採用記憶が
無くてもA群は成立します。計画は入力・規則・hashを固定し、同一再openは保存byteを
再利用、束縛変更は拒否、policy／head／有効集合の変化や破損は無効化します。
監査は「未送信」「送信意図のみ・結果不明」「完了／timeout／欠落／無効」を区別し、
要求に実際に含まれるID・hashと予算で落ちた記録を列挙します。配信・既読・利用は
確認できないため常に`null`で、不明な作業は再送しません。
**コードのみ保存、未実行・未テスト・未マージ。** 公平性・性能の主張はなく、
走査後の取得や再確認から送信までの間は非atomicです。
