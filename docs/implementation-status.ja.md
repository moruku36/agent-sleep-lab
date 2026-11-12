# 実装状況

[English](implementation-status.md) | **日本語** | [ホーム](../README.ja.md)

## 現在の評価 — 2026-11-12

**受入優先とし、裏付けのない完成率は示しません。** 2026-11-12の所有者レビューは
下記4能力で追跡します。初期目標は記録→採用→取得→Light／Deep→比較評価→既存agent一つの接続です。
REM・日記・横展開は含めません。ファイル数・テスト数・入口の準備は受入完了ではありません。
本ページと英語訳だけを現在の状態の正本とし、Gate文書は日付付き履歴とします。

今回の文書更新のGitHub読取りでmain
`9b6ecb59e266f157789af87d0b3ce5203fb32072`と
[PR #45](https://github.com/moruku36/agent-sleep-lab/pull/45)のマージを確認しました。
下表はこのマージ済みruntimeの状態です。別のローカル公開情報試用はその後に記録し、
その実装は今回の文書変更に含めません。先行`feat/live-acceptance-path`のcommit
`1e636d8`は別途保全済みで、過去のPR作成は**UNKNOWN**です。その操作は再送しません。

| 能力 | コード | オフライン検証 | 実環境受入 | 不足 | 次の1アクション | 根拠 |
|---|---|---|---|---|---|---|
| 記録／独立検証／原子的採用／取得／撤回・復元 | 合成store向け実装済み | 既存回帰。今回の結果は下記 | 未実施 | 実データ境界と運用受入 | 許可された実データ境界を一つ定義 | 既存store／writer／retrieval契約 |
| 実model Light／Deep→独立採用→取得 | 本文束縛生成・別verifier／writer。先行の同run CLI branchは別途保全 | 既存契約。新たなmodel呼出しなし | 未実施 | hostの実行bindingと実生成候補の独立確認 | binding解消後、総枠内の最小1呼出しで受領確認 | [実行手順](runtime-guide.ja.md)、上記先行branch |
| 固定論文5課題のA/B実応答・欠測・費用 | 既存plan／journalにoffline準備を接続 | 新7契約合格。全回帰は下記 | 未実施 | 実10結果と総実費の実測 | 5組のmanifestを固定し、実行障害を解消 | [比較準備](runtime-guide.ja.md#オフライン比較準備)、[契約](../tests/test_compare_prepare_cli.py) |
| 実agent一つのcapture→別taskの取得・入力・実行 | 合成bridgeとoffline handoffのみ | 既存合成接続契約 | 未実施 | 実データ許可・保持／削除・scope・秘密情報契約と実利用の追跡 | OSS Contributorの実データ受入契約を定義 | 既存bridge／実行journal。実agent受領なし |

有料利用の許可は受領済みで、一般的な再承認が障害ではありません。
保存済みのhost binding拒否と結果不明の操作は未解決です。準備で再送したり、
host／アカウント制御を変更したりしません。

## ローカルの公開情報試用 — 2026-11-12

[日付付きの試用レポート](public-source-trial-2026-11-12.ja.md)に、公開文書1件の
記録→実モデル生成→別担当の根拠レビュー→原子的採用→取得→別作業での実利用を記載しました。
マージ済み基点へ**ローカル・未commit／未マージの拡張**を加えた試用であり、
マージ済みの合成CLIによる実データ取込みではありません。今回の文書変更ではruntime実装を公開しません。

事前固定した1組の採点は原文のみ7/8、原文＋記憶8/8でした。入力は4,072 bytes増加し、
使用量・実費は不明です。1組だけで一般的な性能改善は示せません。
拡張のローカル回帰は436件合格で、文書branchの試験数ではありません。
正確な版・成果物hash・比較の限界・試験集計はレポートを参照してください。

受入範囲は限定的です。自動Light／Deep、常設agent接続、MiMo有料実行、
固定5課題の受入は完了していません。ローカル実装の公開・レビューと、
対象agentへの接続は別の次工程です。以下の過去のhost binding障害は、
今回の試用で解消・再試行していません。

### 文書のみの更新確認

今回の変更はMarkdown 6ファイルで、runtime codeや非公開の試用成果物は公開しません。
この文書変更のローカル回帰は**重複なし425件が1起動で合格**
（13.517秒、Python 3.12.14）。Markdown 88ファイルの相対リンク521件も合格しました。
既存READMEのリンク先はすべて保持しています。上記ローカル拡張の436件とは別の数値です。
この文書commitのGitHub checksは別のCI記録です。

## PR #45：dispatch前の比較準備（履歴）

- 明示的な[compare-prepare](runtime-guide.ja.md#オフライン比較準備)を追加。
  同じ上限付き比較manifest、別journal、有限のmodel選択を使い、採用storeはread-onlyで開きます。
  固定context／plan／評価contactだけを書き、provider・評価器構築、解答key読出し、
  実行状態の変更はありません。不明intentは不明のままです。
- hash・上限・固定計画分母／順序・既存membership監査を返し、BにAと同じraw prefixと
  適格整理記憶が入ること、現在文脈の再照合を必須にします。後で既存の明示`compare`へ
  同じ固定planと別rubricを、対応するmodel経路で渡せます。
- 新[offline behavior 7件](../tests/test_compare_prepare_cli.py)が1起動で合格（0.980秒）。
  続く全回帰は**重複なし425件が1起動で合格**（34.600秒）しました。
  既存Python 3.13・固定依存を使用し、ローカル計432ケース実行／テスト2起動です。
  文書86ファイルの相対リンク513件と空白チェックも合格しました。
  PRのPython 3.11／3.13 CI・wheelは別の確認で、ここでは未受入です。
- 選択したCodexのdraft呼出しは外側600秒でtimeoutし、正常完了受領は未取得でした。
  対象processの不在を確認後、保存差分をcoordinatorがレビュー・補完・検証し、再送していません。
  coordinatorレビューは独立承認ではありません。実推論・独立受入はありません。
  返答byteは生成後の上限検査で、token・金額上限ではなく、MiMo費用はunavailableです。
  今回は準備であり、live復旧、実Light／Deep、実agent取込ではありません。

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

[PR #39](https://github.com/moruku36/agent-sleep-lab/pull/39)は
`5cea9e224f8bfc306735c400b9cd358db7c0ac9f`で**マージ済み**です。
今回の読取り専用GitHub照会で2026-11-11T01:59:18Zのマージを確認しました。
これは過去の基点に関する確認記録です。

[PR #40](https://github.com/moruku36/agent-sleep-lab/pull/40)は所有者が
`29fef5ad19239e53ce3e07684b2c30e0cc2d1623`で**マージ済み**です。
今回の読取り専用GitHub照会で2026-11-11T03:04:33Zのマージと、同じcommitの
Python 3.11／3.13の[main CI合格](https://github.com/moruku36/agent-sleep-lab/actions/runs/42950289146)を確認。
当時のraw順位付け用worktreeは、このmain commitを基点としました。

[PR #41](https://github.com/moruku36/agent-sleep-lab/pull/41)は所有者により
`e2d525242511cd2c8b46626ce1ab96477a85dd2d`へ**マージ済み**です。
今回の読取り専用GitHub照会で2026-11-11T03:57:26Zのマージと、同じcommitの
Python 3.11／3.13の[main CI合格](https://github.com/moruku36/agent-sleep-lab/actions/runs/42956077100)を確認。
当時の読取り専用費用reportゲートはこの基点を使用しました。

[PR #42](https://github.com/moruku36/agent-sleep-lab/pull/42)は所有者により
`791e8f540db0b4ca549ffec79a96925e907e804b`へ**マージ済み**で、demo draftの基点です。
coordinatorのGitHub照会で2026-11-11T04:35:30ZのMERGEDと同一merge commitを確認しました。
以下の費用reportの検証数値は履歴です。

## 今回のローカルゲート：読み取り専用OSS準備

[PR #43](https://github.com/moruku36/agent-sleep-lab/pull/43)は所有者により
`736988a0cb243da9c263ce28232ec5f44d0e3ea7`へマージ済み
（2026-11-11T23:00:41Z）。GitHubで独立確認しました。
[PR CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/43116115784)と
同一mergeの[main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/43116437958)
は成功です。以下のdemo数値は履歴で、今回の検証ではありません。

- 厳密なmanifestとstore設定を明示する[oss-prepare](oss-prepare.ja.md)を追加。
  採用済み合成・経験用記憶を現在policyでread-only／query-only取得し、
  空なら対象起動前に拒否。worker後の新transactionで変更・失効を再確認します。
  固定source・正確なframe・出力検証の既存ゲートを維持しました。
- 既存の設定検証を変更せず`oss_read_config.py`へ共通化。
  費用CLIの互換性を保ち、準備経路から実行journal／provider／adapterのimportを分離。
  注入worker・provider・transport・capture／採用・dispatch指定は受け付けません。
- [新規7 unique契約ケース](../tests/test_oss_prepare_cli.py)が限定1起動・0.693秒で合格。
  実際の一時採用storeと明記したstand-in workerによる検証です。
  全回帰も**418 uniqueケース／1起動・34.432秒で合格**。
  累計は**425ケース実行／ローカル回帰2起動**です。
- 文書は**相対ファイルリンク503件／Markdown 86ファイル合格**。
  anchor・外部URLは対象外。空白差分検査も合格です。
- 別のcoordinator受入は**1ケース／1起動で合格**。実際の固定OSS Contributor source
  `e40b39c6258ac5a4446c38246bdfd7f5dc5dbf7b`とテスト作成の採用済み合成記憶1件を使い、
  組込みcapture worker 1回、実judge／prompt各2呼出しを確認。
  baseline 962 bytes、reference 3,047 bytes、モデル呼出し・store変更は0です。
  回帰件数とは別に数えています。
- 選択したCodex `gpt-6.1-sol`／`xhigh`の呼出しは600秒でtimeoutし、
  本体draftのみ保存、テスト・文書は未作成でした。process終了を確認し再実行なし。
  完全なresolved-model／正常完了受領は得ていません。
  coordinatorが差分をレビューし、テスト・文書を完成して検証しました。
- オフラインで利用できる入力準備の確認であり、実運用capture・認証付き配送・意味的利用・
  改善の証明ではありません。出力には合成記憶／request本文を含み、公開許可一覧ではありません。
  有料推論・設定／認証変更・mergeは実施していません。feature PR CIは別ゲートです。
  実受入は未完です。

## PR #43のローカルゲート履歴

### 組込み合成オフラインdemo：マージ前のローカル検証

- `agent-sleep-lab demo`、[実行契約](runtime-guide.ja.md#組込みオフラインdemo)、
  [重複なしの契約テスト8件](../tests/test_offline_demo.py)を保存しました。
  呼出し側のデータ・store・provider指定を受け付けず、別々の使い捨て一時SQLite store 3つと
  組込み合成データ、固定時刻、上限付き定型providerを使います。
- 2 eventをcaptureし、Light／Deepを各1回呼び、pending candidateを1件生成します。
  原文との完全一致検査後、通常APIで検証受領1件と4項目のsnapshot評価受領1件を登録し、
  既存の原子的writerで1回採用、適格記憶1件を取得します。
  providerから受領を発行せず、本番ゲートを迂回しません。
- 対応2課題で採用snapshot・policy・独立raw 2件・記憶1件を固定。
  Aは完全なraw prefix、Bは同じprefixと記憶を使います。定型タスク4呼出し・別評価器4呼出しを
  AB→BA、同一上限で行い、要求byteは異なりrecordの脱落はありません。
  解答はprovider要求から分離し、実際の段階・呼出し・byte数、固定context、
  hash付きmembership auditを出力します。
- 初回限定検証の記録は**8ケース実行／1起動：2合格・3失敗・3エラー**でした。
  共通原因は`until_expiry`にnullの期限を与えた不正契約です。
  fixtureに固定時刻より後の実際の期限を設定しました。snapshotの自己一致assertionは、
  採用snapshot・policy・固定context／plan hash・完了した各群のmembership検査に置き換え、
  assertionと本番ゲートを維持しています。
- 修正後は**影響する全8 uniqueケース／1起動、0.919秒で合格**しました。
  初回失敗を含むdemoゲートの累計は**16ケース実行／限定2起動**です。
  合成契約のローカル検証で、独立受入ではありません。文書検査は1起動で
  **相対ファイルリンク489件／Markdown 84ファイル合格**。anchor・外部URLは対象外です。
  空白差分検査も合格しました。
  続けてcoordinatorの**全411 unique回帰／1起動、33.853秒が合格**しました。
  限定2回を含む累計は**427ケース実行／ローカル3起動**です。
  合成の一連の接続を検証したもので、実agent受入ではありません。
  当時はPython 3.11／3.13 PR CIとwheelが未完でしたが、後に両方合格しています（上記）。
  ローカルoffline wheel commandは実行前に承認bindingで拒否され、別経路は試していません。
- 実推論・install・merge・外部の権限／設定変更は行っていません。
  feature公開とレビュー用PRは承認済みで、公開commitの検証はGitHub PR checksを正本とします。
  一時状態の削除、失敗処理、解答の除外、live／provider実行経路の拒否を限定テストで確認。
  定型返答の完全一致点数は意味的な記憶利用・実agent接続・請求・holdout品質・改善の
  証拠ではありません。実受入は未完です。

## マージ済み開発ゲート（検証履歴）

### PR #42のOSS読取り専用offline費用CLI：マージ前のローカル検証

以下の数値は所有者がPR #42をマージする前の記録です。基点の履歴であり、
demoの検証や新たな公開の承認ではありません。

- `oss-cost-report`と[厳格なmanifest／API契約](oss-cost-accounting.md)を保存。
  pair／cohort ID、plan別bridge識別、既存file path、任意の正確なcanonical観測byteを明示します。
  出力は既存の費用集計allowlistのみで、現在policy・整合性を再確認し、provider／write optionはありません。
- AdoptionStore／ExecutionJournal／CohortRegistryに明示的なSQLite read-only／query-only modeを保存。
  書込みmethodを早期拒否し、初期化・移行を行わず、path aliasを拒否します。
  既定writer・保存契約は維持。SQLiteのlock・sidecarはあり得るためfilesystem隔離や認証とは呼びません。
- [合成回帰ソース](../tests/test_oss_cost_report_cli.py)を保存。pair／cohort出力、登録済み全分母、
  unknown／invalid／withheld、canonical／古い観測、未存在・空・foreign・alias DB、
  実行／採用副作用0、早期拒否、WAL上の現在policy、writer互換性を対象とします。
  fixture helperを再利用し、継承・importによるTestCase重複は追加していません。
- coordinatorがPython 3.13.18で**新規12 uniqueケース／限定1起動、2.399秒**、続けて
  **全403 unique回帰／1起動、30.601秒の合格**を確認しました。今回の合計は
  **415 case executions／ローカル2起動**です。**相対リンク479件／Markdown 84ファイル合格**、
  anchor・外部URLは未検査で、空白差分も合格。今回ゲートの新CIやローカルPython 3.11の
  結果は主張しません。テストは合成storeと注入返答だけを使います。
- 当時の検証前にjournalの重複事前checkを除き、従来通り正確な型検査を
  foreign methodアクセスより先に維持しました。この境界も回帰assertionで確認しています。
  これらの検証は完全なagent接続、live／請求確認、性能改善の証明ではありません。

### PR #41の独立raw比較query順位付け：マージ前のローカル検証

以下はPR #41への所有者マージ前の順位付けゲートの記録です。
当時の検証・公開承認は、今回のdemoゲートには適用されません。

[順位付け契約](raw-query-ranking.md)と[実装](../src/agent_sleep_lab/raw_baseline.py)に
`raw_order="query_overlap_descending"`の明示指定を追加しました。
独立raw比較APIと既存のファイル形式compare manifestから選べます。
既定のevent ID順、rules、保存context／planのbyteと再掲互換性を維持し、
移行や新しいdispatch経路は追加していません。

- 既存の上限付き日英NFKC／casefold／日本語語抽出で、保存source本文とeventのsummary値だけを
  採点します。独立に適格な全行を`max_raw`・byte packingより前に重なり降順、同点はevent ID順へ
  並べます。重なり0の行も適格分母に残し、scope・partition・origin・policy・期限・整合性・
  全祖先検査とscan上限を変えず、不正時は閉じて拒否します。
- 順位方式／版、Unicode database版、正確なquery／hash、抽出語、採点fieldを既存設定と共に固定。
  order・query・順位設定の変更は再利用時に競合します。上限で落ちた行も含む全適格source hashを
  束縛し、現在文脈の変化で再送せず失効させます。両群は同一raw完全record prefixと同一byte／
  呼出し上限を使い、Bだけ適格記憶を後ろへ追加できます。reportと順位付きauditにrulesを保持します。
- [raw比較](../tests/test_raw_baseline.py)と[CLI](../tests/test_runtime_cli.py)に合成テスト10件の
  ソースを保存。fixtureメソッドを再利用し、importによるcase重複はありません。
  順位・同点・0点、Unicode／日本語、cap選択、不正入力、metadata／解答除外、適格性・破損・
  scan拒否、固定再掲／競合、上限外source変更の失効、A/B／audit membershipを扱います。
- coordinatorがPython 3.13.18で**新規10 uniqueケース／限定1起動、1.354秒**、続けて
  **全391 unique回帰／1起動、28.049秒の合格**を確認しました。今回の合計は
  **401 case executions／ローカル2起動**です。**相対リンク472件／Markdown 84ファイル合格**、
  anchor・外部URLは未検査で、空白差分も合格。今回ゲートの新CIやローカルPython 3.11の
  結果は主張しません。テストは合成store・rubric・模擬返答を使います。
- 指定Codex CLIはexit 0・最終成果ファイルを伴って正常完了し、実行metadataで
  `gpt-6.1-sol`／`xhigh`を確認。静的レビューとcoordinatorレビューで実装・契約の
  ブロッカーはありません。実行前に、不正入力時の未作成tableを直接照会するテストを、
  table未作成そのものの確認へ修正しました。既定pathの従来の保存fieldは維持し、
  テストは既定／明示ID順の再掲を確認しますが、別保存の変更前binary artifactとの比較ではありません。
- 読取り専用GitHub照会とローカルfetch／worktree準備を使い、元checkoutと無関係な編集は保持。
  live runtime／評価provider呼出し、有料効果計測、設定・認証変更、マージ、scheduleは
  行っていません。所有者は今回のfeature branch公開とレビュー用PR作成を承認しました。
  マージは別の承認が必要で、公開commitのCI結果はGitHubのPR checksを正本とします。
  公平性・意味的関連度・改善の証拠はなく、実受入は未完です。

### PR #40でマージ済みのOffline worker filesystem audit補強

以下は所有者による`29fef5ad19239e53ce3e07684b2c30e0cc2d1623`へのマージ前の
ローカル検証・実装来歴です。当時のworktreeはmain `5cea9e2`を基点としました。
当時の公開承認はfilesystem guardゲートに限定され、今回のraw順位付けの公開承認ではありません。
これらは履歴であり、新しい順位付けコードの検証結果ではありません。

- [Filesystem audit契約](oss-offline-filesystem-guards.md)に共有`install_guards`の
  補強を記載。remove／rmdir／mkdir、rename／replace、hardlink、symlinkのtargetと宛先、
  chmod／chown／utime／truncate／flags／xattr、write-open flagと指定SQLite接続先を扱い、
  影響する両側のpathを照合します。descriptor path、既定以外の監査dir-fd、
  相対・曖昧な変更pathとsymlink componentを拒否します。
- 契約上、一時領域内の絶対pathによるscratchとledger、実際の固定ledgerによる
  既存親directoryへのmkdir試行を維持します。prompt捕捉もsource読込み前に同じguardを使用。
  stdlib-only worker、target pin、payloadとsource／task／reference hash契約は未変更です。
- [使い捨てchild回帰ソース](../tests/test_oss_offline_guards.py)を追加。
  一時的な合成sentinelだけを使い、外側の内容・metadata保持、両端path、bytes／path-like、
  相対・曖昧path、symlink、descriptor／dir-fd、write flag、scratch／ledger、
  prompt捕捉での共有guard導入を扱います。環境固有metadataと不正event形は副作用なしの
  audit probe、捕捉再利用のcaseは代替payload／loaderを使います。
- coordinator確認では、Python 3.13.18で**限定17 uniqueケース／1起動、0.408秒**、
  続けて**全381 unique回帰／1起動、27.043秒が合格**しました。
  今回の新規は11件、合計**398 case executions／ローカル2起動**です。
  Python 3.11や新たなCI結果は主張しません。全回帰は固定合成captureと注入返答を含みますが、
  実model・本番の評価ではありません。**相対文書リンク459件／Markdown 83ファイル合格**、
  anchor・外部URLは未検査で、空白差分検査も合格しました。
- 指定Codex CLIはexit 0・最終成果ファイルを伴って正常完了しました。
  実行metadataで`gpt-6.1-sol`／`xhigh`を確認。独立した静的レビューとcoordinatorレビューで、
  固定ledgerに必要な既存rootへのmkdirだけの例外と、他のroot変更の拒否を確認しました。
- runtime／評価provider呼出し、有料効果計測、対象変更、設定・認証情報変更、マージ、scheduleは
  行っていません。読取り専用GitHub照会とローカルfetch／worktree準備を使い、元checkoutと
  無関係な依存設定の編集は保持しました。公開はこのfeature branchとレビュー用PRに限ります。
  レビュー済みcode用のguard補強であり、敵対的Python、
  native code、継承descriptor、未監査syscall、既存hardlink alias、filesystem raceの
  完全隔離ではありません。実受入は未完です。

### PR #39でマージ済みのOSSオフライン費用集計

`feat/oss-usage-accounting`の基点は[PR #38](https://github.com/moruku36/agent-sleep-lab/pull/38)の
merge commit `85b7dfceda509d0005295b3aa019dd7ae3dea147`です。
当時のGitHub読取りでMERGEDを確認しました。以下のローカル検証とworker来歴は、
PR #39が`5cea9e224f8bfc306735c400b9cd358db7c0ac9f`でマージする前の記録です。
当時の件数・時間は履歴で、今回の検証は上記に記載します。
feature CIの正本は引き続きGitHubのPR checksです。

- [オフライン費用集計契約](oss-cost-accounting.md)を追加。永続journalの対応比較と
  固定cohortを対象に、呼出し側が保持する厳格なJSON artifactとreportを扱います。
  固定binding／cohortと正確なreport snapshotに束縛し、cohortでは各memberの実行report
  hashも含めます。再掲時には現在のpolicyと整合性を照合します。
- 全登録課題の両armと全7費用段階をreportに保持します。使用量・費用の欠測はnullとし、
  通貨を明示して厳密な十進演算で合計します。観測の根拠hashは呼出し側の申告で未検証です。
  登録済みOpenClaw CLIの`model.run`出力から使用量・費用は取得できません。
  請求実績・金額上限・性能改善の証明はありません。
- [新規7件](../tests/test_oss_cost_accounting.py)と既存契約をcoordinatorが確認し、
  Python 3.13.18で**全370 unique回帰／1 invocation、26.989秒合格**です。
  先行の限定9件と修正後1件を含め、この増分は**計380 case executions／3 invocation**。
  費用は合成値、保存先は一時領域、返答は注入fixtureです。
  **相対文書リンク451件／Markdown 82ファイル合格**、anchor・外部URLは未検査です。
  空白差分検査も合格しました。
- 指定のCodex CLIを明示`gpt-6.1-sol`・`xhigh`で起動し、実行metadataで確認しました。
  exit 0・最終成果ファイルを伴って正常完了し、coordinatorが実装をレビューしました。
  実runtime推論・有料効果計測・新規認証・対象変更・マージはありません。
  公開対象はこのfeature branchとレビュー用PRに限ります。
  費用記録の境界を追加したもので、ゲート5全体や既存agent接続の完了ではありません。
  実受入は未完です。

### PR #38でマージ済みの選択課題offline probe（検証履歴）

`feat/oss-selected-issue-capture`は所有者がマージした
[PR #37](https://github.com/moruku36/agent-sleep-lab/pull/37)の
`63ca34df000ad95cd279d7652f4c7669d19f0c34`を基点としていました。
GitHubでMERGEDと同じcommitの
[main CI合格](https://github.com/moruku36/agent-sleep-lab/actions/runs/42921165592)を確認しました。

- [選択課題probe契約](oss-selected-issue-probe.md)を追加。capture入力・出力・summaryは
  v2とし、版付き選択情報、組込み課題番号の厳密な型・範囲、課題／suite hashを
  worker起動前に照合します。既定v1はborderlineのみ、保存済みv1 artifact／plan／cohortは
  移行不要です。
- 固定source・既定rule・実際の採点／bandとjudge／prompt経路を再利用します。
  選択した#3も含め、全件を強制judge probeと明記。元promptのborderline表記は変更せず、
  非borderline probeを通常の自動triageやtargetタスク実行として扱いません。
- adapter受領・固定journal binding・cohort v2文書／reportに選択と来歴を保持。
  同一の検証済みnotes blockだけを比較用に正規化し、課題ごとの全hashを固定します。
  再試行禁止・現在policy・不正出力・全登録課題を分母に残す規則は維持します。
- [新規回帰ソース](../tests/test_oss_selected_probe.py)に実固定workerの5課題captureと
  模擬返答のみのjournal／cohort経路を追加。公開source 11個をローカル固定Git objectから
  改変せずライセンス付きfixtureへ保存し、helperで実pinと照合します。
  Git取得だけを注入し、capture・採点・judge・promptは代替しません。
- coordinatorが残されたdraftをレビューし、**ローカル全363件／1起動が合格**
  （Python 3.13.18、26.045秒）。選択probeの新規11件を含むローカル検証の記録です。
- 別オフライン受入ではソース取得を模擬せず、実ローカル固定Git objectから11個の
  sourceを読み、5つのfresh guarded workerで全選択課題をcaptureしました。
  実score／bandは#1／#4／#5が0.65／accept、#2が0.0／skip、#3が0.5／borderline。
  実judge／promptと無通信capture transportを使用。模擬返答10回だけでjournal再開、
  5課題集計、不正返答の失敗計上、再掲の呼出しゼロ、失効後の点数非表示が合格。
  fixtureの対応差ゼロは実モデルの成績ではありません。
- worker来歴：所有者の明示承認後、同一Codexコマンドをnative一回承認へ提出。
  ローカルmetadataでprovider `openai`、model `gpt-6.1-sol`、effort `xhigh`を確認。
  外側toolは600秒でtimeoutし、最終ファイル・正常完了受領なし。照合時の該当processなし。
  再送・代替worker／model・API開発呼出しはせず、開発使用量／費用は不明です。
- 検証にはオフラインfixtureと模擬返答を使用しました。実推論、有料runtime計測、独立holdout、
  記憶の意味的利用の証拠と採用は検証範囲外です。#1／#4／#5は同文です。
  parser／evaluatorとtarget実装bytesは未変更。実受入は未完です。

### PR #37でマージ済みのcohort基準版（検証履歴）

所有者がマージした[PR #36](https://github.com/moruku36/agent-sleep-lab/pull/36)の
`6e4018c8393103c6f3da362fa409814a61571a3a`を基点とする
`feat/oss-fixture-cohort`です。GitHubでMERGEDと同じcommitの
[main CI合格](https://github.com/moruku36/agent-sleep-lab/actions/runs/42916818253)を確認しました。

- 別の[合成fixture cohort registry](oss-fixture-cohort.md)を追加。
  重複なしの2〜5課題、plan／manifestの厳密な識別情報と比較設定を、
  全memberのintent開始前に固定します。短いjournal予約で競合するintent書込を除外し、
  登録済み集合の差し替えを拒否します。
- 読取専用reportは全登録課題を分母に保持。結果不明・欠落・失効・破損・
  未対応版では全体平均と対応差を出しません。不正な完了判定は再送せず0点。
  返答本文・理由文・正解labelは集計reportへ複写しません。
- **ローカル全352件／1起動が合格**（Python 3.13.18、24.123秒）。
  cohortの新規13件を含みます。feature CIは未実施。
  返答は模擬、複数課題のcaptureはstand-inでした。既定v1は課題#3だけを選び、
  この履歴は新しい任意選択probeの複数課題経路を検証するものではありません。
- 開発worker：自動レビュー拒否後の所有者の明示承認を受け、
  同一Codex CLIコマンドをnative一回承認へ提出。ローカル実行metadataで
  provider `openai`、model `gpt-6.1-sol`、effort `xhigh`を確認しました。
  外側toolは600秒でtimeoutし、最終ファイル・正常完了受領は未取得。
  読取確認で該当processなし。残されたdraftをcoordinatorが独立レビュー・検証しました。
  再送・代替model・API worker呼出しなし。開発の使用量・費用は不明です。
- 未マージ。実推論、有料runtime計測、独立評価集合、信頼区間、理由の品質採点、
  費用schema、採用、target変更、mergeは未実施。合成開発fixtureの記述集計であり、
  性能改善の証拠ではありません。実受入は未完です。

## PR #36でマージ済みの厳格fixture評価

履歴：所有者がマージした[PR #35](https://github.com/moruku36/agent-sleep-lab/pull/35)を
基点とする`feat/oss-verdict-evaluation`です。merge
`7dc833f14034087b1559eb6ffcef71cf2675e582`、ソース
`c9d7d5e18723ee7858972a9bb3d99013bcb31e27`。GitHubでMERGEDと
PR CIのPython 3.11／3.13両check合格を確認しました。

- [厳格な判定parserと固定fixture評価](../src/agent_sleep_lab/oss_verdict_evaluation.py)を追加。
  元OSS parserと同一ではなく、意図的に厳格な部分集合です。
  JSON全体、boolのaccept、空でない上限内の理由文だけを受け、
  重複key、数値からの理由変換、前後の文章、非有限数、surrogate、追加fieldを拒否します。
  エラーは未信頼本文を含まない有限codeです。
- 任意manifestをplan登録時に固定。呼出し前に、合成の正解label、task hashと課題番号、
  evaluator／parser／strict JSON実装hash、固定target sourceと採点条件を束縛します。
  labelはprovider promptへ渡しません。後付け・変更を拒否し、
  旧未採点planはschema移行せず未採点のままです。
- reportで解析済み判定・不正判定・未完了／結果不明を区別します。
  不正な完了返答は再送せず0点。未実行／結果不明から比較差を作りません。
  現在文脈が失効すると理由文と点数を非表示にし、実装hash不一致では勝手に再採点しません。
  1つの合成fixtureの差を科学的効果とは扱いません。
- [新規回帰8件](../tests/test_oss_verdict_evaluation.py)を追加。
  **ローカル全339件が1回で合格**（Python 3.13、18.845秒）。
  strict JSONと課題番号の束縛補修後、関連8件（1.168秒）と16件（2.725秒）も合格。
  合計363ケース実行／3起動で、重複なしは339件です。
- 別オフライン受入では実際の固定sourceと捕捉promptを使用し、返答だけ模擬にしました。
  固定parserとの3例で1例一致・2例を意図的に厳格側で拒否。
  実capture→片側保存→reopen→次群→再掲→失効後の非表示まで合格し、
  1受入あたり模擬呼出し2回。課題番号の束縛前後に2回実施したため、
  差分例は計6実行／end-to-end fixtureは計2回です。作った差であり、実modelの性能ではありません。
- worker来歴：`meta/muse-wonder-1.0`を明示したレビュー1回はツール側で270秒timeout。
  応答・正常完了・解決済みmodel／費用の受領は未取得です。読取照合でprocessは該当なしですが、
  それだけでは遠隔の結果を確定できません。再試行・代替workerなし。
  coordinatorが許可済み実装・レビュー・検証を続行し、Muse正常完了とは報告しません。
- [契約と制限](oss-verdict-evaluation.md)：実推論、有料効果計測、採用、target変更、
  default／認証／schedule／mergeは未実施。labelは認証された正解ではなく合成fixtureで、
  理由の真偽・品質も未検証。残りは独立に根拠付けた評価集合、複数課題集計、
  費用承認下の実接続確認、使用量／費用schemaと実際の対応比較です。
  実受入は未完です。

## PR #35でマージ済みの永続実行journal

履歴：所有者がマージした[PR #34](https://github.com/moruku36/agent-sleep-lab/pull/34)を
基点とする`feat/oss-durable-prompt-execution`です。merge
`4492cb05a5aa057b1905753834bd0bcbb0d84f81`、ソース
`c7071b43e30f95f0b3a7b59b9720f50048b0fbec`。GitHubでMERGEDと
PR CIのPython 3.11／3.13両check合格を確認しました。

- 検証済みcaptureとprompt本文adapterを接続する別の
  [永続実行journal](../src/agent_sleep_lab/oss_execution_journal.py)を追加。
  capture全体、source／task／reference／各群のhash、bridge、adapter／agent／
  model／transportと上限を固定。同じIDで実行設定を変更することを拒否します。
  合成課題の出典と模擬／CLIの実行来歴を区別します。
- 呼出し前にintent、次群の前に返答・限定したhash付き受領をcommit。
  close／reopen後は未実行群だけを続行し、完了した組は再送せず再掲します。
  未完了intent、結果不明、不正返答、受領不一致では停止し、新adapterでも再送しません。
- 呼出し前後とreportで現在文脈を照合。失効時の返答はhash／長さ／状態だけを保存。
  保存済み本文・受領の詳細も、文脈変更／取得不能後はreportに出しません。
  既存の非公開DB内本文の物理削除とは異なります。
- 独自application ID／version／厳密schema、明示初期化、別DBの読取専用事前検査、
  full-sync、短いimmediate transactionを使用。transport中はDB lockを保持しません。
  planのdriverは一つが前提で、重なった場合は二重送信せず保守的に停止します。
  store横断の原子性やstore／worker由来の認証は保証しません。
- [模擬専用の新規8件](../tests/test_oss_execution_journal.py)を追加。
  **ローカル全331件が1回の実行で合格**（Python 3.13、18.842秒）。
  読取専用probeを明示closeする補修後、関連1件も合格（0.108秒）。
  合計332ケース実行／2起動であり、重複なしの件数は331件です。
  capture／採用はテスト作成fixtureで、CLI envelopeもすべて模擬です。
- worker受領：`ok=true`、provider `meta`、model `muse-wonder-1.0`、
  fallback試行なし。開発設計レビュー1回を受け、coordinatorが実装・検証しました。
  workerの案は権限ではなく、live選択flagは所有者承認や外部制御を代替しません。
- [APIと制限](oss-durable-execution.md)：旧模擬journal／型制限は変更なし。
  実推論、今回の実target受入、有料効果計測、新CLI入口、認証、default、
  schedule、mergeは未実施。使用量／費用は未取得、byte上限はtoken／金額上限ではありません。
  残りは別途費用承認下の実接続確認、target判定解析、固定独立評価器、
  対応比較の使用量／費用／効果計測です。実受入は未完です。

## PR #34でマージ済みのprompt本文adapter

履歴：所有者がマージした[PR #33](https://github.com/moruku36/agent-sleep-lab/pull/33)を
基点とする`feat/oss-registered-mimo-adapter`です。merge
`19c7e39440f4b938ba95250e212a5fce01d0f8c3`、ソース
`76e5b026762c5cd646fe2c92630405e09e6d4a1a`。GitHubでMERGEDと
PR CIのPython 3.11／3.13両check合格を確認しました。

- 明示した登録MiMoへ渡す専用の[prompt本文adapter](../src/agent_sleep_lab/oss_mimo_adapter.py)を追加。
  呼出し予約前にcapture全体、固定source／task／reference／request／promptのhashと
  A/B関係を照合。選択したuser本文に新たな指示を加えず、そのまま転送します。
  元HTTP要求の再現ではなく、元URL／header／model／設定の同一性は主張しません。
- paid／生成上限なしの厳格な明示選択、1〜2回、最大120秒、要求／envelope／
  生成後byte上限、CLIのmodel／provider／fallbackなし／text出力の照合と、
  hash付きの限定受領を実装。使用量／費用の対応schemaは未対応で、未取得のまま。
  token／金額上限ではなく、選択flagは所有者承認やhost制御を代替しません。
- [模擬専用6件](../tests/test_oss_mimo_adapter.py)でUnicode本文の一致、
  明示選択／予算、capture不正、model不一致／fallback／上限超過、
  timeout／割込み後の停止、私的metadataを出さない未取得表示を確認。
  **ローカル全323件が1回の実行で合格**（Python 3.13、17.043秒）。
  先行した標準Python 3.9の起動は依存不足のimportで停止し、ケース実行は0件でした。
- worker受領：provider `meta`、model `muse-wonder-1.0`、
  `ok=true`、fallback試行なしの正常完了を確認。coordinatorが未信頼の案をレビューし、
  実際と異なる返答形式、明示選択／予算、capture束縛、失敗処理を修正。
  workerの追加呼出しはありません。
- [契約と制限](oss-exact-prompt-adapter.md)：停止／予算は**instance内のメモリのみ**。
  永続live journal、現在policyの実行driver、実OSSの今回受入、実評価は未実施です。
  adapterの実行はすべて模擬transport。従来journalはschema／型制限を変えず模擬専用。
  次は現在文脈を照合する永続実行、target判定の解析、固定評価器と対応比較の
  使用量／費用／効果計測です。実受入は未完です。

## PR #33でマージ済みのoffline対応結果journal

履歴：所有者がマージした[PR #32](https://github.com/moruku36/agent-sleep-lab/pull/32)を
基点とする`feat/oss-paired-outcome-journal`です。merge
`46a1e585e580275aef003c72bc74f08c9be09b52`、ソース
`96ba94bb25d71089a5f6abdd8cd14926e42ddb97`。GitHubでMERGEDと
PR CIのPython 3.11／3.13両check合格を確認しました。

- 別の[対応結果journal](../src/agent_sleep_lab/oss_paired_outcome.py)を追加。
  代替の課題promptではなく実OSSから捕捉した要求artifactを受け取ります。
  登録時にcapture、source／task／referenceのhash、現在policyの文脈、
  呼出し側指定のworker labelを照合し、要求2本の正確なbyte・元参考byte・
  retrieval／bridge識別・両群共通byte上限を固定します。
  artifactや呼出し側管理のstore／summary labelは認証された権限ではありません。
- 各群の呼出し前にintentをcommitし、返答をcommitしてから次の群へ進みます。
  close／reopenで未実行の次群だけを続行し、保存済み返答は再送せず再掲します。
  結果不明なら計画を恒久停止。文脈変更・取得不能時は残りを実行せず、
  返答後とreport時にも照合して失効後の返答本文を出しません。
- 別application ID／schemaの非公開SQLite journalを使い、明示的なfull-sync、
  別DBの拒否、保存返答の整合性検査を追加。計画のdriverは一つを前提とし、
  採用storeとの横断的な原子transactionではありません。
- **模擬実行専用：**明示したローカルfixture providerだけを受け付けます。
  返答は合成byteであり、実targetの判定や実model受領ではありません。
  使用量・費用は未取得のまま。byte上限は生成token／金額上限ではありません。
  live provider、CLI、評価器は追加していません。
- [新規回帰8件](../tests/test_oss_paired_outcome.py)でUnicode要求のbyte一致／来歴、
  永続的な続行／再掲、結果不明、返答前後の除外、束縛／サイズ不正、
  文脈取得不能、DB識別／同期、返答破損を確認。
  **ローカル全317件が1回の実行で合格**（Python 3.13、17.497秒）。
- 別受入では、日本語の非空参考を実際の固定OSS judge／promptへ通し、
  その要求byteを模擬journalへ接続。片群実行→close／reopen→残り実行→
  全再掲まで模擬呼出しは合計2回。現在policyの除外後は両返答本文を非表示と確認。
  準備／模擬実行による採用store書込み、外部provider呼出し、実model判定は0件。
  使用量／費用の実測なし。採用・検証／評価データは明示したテストfixtureです。
- worker来歴：`claude-fable-5-2`を明示指定しましたが、本体と6件の保存後、
  300秒でtimeout。正常完了／解決済みmodelの受領は未取得で、再試行・切替なし。
  coordinatorが保存コードをレビュー・補強し、回帰2件を追加して検証しました。
- 残り：現在文脈を照合する上限付きlive provider接続、実model識別／使用量受領、
  targetの判定解析、固定した独立評価器、対応比較の費用記録と効果計測。
  今回はoffline実行の接続であり、意味的な記憶利用／性能の証明ではありません。
  既知のguardの穴は未完です。

## PR #32でマージ済みの採用参考準備

履歴：マージ済みPR #31を基点とした`feat/oss-adopted-reference-preparation`です。
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

## マージ済みguard検証の基点（検証履歴）

6件はfresh childでsocket／process／環境／cwd／write-open／SQLite／資源の
選択した制限を確認したものです。敵対コード用sandboxではありません。
別の副作用なしevent probeでは`os.remove`、`os.rename`、`os.mkdir`、
`os.link`、`os.symlink`、`os.chmod`、`os.truncate`が未捕捉でした。
実外部変更は行っていません。当時の基点はこれらのeventを補強していませんでした。
今回のローカル・未マージの補強は上記に記載し、この過去6件を追加境界の検証とはしません。

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

## PR #31の検証とPR #32への引き継ぎ（履歴）

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
4. 明示指定のlexical raw順位付けと読取り専用費用reportは所有者がPR #41／#42でマージ済みです。
   offline demoもPR #43で所有者マージ済み・CI成功です。
   上記の読み取り専用準備ゲートは実運用受入の完了ではありません。
   意味的関連度・公平性、物理purge、広い本番障害受入は未完で、
   オフラインテスト合格で完了とはしません。

入口と契約は[ランタイム手順](runtime-guide.ja.md)を参照してください。
MiMo CLIには呼出しごとの最大出力token指定がなく、生成後byte検査は
金額・tokenの厳密上限ではありません。不明終了にも費用が生じた可能性があります。
