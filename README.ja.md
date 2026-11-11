# agent-sleep-lab

[English](README.md) | **日本語**

AIエージェントの作業経験を、根拠付きの外部記憶に整理し、次の作業で役立つか比較する実験用ハーネスです。記録、Light／Deep整理、独立した検証、原子的な採用、取得、比較評価を分離します。**モデルの重み学習ではなく、外部記憶の実験**です。

## なぜ作るか

履歴が残ることと、経験を活用できることは別です。何を残すか、根拠は何か、いつ修正するか、再利用で成果と総費用が改善するかを調べます。原資料や生成した記憶から実行権限を得ることはありません。

## 現在の開発

能力・進捗・マージ状態・検証結果の正本は[実装状況](docs/implementation-status.ja.md)に集約します。Gate文書は日付付きの履歴で、現在の作業指示ではありません。実行入口は[ランタイム手順](docs/runtime-guide.ja.md)を参照してください。

組込み合成データによるオフラインの流れを試すコマンド：

```sh
agent-sleep-lab demo
```

データ・store・providerの指定を受け付けず、使い捨ての一時状態で動かしてJSONを出力します。
[demo契約](docs/runtime-guide.ja.md#組込みオフラインdemo)にfixture受領、固定したraw／memory群、
上限、解答分離を説明しています。検証結果は[実装状況](docs/implementation-status.ja.md)を参照してください。

[合成fixture cohort契約](docs/oss-fixture-cohort.md)は事前登録した複数課題の集計用で、実モデル・独立holdoutの評価ではありません。
[選択課題offline probe契約](docs/oss-selected-issue-probe.md)は既定v1と区別した明示的な課題選択と強制judgeの来歴を定義します。

初期版の完成条件は、記録→採用→取得→Light／Deep→比較評価→既存agent一つの接続です。REM・日記・定期処理・横展開は後続の任意項目です。手動下書きの受け渡しは実agent接続ではなく、偽providerの採点は実モデルの改善証拠ではありません。

## 全体像

```mermaid
flowchart LR
  A[作業経験] --> B[原証拠の保存]
  B --> C[Light選別]
  C --> D[Deep記憶案]
  D --> E[独立した検証と評価]
  E --> F[原子的な採用]
  F --> G[scope付き取得]
  G --> H[次の作業と対応比較]
```

公開repoには合成fixtureのみを置きます。実会話・認証情報・私的記憶・評価の解答は非公開の実行保存先に分離します。実行時の正本はSQLiteであり、JSONやMarkdownは入出力形式です。ファイルの置き換えだけでは採用の原子性を保証しません。

## 読む順序

- [全体設計](docs/architecture.ja.md)／[実装契約と受入](docs/contracts-and-acceptance.ja.md)
- [実行手順](docs/runtime-guide.ja.md)／[データ契約](schemas/README.md)
- [評価計画](docs/evaluation.ja.md)／[ロードマップ](docs/roadmap.ja.md)
- [研究との対応](docs/research-basis.ja.md)／[Sleep設計](docs/dreaming.ja.md)／[外部記憶優先の判断](docs/decisions/0001-external-memory-first.md)
- [接続境界](docs/integration.ja.md)／[忘れるagentの接続設計](docs/dots-integration.ja.md)
- [合成例](examples/README.md)／[テスト方針](docs/testing-budget.ja.md)

下地にはGoogleの[Sleep framework](https://research.google/blog/the-sleep-framework-a-new-way-for-llms-to-retain-knowledge-in-continual-learning/)、Anthropicの[agent memory構成](https://www.anthropic.com/research/components-of-agent-memory)、OpenClawの[Dreaming](https://docs.openclaw.ai/concepts/dreaming)があります。各システムの公式実装・再現実験ではありません。

## 開発時の確認

Python 3.11以上で次を実行します。

```sh
python -m pip install .
python tests/run_tests.py
python tools/check_docs.py
```

PR・mainのCIではPython 3.11／3.13の全件回帰、文書内の相対ファイルリンク、wheelビルドを確認します。有料モデルはCIから呼びません。修正中は具体的なテスト名を指定できます。fixture用のimport aliasによる同一テストIDの重複は除きます。
