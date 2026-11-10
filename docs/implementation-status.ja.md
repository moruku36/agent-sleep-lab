# 実装状況

[English](implementation-status.md) | **日本語** | [ホーム](../README.ja.md)

2026-11-10：初期版は**約40%**。Gate 4CのCI前スナップショットです。
その後の結果はPR checksを参照。100%は記録→採用→取得→Light/Deep→比較評価→
既存agent一つへの接続。REM・日記・横展開は対象外。ファイル数やテスト数では計算しません。

## 現在表

| 段階 | 確認済み基盤 | feature branch／残る境界 |
|---|---|---|
| 証拠・出典・受領・policy・採用 | 合成ライブラリはマージ済み | 実認証ではない。広い障害受入は未完 |
| 取得・rollback・論理忘却 | PR #16までレビュー修正マージ済み | 物理削除・配布記録なし |
| Light/Deep・run lifecycle | [Gate 4A](gate-4-light-deep.md)／PR #17マージ済み | 偽provider最小縦切り。広い障害受入は未完 |
| 比較基盤 | [Gate 4B](gate-4b-comparison.md)／PR #19マージ済み | 合成の対応A/B計画・接触履歴。性能実験ではない |
| 取得から比較への接続 | [Gate 4C](gate-4c-retrieval-comparison.md)を`feat/gate-4c-paper-retrieval`に保存・レビュー済み | CI前：未テスト・未実行・未マージ。出典一致の文脈のみで、完全な生取得baselineではない |
| 既存agent接続 | 未実装 | 実adapter一つの接続が必要 |

## 受入証拠とテスト枠

- **過去Gate 3**：PR #16基盤`8e2f871eb1ace6f29378ce44fad8821f36259e18`。
  CI42755593975で10項目を1回合格。試行累計**23実行／5回**、枠終了。
  このbranchで再実行・リセットしません。
- **Gate 4A**：PR #17マージ済み。対象コード`a5d64acb294186c840fee7222be5f000661940e2`。
  [CI42772057834](https://github.com/moruku36/agent-sleep-lab/actions/runs/42772057834)で
  新規5項目を1回・0.197秒で合格、wheel成功。Ubuntu／Python 3.13.18。
  試行累計**5実行／1回**、ローカル0。当時の見積り35〜40%。
- **Gate 4B**：[PR #19](https://github.com/moruku36/agent-sleep-lab/pull/19)は
  `acc553050b4437333514d8d534ceebed08609c1a`でマージ済み。
  対象コード`7902b59bd21fcef83c82f5c6cf086222331428f5`を
  [CI42778158265](https://github.com/moruku36/agent-sleep-lab/actions/runs/42778158265)で
  新規5項目・0.149秒で合格、wheel成功。結果記録だけのpushが予期せず
  [CI42778493776](https://github.com/moruku36/agent-sleep-lab/actions/runs/42778493776)を
  起動し、head `568cccb4c1c27d7b36095ff6a23ef3ec6d86b401`で同じ5項目を
  0.168秒で再合格、wheel成功。取消要求時には終了済みで、取消は成立していません。
  実累計**10実行／2回**、ローカル0、枠終了。以前の5／1は最初の観測のみ。
  [当時の訂正](../reports/gate-4b-acceptance-20261110.md)。
- **Gate 4C**：新しい取得接続5メソッドだけをbounded runnerとPR-only workflowで
  明示選択。**このCI前時点では0実行、合格主張なし。** PR CIで5項目を1回の計画。
  ローカル二重実行・push CI・matrix・過去全件はなし。修正を含む上限は10実行。
  PR paths判定は累積diffのため、CI後に結果記録だけのpushをしません。
  その後の結果はPR checksとリポジトリ外のローカル受領に記録します。

## Gate 4Cの境界

読み取り専用adapterが、現行取得で適格と再確認した記憶のevent／source本文とhash、
完全な統合記録、scope・partition・取得条件・snapshot・policyを固定します。
A群にはその生出典、B群には同じ生参照の先頭部分＋統合記録を同じ上限内で渡します。
取得記憶が引用しない生証拠は含まないため、**出典一致の表現fixtureであり、完全な
生取得baselineの公平な比較ではありません**。論文はすべて架空。同時作成した
経験と課題は独立holdoutではなく、偽の返答・scoreは品質・節約・性能・採用受領ではありません。

各送信・評価・報告で現行storeを再確認し、撤回・証拠欠落や不一致・文脈変更なら
無効化して復活させません。保存文脈と返答は再openで再実行なしに引き継ぎます。
固定文脈は保持されるので物理削除ではありません。複数read間と再確認から送信までの
競合は未解決。ローカル構築・run登録は認証ではありません。
ハーネス内の実API・network・CLI・REM・日記・定期処理・追加支出は追加なし。

## 残る作業

完全な生取得baselineの固定、配布memory記録、実比較protocolと総費用計測、広い
crash・並行受入、物理purge・除外台帳容量・忘却後整理、capture／利用policy統合、
出典／runの認証、既存agent一つへの接続。性能改善は未測定。
[当時のレビュー記録](review-followup.ja.md)／[履歴](../reports/implementation-status-history-20261110.md)。
