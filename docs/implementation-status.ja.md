# 実装状況

[English](implementation-status.md) | [ホーム](../README.ja.md)

最終更新：2026-11-10 JST。**実装済みはゲート1とゲート2Aまでで、どちらもmainへマージ済みです。ゲート2Bの最初の受領・方針管理は実装・ローカル受入済み（全152テスト合格）です。記憶採用はまだ未実装です。公開・マージ状態は実際の配送リンクと区別します。**

これは「今、何が動くか」を把握するためのページです。[ロードマップ](roadmap.ja.md)の将来計画、各ゲートの受入結果、性能実験の結果は区別します。

## 今できること／まだできないこと

| 機能 | 現状 | 範囲・制約 |
|---|---|---|
| event・memory・promotion requestの形式検査 | 実装・検証・マージ済み | 読み取り専用のオフラインCLI。形式に合っていても採用許可や事実確認にはならない |
| 出典sidecarと原証拠の保存 | 実装・検証・マージ済み | 合成データ限定のSQLiteライブラリ。event・原証拠・出典を一括保存 |
| 再送、ID競合、root重複の扱い | 実装・検証・マージ済み | byte一致の再送、競合拒否、生成物を独立rootにしない系譜検査 |
| 保存済み証拠の完全性確認 | 実装・検証・マージ済み | hash・原証拠の存在・期限。派生追加時は祖先の現在設定の許可版・partitionも確認 |
| 検証／評価受領と現在の方針管理 | 実装・ローカル受入済み | [2Bの最初の単位](gate-2b.ja.md)。追加42件・合計152件と別環境wheel検証が合格 |
| 記憶の採用・active版の更新 | **未実装：次の2B** | 検証／評価受領、現在の許可・除外、期待親版、operation IDを結び付ける必要がある |
| 記憶取得・撤回・rollback | 未実装：ゲート3予定 | scopeでの絞込、上限付きbundle、現在の除外を適用した非復活 |
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

## 次：ゲート2Bの完了条件（未実施）

受領・方針管理の最初のruntimeと3種類のschemaをローカル受入済みで、全152テスト（既存110件＋追加42件）と別環境wheel検証が合格しました。schema定義照合・不正入力・受領再送の整合性も補強済みです。[受入記録](../reports/gate-2b-progress.md)と[実際のPR](https://github.com/moruku36/agent-sleep-lab/pulls)で公開・マージ・CIを確認できます。以下は残る2B全体の条件で、記憶採用はまだできません。

1. 候補本文の自己申告とは別の模擬境界から、検証・評価受領を解決する。受領は対象memory／snapshot・原証拠・scope・手法／protocolの正確なhashに結び付ける。
2. writerが親snapshotと操作manifestから候補を構築する。無関係な記憶の欠落、未知のtarget、ID衝突、循環、scope変更を拒否する。
3. 現在の許可・除外、祖先を含む証拠、期限、期待親版を、active更新と同じSQLite transactionで照合する。
4. operation ID・request digest・採用受領・active参照を一括commitし、応答消失後はoperation照会で結果を確認できるようにする。
5. 偽造／不一致の受領、証拠の変更・消失、同時null親初期化、競合writer、commit前後のプロセス終了、応答消失を合成fixtureで検査する。

[実装契約とSLP-01〜12](contracts-and-acceptance.ja.md)が判断基準です。SLPの全体受入はまだ完了していません。2Aの接続再open・SQL rollbackを、2Bのプロセスクラッシュや電源断の検証とは扱いません。2Bの採用時除外検査だけで、ゲート3の取得・rollback・削除まで完了したとはしません。

## 現在の限界

- 取込境界はローカルの模擬設定で、実際の利用者やadapterを認証していません。hashも真実性・同意の証明ではありません。
- `get()`は生の参照、`verify()`は保存内容の完全性・期限の検査であり、現在の撤回を含む採用可否の判定ではありません。
- active記憶、sleep provider接続、実環境adapter、性能実験はありません。実会話・認証情報・私的記憶を公開repoへ入れません。
- プロセスクラッシュ・電源断・ネットワークファイルシステムでの耐久性受入は未実施です。

## 更新方法

以後、意味のある実装単位ごとに、このページと英語版・READMEを更新します。「設計のみ／実装済み／実行確認済み／push済み／マージ済み」を区別し、対象PR・commit・CI・受入記録を添えます。未完了や本当の待ち状態も残し、予定を完成扱いにはしません。
