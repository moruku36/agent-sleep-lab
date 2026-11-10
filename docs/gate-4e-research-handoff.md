# Gate 4E — manual research-notes request/result handoff journal

[Home](../README.md) | [Status](implementation-status.md) | [Gate 4D](gate-4d-raw-baseline.md)

**Pre-CI snapshot (2026-11-10): saved and reviewed on `feat/gate-4e-research-handoff`;
NOT executed, NOT tested, NOT merged at this commit.** Zero of the trial's ten
case executions are used. Subsequent results are in PR checks, not an extra status-only push.
This is preparation for one existing-agent integration: a draft exchange journal.
It is not live delivery, not an agent connection and not a quality, cost or
model-performance experiment. The last verified overall estimate (about 45%) is
unchanged by this document. 日本語の要約は末尾にあります。

- Module: `src/agent_sleep_lab/research_handoff.py` (`ResearchHandoffJournal`)
- Tests (code only): `tests/test_research_handoff.py`
- Existing runtime libraries are unchanged. The focused runner/workflow and bilingual status are aligned before CI.

## Fixed target

`moruku36/independent-tech-research-notes` at commit
`b6ba067024c908cc931fc582c9904cb4596877da`, observed read-only by the main
assistant. The module holds this as a constant; there is no transport URL and
nothing fetches, edits or posts to that repository. Allowed outputs are exactly
`surveys/<topic>/<slug>.md` and `surveys/<topic>/<slug>.ja.md`. The template
headings and overview labels are stored as data for a mechanical check; they
grant no permission and are not instructions. No real note is copied; every
fixture draft is fictional.

## Contract

| Area | Behavior |
|---|---|
| Source of content | One frozen `RawBaselineComparison` plan + `task_index` + `arm`. The packed request bytes come from the plan after `audit()` verifies plan digest, context binding and request hash. Callers cannot supply replacement references. |
| Envelope | Canonical bounded JSON (at most 262,144 bytes): protocol version, handoff ID, plan/context hashes, task/arm, scope, frozen policy hash and head binding, target repository + commit, the two output paths, exact packed request + hash + size, `draft_only`, `references_untrusted`, `reference_data_only`, `grants_permissions: false`, response limits and keys. Evaluator identity, answers, model label and caller config are not exported. |
| Paths | `topic` and `slug` must each match ASCII `[a-z0-9]+(-[a-z0-9]+)*`, at most 64 characters, and may not be `template`. This excludes traversal, absolute paths, backslashes, control characters, dots, upper case and non-ASCII lookalikes. |
| Prepare | Idempotent, immutable binding. A changed plan/task/arm/path/protocol for the same ID raises `handoff binding conflict`. A unique plan/task/arm slot within the journal prevents a new ID from resending the same arm. Existing non-invalidated preparations are rechecked too. Stale context, invalidated plan or an already-dispatched matching comparison arm is refused. |
| Claim | One time. The row moves `prepared → export_intent_outcome_unknown` in a single conditional update before the bytes are returned. A repeated or reopened claim raises and never returns the packet again. Status keeps the request hash for reconciliation. Returned bytes are not delivery, reading or use. |
| Live recheck | Before preparing, before releasing the packet and before accepting a result: the Gate 4D live check (policy, head, eligible set, evidence bytes) plus plan and arm status. A failure sets `invalidated` (sticky); a frozen context is never refreshed. |
| Result import | Malformed input is rejected before journal mutation (a live eligibility failure instead records invalidation): bytes only, at most 131,072 bytes total, strict UTF-8 JSON with duplicate keys rejected, exact key set, exact protocol/kind/ID/request hash/plan/task/arm, exactly the two allowed paths, each output non-empty text of at most 49,152 UTF-8 bytes. Only a claimed handoff can receive a result. Identical re-import is idempotent; different bytes raise `handoff result conflict`. |
| Result state | `received_unreviewed`. Not adopted, not verified, not captured as evidence, not scored, not proof that an agent ran. Draft text is never parsed for instructions or executed. |
| Structure check | Mechanical only: headings present in order, three overview labels, a link to the other language file, 6–7 `- ` lines under the practical-reading heading. Reported with an explicit limits label; it never rejects a result and is not a semantic, alignment, quality or real-paper assessment. |
| Status | `prepared`, `export_intent_outcome_unknown`, `received_unreviewed`, `invalidated`, with exact hashes and paths, `delivery_confirmed: null`, `agent_execution_confirmed: null`, `requires_human_review: true`, `adopted: false`, `verified: false`. Status never contains the packet. |
| Separation | Only the private journal is written. No draft file, accepted-store change, `ComparisonStore` reply/score/arm row or adoption receipt is created; no agent, network or model is called. |

## Honest limits

- **Untested at this pre-CI snapshot.** Five NEW methods only; no historical suite.
- **Not authentication.** Anyone who can open the journal and stores can prepare and claim; the trusted host is assumed.
- **Two databases, no shared transaction.** The journal and the comparison store are separate SQLite files. A fake comparison run started after a handoff is prepared is noticed only at the next recheck (claim or import), and a run started after a claim is not prevented.
- **Recheck-to-use race.** Policy, head or evidence can change after a recheck and before the caller uses the returned bytes; external policy systems are invisible.
- **Unknown stays unknown.** There is no retry, timer, resend or operator path to re-release a claimed packet or to resolve a lost one.
- **Stored results are retained, not erased.** Re-import of identical bytes and `unreviewed_result` recheck eligibility; later revocation invalidates and withholds the draft, but cannot recall bytes already released. Read-only `status` is historical journal state, not a live eligibility promise. Journal request/binding and result hashes are checked before use.
- **The bytes are returned in memory.** What the caller does with them (files, chat, another tool) is outside this module and unrecorded.
- **`unreviewed_result` returns eligible stored draft bytes** for a human reviewer after recheck; they remain untrusted data. A failure invalidates the journal row and does not return the draft.
- The main assistant read the target templates at the pinned commit; the worker used that observation without a network call. Template presence checks do not prove substantive compliance, and a future target commit requires separate review.

## Five test methods

```
test_research_handoff.ResearchHandoffTests.test_envelope_binds_frozen_arm_target_and_paths_without_answers
test_research_handoff.ResearchHandoffTests.test_prepare_is_stable_across_reopen_and_rejects_changed_binding
test_research_handoff.ResearchHandoffTests.test_claim_is_one_shot_and_leaves_durable_unknown_outcome
test_research_handoff.ResearchHandoffTests.test_result_import_is_strict_bound_idempotent_and_unreviewed
test_research_handoff.ResearchHandoffTests.test_policy_or_evidence_change_invalidates_before_export_and_import
```

`tests/run_tests.py` defaults and the PR-only workflow select exactly these five
NEW methods. Gate 3 (23/5), Gate 4A (5/1), Gate 4B (10/2, exhausted), Gate 4C
(5/1) and Gate 4D (5/1) are historical and not rerun or reset.

## 日本語要約

Gate 4Eは、固定済みのGate 4D計画の1群（plan＋task_index＋arm）から、研究ノート用の
依頼封筒（JSON）を作り、信頼しない下書き結果を受け取るための**手動の受け渡し台帳**
です。対象は `moruku36/independent-tech-research-notes` のcommit
`b6ba067024c908cc931fc582c9904cb4596877da` に固定で、出力は
`surveys/<topic>/<slug>.md` と `.ja.md` の2つだけです。封筒には固定済みの要求byte・
hash、計画／文脈hash、scope、policy／head束縛、下書き専用・参照は信頼しない旨を含め、
評価者の答えや設定は含めません。準備は冪等で束縛は不変、変更は拒否します。
取り出しは1回だけで、byteを返す前に「送信意図・結果不明」を保存し、再openや
同じ群に対する別IDでも再取得できません。byteを返したことは配信・既読・利用の確認ではありません。
結果は厳密に検証してから `received_unreviewed` として保存し、採用・検証・評価・
実行はしません。準備・取り出し・受入の前に現行policy／head／証拠を再確認し、
保存済み下書きの再取り出しや同一返答の再受入も再確認し、撤回後は無効化・非開示に
しますが、既に渡したbyteの回収や物理削除ではありません。雛形の構造確認は機械的なもので、
内容や品質の評価ではありません。**コードのみ保存、未実行・未テスト・未マージ。**
認証なし、2つのDB間の同期なし、再確認から利用までの競合、再送手段なしは未解決です。
