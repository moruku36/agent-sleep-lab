# ゲート2B・最初の単位：受領契約と現在の方針

[English](gate-2b.md) | [ホーム](../README.ja.md)

**状態：最初の単位をローカル受入済み。macOS arm64／Python 3.13.18で152テスト合格（既存110件＋追加42件）です。** 新wheelを別環境へ入れ、checkout外で受領・方針を確認しました。公開・マージ・CIは別の観測なので、[受入記録](../reports/gate-2b-progress.md)と[実際のPR](https://github.com/moruku36/agent-sleep-lab/pulls)を参照してください。**ゲート2B全体は未完了で、active記憶や採用writerはありません。**

## 実装済み

- 検証受領・評価受領・現在の方針の3種類の厳密なversioned schemaとpackage側の同一コピー。サイズ上限、厳密JSON、項目間整合性、ID・hash・日時・目的・partitionの完全一致形式を検査。
- `runtime_artifacts.py`：検査・符号化と、固定identity／版／手法を付与する模擬verifier・evaluator・control境界。候補からidentityを自己申告できません。実際の利用者や呼出側を認証する機能ではありません。
- `runtime_store.py`：明示的なstore形式v2、受領の不変登録・ID/hash解決、現在の方針の永続CAS更新、追加のみの除外、`eligibility_failures`による再検査。

## 保存形式と移行

[ADR 0005](decisions/0005-runtime-store-extension.md)に従い、v2はゲート2Aのテーブルへ`receipts`と`policy_revisions`を追加します。v1は専用の`upgrade_store_v1_to_v2`を呼ぶまで拒否し、v1用APIもv2を拒否します。移行は空の追加テーブルを作るだけで、既存の証拠・原bytes・系譜を書き換えません。旧memoryの不足情報を補う移行ではありません。

v1移行時とv2起動時に、テーブル・index・triggerの定義を、既知DDLから作るschema専用のメモリ内参照と照合します。triggerの欠落／置換、列定義の変更、不明版・余計なobjectは拒否。途中の拡張失敗はv1へrollbackします。合成一時DBでの確認済みであり、実DB移行や電源断の受入ではありません。

証拠・受領・方針は**同じstore接続**で読みます。schema専用参照接続は実データに触れません。将来の採用writerが一つの`BEGIN IMMEDIATE`内で使うための構成で、単独の検査呼出しが複数API間の一貫した状態を保証するわけではありません。現在の実装には採用transaction自体がありません。

## 受領と方針の意味

- 検証登録は保存された証拠hash・scope・完全性と結び付けます。評価登録は合成の評価結果を記録するだけで、候補snapshotの採用可否をまだ判断しません。
- 受領はkind・ID・正確なhashで解決し、破損bytesやidentity列の不一致を拒否。同じclaimの再登録は元の時刻/hashを保持し、期限を延ばしません。内容違いは競合です。
- 方針はsnapshot外の追記履歴。期待現在版が一致した場合だけ次版を割り当て、再openでリセットしません。欠落・破損は失敗扱い。この単位では除外を取り消せません。
- 適格性検査は受領のmemory hash・scope・模擬verifier・手法・確認結果・日時／期限、証拠と全祖先/root、現在の許可版・目的・partition・除外を再確認します。
- 失敗0件でも、本文・記憶種別の事実確認や採用許可・active化ではありません。preferenceの由来、hypothesisの扱い、正確な評価との一致は後続writerで実装します。境界・hashは認証や同意の証明ではなく、協調的なDB全体改ざんも防げません。

## 実行した確認

`.venv/bin/python tests/run_tests.py`で**152件合格**。追加42件は契約、自己申告identity、受領破損、現在の除外・期限・許可、方針CAS・再open、同一接続でのlock、v1/v2の定義照合、証拠保持・途中失敗rollback等です。別接続のlockや順序付き更新の検査であって、プロセス間採用競合やクラッシュの検証ではありません。

[wheel検証スクリプト](../tools/check_runtime_installed.py)を新環境・checkout外から実行し、schemaコピー、明示移行、capture、検証／評価受領、解決、方針CAS、祖先root除外、再openを確認。既存CLI・証拠ストアのwheel確認も合格しました。Python 3.11／3.13のCIへ追加済みですが、成功は実際の実行記録と区別します。

## 未実装

後続の[純粋な候補構築](gate-2b-candidates.ja.md)で操作・候補・原証拠manifest・request・受領形式と、親版からの構築を実装しました。ただしDBの権威とは未接続です。記憶種別の実出典との照合、評価の採用判定、active参照、operation ID/digestの永続照会・再送、原子的な採用writerは未実装です。同時採用・プロセスクラッシュ・応答消失fixtureも未実装です。ゲート3の取得・rollback・削除、SLP全体受入、実adapter、定期実行、性能実験はまだありません。
