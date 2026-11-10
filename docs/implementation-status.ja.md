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

## 今回の開発branch

PR #29を基点とする`test/oss-offline-guard-boundaries`です。

- 指定のFable coding workerは引き続き利用上限待ちです。表示されたresetは05:30 JST。
  再試行・別coding worker／モデルの起動なし。今回はcoordinatorによる検証／文書更新であり、
  新たなFable実装の正常完了ではありません。
- [実guardの受入6件](../tests/test_oss_offline_guards.py)を追加。
  mockではなく、各件で使い捨ての隔離子processを使用。socket生成、
  subprocess／環境／cwd制限、外部へのtext／byte／raw／symlink経由write-open拒否、
  一時scratch／指定ledgerの許可、他のSQLite拒否、資源上限と親processへの非漏洩を確認。
  pin済み対象コードや外部接続先は使いません。一部process種別は実exec／forkではなく、
  副作用のない監査event probeです。
- 確認した制限は合格しましたが、**filesystem書込み全体の隔離は成立していません**。
  別の副作用なし監査event調査で`os.remove`、`os.rename`、`os.mkdir`、
  `os.link`、`os.symlink`、`os.chmod`、`os.truncate`が捕捉されないと確認。
  対応する実filesystem操作は実行せず、外部の合成sentinelは変更されていません。
- worker guardのdocstringを「全filesystem書込み」ではなく、選択したwrite-open／SQLite
  検査と限界を記載するよう修正。guardの実際の挙動は変更していません。
  既存descriptor・native code・syscall全体の隔離は対象外で、敵対的Python用sandboxではありません。
- coding worker待ちが解消した後の実装修正は、path／dir-fdを含むfilesystem変更経路の
  拒否と意味のある境界テストです。今回見つかった穴は未修正として残しています。
  空でない採用記憶の意味的利用と実データ許可も未完です。

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

- 既存Python 3.13.18環境で**全301項目／全件1回、15.011秒で合格**。
  新規guard 6件を含みます。先行の限定6件／1回も0.127秒で合格。
  今回は合計**307項目実行／2 invocation**です。
- 別診断：上記7種の未捕捉filesystem変更イベントを副作用なしでprobe。
  回帰項目には数えず、実変更・対象コード実行・通信／モデル呼出し・採用・受領作成なし。
- 文書：**相対リンク366件／Markdown 76ファイル合格**。
  anchor・外部URLは対象外。空白差分検査も合格。feature CI未実行。
- 履歴：PR #29は295項目／全件1回14.343秒と先行8件（計303実行／2 invocation）、
  相対リンク364件／Markdown 76ファイル。別の実固定worker受入ではjournal dispatch 1回、
  capture中断／再開／合成5観測replayを確認し、worker再実行なし。
  今回のguard検証試行の実行ではありません。
- 7種の変更イベント未捕捉、広いsandbox／OS隔離、空でない採用記憶の利用、
  実データ運用、実5課題A/B改善は未完です。

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
