# 実装状況

## Gate 4A 受入結果 — 2026-11-10

[PR #17](https://github.com/moruku36/agent-sleep-lab/pull/17)はマージ済み。
対象head `a5d64acb294186c840fee7222be5f000661940e2`、
[CI42772057834](https://github.com/moruku36/agent-sleep-lab/actions/runs/42772057834)で
**新規5項目／1回・0.197秒・全合格**、wheel成功。Ubuntu／Python 3.13.18。
ローカル実行0項目。試行累計5項目／1回。文書更新で二重CIは起動しません。
合成の記録→Light→Deep→独立受領→採用→取得と中断境界の重点受入により、
初期版全体見積りは**約40%**。本番接続・比較評価・広い障害受入は未完。


[English](implementation-status.md) | **日本語** | [ホーム](../README.ja.md)

2026-11-10：初期版は**約約40%**。Gate 4Aの最小縦切りを重点受入した後の見積り。
100%は記録→採用→取得→Light/Deep→比較評価→既存agent一つへの接続。
REM・日記・横展開は対象外。ファイル数やテスト数による計算ではありません。

## 現在表

| 段階 | 確認済み基盤 | feature branch／残る境界 |
|---|---|---|
| 証拠・出典・受領・policy・採用 | 合成ライブラリはマージ済み | 実認証ではない。広い障害受入は未完 |
| 取得・rollback・論理忘却 | PR #16までレビュー修正マージ済み | 物理削除・取得固定・配布記録なし |
| Light/Deep・run lifecycle | Gate 4A／PR #17マージ済み | 偽provider最小縦切り・重点CI合格。広い障害受入は未完 |
| 比較評価 | 未マージ | [Gate 4B](gate-4b-comparison.md)：オフライン合成の対応A/Bライブラリと評価接触記録を`feat/gate-4b-offline-comparison`にコードとして保存。**重点CI5項目合格・未マージ**。論文fixture・取得固定との接続・統計・実runは未完 |
| 既存agent接続 | 未実装 | 実adapter一つの接続が必要 |

## 証拠とテスト枠

PR #16基盤：`8e2f871eb1ace6f29378ce44fad8821f36259e18`。
過去CI42755593975は10項目を1回で合格。過去Gate3累計は23項目／5回で枠終了。
今回その再実行・枠リセットはしません。

[Gate 4A](gate-4-light-deep.md)は実装済み・マージ済み・重点CI5項目合格です。
新規5項目を明示選択し、PR CIで1回だけ検証する計画。ローカル二重実行なし。
実行前に合格とは表示しません。

Gate 4B：CI42778158265で新規5項目／1回・0.149秒・全合格、wheel成功。
ローカル実行0。PR #19は未マージ。全体見積り約40%。偽scoreから採用受領・
性能主張・節約額は出力しません。

## 制限と次の到達点

ローカルrun IDをscope／入力／config／親hashへ束縛し、Light／Deepと
呼出し前の保守的なbyte／回数予約を保存します。操作案は最小addのみ。
独立受領は信頼するローカルpreparerと既存writerが担当し、生成物は権限を持ちません。
run登録は認証ではありません。ハーネス内の実API・REM・日記・定期処理は追加なし。

物理purge、除外台帳容量・忘却後整理、capture／利用policy統合、取得固定、
配布memory／評価接触記録、広いcrash・並行受入、比較評価、実agent接続は未完。
性能改善は未測定。[当時のレビュー記録](review-followup.ja.md)／
[今回の境界](gate-4-light-deep.md)／[履歴](../reports/implementation-status-history-20261110.md)。

## Gate 4B 重点受入 — 2026-11-10

[PR #19](https://github.com/moruku36/agent-sleep-lab/pull/19)は未マージ。
[CI42778158265](https://github.com/moruku36/agent-sleep-lab/actions/runs/42778158265)：
対象コード `7902b59bd21fcef83c82f5c6cf086222331428f5`、Ubuntu／Python 3.13.18。
**新規5項目・1回・0.149秒で全合格**、wheel成功。ローカルテスト0、再実行なし。
文書だけの結果追記で追加CIは起動しません。比較の計画固定・接触履歴・再開・欠測処理を
重点受入したため全体約40%。実際の論文課題評価・取得接続・既存agent接続は未完。
