# 読み取り専用OSSリクエスト準備

[English](oss-prepare.md) | [ランタイム手順](runtime-guide.ja.md)

`oss-prepare`は、既存storeの採用済み**合成・経験用記憶**を、
固定したOSS Contributorのリクエスト生成経路へ渡します。
記憶なし／ありの入力をオフラインで準備するだけで、送信しません。
実運用への配送、実データ取込み、意味的利用や性能改善の証拠ではありません。

## 使い方

```sh
agent-sleep-lab oss-prepare --manifest /private/run/prepare.json --store-config /private/run/store.json
```

store設定は[既存の例](../configs/runtime-store.example.json)と同じ厳密な境界検証を使います。
対応schema・現在policy・採用済み記憶のあるSQLiteファイルを明示してください。
初期化・migration・記憶採用は行いません。境界の名前はローカル模擬設定であり、
呼出者やstoreの認証ではありません。

manifestは以下の厳密なJSONです。重複キーと未知fieldを拒否します。

```json
{
  "protocol": "agent-sleep-oss-prepare-input/1",
  "target_repo": "/absolute/local/oss-contributor-agent",
  "bridge": {
    "scope": {"project": "p", "task_family": "t"},
    "repository": "moruku36/oss-contributor-agent",
    "agent_commit": "e40b39c6258ac5a4446c38246bdfd7f5dc5dbf7b"
  },
  "retrieval": {"query": "duplicate", "max_bytes": 32768, "max_records": 16}
}
```

manifestと設定は各32,768 bytes以内。queryは空でない表示可能文字列、最大1,024文字です。
max_bytesは1〜32,768、max_recordsは1〜256の整数で、booleanを認めません。
byte上限はcanonical bundle全体のUTF-8 bytesであり、token・金額上限ではありません。
対象repoは既存の絶対directoryを指定します。既存parentが固定Git objectと確認済みblob hashを
検証し、対象worktreeはimportしません。origin URLはローカルの未認証な申告です。

## 読取り→準備→再確認

1. 既存storeをread-only／query-onlyで開き、明示scopeの現在policyに適合する採用済み経験記憶を取得。
2. 取得結果が空なら対象コードの準備前に拒否。
3. 正確なbundle bytesを固定し、既存の組込みprompt-capture workerを両群まとめて1回だけ実行。
   記憶あり群だけに上限付きの非信頼参考データを挿入。出典・frame・入力・比較可能性の検証を維持。
4. 新しい読取りtransactionで再取得し、版・policy・記録・その他contextの変化や失効を拒否。
   取得時刻`as_of`だけは更新可能。
5. protocol `agent-sleep-oss-prepare-output/1`、`synthetic_only`、
   context hash、検証済みsummary、capture文書を1つのJSONで出力。

成功はexit 0。失敗はexit 2、artifactを出さず、入力path・worker本文・例外詳細を
繰り返さない一般化diagnosticを出します。自動retryはありません。
provider・adapter・worker argv・transport・plugin・journal・出力fileの指定を受け付けません。
推論・capture・受領登録・採用・対象設定やledgerの変更はありません。
SQLiteのlock／sidecar利用はあり得て、filesystem隔離ではありません。

出力には**合成の記憶本文とrequest payload全文**が含まれます。runtime出力は非公開で扱い、
stdoutを公開許可一覧と見なさないでください。後続推論への許可にもなりません。
出力後にもpolicyは変わるため、将来のconsumerは現在contextを再検証する必要があります。
永続dispatch journalや敵対コード向けsandboxではありません。

## 検証の範囲

現時点の証拠は[実装状況](implementation-status.ja.md)に集約します。
契約テストは一時的な実storeと明記したstand-in workerを使います。
固定された実対象コードでの別のローカル受入も可能ですが、いずれもモデルを呼ばず、
storeの認証・意味的利用・性能改善を証明しません。
