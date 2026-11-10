# 実装状況

[English](implementation-status.md) | [ホーム](../README.ja.md) | [履歴](../reports/implementation-status-history-20261110.ja.md)

最終確認：2026-11-10 JST。**初期版は約30〜35%**。以前の45%は基盤への偏重を訂正しました。sleepの中心仮説をまだ測っていません。
定義は記録→採用→取得→Light/Deep→比較評価→既存agent1つへの接続。REM・日記・横展開は対象外。件数から進捗を計算しません。

## 現在表

| 段階 | mainの実装 | 検証／残る範囲 |
|---|---|---|
| 契約CLI | マージ済み | オフライン構造検証。真実性・許可の認証ではない |
| 出典付き証拠・系譜 | マージ済み | 合成SQLite、再送・scope・祖先検査 |
| 受領・方針・原子的採用 | 中核マージ済み | 登録run、追加障害受入、2B全体は未完了 |
| 取得 | PR #13マージ済み | scope・現在policy・UTF-8 byte予算。固定取得・渡したmemory記録は未実装 |
| rollback | PR #14マージ済み | 現在の除外で全件再確認、性能評価ではない |
| 監査付き論理忘却 | **PR #15マージ済み・重点CI合格** | 追加除外＋受領。物理削除ではなく台帳上限・忘却後の整理経路に課題 |
| 物理削除・再取込抑止 | 未完了 | 本文・backup・cache・呼出し済みbundleを消さない |
| Light/Deep・coordinator | **未実装** | 次は偽providerの最小縦切り、run登録・状態・上限制御 |
| 論文fixture・A/B runner | **未実装・比較未実施** | SLP-12の評価集合接触記録も未実装 |
| 既存agent接続 | **未実装** | 書込みはライブラリのみ。run_idは監査ラベル |

## 直近の照会済み証拠

- [PR #15](https://github.com/moruku36/agent-sleep-lab/pull/15)：MERGED、merge `dd79e234fc2888f99685fb2dcf3961b04645f399`、2026-11-10T03:56:07Z。
- [CI42752368409](https://github.com/moruku36/agent-sleep-lab/actions/runs/42752368409)：head `ea28c71bf32dd0625f0c886dcc15bc65060df29b`、3項目・1回・0.652秒で合格、wheel成功。
- 同じGate3試行は**13項目・4回で承認枠を使い切り**。旧writer19項目・5回は別の歴史的記録です。
- 今回の[レビュー修正](review-followup.ja.md)はbranch上の**未実行・未マージ**。新規5＋既存5の回帰案を用意し、PR CI1回・追加10項目（累計23項目・5回）の増枠承認待ち。全件実行・CI全件化はしていません。
- 利用者提供のWindows／Python3.15.2の「211項目、207合格・4不合格」は外部報告。対象SHA・ログ未照合で当方の受入数に合算しません。今回のWindows修正もnative環境未検証。
- POSIX SIGKILLテストは機能がない環境でskip予定。Windowsのクラッシュ復旧の保証ではありません。

## 制約と次の一歩

ローカルの模擬境界であり、認証や実agent接続ではありません。検索の関連度・sleepの性能改善は未測定。
[12指摘の対応表](review-followup.ja.md)で修正・部分修正・未解決を区別しています。新たな構造移行で物理削除・台帳上限・評価不要整理・許可統合・journal索引を解決する前に、本番利用とは呼びません。

修正の重点受入後、偽providerで入力→Light→Deep→既存検証／採用→取得の1周を先に作ります。その後に論文fixture比較、1 agent接続。
[設計ロードマップ](roadmap.ja.md)／[採用契約](contracts-and-acceptance.ja.md)。過去の訂正・全件受入は[履歴](../reports/implementation-status-history-20261110.ja.md)へ分離しました。
