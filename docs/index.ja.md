# 文書索引

[English](index.md) | **日本語** | [ホーム](../README.ja.md)

現在の能力・マージ／検証の証拠・残る課題は[実装状況](implementation-status.ja.md)を
参照してください。設計文書は契約や提案、日付付きレポートは試した版の記録であり、
現在の作業指示ではありません。

## 実行と接続

| 目的 | ガイド |
|---|---|
| モデルを呼ばない合成データの手順を試す | [組込みオフラインdemo](runtime-guide.ja.md#組込みオフラインdemo) |
| sleep・review・採用・取得・比較を明示的に呼ぶ | [ランタイム手順](runtime-guide.ja.md) |
| review済み公開byte列を、実行storeへ受け入れずに準備する | [公開資料の受入準備](public-source-intake.ja.md) |
| 別の公開文書1件storeとreview・削除・consumer境界を使う | [公開文書lifecycle](public-document-lifecycle.ja.md) |
| Light／Deepを明示接続し、許可・review・採用を分離する | [公開文書モデル契約](public-document-model.ja.md) |
| 採用済み合成記憶から比較用のOSS入力をofflineで作る（送信なし） | [OSSリクエスト準備](oss-prepare.ja.md) |
| 事前登録した合成の複数課題を集計する（実モデル・holdoutの証拠ではない） | [Fixture cohort (English)](oss-fixture-cohort.md) |
| 既定v1と別に、課題の明示選択と強制judgeの来歴を調べる | [選択課題offline probe (English)](oss-selected-issue-probe.md) |
| 対象agentの制約と「忘れる」前提を知る | [接続境界](integration.ja.md)、[対象agentの接続設計](dots-integration.ja.md) |

公開fixtureは合成データに限定します。非機密の試用要約を公開しても、その入出力の公開や、
合成専用の入口へ実データを渡す許可にはなりません。adapterは対象側の実行・テスト・公開・
offline制約とnative承認を引き続き守ります。

## 設計と評価

履歴が残ることと、経験を活用できることは別です。何を残すか、根拠は何か、
いつ修正するか、再利用で成果と総費用が改善するかを調べます。

- [構成の概要](architecture-overview.ja.md)：図、source module対応、store境界。
- [全体設計](architecture.ja.md)／[実装契約と受入](contracts-and-acceptance.ja.md)。
- [データ契約](../schemas/README.md)／[合成例](../examples/README.md)。
- [評価計画](evaluation.ja.md)／[研究handoff](gate-4e-research-handoff.ja.md)／[ロードマップ](roadmap.ja.md)。
- [研究との対応](research-basis.ja.md)／[Sleep設計](dreaming.ja.md)／[外部記憶優先の判断](decisions/0001-external-memory-first.md)。

初期版の完成条件は、記録→採用→取得→Light／Deep→比較評価→既存agent一つの接続です。
REM・日記・定期処理・横展開は後続の任意項目であり、クイックスタートの必須部分ではありません。

背景にはGoogleの[Sleep framework](https://research.google/blog/the-sleep-framework-a-new-way-for-llms-to-retain-knowledge-in-continual-learning/)、
Anthropicの[agent memory構成](https://www.anthropic.com/research/components-of-agent-memory)、
OpenClawの[Dreaming](https://docs.openclaw.ai/concepts/dreaming)があります。
各システムの公式実装・再現実験ではありません。

## 作業指示ではない試用記録

- [2026-11-12の公開情報試用](public-source-trial-2026-11-12.ja.md)：別のローカル・未マージ拡張によるものです。レポート公開でその実行経路が公開されるわけではありません。
- [2026-11-13の部分的な実測](live-development-measurement.ja.md)：byte／時間の観測、未完の受入と会計上の制限。
- その他の日付付きgateレポートも過去の証拠です。利用可能な能力の判断には[現在の実装状況](implementation-status.ja.md)を参照してください。

## 開発時の確認

[クイックスタート](../README.ja.md#クイックスタート)に従ってリポジトリからインストールした後：

```sh
.venv/bin/python tests/run_tests.py test_public_document_model.PublicDocumentModelTests.test_document_text_cannot_supply_permission
.venv/bin/python tools/check_docs.py
```

上のテスト名は影響ケースの明示選択例であり、今回の確認を再実行する指示ではありません。
通常3〜5件の意味あるケースを選び、local・CI・retry・子agentを合算して最大10ケース実行とし、
UNKNOWNも予約枠に保持します。文書だけの変更は通常reviewで確認し、回帰実行を増やしません。
runnerの無指定全件実行は使いません。PR・main CIはPython 3.13でimport・testなしのAST構文検査と
文書の相対file link検査だけです。依存install・回帰全件・version matrix・wheel・有料推論はありません。
exact headの結果は[現在の実装状況](implementation-status.ja.md)で確認します。
文書checkerはanchorや外部URLを検査しません。[repo指示](../AGENTS.md)と
[テスト方針](testing-budget.ja.md)も参照してください。

## ライセンス

[Package metadata](../pyproject.toml)は**UNLICENSED**です。オープンソースライセンスは付与していません。
