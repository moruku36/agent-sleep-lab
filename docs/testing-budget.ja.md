# 開発時のテスト方針

[English](testing-budget.md) | **日本語** | [ホーム](../README.ja.md)

[AGENTS](../AGENTS.md)にある所有者の2026-11-13個人開発方針が、
2026-11-10の全件回帰overrideに優先します。通常は変更に関係する3〜5ケースを選び、
**1開発試行で最大10ケース実行**です。local・CI・retry・全子agentを合算し、
個別taskのより狭い割当を守ります。使い切った枠やUNKNOWN予約を試行名の変更でresetしません。

## 実行前に選択

`python tests/run_tests.py <明示した完全method名>`を使います。
無指定の過去互換全探索や、割当より多数のケースを含むclass／module指定は使いません。
`--list <明示名>`はload／列挙だけでtest本体は実行せず、合格結果ではありません。
ケース実行数と起動回数は別々に報告します。可逆的な文書だけの変更は通常reviewと
`python tools/check_docs.py`で確認し、回帰実行を増やしません。

## 実際のCI

[workflow](../.github/workflows/gate-1.yml)はPython 3.13のみです。

| event | 静的確認 | 回帰 |
|---|---|---|
| PR | importなしAST構文検査、Markdown相対file link検査 | pin済みruntime依存をinstallし、明示した4ケースを1起動 |
| main push | 同じ静的確認 | 依存install・ケース実行なし |

matrix・wheel・全件回帰・demo command・有料model／API呼出しを静的確認に隠しません。
link checkerはanchor／外部URLを検査しません。PR作成・更新・rerunごとにさらに4ケースを
消費し得るため、公開前に予約します。許可と予約枠は試行ledgerに記録します。

現在の選択は既存`test_demo_text.DemoTextTests`の4methodで、
JSON直列化互換、追加dispatchなしの単一結果text表示、不正formatの実行前拒否、
失敗exitと一時state cleanupです。1methodを1ケースと数え、内部assertionや台本fixture呼出しは
別unittestケースでも実モデル呼出しでもありません。
次の変更では影響する4ケースに入れ替え、過去選択を積み増ししません。

日付付き報告と過去テストは保持します。多件数・旧matrix・旧runner commandは当時の履歴で、
現在の指示ではありません。失敗時も自動rerunせず、結果と残枠を確認します。
追加が必要なら具体的な増枠理由を示し、全件実行を既定にしません。
live実験には別の明示許可が必要です。回帰上限はmodel・token・金額上限ではありません。
