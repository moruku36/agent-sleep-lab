# ゲート3：監査付きの論理忘却

[English](gate-3-forgetting.md) | **日本語** | [実装状況](implementation-status.ja.md)

`feat/gate-3-audited-forgetting`に実装済みですが、**未検証・未マージ**です。合成データ用のローカルライブラリで、実agent接続や物理削除ではありません。取得（PR #13）とrollback（PR #14）はマージ済み。[レビューと予算記録](../reports/gate-3-forgetting-progress.md)。

## API（説明用・未実行）

```python
from agent_sleep_lab.adoption_candidates import build_forget_request

# store: 既存AdoptionStore、control: 明示設定したControlBoundary
scope = {"project": "p", "task_family": "t"}
preview = store.plan_forget_impact(scope=scope, event_ids=["e-2"])
request, request_sha256 = build_forget_request(
    operation_id="forget-1", run_id="synthetic-forget",
    scope=scope, expected_policy_revision=preview.policy_revision,
    event_ids=["e-2"],
)
result = store.commit_forget(request_bytes=request, control=control)
receipt = store.resolve_operation("forget-1")  # 応答消失を照会で解決
```

対象は`memory_ids`／`event_ids`／`root_ids`。最低1個、各種最大16・合計32個のIDを指定します。builderは重複除去・整列し、保存requestは一意で整列した配列を要求。IDだけを指定し、本文を渡しません。対象はすべて同じproject・task_family内の既存行、rootはroot eventであることが必要です。未知・別scope・非rootは同じ`forget.target_unavailable`。memoryのbytes・hash・schema、対象eventの完全性を確認しますが、許可の期限切れだけでは忘却を妨げません。破損証拠では停止するため、破損データの救済APIではありません。

## 原子性と監査

- dry runは同一接続の読取りtransactionで、書込みなし。対象／新規除外ID、影響するevent・memory、保持snapshotのmember参照、現在headへの影響と決定的hashを返します。event／rootの派生先と依存memoryを追い、memoryだけの指定では共有証拠や無関係なmemoryを除外しません。参照数には履歴の非active memberも含みます。
- previewは**ロックされた承認tokenではありません**。hashはscope・policy版・対象／新規除外・影響ID／参照・現在head／影響フラグを含みます。commit自身のtransactionで再計算するため、policy版が不変でも途中のcapture／adoptionで影響は変わり得ます。
- 1つの`BEGIN IMMEDIATE`でoperation照会、policy版CAS、同一scopeの対象解決・影響再計算を行い、次のpolicy版と不変request／receipt行を一括保存。途中で失敗すればどちらも残りません。既存除外と無関係な許可・目的・partitionは保持し、明示control境界が実行者・時刻を記録します。
- 古い版は`adoption.policy_conflict`、全対象が既に除外済みなら`forget.no_new_exclusion`。拒否はIDを消費しません。policyの除外上限（各種1,024個）を超えれば全体を拒否します。
- 新artifactは`agent-sleep-forget-request/1`と`agent-sleep-forget-receipt/1`。採用v1/v2・rollbackは不変、保存v3のtableを再利用し移行不要。journalのmanifest／source列は空。旧readerは新しい行種別を解釈できず、ダウングレード保証はありません。
- receiptはrequest hash、scope・run監査ラベル、変更前後のpolicy版・結果hash、追加ID、影響hash・件数、`outcome: logically_forgotten`、`physical_erasure: not_performed`。原文を複製しません。
- 完全再送は再open・後続policy変更の後も過去の受領だけを返し、policy／headを再更新しません。同一IDで別内容・別操作種別は競合。照会では前後policyのhash・版・正確な除外差分・無関係な方針の維持を照合します。現在の利用許可を与えるものではありません。
- head・memory・snapshot・過去受領は保持。次の取得は現在除外を反映し、採用／rollbackは除外されたactive memberが1件でもあれば全体を拒否します。全員が適格な過去snapshotへの復元は可能です。

## 合成実装の走査上限

途中切捨てはせず、scope event 4,096・scope系譜link 32,768・**保存memory全体4,096／snapshot全体1,024**・影響snapshot参照16,384を超える取得は停止します。memory／snapshot表にscope索引がないため、別scopeの行も全体上限に含みます。既存artifactのbyte・member上限も適用。これは保守的な取得件数上限で、一定時間・使用byteメモリ量・DB全体の走査費用の保証ではありません。完全性・祖先・journal／policy照会には従来の費用が残ります。

## 限界

**論理除外のみ**です。原証拠・本文・SQLiteページ・保持履歴・backup・呼出し側の取得済みbundle・外部cache／index／日記・出力は消しません。渡し済みbundleは回収不能。無関係な新ID・系譜に同内容を再登録することを内容hashで抑止しません。物理掃除・安全消去・内容単位の再取込抑止・run認証／登録・実利用者の認証・評価中の取得固定・渡したmemory記録は未実装。境界は模擬設定で認証情報ではなく、ゲート3全体の完了や性能改善も主張しません。

## 検証待ち

`tests/test_forgetting.py`は重点3メソッド：scope付き影響とpolicy／journal原子性、取得・採用・rollbackでの派生先非復活、policy CAS・ID競合・応答消失後の再open／完全再送。**本体は0項目実行**で、選択一覧は受入ではありません。同じゲート3試行は10項目・3回で枠を使い切り。次は追加3項目をPR CI1回（累計13項目・4回）だけ実行する承認が必要です。ローカル再実行・過去全件回帰はしません。PR作成自体がCIを起動するので、増枠までPRも作成しません。
