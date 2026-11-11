# ランタイム手順

[English](runtime-guide.md) | **日本語** | [実装状況](implementation-status.ja.md)

コマンド契約は実API成功・既存agent接続の完了とは区別してください。自己完結した`demo`以外には、既存の合成限定v3採用storeと、独立した境界・policy・登録済み受領が必要です。通常のruntime CLIはstore未存在やjournalとの同一パスを拒否し、権限・検証受領を自動作成しません。

既存のOSS対応比較／cohortには、実行optionを持たない明示的offline reader
`oss-cost-report --manifest local/report.json`を使います。
[読取り専用CLI・manifest・SQLiteの制限](oss-cost-accounting.md#read-only-cli-and-input-manifest)を参照してください。

## 組込みオフラインdemo

```sh
agent-sleep-lab demo
```

`--help`だけを受け付け、呼出し側のデータ、file path、store、出力先、manifest、
provider／live optionは実行前に拒否します。組込みの合成catalog観測と定型返答だけを使います。
この経路にはnetwork、subprocess、実provider、認証情報の読出し、fallback、schedule、
既存agentの実行は含みません。現在の検証結果は[実装状況](implementation-status.ja.md)に集約します。

毎回新しい一時directoryに、証拠／採用・sleep・比較用の別々のSQLite storeを3つ作ります。
capture境界とpolicyはローカルfixtureで、既存storeや権限を入力にしません。
成功・失敗とも接続を閉じて一時状態を削除します。固定fixture時刻
`2026-11-12T00:00:00Z`より後の`2026-11-13T00:00:00Z`を証拠の利用期限に設定し、
実環境の許可には使いません。完了・削除後だけ`temporary_state_removed:true`を含むJSONを
出力し、エラーは成功reportなしのexit 2で返します。

正常完了時の件数は以下の通りです。fixture操作の件数であり、実model呼出しや
独立に受け入れた性能結果ではありません。

| 操作 | 件数 |
|---|---:|
| 経験eventのcapture | 2 |
| 定型Light／Deep呼出し | 1／1 |
| 生成したpending candidate | 1 |
| ローカル原証拠一致検証／登録した検証受領 | 1／1 |
| ローカルsnapshot評価／検査項目／登録した評価受領 | 1／4／1 |
| 通常writerによる原子的採用 | 1 |
| 取得した適格記憶 | 1 |
| 対応課題／定型タスク呼出し／別評価器の呼出し | 2／4／4 |

Deepは生成claimを保持した未検証candidateを出します。別のtrusted fixture preparerが
capture原文との完全一致、証拠bindingの不変性、生成claimとcandidate snapshotを確認し、
通常のverifier／evaluator APIで受領を登録します。providerは受領を発行しません。
通常の原子的writerが親版・policy・証拠・受領hashを再確認して採用します。
ローカルfixtureの検査と、独立した科学的検証は区別します。

比較は採用snapshot、policy、正確なcontextを固定します。Aには記憶が引用していないeventも
含む、独立に選択したraw 2件を入れ、Bには同じ完全recordのraw prefixと採用記憶1件を入れます。
両対応組の要求byteが異なり、recordの脱落がないことが必須です。順序はAB→BA、
各群の上限は同一で、返答履歴を共有しません。`comparison.frozen_context`、固定membership、
reportとauditでcontext／plan hash、詰めた要求hash、群ごとの内容・状態を確認できます。

sleepの上限は2呼出し、累積入力32,768 byte、出力予約4,096 byte、段階ごとの出力2,048 byte、
candidate 2件です。比較は各群2呼出し、1要求16,384 byte、1返答128 byte。
記憶取得は16,384 byte・1件、rawは最大2 eventを走査して最大2件を選びます。
reportは実際のsleep段階・呼出し・入出力byte、比較呼出し・入力byteと評価器呼出しを記録します。
byte上限をtoken・金額上限とは呼びません。

評価器専用の解答mapはsleep証拠・課題・呼出し側設定・provider要求から分離します。
両群に同じ定型返答を使い、完全一致点数は接続確認用で、記憶の意味的利用を測りません。
費用はsynthetic-zeroまたはunavailableの区別を維持し、節約実績を作りません。
REM・日記・実agent配信／利用・実model確認・独立holdout・性能改善はこのdemoの対象外です。

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
