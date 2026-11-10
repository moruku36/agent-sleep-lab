# ゲート3：scope付き取得ライブラリ（最初の単位）

[English](gate-3.md) | **日本語** | [実装状況](implementation-status.ja.md)

状態：**scope付き取得は[PR #13](https://github.com/moruku36/agent-sleep-lab/pull/13)でMERGED**（merge commit `9e3d1107f96034b61a812ab2a5abb1c95ef5eaba`、マージ確認済み）。マージ前にローカル重点4項目を1回実行して0.782秒で全合格、PR CI 3項目がhead `90b3d9e`で合格（当時の記録であり、後続commitの保証ではありません）。**下記のrollbackは別の単位で、`feat/gate-3-safe-rollback`上の実装済み・未実行です。未マージで、PRで3項目のCIを1回実行するまで未検証です。** それまで初期版全体は約40%のまま。ゲート3全体は未完了です（[未実装](#未実装)参照）。

契約の根拠：[契約書 5〜6節](contracts-and-acceptance.ja.md)。取得の単位は既存の`AdoptionStore`に対する読み取り専用ライブラリ（`src/agent_sleep_lab/retrieval.py`）です。writer／採用の意味は変えません。

## API

```python
from agent_sleep_lab.retrieval import retrieve_reference_bundle

bundle = retrieve_reference_bundle(
    store,                      # AdoptionStore（自身の接続と検証者境界を使用）
    scope={"project": "p", "task_family": "t"},   # 完全一致。空でない文字列2つ
    max_bytes=8192,             # 必須。bundle全体の直列化後UTF-8 byte数
    partition="experience",     # "experience" | "development"。"evaluation"は配布しない
    query=None,                 # 任意の短い文字列。順位付けだけに使用
    max_records=16,             # 1〜256
)
bundle.document      # dict（参考データであり指示ではない）
bundle.bundle_bytes  # 予算と照合した正確なbyte列
bundle.bundle_sha256, bundle.used_bytes
```

## 動作

1. storeの接続で遅延型の読取りtransaction（`BEGIN`〜`ROLLBACK`）を1つ開き、head・snapshot・現在policy（除外はpolicy chainの一部）・memory・受領・証拠を呼出し全体で同じ時点に固定します。書込みはしません。
2. headとsnapshotは過去のメタデータで、候補の選択にだけ使います。`active`の各memberを順位付けの前に**現在の**policyで再確認します。
   - memory本文がsnapshotのhashと契約に一致、scope完全一致、`valid_until`未経過
   - `eligibility_failures`が空：設定済み検証者による登録済み・confirmed・期限内の受領がmemory hashとscopeに結び付き、全証拠と**全祖先・root**の完全性、現在の許可版、許可された目的／partition、synthetic、除外（memory・event・root）に該当しない
   - 受領とmemoryの証拠集合が一致、全祖先が指定partition、種別／起源の規則（例：preferenceは利用者訂正のroot）を満たす
   「verified」は登録済みconfirmed受領のことで、memory自身の`status`文字列ではありません。未採用candidateとsnapshot内の`stale`・`superseded`は返しません。不変の元本文に`status: candidate`が残る場合も、recordの`eligibility: verified`は現在の登録受領に基づく判定で、本文の自己申告とは区別します。
3. **安全側に停止**：policy・schema・head・snapshot・journal・active memoryの欠落や破損は`StorageError`で、部分的なbundleは返しません。不適格や期限切れは除外（件数のみ、IDは出さない）。**適格0件は正常結果**です（未初期化scopeも同様）。
4. 順位：claim／tagsに含まれる異なる検索語の数（小文字化・空白分割）、次に`memory_id`。queryなしは`memory_id`順。モデル・embedding・通信は使いません。
5. 予算：受入済みtokenizerがないため、単位は**正規直列化bundleのUTF-8 byte数**（`budget.unit`、`budget.tokenizer: null`）です。tokenとは呼びません。低順位のrecordは丸ごと、末尾からまとめて落とします（上位を落として下位を残すことはない）。残したrecordのscope・根拠参照・hashは切りません。headerだけで`max_bytes`を超えると`retrieval.budget_too_small`で失敗します。

## bundleの項目

`schema_version`、`reference_data_only`、`synthetic_only`、`scope`、`partition`、`as_of`、`snapshot_sha256`（headなしはnull）、`policy {revision, sha256}`、`exclusions {version, policy_sha256}`（除外版＝policy版）、`budget`、`counts {active_members, eligible, returned, dropped}`（適格総数は上限適用前、省略数は件数・byte両上限を含む）、`records`。各record：`eligibility: verified`、`rank`、`score`、`memory_id`、`memory_sha256`、`kind`、`verification_receipt`、`evidence`（event／source／provenanceのhash）、memory全体。

## 安全なrollback（CIまで未実行）

明示的な**制御上の復旧**です。同一scopeで保持済み・過去に採用済みのsnapshotを復元します。新しいモデル候補の採用ではなく、評価受領は不要で、**性能や評価の主張ではありません**。

```python
from agent_sleep_lab.adoption_candidates import build_rollback_request

request_bytes, request_sha256 = build_rollback_request(
    operation_id="rb-1",            # 新規ID。採用・rollbackを含め再利用しない
    run_id="my-audit-label",        # 呼出し側の監査ラベル。認証済みrunではない
    scope={"project": "p", "task_family": "t"},
    expected_head_snapshot_sha256=head_hash,    # 現在headのcompare-and-swap
    target_snapshot_sha256=target_hash,         # 同一scopeで保持済みのsnapshot
    expected_policy_revision=policy_revision,   # 現在policy版のcompare-and-swap
)
result = store.commit_rollback(request_bytes=request_bytes)   # AdoptionResult
store.resolve_operation("rb-1")  # 応答消失時の照会。過去の受領bytesを返す
```

契約上の判断：

1. **版付きの追加artifact。** `agent-sleep-rollback-request/1`と`agent-sleep-rollback-receipt/1`（`outcome: rolled_back`）を専用schemaで追加。採用request／receipt v1/v2のschemaとbytesは不変で、既存journalは変わらず再生できます。保存の移行は不要：v3のtableを使い、rollbackのjournal行はrollbackのrequest／receiptを保存し、manifest／source列は**空**にします（空以外は`adoption.journal_corrupt`）。旧コードはrollback行を読めません（前方のみ、ダウングレードは主張しません）。
2. **1つのwriter transaction（`BEGIN IMMEDIATE`）。** operation照会 → 現在policy版のCAS（`adoption.policy_conflict`）→ scope headのCAS（`rollback.head_conflict`）→ 対象の存在・scope確認（`rollback.target_unavailable`、`rollback.scope_mismatch`）→ **対象のactive memberすべて**の再確認 → journal行（request digest＋受領）とheadを一括更新。headがnullのscopeは不可（未初期化への復元は非対応）。対象は期待headと異なる必要があります（契約検査）。
3. **全件か無か。** 対象の各active memberを採用writerと同じ規則で再確認：本文／hash／契約、期限、登録済みconfirmed検証受領、証拠と**全祖先・root**、現在の許可版、許可された目的／partition、除外、種別／起源の規則。1件でも失敗すればrollback全体を拒否します（`adoption.ineligible`、`candidate.memory_expired`、`adoption.memory_missing`など）。黙って絞り込み・書換え・部分復元はせず、headと履歴は不変。`stale`／`superseded`のmemberは記録どおりに引き継ぎます。
4. **過去の許可は復活しない。** headを戻しても古い許可は戻りません。取得も次の採用も現在policyで再確認し、除外されたmemoryは除外されたままです。元のsnapshot・memory・受領・証拠・過去のjournal行は変更しません（append-onlyのtriggerは維持）。
5. **冪等性。** 同じbytesの完全再送は、head書込みも現在状態の再判定もせず過去の受領を返します（`status: replayed`）。後からの撤回や再openの後でも同じです。同じoperation IDで内容が違えば`adoption.operation_conflict`。拒否されたrollbackはoperation IDを消費しません。
6. **rollback後の採用。** 新しいheadは復元したsnapshotで、次の採用はそれを期待親版に指定して従来どおり動きます。取得も同じ経路でheadを読みます。
7. 「過去に採用済み」には、保持snapshotと、hash・同一scopeが結び付く元の`adopted` journal受領の両方を同じtransactionで要求します。孤立blobだけでは拒否（`rollback.target_not_adopted`）し、新しい評価の合格とは扱いません。合成限定の実装ではローカルjournalを走査して元受領を探します。

未実装：物理削除／purge／cache掃除、評価中のsnapshot固定、渡したmemoryの記録、run認証・登録。`tests/test_rollback.py`の3項目（scope内の成功と後続採用／現在の撤回による拒否とhead・履歴不変／古いhead・ID競合・完全再送を再open越しに確認）は**未実行**で、PR CIの1回に予約しています（3項目）。

## 未実装

削除・物理purge・cache掃除、評価中の取得固定、渡したmemoryの記録、ゲート2B全体の受入、Light/Deep生成、比較評価、adapter接続はいずれも未完了です。ここにゲート3全体や性能の主張はありません。

## 限界

- 合成限定。削除／cache掃除・run登録・adapter・呼出し側の認証・本番利用・live agent接続ではありません（rollbackは上記のとおり未実行）。
- 順位は簡易で決定的な規則で、品質を主張しません。性能改善は主張しません。
- 除外はmemoryとその証拠の祖先に適用し、query文字列には適用しません。
- 評価中のsnapshot固定（撤回は適用し続ける）と、渡したmemoryの記録は未実装です。
- `eligibility_failures`、`_head`などはwriterと同様に使うstore内部で、公開APIの約束ではありません。

## ローカル重点受入

履歴（2026-11-10、取得の単位）：`.venv/bin/python tests/run_tests.py --limit 4 test_retrieval.RetrievalTests`をmacOS arm64／Python 3.13.18で1回実行、4項目が0.782秒で全合格。その後PR CIの3項目がhead `90b3d9e`で合格し、PR #13はマージ済みです。[受入記録](../reports/gate-3-retrieval-progress.md)に残る境界を記載します。旧writer試行（**19項目・5回**）は履歴で、枠は使い切り済みです。

現在の試行の集計（同じゲート3の試行）：**10項目中、7項目・2回実行を使用済み**（取得のローカル4＋CI3）。rollbackの単位は**実行0項目**で、残り3項目はPR CIの1回に予約しています。そこで失敗すると余裕はなく、追加実行には所有者の明示的な増枠が必要です。

`tests/test_retrieval.py`は4メソッド（変更なし）。`tests/test_rollback.py`はちょうど3メソッド。`tests/run_tests.py`の既定はrollbackの3項目に変更（上限10は不変、取得の項目は名前指定で選択可）。[テスト運用](testing-budget.ja.md)を参照。
