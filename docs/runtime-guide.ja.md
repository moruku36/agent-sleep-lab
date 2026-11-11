# ランタイム手順

[English](runtime-guide.md) | **日本語** | [実装状況](implementation-status.ja.md)

以下は実装した入口です。実API成功・既存agent接続の完了とは区別してください。既存の合成限定v3採用storeと、独立した境界・policy・登録済み受領が必要です。CLIはstore未存在やjournalとの同一パスを拒否し、権限・検証受領を自動作成しません。

## 設定

[store設定例](../configs/runtime-store.example.json)を非公開ファイルへコピーし、既存のSQLiteパス、capture／verifier／evaluator境界、許可手順・protocol・hashを合わせます。これはローカル模擬境界の設定であり認証情報ではありません。APIキーは書きません。設定をPythonとして実行せず、パスは作業ディレクトリ基準です。

## Light／Deep

```sh
agent-sleep-lab sleep --store-config private/store.json --manifest configs/sleep.example.json --journal private/sleep.sqlite --provider script --replies configs/sleep-replies.example.json
agent-sleep-lab sleep-status --journal private/sleep.sqlite --run-id sleep-public-fixture-1
```

runにscope、event ID、設定、上限、候補の観測時刻を固定します。原証拠本文とevent／source／provenance hashは現在適格なstoreから取得し、モデル呼出しの前後でpolicy・head・本文を再検査します。Deepはop／memory_id／Lightが選んだevent_ids／生成claimだけを返します。生成文を保持した未検証candidateを作り、trusted preparerの別文へのすり替えを拒否します。独立検証・評価・既存writerによる採用は引き続き必須です。IDだけの旧version 1は偽provider限定です。

有料MiMoを明示選択する場合：

```sh
agent-sleep-lab sleep --store-config private/store.json --manifest configs/sleep.example.json --journal private/sleep.sqlite --provider mimo --agent YOUR_REGISTERED_AGENT
```

登録済みOpenClawアカウントを使い、モデルはxiaomi/mimo-v2.6-pro固定です。本packageから認証ファイルやAPIキーを読み出しません。shellを使わずargvで起動し、provider・モデル・fallbackなしの受領を照合します。実行前に回数を消費し、sleepは最大2段階、transport上限120秒、自動再試行なしです。

**CLIには呼出しごとの最大出力token指定がなく、byte上限は生成後の検査です。金額・tokenの厳密な生成上限とは呼びません。** 不明終了でも課金された可能性があります。所有者の明示的な有料利用指示とアカウント側の予算内で使い、CIからは呼びません。

中断したprovider／準備callbackは再実行しません。古いworkerの停止を確認した後だけrecover_stopped_provider／recover_stopped_preparationを呼ぶと、結果不明のincompleteへ進めます。登録済みartifact・受領は別途照合し、新しい操作で二重実行しないでください。

## 採用・取得

```sh
agent-sleep-lab adopt --store-config private/store.json --manifest private/prepared-adoption.json
agent-sleep-lab retrieve --store-config private/store.json --manifest configs/retrieve.example.json
```

採用入力は独立したtrusted preparationが作るrequest_bytes／manifest_bytes／source_manifest_bytesのhex文字列と、memory_bytesのID→hex mapです。モデルの自己申告receiptを使わず、CLIからreceiptを登録しません。既存writerが期待親版、現在policy、原証拠、独立検証・評価受領を再検査します。取得は現在の適格性を確認し、queryの有効語がある場合はスコア0を除外します。queryなしの一覧は可能です。

## 対応比較

```sh
agent-sleep-lab compare --store-config private/store.json --manifest private/comparison.json --journal private/comparison.sqlite --provider mimo --agent YOUR_REGISTERED_AGENT --rubric private/exact-match-rubric.json
```

manifestはplan_id、1〜5件のtasks（task_id／prompt）、retrieval（scope／max_bytesなど）、budget（各群calls／request_bytes／reply_bytes）、config、evaluator_identity（name／version／protocol_sha256）を持ちます。解答は別の非公開rubricファイルでtask ID→期待文字列として与え、canonical JSON hashをprotocol_sha256へ固定します。解答はprovider依頼へ入れません。完全一致の機械的fixture採点は、独立した論文品質評価ではありません。実応答でも合成rubricであることを表示します。

原証拠は`retrieval.query`を指定しても既定ではevent ID順です。
`retrieval.raw_order: "query_overlap_descending"`の明示指定で、既存の上限付きqueryと
日英の語抽出を使い、raw件数上限・byte packingより先に全適格原証拠を順位付けします。
重なり0の行も分母に残します。[API／manifest契約](raw-query-ranking.md)に検証、
順位方式・queryの固定と旧planの互換性を記載しています。両群のraw prefixは同一で、
公平性・改善の証拠にはなりません。

各群の予算は同一で実行順を交互にします。詰めたA/Bが一つでも同じなら、登録・呼出し前に拒否します。原ログを減らすか上限を増やしてください。ライブラリのdiagnostic_only=Trueは入力監査だけに使え、comparable:false／comparison:nullとなります。原ログの完全record・prefix監査を維持します。受領・結果不明状態は非公開journalへ残し、不明intentを再送しません。実API費用は不明のまま保持し、合成0費用や節約実績としません。

[5課題fixture](../examples/paper-pilot/README.md)は実応答試行の準備であり、実施済み・独立holdoutではありません。研究ノートhandoffの対象はrepo名と40桁commitを呼出し側が明示し、libraryへ固定しません。
