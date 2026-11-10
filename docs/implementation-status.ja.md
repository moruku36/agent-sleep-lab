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

## 今回の開発branch

PR #27のmerge commitを基点とする`feat/oss-offline-parent-checker`です。

- stdlibの[親checker／consumer](../src/agent_sleep_lab/oss_offline_parent.py)を追加。
  上限付き読取り専用gitで明示root、ローカルorigin申告、固定commit、11件のsource hashを
  照合します。Git objectからbyteを固定し、worktreeファイルの読込みや対象checkoutへの
  書込みは行いません。
- 組込み合成課題と上限付き正規化済みexperience参考byteだけを受理。
  一時cwd・最小環境・shellなし・timeout・入出力上限付きの新しい
  `python -I -B` workerを1回起動し、出力protocolとsource／task／参考／notesを照合。
- journal互換consumerの受領は未確認自己申告です。注入されたworker commandは代替と明示。
  配信確認、意味的記憶利用、採用、改善の証明にはしません。
- coordinatorの差分レビュー後、**実際のpin済みソースによるオフライン実行が1回合格**。
  ローカルrepoのcommit `e40b39c6258ac5a4446c38246bdfd7f5dc5dbf7b`について、
  Git blob 11件すべてが埋込みSHA-256と一致しました。実際の収集・digest・一時ledger経路で、
  candidate／低得点skip／pending LLM／重複skip／infra errorの5判定とpending 1件を確認。
- 参考は空の合成adoption storeから実際に取得し、record 0件・active snapshotなしでした。
  返った5判定を同じ一時合成storeへ`CollectOnlyBridge`経由でcaptureしました。
  記憶・採用・検証／評価受領は作成していません。
- 合成入力での固定コード実行とcapture契約の接続確認であり、**採用記憶の利用確認ではありません**。
  参考は`Target.notes`へ到達しますが、`llm=None`では意味的利用されません。
  受入script／artifactはローカルのcoordinator記録であり、可搬な回帰や本番導入ではありません。
- 残り：bridge／journal／consumerの一気通貫orchestration、journalとworker（32,768 byte）の
  上限整合、bundle key集合の乖離検出、汎用consumerのstore由来束縛、
  guard境界の独立テスト、空でない採用記憶の利用、実データの許可契約。
  guardは敵対的Pythonのsandboxではありません。originは書換え可能で認証済み識別ではなく、
  敵対的Git設定も未検証です。
- Claude Codeの正常完了をcoordinatorのterminal受領で確認：
  `is_error=false`、`terminal_reason=completed`、canonical model
  `claude-fable-5-2`、provider `firstParty`、permission denial・subagentなし。
  別モデルへの切替なし。coordinatorは実装前に両READMEと設計／評価文書を読みましたが、
  coding worker自身はその4文書をすべて読んではいません。
- PR #27の厳格入力／loader契約と代替sourceの単体21件はマージ済み基盤です。
  今回の実オフライン受入と新規親契約10件とは区別します。

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

- Python 3.13.18で**全286項目／ローカル全件1回、14.081秒で合格**。
  親checker新規10件と既存worker 21件を含みます。新規回帰は代替source・git応答・processを
  使用し、対象checkout不要、ネットワーク／モデル呼出しなしです。
- 別のローカル受入：実pin済みworker 1回、合成5判定のcapture、
  採用記憶0件・検証／評価受領0件。worker出力SHA-256：
  `fb0503a72112677b5610a5471f378578539d1dc43c4906704c94ca51ef8266af`。
  回帰項目として数えず、回帰内での繰返しもしていません。
- 文書：**相対ファイルリンク362件／Markdown 76ファイル合格**。
  anchor・外部URLは対象外。空白差分検査も合格。feature CI未実行。
- 履歴：PR #27のローカル全276項目／1回13.446秒、相対リンク364件／Markdown 76ファイル。
  PR #26は255項目／1回13.415秒、相対リンク362件／76ファイル。今回試行の実行ではありません。
- guardの拒否境界、journal一気通貫dispatch、実データ利用、5課題実A/B、
  実モデル性能改善は未確認です。

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
