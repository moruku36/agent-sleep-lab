# 旧状態ページの保存（2026-11-10）

**履歴のみ。** 以下の45%・未マージ・未検証・予算待ちは当時の記述で、[現在表](../docs/implementation-status.ja.md)が置き換えます。

# 実装状況

[English](../docs/implementation-status.md) | [ホーム](../README.ja.md)

最終更新：2026-11-10 JST。ゲート1・2A、2B補助機能／採用中核、run監査ラベル、取得（PR #13）とrollback（PR #14）はマージ済み。2B・3全体の受入は未完了。[監査付き論理忘却](../docs/gate-3-forgetting.ja.md)は実装済みですが**未検証・未マージ**です。

直近の検証済み成果：PR #14は`ab25b0036ca3a04de92a0df665a8731ee59f22a7`でマージ済み。[CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42748316078)はhead `901ef2d`でrollbackの3項目を1回実行して合格（0.452秒）、wheelビルドも成功しました。初期版全体は**約45%**。同じゲート3試行は取得のローカル4＋CI3＋rollback CI3で**10/10項目・3回実行、枠を使い切り**です。忘却は**実行0項目**。次のPR作成前に、**CI1回・追加3項目（累計13項目・4回実行）**の明示増枠が必要です。ローカル再実行は予定しません。旧writer試行（19項目・5回）や過去の全件検証は履歴で、今回変更の検証ではありません。[レビュー記録](../reports/gate-3-forgetting-progress.md)。sleepエンジンや性能改善の実測はまだありません。

## テスト集計の履歴（2026-11-10の記録）— 上記の最終合計で置換

以前の「13項目・3回」には[PR #10のCI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42712205113)（旧writer版の3項目・1回・0.235秒）が漏れていました。その時点の訂正値は16項目・4回（中核7＋既存PR CI3＋プロセス3＋run ID3）で、当時の承認上限13を超えており、後付け承認ではありません。run ID PRのCIを加え、旧writer試行の最終合計は**19項目・5回**です。以下の記録に残る「未マージ」「承認待ち」の表現は当時の履歴です。

これは「今、何が動くか」を把握するためのページです。[ロードマップ](../docs/roadmap.ja.md)の将来計画、各ゲートの受入結果、性能実験の結果は区別します。

## テスト上限の更新（2026-11-10）

今後は1試行で合計10項目以下、通常は重点3項目を1回実行します。ローカル・CI・再実行も合算し、自動CIはPRだけ・Python 3.13だけ・3項目に限定。全件回帰や重複実行はしません。下記の174項目合格は候補構築実装の当時の受入記録で、この上限設定commitで全件を再実行したという意味ではありません。[詳しい運用](../docs/testing-budget.ja.md)。

## 全体の進捗目安

初期版全体は**約45%**です。記録→採用→取得→Light/Deep→比較評価→既存agent1つへの接続を100%とし、REM・日記・広域展開を除きます。基本取得とrollbackまで重点検証・マージ済みで、未検証の忘却は率に加算しません。2B全体の受入・取得固定・渡したmemory記録・sleep段階・評価runner・接続が残ります。ファイル数・テスト数から算出せず、性能改善率でもありません。

## 今できること／まだできないこと

| 機能 | 現状 | 範囲・制約 |
|---|---|---|
| event・memory・promotion requestの形式検査 | 実装・検証・マージ済み | 読み取り専用のオフラインCLI。形式に合っていても採用許可や事実確認にはならない |
| 出典sidecarと原証拠の保存 | 実装・検証・マージ済み | 合成データ限定のSQLiteライブラリ。event・原証拠・出典を一括保存 |
| 再送、ID競合、root重複の扱い | 実装・検証・マージ済み | byte一致の再送、競合拒否、生成物を独立rootにしない系譜検査 |
| 保存済み証拠の完全性確認 | 実装・検証・マージ済み | hash・原証拠の存在・期限。派生追加時は祖先の現在設定の許可版・partitionも確認 |
| 検証／評価受領と現在の方針管理 | 実装・検証・マージ済み | [2Bの最初の単位](../docs/gate-2b.ja.md)。追加42件・合計152件と別環境wheel検証が合格 |
| 親版＋操作から候補snapshotを構築 | 実装・ローカル受入・PR #9でマージ済み | [候補構築](../docs/gate-2b-candidates.ja.md)。追加22件・合計174件。DB書込みや採用はしない |
| 記憶の採用・active版の更新 | 合成限定の中核を実装・ローカル検証・マージ済み（PR #10、#11） | [v3 writer](../docs/gate-2b-adoption.ja.md)。履歴・現在版の一括保存、再送照合。run IDラベルは重点受入済み、登録run照合／追加障害受入は残る（2B全体は未完了） |
| scope付き取得（読み取り専用ライブラリ） | 実装・ローカル検証済み・**PR #13でマージ済み** | [ゲート3の単位](../docs/gate-3.ja.md)。マージ前にローカル4項目（0.782秒）とCI3項目（head `90b3d9e`）が合格。UTF-8 byte予算、tokenizerなし。評価中の取得固定・渡したmemoryの記録は未完了 |
| rollback（明示的な制御上の復旧） | **マージ済み（PR #14）**、CI3項目合格 | [ゲート3](../docs/gate-3.ja.md)。現在policyで全件再確認、headとpolicyのCAS。新規採用・評価ではない |
| 論理忘却 | **実装済み・未検証** | [契約](../docs/gate-3-forgetting.ja.md)。追加除外と監査受領を原子的に保存 |
| 物理purge・cache掃除 | 未実装 | 本文・履歴・backup・取得済みbundleの消去なし |
| Light／Deepによる候補生成 | 未実装：ゲート4予定 | 偽providerでの手動coordinatorと復旧検査から開始 |
| 論文整理のA/B評価 | 未実装・未実施：ゲート5予定 | 全試行・失敗・費用を記録するrunner。性能改善は未測定 |
| 既存エージェントへの接続 | 未実装・未実施：ゲート6予定 | 単独受入後、一つの対象へ限定して接続 |
| REM・日記・定期実行 | 初期範囲外／未実装 | 自動実行や常駐サービスは設定していない |

## マージ済みの成果と検証根拠

### ゲート1：読み取り専用の契約検証CLI

- [PR #5](https://github.com/moruku36/agent-sleep-lab/pull/5)をマージ済み。mainのmerge commit：`dcc7dac2cba8e5437695d49ef42a1903bef68760`。
- 厳密なJSON解析、同梱schemaによる検証、診断上限、CLIの終了コード、パッケージ配布の確認を実装。
- 当時のローカルテスト**87件合格**。wheelを別環境へ入れ、checkout外からCLIと同梱schemaを確認。
- [mainのCI成功記録](https://github.com/moruku36/agent-sleep-lab/actions/runs/42654863953)。
- [使い方](../docs/gate-1.ja.md)／[詳細な受入記録](../reports/gate-1-progress.md)。

### ゲート2A：出典契約と合成限定の証拠ストア

- [PR #6](https://github.com/moruku36/agent-sleep-lab/pull/6)をマージ済み。mainのmerge commit：`88bd44ca9c884d906bb76bf019e7f515eea6af71`。
- `agent-sleep-provenance/1`、SQLiteでの原子的capture、再送・競合・系譜・完全性検査を実装。
- ローカルで**合計110件合格（既存87件＋追加23件）**。87件と110件を足した197件ではない。
- 新しいwheelを別環境に導入し、checkout外でschema一致・capture／replay・系譜・再open・読み取り専用検証を確認。ゲート1 CLIも確認済み。
- Python **3.11／3.13**のCI合格。[マージ後mainのCI成功記録](https://github.com/moruku36/agent-sleep-lab/actions/runs/42679309578)は上記merge commitに対応。
- [範囲と使い方](../docs/gate-2a.ja.md)／[詳細な受入記録](../reports/gate-2a-progress.md)／[保存方式の判断](../docs/decisions/0004-local-evidence-store.md)。

受入記録はその時点で実際に行った確認を残す履歴です。本ページは、その後の公開・マージ・CI確認もまとめる入口です。テスト合格は独立したセキュリティ認証や性能改善の証明ではありません。

### ゲート2Bの最初の単位：受領と現在の方針

- [PR #8](https://github.com/moruku36/agent-sleep-lab/pull/8)はマージ済み。merge commit：`a43301ff28f50ccaeb4975162c17e3d8410b38ab`。[マージ後mainのCIも成功](https://github.com/moruku36/agent-sleep-lab/actions/runs/42702164583)。
- runtime実装commit：`55dbb9f06d790e31c193faa479f24cc4d16b7ec0`。後続の進捗リンクだけのcommitは実装範囲を広げません。
- **全152テスト合格（既存110件＋追加42件）**。新wheelの受領・方針・明示移行と、既存CLI・証拠ストアの検証もcheckout外で合格。
- 実装commitのPython 3.11／3.13で[CI成功を確認](https://github.com/moruku36/agent-sleep-lab/actions/runs/42701391859)。後続文書commitのCIはPRで区別できます。
- [範囲](../docs/gate-2b.ja.md)／[受入と残る限界](../reports/gate-2b-progress.md)。この過去の単位では採用未実装でした。後続のv3中核は下記を参照。

### 後続の単位：候補snapshot構築

- [範囲と使い方](../docs/gate-2b-candidates.ja.md)／[受入記録](../reports/gate-2b-candidates-progress.md)。5種類の契約と、親版＋操作からの決定的な候補構築を追加。
- 全174テスト（既存152件＋追加22件）と新wheelのcheckout外検証が合格。公開・マージ状態は受入記録と実際のPRで区別します。
- `active`ラベルは候補内だけの状態で、受領形式を作れても実際のcommitの証拠にはなりません。後続の採用writer中核は今回重点検証済みですが、2B全体の受入は残ります。

## 最新の単位：監査付き論理忘却（未検証）

[契約](../docs/gate-3-forgetting.ja.md)／[レビュー記録](../reports/gate-3-forgetting-progress.md)。影響dry run、現在policy CAS、追加除外＋不変受領の一括commit、応答消失照会・完全再送を実装。本文・履歴を消すものではありません。重点3項目は未実行で、増枠前のPR／CIは作成しません。

## 前の成果：安全なrollback（PR #14、マージ済み）

同一scopeの保持済み・採用済みsnapshotを復元し、全active memberを現在policyで再確認。1件でも不適格なら全体を拒否します。headと受領の原子性、完全再送・ID競合は重点CI3項目で合格（1回・0.452秒、head `901ef2d`）。[CI記録](https://github.com/moruku36/agent-sleep-lab/actions/runs/42748316078)。

## 前の成果：ゲート3の基本scope付き取得（マージ済み、PR #13）

[APIと限界](../docs/gate-3.ja.md)：`AdoptionStore`に対する読み取り専用・合成限定のライブラリ。同一接続の読取りtransaction、順位付け前の現在policy・祖先の再確認、完全性が確認できない場合の安全停止、明示的なUTF-8 byte予算。当時の記録：ローカル重点4項目を1回実行して全合格（0.782秒）、PR CI 3項目がhead `90b3d9e`で合格、PR #13はマージ済み。同じ試行の現在集計は後続rollback CIを含め**10/10項目・3回実行、枠を使い切り**。旧writer試行（19項目・5回）は履歴で、枠は使い切り済みです。[受入記録](../reports/gate-3-retrieval-progress.md)。

## 前の成果：合成限定の採用writer中核（マージ済み）

PR #9はMERGED（`122fed26305a5d039de3d14b5c42633811b8affc`、`2026-11-09T22:19:24Z`）。PR #10・#11・文書のみの#12もGitHub読取りでMERGED確認済みです。以下はfeature branch期間の記録で、「未マージ」や上限の記述は当時の履歴です。

[API・範囲・正確な受入](../docs/gate-2b-adoption.ja.md)。branchは`feat/gate-2b-durable-adoption`、土台はPR #9のhead `31353d17035394840856283ad932c8005d120133`。重点7項目・実行1回・合計7項目合格。全件回帰・wheel実行検証・CIは未実施。続行でcommit直前／直後のSIGKILL・2プロセス同時競合の3項目を1回実行して合格し、同じ試行は計10項目・2回実行で上限到達です。さらに[run ID連携](../docs/gate-2b-run-id.ja.md)の3項目が1回・0.239秒で合格。明示増枠により累計13項目・3回実行で枠を使い切りました。先の10項目は今回コードで再実行していない履歴です。追加CI・新PR・マージなし。feature branchへの公開根拠は別途記録します。Muse Wonderから設計助言を受け、実装・レビュー・検証は別途実施。モデルの性能同等性を証明したものではありません。

## 残るゲート2Bの完了条件

受領・方針管理の最初のruntimeと3種類のschemaをローカル受入済みで、全152テスト（既存110件＋追加42件）と別環境wheel検証が合格しました。schema定義照合・不正入力・受領再送の整合性も補強済みです。[受入記録](../reports/gate-2b-progress.md)と[実際のPR](https://github.com/moruku36/agent-sleep-lab/pulls)で公開・マージ・CIを確認できます。以下1〜4は今回の合成v3中核で実装・重点検証済みですが、2B全体は未完了です。版付きrun ID監査ラベルは重点受入済みです。登録run照合、証拠／受領／rootの追加fixture、プロセスクラッシュ・応答消失の追加検証が残ります。

1. 候補本文の自己申告とは別の模擬境界から、検証・評価受領を解決する。受領は対象memory／snapshot・原証拠・scope・手法／protocolの正確なhashに結び付ける。
2. 受入済みの純粋な候補構築を、writerの信頼できる現在親版・全ID履歴の照合へ接続する。無関係な記憶の欠落、未知のtarget、ID衝突、循環、scope変更を拒否する。
3. 現在の許可・除外、祖先を含む証拠、期限、期待親版を、active更新と同じSQLite transactionで照合する。
4. operation ID・request digest・採用受領・active参照を一括commitし、応答消失後はoperation照会で結果を確認できるようにする。
5. 偽造／不一致の受領、証拠の変更・消失、同時null親初期化、競合writer、commit前後のプロセス終了、応答消失を合成fixtureで検査する。

[実装契約とSLP-01〜12](../docs/contracts-and-acceptance.ja.md)が判断基準です。SLPの全体受入はまだ完了していません。2Aの接続再open・SQL rollbackを、2Bのプロセスクラッシュや電源断の検証とは扱いません。2Bの採用時除外検査だけで、ゲート3の取得・rollback・削除まで完了したとはしません。

## 現在の限界

- 取込境界はローカルの模擬設定で、実際の利用者やadapterを認証していません。hashも真実性・同意の証明ではありません。
- `get()`は生の参照、`verify()`は保存内容の完全性・期限の検査であり、現在の撤回を含む採用可否の判定ではありません。
- 合成限定の採用ライブラリがあります。ゲート3の取得ライブラリは合成の重点検証を経てマージ済み、rollbackも重点CIを経てマージ済み、論理忘却は未検証で、いずれもlive agent接続ではありません。sleep provider接続、実環境adapter、性能実験はありません。実会話・認証情報・私的記憶を公開repoへ入れません。
- プロセス強制終了／同時書込みの重点3項目は合格。追加のクラッシュ境界・電源断・ネットワークFSの耐久性は未検証です。

## 更新方法

以後、意味のある実装単位ごとに、このページと英語版・READMEを更新します。「設計のみ／実装済み／実行確認済み／push済み／マージ済み」を区別し、対象PR・commit・CI・受入記録を添えます。未完了や本当の待ち状態も残し、予定を完成扱いにはしません。
