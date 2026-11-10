# 実装状況

[English](implementation-status.md) | **日本語** | [ホーム](../README.ja.md)

## 現在の評価 — 2026-11-11

**初期版は暫定30〜35%。従来の50%見積りは撤回します。**
100%は記録→採用→取得→Light／Deep→比較評価→既存agent一つの接続です。
REM・日記・横展開は含めません。ファイル数、テスト数、入口の準備では進捗を上げません。
本ページと英語訳だけを現在の状態の正本とし、Gate文書は日付付き履歴とします。

## 確認済みのマージ基点

所有者が[PR #23](https://github.com/moruku36/agent-sleep-lab/pull/23)を
2026-11-10に**マージ済み**です。
merge commitは`025e32314efd246dd5b04b3476fa5b2865287a3c`、
対象ソースは`087f2a3da8e4188a70a7a84d50d1a8d4eb14e1dc`。
GitHubの読取りでマージと
[main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42798899032)成功を確認しました。
[PR CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42796639749)は
Python 3.11／3.13それぞれ全241件合格（合計482実行／matrix 2回）、
相対ファイルリンク339件、wheelビルド合格です。CIの有料API呼出しは0です。

[PR #24](https://github.com/moruku36/agent-sleep-lab/pull/24)も**マージ済み**です。
merge commitは`2117e96fcad631f69422541b6a6dbad9c6c025ed`、
ソースは`ab05819d253d15ed7e3dc733f52efd4b034df604`。
専用merge tool停止後に所有者がマージしました。
[PR CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42801027617)の両checkと
[main workflow](https://github.com/moruku36/agent-sleep-lab/actions/runs/42801229632)は成功です。
合成collect-only bridgeの追加であり、本番agent接続ではありません。

[PR #25](https://github.com/moruku36/agent-sleep-lab/pull/25)も**マージ済み**です。
merge commitは`ccb06aa4bdb1defef8fc8564e818522b650fd59a`、
対象ソースは`9387f1fef1565f3edcf94740e22d97f7187ac41f`。
GitHubの読取りで2026-11-10T10:54:59Zのマージを確認しました。
参考記憶の受け渡しjournalはこの基点に含まれます。

基盤は合成の証拠・出典・policy・受領、原子的な採用、取得、rollback／論理忘却、
本文・hash付きv2 Light／Deep、生成candidate、明示CLI、MiMo adapter、
永続checkpoint、同一A/B拒否、比較不可の診断モード、手動handoff、停止後の復旧です。
生成candidateの独立検証・採用は自動ではありません。
本番認証、物理purge、本番agent接続とは区別します。

[PR #26](https://github.com/moruku36/agent-sleep-lab/pull/26)も**マージ済み**です。
merge commitは`9a36ee6dca4569ea2fe1d32dd42969ea9a62c6c3`、
対象ソースは`37439d00d95a4f74d5225a3dc2aab27fdf3c658c`。
GitHubの読取りで2026-11-10T15:34:08Zのマージを確認しました。
CI結果はここには記録していません。途中のoffline workerを保全draftとして
マージしたもので、動作する接続checkerではありません。

[PR #27](https://github.com/moruku36/agent-sleep-lab/pull/27)も所有者が**マージ済み**です。
merge commitは`93ddb1a070c6ffdee65cd0809eea5c8ae68203c5`、対象ソースは
`442b7ea1b4f67c878d67599a42bde6864604810b`。
GitHubで2026-11-10T15:50:40ZのマージとPR CI（Python 3.11／3.13）の合格を確認しました。workerの入力検証と読込み契約テストの追加であり、
動作する接続checkerではありません。

[PR #28](https://github.com/moruku36/agent-sleep-lab/pull/28)も**マージ済み**です。
merge commit `709e7642be3de65f83abd76e5337357829450aa5`、
対象ソース `6a3bba2c53158053583ff86dab56da87c4a60027`。
GitHubで2026-11-10T16:07:42ZのマージとPR CI（Python 3.11／3.13）の合格を確認。
親checkerと代替sourceの契約10件をマージしました。別のローカル受入では空の合成参考で
固定対象コードを1回動かし、合成5判定をcaptureしましたが、journal経由ではありませんでした。

[PR #29](https://github.com/moruku36/agent-sleep-lab/pull/29)も**マージ済み**です。
merge commit `85300ee064b6a9621119c5748f6c8267e240d030`、
対象ソース `9a7e3b8f25268d81503aa8bba91f5feb29d5647c`。
GitHubで2026-11-10T17:54:44ZのマージとPR CI（Python 3.11／3.13）合格を確認しました。

[PR #30](https://github.com/moruku36/agent-sleep-lab/pull/30)も**マージ済み**です。
merge commit `9f281875925dd66a90b09c07af1562e3cdae3beb`、
対象ソース `9d0cbb69dae3943becdbf7d886b4df488cb600dd`。
GitHubで2026-11-10T18:11:11Zのマージを確認。
PR両checkと[main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42872601554)合格。
選択したguard受入6件と正確な制限文書であり、guard挙動の補強ではありません。

## 今回の開発branch

マージ済みPR #31を基点とする`feat/oss-adopted-reference-preparation`です。
**ローカル検証済み：**全309件の重複なし回帰テストが1回の実行で合格しました
（Python 3.13、15.290秒）。PR CIは別途報告します。有料／実モデルの評価推論は未実行です。

- 参考bundleの正規形検査を、取得側と同じbyte形式（key整列・compact・
  escapeなしUTF-8）へ統一。stdlibの`canonical_reference()`一つを
  [prompt捕捉worker](../src/agent_sleep_lab/oss_prompt_capture_worker.py)と
  共有の[parent payload作成](../src/agent_sleep_lab/oss_offline_parent.py)で使います。
  ASCIIのみのbundleは従来とbyte同一。escape済み、空白変更、BOM、重複key、
  不正UTF-8、単独surrogate、上限超過は拒否します。
  promptのframe境界では追加でframe marker入りを拒否します。
  厳格JSON、32,768 byte／256 record上限、参考の正確なSHA-256は変更なし。
  worker protocolの出力は正規ASCIIのままです。
- [新規統合3件](../tests/test_oss_adopted_reference.py)は一時採用storeを使い、
  検証／評価受領と採用は**テスト作成のfixture**、workerは明示した代替です。
  空でない利用可能なUnicode参考がreference群だけにbyte一致で入ること、
  A/B同条件、現在policyの除外、scope不一致、準備中にstoreを変更しないこと、
  不正／非正規byteの拒否を確認する内容です。
- 主張しないこと：store由来の認証、記憶の意味的利用、model判定、性能結果。
  `OfflinePipeline`は引き続きASCII正規形のみ。既知のfilesystem guardの穴は未完です。
- 固定ソースの実受入も合格。一時採用storeにテスト作成の採用・検証／評価fixtureを置き、
  日本語の合成記憶1件がreference promptだけに入ると確認しました。
  baseline 962 UTF-8 byte、reference 3,079 byte。現在policyで除外後、別の新規workerでは
  取得0件となり本文も消えました。各workerで実際の固定judge／promptが各2回動き、
  準備によるstore書込み・provider通信・返答・判定はすべて0件です。
- worker来歴：正常完了受領で`claude-fable-5-2`を確認
  （`terminal_reason=completed`、`is_error=false`）。切替なし。
  coordinatorが保存済み変更をレビューし、テストの境界の誤認1か所を修正して検証しました。
- 残り：明示上限付きlive provider executorと実model受領、
  永続的な対応比較の結果／費用記録、固定評価器。

## PR #31でマージ済みのprompt契約

履歴：PR #30を基点とし、PR #31でマージした`feat/oss-reference-prompt-contract`です
（merge `c8b6ccc`、ソース `c61cbb1`）。GitHubでMERGEDと
PR CIのPython 3.11／3.13両check合格を確認しました。
所有者の優先は、計測前に記憶利用と比較実行を実装することです。
**有料／実モデルの計測は行っていません。**

- 別の[prompt捕捉parent](../src/agent_sleep_lab/oss_prompt_capture.py)と
  [stdlib worker](../src/agent_sleep_lab/oss_prompt_capture_worker.py)を追加。
  既存worker／pipeline protocolは変更なし。同じ11件の固定blobを既存preflightで照合し、
  新しいguard付きprocessで実際のpin済み`OpenAITriager.judge → triage_prompt`を
  組込みborderline課題について動かします。
- 両群の課題、実default score／理由、mock model、要求設定は同じです。
  baselineにproject notesはなく、reference群は上限付き参考bundleの正確なbyteを
  明示的な未信頼データframeへ入れて挿入します。parentが要求／prompt hashを再計算し、
  promptはその連続した挿入だけが異なり、prompt以外の要求fieldは一致すると照合します。
- 注入したローカルtransportが要求を記録し、pin済み`LLMTriageError`を送出します。
  外部送信・返答・架空の判定はありません。endpoint／model／credentialは明示的な
  不活性fixture名で、環境の認証情報は参照せず、header値も出力しません。
- `prepare_from_bridge()`は明示された既存bridgeのscope／現在policyを使って取得し、
  workerのbyte／record上限と固定repository／commitを照合します。
  store由来は呼出し側管理で認証済みではありません。artifact作成はdispatch許可ではなく、
  将来のexecutorは現在文脈の再照合が必要です。
- **実際の固定ソースによる受入が1回合格**：issue #3、実score 0.5、
  固定judge／prompt関数が各2回、要求2本を捕捉、provider通信・返答・判定0件、
  採用・検証／評価受領0件。参考は空の一時合成store由来でrecord 0件。
  baseline prompt 962 UTF-8 byte、reference prompt 1,960 byteでした。
  実要求経路への参考データ配置の確認であり、採用記憶の意味的利用ではありません。
  収集pipeline全体の動作は変更していません。
- [新規契約5件](../tests/test_oss_prompt_capture.py)は代替sourceを使い、
  frame、束縛／label拒否、A/B同条件、返答なしtransport、preflight／代替labelを確認。
  実モデル評価ではありません。
- worker来歴：`claude-fable-5-2`を明示指定しましたが、2モジュール保存後に300秒でtimeout。
  正常完了／解決済みmodelの受領は返らず、Fable正常完了とは呼びません。
  process照合では1日以上前からの無関係なClaude processのみ確認。
  worker再試行・別workerへの切替はなく、coordinatorが保存済みコードをレビューし、
  テスト・実受入・実装状況更新を行いました。
- 残り：空でない独立に利用可能な採用記憶の接続、明示上限付きlive provider executorと
  実model受領、永続的な対応比較の結果／費用記録、固定評価器。
  PR #31時点の捕捉経路はASCII正規形bundleのみ対応でした（今回branchで対応し、ローカル検証済み）。
  frameはprompt injection耐性や認証済み由来の証明ではありません。

## マージ済みguard検証の基点

6件はfresh childでsocket／process／環境／cwd／write-open／SQLite／資源の
選択した制限を確認したものです。敵対コード用sandboxではありません。
別の副作用なしevent probeでは`os.remove`、`os.rename`、`os.mkdir`、
`os.link`、`os.symlink`、`os.chmod`、`os.truncate`が未捕捉でした。
実外部変更は行っていません。この穴とpath／dir-fd補強は未完で、
今回branchもguardの実挙動は変更しません。

## PR #29でマージ済みのpipeline

履歴：PR #28を基点とし、PR #29でマージした`feat/oss-offline-journal-pipeline`です。

- [OfflinePipeline](../src/agent_sleep_lab/oss_offline_pipeline.py)を追加：
  bridge取得→永続reference journal→親checker→判定保存→capture。
  bridgeのrepository／commitは組込み固定課題と一致必須。
  参考上限をworkerの32,768 byte／256 record以下に統一します。
- 取得条件、対象path、起動設定、capture時刻／session／許可を正規化契約へ固定し、
  hashをjournalのconsumer versionへ束縛してからdispatchします。
  同一use IDでの設定変更は競合。上限付きconsumer出力へ契約・checker要約・
  hash付き実返却判定を保存してからcaptureへ進みます。
- captureは保存済み出力だけから再開。決定的event IDと既存storeの同一byte再送により、
  部分中断後もworkerを再実行しません。結果不明・不正受領・invalidatedは再dispatchせず、
  成功としてcaptureしません。capture前・各件の間・完了後に現在文脈を照合し、
  再送でもcapture境界が許可を確認します。policy変更前に保存した観測はrollbackせず、
  残りを止めて部分観測と報告します。
- 読取り専用`ReferenceUseJournal.context_unchanged()`を追加。
  schema変更・migration・新DB・自動retry機構なし。
- **実際の固定workerをjournal経由で動かす別受入が合格**：
  一時合成storeの空参考、実worker 1回、capture 3件目の直前で中断、
  journal再open後に2件replay＋3件新規capture。さらに呼ぶと全5件replayで、
  worker総実行は1回のままでした。candidate／低得点skip／pending LLM／重複skip／
  infra errorの5判定を確認。採用記憶・検証／評価受領は0件です。
- [新規回帰9件](../tests/test_oss_offline_pipeline.py)は実際の一時合成store／journalと
  mock checkerを使用し、対象コードは動かしません。再送、部分再開、契約競合、
  結果不明、文脈変更、現在のcapture許可、上限、capture中policy変更、出力超過を検証。
  mock結果は代替と明示します。
- 実装来歴：Claude Codeのterminal metadataで`claude-fable-5-2`／`firstParty`を確認。
  ただし**正常完了ではありません**。`is_error=true`、
  `terminal_reason=api_error`、HTTP 429 `usage_limit_reached`で停止し、
  pipelineとjournal accessorだけを保存しました。coordinatorが途中成果をレビューし、
  受入9件と各capture間の文脈照合を追加して検証／実装状況更新を完了しました。
  別coding worker／モデルは起動していません。
- 合成オフライン接続であり、本番接続や認証済み配信／利用ではありません。
  受領は未確認自己申告で`delivery_and_use_verified`はfalse。
  空参考は`Target.notes`へ届きますが、`llm=None`では意味的利用されません。
- 残り：空でない採用記憶の利用、guard境界の追加検証／補強、bundle key乖離とstore由来束縛、
  実データ許可、実比較評価。capture／journal／storeを跨ぐ単一transactionではありません。
  明示storeは呼出し側の管理で認証済みではなく、再開には同じ証拠storeの存続が必要です。
  origin URLは変更可能で、guardは敵対的Pythonのsandboxではありません。
  実受入script／artifactはローカルcoordinator記録で、repo内の可搬な実対象回帰ではありません。

以下はPR #25でマージ済みです。

- [参考記憶の受け渡しjournal](reference-use.ja.md)は上限付きtask／参考byteと識別を固定し、
  呼出し前の意図永続化、CAS、結果不明時の再実行防止、前後の文脈照合を行います。
- 有効な返答はhash付きですが、受領は未確認自己申告です。
  `delivery_and_use_verified`は常にfalseであり、実行記録は意味的利用の証明ではありません。

以下はPR #24でマージ済みです。

- 既存OSS Contributorの`TriageDecision`辞書契約に対応する、
  明示的な[collect-only bridge](oss-bridge.ja.md)を追加。
- 判定やLLMの理由は未信頼の観測として記録し、issueの事実確認とは呼びません。
  記憶、検証／評価受領、採用は作成しません。pending／失敗も成功扱いしません。
- 取得はscope・byte上限・現在policy・除外を守る読取り専用です。
  対象ledger、採点、設定、定期処理、patch／PR経路、本番hostは変更しません。
- **合成データのオフライン接続部品**であり、実ログ取り込み・実agentへの配信／利用の
  確認ではありません。実運用には非合成データの保持・利用許可契約が必要です。
  実ログを合成と偽って渡してはいけません。

## 今回branchの検証

- `feat/oss-adopted-reference-preparation`：**未実行です。** 新規3件、全回帰、
  文書検査、固定ソース受入はcoordinatorの作業待ち。以下の数値はPR #31の履歴です。
- 既存Python 3.13.18環境で**全306項目／全件1回、15.327秒で合格**。
  新規prompt捕捉5件を含みます。先行の限定5件は4合格／fixture誤り1件。
  代替source pathを必須trace名に合わせて修正し、影響する1件だけ再実行して合格。
  今回は合計**312項目実行／3 invocation**です。
- 別の実受入：fresh prompt捕捉worker 1回、固定judge／prompt経由の要求2本、
  外部呼出し／model判定なし、空の参考データ。回帰項目には数えません。
  worker出力SHA-256：
  `2d26697d97af0cf4277582b77155fefcf72febdb4d2e0a651d800bee734acc02`。
- 文書：**相対リンク370件／Markdown 76ファイル合格**。
  anchor・外部URLは対象外。空白差分検査も合格。feature CI未実行。
- 履歴：PR #30は301項目／1回15.011秒と先行6件（計307実行／2 invocation）、
  相対リンク366件／Markdown 76ファイル。7eventの別診断は回帰ではありません。
  PR #29の295項目＋先行8件、実空参考pipeline復旧受入も履歴であり、今回は再実行していません。
- 空でない採用記憶の意味的利用、実比較評価、既知のfilesystem変更guard補強は未完です。

## 本当に残っていること

1. MiMoの実行承認・binding拒否を解消し、実provider／モデルの受領を得ること。
   保存済みレビューcommandは所有者が承認しましたが、同一commandの
   `ask=always`申請も「承認を安全に紐付けられない」と実行前に拒否されました。
   別経路・別モデルは使っていません。以前の設計依頼は受領なしtimeoutで費用不明です。
2. 適用予算内で、独立に採用済みの経験と固定評価器を使い、5課題の実応答を比較すること。
   [架空の開発課題](../examples/paper-pilot/README.md)は準備のみで独立holdoutではなく、
   完全一致fixture採点を科学的な論文品質の証明とはしません。
3. 既存agent一つの実capture／取得利用を確認すること。オフラインadapter契約と
   手動handoffは準備です。実データ境界と実配信・利用検証は未完です。
   今回のローカルjournalは実行記録であり、認証済みの利用証明ではありません。
4. raw関連度順位付け、物理purge、広い本番障害受入も未完です。
   オフラインテスト合格で完了とはしません。

入口と契約は[ランタイム手順](runtime-guide.ja.md)を参照してください。
MiMo CLIには呼出しごとの最大出力token指定がなく、生成後byte検査は
金額・tokenの厳密上限ではありません。不明終了にも費用が生じた可能性があります。
