# ゲート3：scope付き取得ライブラリ（最初の単位）

[English](gate-3.md) | **日本語** | [実装状況](implementation-status.ja.md)

状態：**`feat/gate-3-scoped-retrieval`で実装・ローカル重点検証済み、未マージ。** 合成4項目を1回実行し、0.782秒で全合格。CIは未実施で、同じ試行の上限10項目内に3項目を予約。初期版全体は約40%。ゲート3全体・rollback／削除・採用の追加受入・live接続は未完了です。

契約の根拠：[契約書 5〜6節](contracts-and-acceptance.ja.md)。既存の`AdoptionStore`に対する読み取り専用ライブラリ（`src/agent_sleep_lab/retrieval.py`）です。writer／採用の意味は変えません。

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

## 限界

- 合成限定。rollback・削除／cache掃除・run登録・adapter・呼出し側の認証・本番利用・live agent接続ではありません。
- 順位は簡易で決定的な規則で、品質を主張しません。性能改善は主張しません。
- 除外はmemoryとその証拠の祖先に適用し、query文字列には適用しません。
- 評価中のsnapshot固定（撤回は適用し続ける）と、渡したmemoryの記録は未実装です。
- `eligibility_failures`、`_head`などはwriterと同様に使うstore内部で、公開APIの約束ではありません。

## ローカル重点受入

`.venv/bin/python tests/run_tests.py --limit 4 test_retrieval.RetrievalTests`をmacOS arm64／Python 3.13.18で1回実行、4項目が0.782秒で全合格。同じ試行は4項目・1回実行で、CIは未実施。全件回帰・既存writerテストの再実行なし。[受入記録](../reports/gate-3-retrieval-progress.md)に残る境界を記載します。

`tests/test_retrieval.py`は4メソッドのみ：通常の上限付き取得、scope／partition絞込み、撤回・祖先除外、破損時の安全停止と正常な0件。`tests/run_tests.py`の既定は3項目（絞込みは名前指定）。試行の上限はCI込みで合計10回です。[テスト運用](testing-budget.ja.md)を参照。
