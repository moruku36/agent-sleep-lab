# 実装状況

[English](implementation-status.md) | [ホーム](../README.ja.md)

最終更新：2026-11-10 JST。**ゲート1・2A・2B受領／方針管理、候補構築（PR #9）、合成限定の採用writer中核（PR #10）、後続のrun ID／プロセス検証（PR #11）はすべてMERGEDです。PR #12は文書のみのマージです**（PR #10は`629560858b5aef5423d75d90a71df99b6eec65d3`）。**ゲート2B全体の受入は未完了**（信頼できるrun登録と追加の障害fixtureが残る）。旧writer試行は終了し、最終合計は**19項目・5回実行で枠を使い切りました**。**ゲート3のscope付き取得は[PR #13](https://github.com/moruku36/agent-sleep-lab/pull/13)でMERGED（`9e3d1107f96034b61a812ab2a5abb1c95ef5eaba`。マージ前にローカル4項目＋CI3項目が合格、CIはhead `90b3d9e`）。合成限定のrollbackは`feat/gate-3-safe-rollback`で実装済みですが未実行です（限定CI待ち・未マージ）。初期版全体は、3項目のPR CIを1回実行して検証されるまで約40%のままです。**削除・評価中の取得固定・渡したmemoryの記録・2B全体の受入・Light/Deep・比較評価・adapterは未完了です。

## テスト集計の履歴（2026-11-10の記録）— 上記の最終合計で置換

以前の「13項目・3回」には[PR #10のCI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42712205113)（旧writer版の3項目・1回・0.235秒）が漏れていました。その時点の訂正値は16項目・4回（中核7＋既存PR CI3＋プロセス3＋run ID3）で、当時の承認上限13を超えており、後付け承認ではありません。run ID PRのCIを加え、旧writer試行の最終合計は**19項目・5回**です。以下の記録に残る「未マージ」「承認待ち」の表現は当時の履歴です。

これは「今、何が動くか」を把握するためのページです。[ロードマップ](roadmap.ja.md)の将来計画、各ゲートの受入結果、性能実験の結果は区別します。

## テスト上限の更新（2026-11-10）

今後は1試行で合計10項目以下、通常は重点3項目を1回実行します。ローカル・CI・再実行も合算し、自動CIはPRだけ・Python 3.13だけ・3項目に限定。全件回帰や重複実行はしません。下記の174項目合格は候補構築実装の当時の受入記録で、この上限設定commitで全件を再実行したという意味ではありません。[詳しい運用](testing-budget.ja.md)。

## 全体の進捗目安

初期版全体は**約40%前後（35〜45%程度の粗い見積もり）**です。記録→採用→取得→Light/Deep→比較評価→既存エージェント1つへの接続が動く状態を100%とし、REM・日記・複数agent展開は除きます。ファイル数やテスト件数から算出した率ではありません。検証・保存・受領・候補構築に加え、合成限定の採用writer中核を重点検証できたため更新しました。run ID監査ラベルと重点クラッシュ境界も検証済みですが、基本取得を現在policy・除外・byte上限付きで重点検証できたため更新しました（直近の増分はこれ）。未実行のrollbackはCI検証まで見積りに加えません。登録済みrunの照合・追加の障害受入・評価中の取得固定・rollback／削除・coordinator・評価runner・接続が残るため、まだ前半です。性能改善率ではありません。

## 今できること／まだできないこと

| 機能 | 現状 | 範囲・制約 |
|---|---|---|
| event・memory・promotion requestの形式検査 | 実装・検証・マージ済み | 読み取り専用のオフラインCLI。形式に合っていても採用許可や事実確認にはならない |
| 出典sidecarと原証拠の保存 | 実装・検証・マージ済み | 合成データ限定のSQLiteライブラリ。event・原証拠・出典を一括保存 |
| 再送、ID競合、root重複の扱い | 実装・検証・マージ済み | byte一致の再送、競合拒否、生成物を独立rootにしない系譜検査 |
| 保存済み証拠の完全性確認 | 実装・検証・マージ済み | hash・原証拠の存在・期限。派生追加時は祖先の現在設定の許可版・partitionも確認 |
| 検証／評価受領と現在の方針管理 | 実装・検証・マージ済み | [2Bの最初の単位](gate-2b.ja.md)。追加42件・合計152件と別環境wheel検証が合格 |
| 親版＋操作から候補snapshotを構築 | 実装・ローカル受入・PR #9でマージ済み | [候補構築](gate-2b-candidates.ja.md)。追加22件・合計174件。DB書込みや採用はしない |
| 記憶の採用・active版の更新 | 合成限定の中核を実装・ローカル検証・マージ済み（PR #10、#11） | [v3 writer](gate-2b-adoption.ja.md)。履歴・現在版の一括保存、再送照合。run IDラベルは重点受入済み、登録run照合／追加障害受入は残る（2B全体は未完了） |
| scope付き取得（読み取り専用ライブラリ） | 実装・ローカル検証済み・**PR #13でマージ済み** | [ゲート3の単位](gate-3.ja.md)。マージ前にローカル4項目（0.782秒）とCI3項目（head `90b3d9e`）が合格。UTF-8 byte予算、tokenizerなし。評価中の取得固定・渡したmemoryの記録は未完了 |
| rollback（明示的な制御上の復旧） | **実装済み・未実行**。branch `feat/gate-3-safe-rollback`、限定CI待ち | [ゲート3のrollback](gate-3.ja.md)。同一scopeの保持済みsnapshotを新しいoperation IDで復元。headとpolicyのCAS、現在policyでの全件再確認（全件か無か）。新規採用でも評価の主張でもない。PR CI 1回の3項目を予約 |
| 削除・物理purge・cache掃除 | 未実装 | 取得・採用・rollbackでの現在除外の非復活は再確認のみ。物理削除やindex／cache掃除はなし |
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
- [使い方](gate-1.ja.md)／[詳細な受入記録](../reports/gate-1-progress.md)。

### ゲート2A：出典契約と合成限定の証拠ストア

- [PR #6](https://github.com/moruku36/agent-sleep-lab/pull/6)をマージ済み。mainのmerge commit：`88bd44ca9c884d906bb76bf019e7f515eea6af71`。
- `agent-sleep-provenance/1`、SQLiteでの原子的capture、再送・競合・系譜・完全性検査を実装。
- ローカルで**合計110件合格（既存87件＋追加23件）**。87件と110件を足した197件ではない。
- 新しいwheelを別環境に導入し、checkout外でschema一致・capture／replay・系譜・再open・読み取り専用検証を確認。ゲート1 CLIも確認済み。
- Python **3.11／3.13**のCI合格。[マージ後mainのCI成功記録](https://github.com/moruku36/agent-sleep-lab/actions/runs/42679309578)は上記merge commitに対応。
- [範囲と使い方](gate-2a.ja.md)／[詳細な受入記録](../reports/gate-2a-progress.md)／[保存方式の判断](decisions/0004-local-evidence-store.md)。

受入記録はその時点で実際に行った確認を残す履歴です。本ページは、その後の公開・マージ・CI確認もまとめる入口です。テスト合格は独立したセキュリティ認証や性能改善の証明ではありません。

### ゲート2Bの最初の単位：受領と現在の方針

- [PR #8](https://github.com/moruku36/agent-sleep-lab/pull/8)はマージ済み。merge commit：`a43301ff28f50ccaeb4975162c17e3d8410b38ab`。[マージ後mainのCIも成功](https://github.com/moruku36/agent-sleep-lab/actions/runs/42702164583)。
- runtime実装commit：`55dbb9f06d790e31c193faa479f24cc4d16b7ec0`。後続の進捗リンクだけのcommitは実装範囲を広げません。
- **全152テスト合格（既存110件＋追加42件）**。新wheelの受領・方針・明示移行と、既存CLI・証拠ストアの検証もcheckout外で合格。
- 実装commitのPython 3.11／3.13で[CI成功を確認](https://github.com/moruku36/agent-sleep-lab/actions/runs/42701391859)。後続文書commitのCIはPRで区別できます。
- [範囲](gate-2b.ja.md)／[受入と残る限界](../reports/gate-2b-progress.md)。この過去の単位では採用未実装でした。後続のv3中核は下記を参照。

### 後続の単位：候補snapshot構築

- [範囲と使い方](gate-2b-candidates.ja.md)／[受入記録](../reports/gate-2b-candidates-progress.md)。5種類の契約と、親版＋操作からの決定的な候補構築を追加。
- 全174テスト（既存152件＋追加22件）と新wheelのcheckout外検証が合格。公開・マージ状態は受入記録と実際のPRで区別します。
- `active`ラベルは候補内だけの状態で、受領形式を作れても実際のcommitの証拠にはなりません。後続の採用writer中核は今回重点検証済みですが、2B全体の受入は残ります。

## 最新の単位：ゲート3の安全なrollback（実装済み・未実行）

[rollbackの契約](gate-3.ja.md)：`AdoptionStore.commit_rollback`は、同一scopeで保持済み・過去に採用済みのsnapshotを、新しいoperation ID・明示的なrun監査ラベル・期待head・期待policy版を指定し、1つの`BEGIN IMMEDIATE` transactionで復元します。対象のactive memberすべてを現在の許可・期限・除外で再確認し、1件でも失敗すればrollback全体を拒否してheadと履歴は不変です。rollbackのrequest digestと受領はheadと同じtransactionで保存するため、応答消失はoperation照会で解決できます。完全再送は過去の受領を返し、同じIDで内容違いは競合です。版付きの新artifact `agent-sleep-rollback-request/1`／`-receipt/1`。採用v1/v2のartifactと再生は不変で、保存の移行は不要（v3のtableを再利用）。**rollbackは制御上の復旧で、新しい候補の採用ではなく、性能や評価の主張もしません。** `tests/test_rollback.py`に重点3項目がありますが、**1項目も実行していません**。`tests/run_tests.py`の既定で、PR CIの1回に予約しています。未実装：削除・purge・cache掃除、評価中の取得固定、渡したmemoryの記録、2B全体の受入、Light/Deep、比較評価、adapter。

## 前の成果：ゲート3の基本scope付き取得（マージ済み、PR #13）

[APIと限界](gate-3.ja.md)：`AdoptionStore`に対する読み取り専用・合成限定のライブラリ。同一接続の読取りtransaction、順位付け前の現在policy・祖先の再確認、完全性が確認できない場合の安全停止、明示的なUTF-8 byte予算。当時の記録：ローカル重点4項目を1回実行して全合格（0.782秒）、PR CI 3項目がhead `90b3d9e`で合格、PR #13はマージ済み。同じ試行の集計は**10項目中7項目・2回実行を使用済み**で、残り3項目はrollbackのPR CIに予約。旧writer試行（19項目・5回）は履歴で、枠は使い切り済みです。[受入記録](../reports/gate-3-retrieval-progress.md)。

## 前の成果：合成限定の採用writer中核（マージ済み）

PR #9はMERGED（`122fed26305a5d039de3d14b5c42633811b8affc`、`2026-11-09T22:19:24Z`）。PR #10・#11・文書のみの#12もGitHub読取りでMERGED確認済みです。以下はfeature branch期間の記録で、「未マージ」や上限の記述は当時の履歴です。

[API・範囲・正確な受入](gate-2b-adoption.ja.md)。branchは`feat/gate-2b-durable-adoption`、土台はPR #9のhead `31353d17035394840856283ad932c8005d120133`。重点7項目・実行1回・合計7項目合格。全件回帰・wheel実行検証・CIは未実施。続行でcommit直前／直後のSIGKILL・2プロセス同時競合の3項目を1回実行して合格し、同じ試行は計10項目・2回実行で上限到達です。さらに[run ID連携](gate-2b-run-id.ja.md)の3項目が1回・0.239秒で合格。明示増枠により累計13項目・3回実行で枠を使い切りました。先の10項目は今回コードで再実行していない履歴です。追加CI・新PR・マージなし。feature branchへの公開根拠は別途記録します。Muse Wonderから設計助言を受け、実装・レビュー・検証は別途実施。モデルの性能同等性を証明したものではありません。

## 残るゲート2Bの完了条件

受領・方針管理の最初のruntimeと3種類のschemaをローカル受入済みで、全152テスト（既存110件＋追加42件）と別環境wheel検証が合格しました。schema定義照合・不正入力・受領再送の整合性も補強済みです。[受入記録](../reports/gate-2b-progress.md)と[実際のPR](https://github.com/moruku36/agent-sleep-lab/pulls)で公開・マージ・CIを確認できます。以下1〜4は今回の合成v3中核で実装・重点検証済みですが、2B全体は未完了です。版付きrun ID監査ラベルは重点受入済みです。登録run照合、証拠／受領／rootの追加fixture、プロセスクラッシュ・応答消失の追加検証が残ります。

1. 候補本文の自己申告とは別の模擬境界から、検証・評価受領を解決する。受領は対象memory／snapshot・原証拠・scope・手法／protocolの正確なhashに結び付ける。
2. 受入済みの純粋な候補構築を、writerの信頼できる現在親版・全ID履歴の照合へ接続する。無関係な記憶の欠落、未知のtarget、ID衝突、循環、scope変更を拒否する。
3. 現在の許可・除外、祖先を含む証拠、期限、期待親版を、active更新と同じSQLite transactionで照合する。
4. operation ID・request digest・採用受領・active参照を一括commitし、応答消失後はoperation照会で結果を確認できるようにする。
5. 偽造／不一致の受領、証拠の変更・消失、同時null親初期化、競合writer、commit前後のプロセス終了、応答消失を合成fixtureで検査する。

[実装契約とSLP-01〜12](contracts-and-acceptance.ja.md)が判断基準です。SLPの全体受入はまだ完了していません。2Aの接続再open・SQL rollbackを、2Bのプロセスクラッシュや電源断の検証とは扱いません。2Bの採用時除外検査だけで、ゲート3の取得・rollback・削除まで完了したとはしません。

## 現在の限界

- 取込境界はローカルの模擬設定で、実際の利用者やadapterを認証していません。hashも真実性・同意の証明ではありません。
- `get()`は生の参照、`verify()`は保存内容の完全性・期限の検査であり、現在の撤回を含む採用可否の判定ではありません。
- 合成限定の採用ライブラリがあります。ゲート3の取得ライブラリは合成の重点検証を経てマージ済み、rollback writerは未実行で、いずれもlive agent接続ではありません。sleep provider接続、実環境adapter、性能実験はありません。実会話・認証情報・私的記憶を公開repoへ入れません。
- プロセス強制終了／同時書込みの重点3項目は合格。追加のクラッシュ境界・電源断・ネットワークFSの耐久性は未検証です。

## 更新方法

以後、意味のある実装単位ごとに、このページと英語版・READMEを更新します。「設計のみ／実装済み／実行確認済み／push済み／マージ済み」を区別し、対象PR・commit・CI・受入記録を添えます。未完了や本当の待ち状態も残し、予定を完成扱いにはしません。
