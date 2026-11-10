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

## 今回の開発branch

PR #26のmerge commitを基点とする`feat/oss-offline-worker-contract`です。
workerは引き続き**未完成のdraft**であり、動作する接続checkerではありません。

- 途中の[offline worker](../src/agent_sleep_lab/oss_offline_worker.py)の入力検証を強化。
  payloadの完全一致key、上限付き小文字hex、項目ごとのbyte上限、厳格JSON
  （重複key・非有限数・BOM・不正UTF-8を拒否）、合成experience参考bundleの完全一致keyと
  件数／snapshot照合、組込み合成課題byteのみ受理。
- 読込みはcompile直前にsource hashを再照合し、mapping順ではなくレビュー済み順を使い、
  全sourceのcompile後にだけ実行し、同名moduleが既にあるprocessを拒否します。
  worker自身の`__future__`指定がpin済みコードへ漏れる点も修正しました。
- **[契約テスト](../tests/test_oss_offline_worker.py)21件を追加、全合格**。
  入力検証と読込みの単体動作をテスト用の代替sourceで確認し、対象コードは実行しません。
- 三段階を区別します。**構文／import・単体動作**は下記回帰で合格。
  **実際の対象接続**（`run()`・guard・pin済み対象source）は未実行・未検証です。
- 親checker、対象checkout／commit検証、bridge／journal接続、一気通貫の実行は未実装です。
  埋込みsource pinの独立検証も未実施です。bundleのkey集合は取得契約のローカル複製で
  乖離検出テストはなく、正規化byteやstore由来の確認もしません。
  実データには使用しないでください。
- guardは敵対的Pythonのsandboxではなく、境界テストも未実施です。
  参考byteは対象notesへ代入しますが、`llm=None`のtriageは意味的に利用しません。
  記憶の効果や本番接続を示すものではありません。
- 今回の改訂はClaude Codeで作成しました。coordinatorが正常完了のterminal受領
  （`is_error=false`、`terminal_reason=completed`）を取得し、canonical modelは
  `claude-fable-5-2`（Fable 5.2）、providerは`firstParty`と確認しました。
  permission denial・subagentはなく、別モデルへの切替はしていません。PR #26の以前の試行はCodex CLI `gpt-6.1-sol`／`xhigh`指定で、
  モデル受領なしにtimeoutしました。

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

- 既存のPython 3.13.18検証環境で**全276項目／ローカル全件1回、全合格、13.446秒**。
  workerの単体／契約テスト新規21件を含みます。install・ハーネスの有料推論はありません。
- **相対ファイルリンク364件／Markdown 76ファイル合格**。anchorと外部URLは対象外です。
  今回featureのCIは未実行です。
- 履歴（今回の編集前、PR #26のbranch）：Python 3.13.18で既存の全255項目／1回が
  13.415秒で合格、相対ファイルリンク362件／Markdown 76ファイル合格。
  これらはworkerを実行しておらず、今回branchの検証ではありません。
- workerの入力検証と代替sourceの読込みは単体レベルのみ検証済みです。
  実際の`run()`、guard、対象ソース実行、一気通貫の接続は未検証です。
- PR #25の以前の255項目／13.588秒とPR #24の247項目／12.183秒は履歴であり、
  今回試行の実行回数には含めません。
- 5課題の実A/B、実モデルの性能改善は未確認です。

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
