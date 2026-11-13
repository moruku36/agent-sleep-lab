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


## provider計測値の保存

論文pilotの`OpenClawMimoProvider`は、
[model.runの公式JSON契約](https://docs.openclaw.ai/cli/infer#json-output)で
返された値だけをallowlistで保存します。公開契約への互換対応であり、
**現行のインストール済みCLI・アカウントで値が返ることを確認したわけではありません**。
参照した公式実装は
[usage正規化](https://github.com/openclaw/openclaw/blob/db4b2edd6d0882dd93ce2fdc670a5861e42621f3/src/agents/usage.ts)と
[CLI契約テスト](https://github.com/openclaw/openclaw/blob/db4b2edd6d0882dd93ce2fdc670a5861e42621f3/src/cli/capability-cli/model.run-outcomes.test.ts)です。

- `usage`は与えられた正規名のtoken値（`input`、`output`、`cacheRead`、
  `cacheWrite`、`cacheWrite1h`、`cacheWrite5m`、`reasoningTokens`、`total`）と、
  有限非負の費用合計・内訳、定義済みの費用状態・使用量可用性labelだけを保存します。
  token合計・価格は計算しません。
- `last_call_usage`は`lastCallUsage`の別snapshotです。aggregateの欠測を
  最後の1呼出しで補いません。Gatewayの集計は複数呼出しに及ぶことがあります。
- `usage_state`／`last_call_usage_state`で、`not_observed`（未確認envelope）、
  `absent`、`unavailable`、`invalid`、`observed`を区別します。
  欠測・既定の0だけのsnapshotは測定0とみなしません。明示availableの0や
  provider-billedの0費用は保持します。
- receiptの`cost`は、CLIに`totalOrigin: "provider-billed"`がある場合だけ
  `provider_billed`とします。それ以外は`recorded_unverified_billing`で、
  課金されたと断定しません。runtimeの出所表示であり、請求書との独立照合ではありません。
  `costStatus: "unavailable"`または使用量unavailableなら費用を除きます。
  envelopeで通貨は確定できないためnullのままです。
- 未知・アカウント・自由文metadataは保存しません。既知fieldが不正ならそのsnapshotを
  invalidにし、正常な返答自体は捨てません。モデル・fallbackなしを照合した後、
  本文・byte検査より先に計測値を保存し、不正な返答でも使用量が残るようにします。
- 既存Light／Deep checkpoint（`sleep-status`）と非公開A/B journalの
  `provider_receipts`に保存し、再open後も保持します。schema移行・新規dispatch・
  再試行・採用・取込み許可・モデル変更は追加しません。注入transportの受領は
  非liveと明示します。別のOSS adapterと`compare-inspect`は変更しません。

応答ごとの値があっても総費用計測は完成しません。capture・整理・独立検証・取得・
タスク実行・評価の全段階と、通貨・課金の出所が必要です。既存比較の段階／総費用は
unavailableを維持し、節約額を作りません。過去の実行bindingと合成限定store境界は
別事項です。新しい指定MiMo Lightは設定変更なしで1件成功しましたが、現local CLIは
使用量／費用を返しませんでした。[現在の観測](implementation-status.ja.md)を参照してください。
限定一覧を見る`infer model inspect`で見つからなくても、明示的な推論の利用不可とは
断定できません。全catalog確認と、許可済みの有限呼出しは別の事実を確かめます。
認証登録やcatalogの`available:true`だけでは実応答を証明できません。

## 公開文書の取込み準備

別の[公開文書staging API](public-source-intake.ja.md)で、確認済みの正確な原文／URL／scope、
呼出し側が設定する有限許可と現在の有効性を、モデル呼出し・store受入なしで検査します。
artifactは非公開・非合成です。上記runtime CLIの合成制限を緩めたり、
削除を実施したり既存agentを接続したりするものではありません。

## 採用・取得

```sh
agent-sleep-lab adopt --store-config private/store.json --manifest private/prepared-adoption.json
agent-sleep-lab retrieve --store-config private/store.json --manifest configs/retrieve.example.json
```

採用入力は独立したtrusted preparationが作るrequest_bytes／manifest_bytes／source_manifest_bytesのhex文字列と、memory_bytesのID→hex mapです。モデルの自己申告receiptを使わず、CLIからreceiptを登録しません。既存writerが期待親版、現在policy、原証拠、独立検証・評価受領を再検査します。取得は現在の適格性を確認し、queryの有効語がある場合はスコア0を除外します。queryなしの一覧は可能です。

## オフライン比較準備

```sh
agent-sleep-lab compare-prepare --store-config private/store.json --manifest private/comparison.json --journal private/comparison.sqlite --model xiaomi/mimo-v2.6-pro
```

独立raw A/Bの既存planを、provider構築前に固定・検査する明示的offline操作です。
必須の`--model`は`xiaomi/mimo-v2.6-pro`か`fake-model-1`だけを受け付け、
labelを固定するだけで有料実行しません。agent・provider・live・dispatch・rubric-key・
実行optionはありません。

下記`compare`と**同じ非公開manifest・別journal**を使います。`plan_id`、
1〜5件の一意な`{task_id,prompt}`、`retrieval`、`evaluator_identity`、任意の
`budget`／`config`で、既存の既定値を保ちます。未知field、JSON重複key、不正予算、
DB alias（hardlinkを含む）は拒否します。manifest／store設定は各1 MiB以下、
retrievalの`max_bytes`は1 MiB以下、`scan_limit`は1,024以下、`max_raw`は64以下です。
既存の取得・packing上限も適用します。呼出し側`config`はmetadataであり、権限や実行optionではありません。

採用storeは`read_only=True`／SQLite query-onlyで開きます。書込先は既存
`ComparisonStore`の別journalだけで、固定context・plan・評価contactを保存します。
検証／採用受領やdispatch行は作りません。journalには固定した非公開の原文・要求が
入るため、公開artifactに含めないでください。同一再openはplan byteと実行状態を保ち、
束縛変更・古い現在文脈・適格記憶なし・同一A/Bを拒否します。
不明intentは不明のまま表示し、再送・状態変更しません。

上限付きJSONはplan／config／taskset／context／policy／snapshot／評価器のhash、model、
両群同一上限、AB／BA順、要求hash・長さ・状態、既存membership hash監査と現在の有効性を返します。
原文・prompt・query・返答・解答keyは出しません。各BにはAと同じ完全raw prefixの後に
整理記憶が入ることが必須です。**5課題では計画した10枠（各群5枠）が固定分母**で、
欠測・失敗・不明結果で縮めません。返答byteは**生成後の検査**で、token・金額上限ではありません。
準備操作では使用量・実費を測定しません。後続MiMo応答の観測値は上記のとおり保存できますが、
総費用はunavailableのままで、0費用・性能・受入完了を主張しません。

追加の`input_volume`で、計画した入力の増加量を明示します。

- `pairs`はAB／BAのdispatch位置ではなく、0始まりの`task_index`順です。
  各組に`a_request_bytes`、`b_request_bytes`、`delta_bytes`（B−A）と
  `delta_percent`（100 × (B−A) / A）を返します。
- `totals`はAとBを別々に合計し、`combined_request_bytes`（A+B）と
  合計間の差・増加率を返します。**各組の増加率の平均ではありません**。
  増加率は小数第2位へhalf-upで丸め、正確な整数byte数を正本とします。
- `task_pairs`と`total_arms`は実行状態によらず全計画枠を含みます。
  計画を1巡する入力量であり、実送信・再試行・全工程の消費量ではありません。
  固定した各課題にA・B各1件と正の整数長が揃うことを検査します。
- `basis: "planned_serialized_utf8_json_request_bytes"`は、hash検証した
  正確な直列化要求の長さです。既存packerは`ensure_ascii=True`でUnicodeを
  ASCII escapeし、その出力はUTF-8としても有効です。元の文章・ファイルの大きさ、
  provider／system wrapper、実送信byte、token、金額ではありません。
  入力の追加だけで同量文脈の公平性・品質改善・節約を示すものではありません。

準備では評価器identityとprotocol hashだけを読み、解答keyは読みません。後で既存の明示的な
`compare --provider script`（`fake-model-1`用）、または`--provider mimo --agent ...`へ
同じmanifest／journalとhash一致する別`--rubric`を渡せます。model・予算・課題の束縛は同一必須です。
現在の有効性は読取り時点の観測で、dispatch許可やDB間の原子的保証ではありません。
アカウント／承認binding、対象hostの制限、実応答・総実費・独立受入は未解決で、準備で回避しません。

## 保存済み比較の読取り専用確認

```sh
agent-sleep-lab compare-inspect --store-config private/store.json --journal private/comparison.sqlite --plan-id my-comparison
```

準備後・中断後・実行後に、**既存**の独立raw比較（1〜5組）を確認します。
`compare-prepare`と違ってplanや評価contactを作りません。`compare`や既存reportと違って、
providerの実行／再試行、返答の採点、失効／復旧状態の書込みをしません。
受け付ける引数は`--store-config`、`--journal`、`--plan-id`だけで、
manifest・rubric・provider・model・実行optionは不要かつ指定不可です。

両DBをSQLiteのread-only／query-onlyで開きます。欠落・空・異種・別名参照
（hardlinkを含む）・破損・未対応journalは、初期化や移行をせず拒否します。
保存context・plan・要求のhashとmembershipを照合し、journalは1読取りtransactionで確認します。
証拠storeの現在適格性は別の観測で、DB間の原子的保証ではありません。
通常のSQLite読取りlockやWAL／SHM sidecarが必要になる場合はあります。

期限切れ・許可撤回・文脈変更でも、保存済み`status`はそのまま返し、
`current_validity.valid:false`で不一致を示します。確認時の観測であり、
dispatch許可・出自認証・受入完了ではありません。整合性不正は固定診断とexit 2、
部分実行や古い文脈の**確認成功**はexit 0で、実行成功の判定ではありません。
既にinvalidatedのplanは、現在文脈が再一致してもinvalidatedのままです。

- `outcomes.A/B`は全計画分母を保ち、`planned_not_dispatched`、
  `dispatch_intent_outcome_unknown`、`replied`、`completed`、`timeout`、
  `missing`、`invalid`を別に数えます。不明intentを失敗や再送許可へ変えず、
  応答済みと採点済みを区別します。
- `arms`は課題index・群・実行位置・要求hash／byte・保存状態・結果既知flagと
  既存0/1採点（完了前はnull）です。`evaluator_pass`は保存済み合格数、
  `all_outcomes_scored`は全予定枠がcompletedの場合だけtrueです。
  実modelの返答でも採点は合成の完全一致rubricで、検証済みmodel受領ではありません。
- `input_volume`は準備時と同じ計画直列化byte定義で、完了状態によらず全枠を数えます。
- prompt・query・原証拠／記憶本文・返答・自由記述理由・provider受領原文は返しません。
  IDやhashも必要に応じ非公開にし、自動公開の許可一覧とは扱いません。
- 使用量・実費はunavailable（0ではない）、`comparison`と`performance_claim`はnullです。
  採用や実環境受入の完了は発行しません。

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

各群の予算は同一で実行順を交互にします。詰めたA/Bが一つでも同じなら、登録・呼出し前に拒否します。原ログを減らすか上限を増やしてください。ライブラリのdiagnostic_only=Trueは入力監査だけに使え、comparable:false／comparison:nullとなります。原ログの完全record・prefix監査を維持します。受領・結果不明状態は非公開journalへ残し、不明intentを再送しません。MiMo応答の使用量・費用観測値は上記のとおり保持しますが、段階／総費用は不明のままとし、合成0費用や節約実績としません。

[5課題fixture](../examples/paper-pilot/README.md)は実応答試行の準備であり、実施済み・独立holdoutではありません。研究ノートhandoffの対象はrepo名と40桁commitを呼出し側が明示し、libraryへ固定しません。
