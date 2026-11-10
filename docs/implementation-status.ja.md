# 実装状況

[English](implementation-status.md) | **日本語** | [ホーム](../README.ja.md)

2026-11-10：初期版は**約30〜35%**。Gate 4A受入待ちのため据え置き。
100%は記録→採用→取得→Light/Deep→比較評価→既存agent一つへの接続。
REM・日記・横展開は対象外。ファイル数やテスト数による計算ではありません。

## 現在表

| 段階 | 確認済み基盤 | feature branch／残る境界 |
|---|---|---|
| 証拠・出典・受領・policy・採用 | 合成ライブラリはマージ済み | 実認証ではない。広い障害受入は未完 |
| 取得・rollback・論理忘却 | PR #16までレビュー修正マージ済み | 物理削除・取得固定・配布記録なし |
| Light/Deep・run lifecycle | マージ済みruntimeなし | 偽provider最小縦切り実装、受入待ち |
| 比較評価 | 未実装 | 論文fixture・A/B runner・評価接触記録が必要 |
| 既存agent接続 | 未実装 | 実adapter一つの接続が必要 |

## 証拠とテスト枠

PR #16基盤：`8e2f871eb1ace6f29378ce44fad8821f36259e18`。
過去CI42755593975は10項目を1回で合格。過去Gate3累計は23項目／5回で枠終了。
今回その再実行・枠リセットはしません。

[Gate 4A](gate-4-light-deep.md)は実装済み・未マージ・runtime未実行です。
新規5項目を明示選択し、PR CIで1回だけ検証する計画。ローカル二重実行なし。
実行前に合格とは表示しません。

## 制限と次の到達点

ローカルrun IDをscope／入力／config／親hashへ束縛し、Light／Deepと
呼出し前の保守的なbyte／回数予約を保存します。操作案は最小addのみ。
独立受領は信頼するローカルpreparerと既存writerが担当し、生成物は権限を持ちません。
run登録は認証ではありません。ハーネス内の実API・REM・日記・定期処理は追加なし。

物理purge、除外台帳容量・忘却後整理、capture／利用policy統合、取得固定、
配布memory／評価接触記録、広いcrash・並行受入、比較評価、実agent接続は未完。
性能改善は未測定。[当時のレビュー記録](review-followup.ja.md)／
[今回の境界](gate-4-light-deep.md)／[履歴](../reports/implementation-status-history-20261110.md)。
