# 研究との対応と検証範囲

確認日：2026-11-08 JST。記事本文を確認して設計へ対応付けた。論文の独立再現、コード実行、性能測定は行っていない。

## Google Sleep

[Google Researchの記事](https://research.google/blog/the-sleep-framework-a-new-way-for-llms-to-retain-knowledge-in-continual-learning/)はAli Behrouz、Vahab Mirrokniによる2026-10-27の紹介。元論文は[Language Models Need Sleep](https://arxiv.org/abs/2606.03979)。本リポジトリでは記事の手法説明を確認し、論文全体を再検証したとは扱わない。

短期情報を長期パラメータへ定着させる工程と、生成した練習データで能力を改善するdreamingを扱う。専用のモデル構造と重み更新が含まれる。

ここから採り入れるのは「活動と整理を分ける」「経験を検証可能な形で再利用する」という設計上の着想。外部メモリーの編集や確認問題の生成を行っても、Google方式の再現やモデル自体の学習とは呼ばない。重み更新は後続の独立した研究課題とする。

## Anthropicのagent memory

[Lance Martinの記事](https://www.anthropic.com/research/components-of-agent-memory)は2026-11-06公開の企業技術記事。モデルの重み更新を対象から外し、セッションをまたいで読める外部文脈を扱う。

原ログ、記憶ノート、wikiなどの表現、小さな注入文脈を区別し、オフラインでの整理・訂正を説明する。記憶を利用する能力はモデルや指示に左右され、wiki作成・保守の負担もある。

本リポジトリの初期設計は、原証拠へのリンク、記憶の訂正、必要な項目の取得を中心にする。wikiは必須とせず、比較で有用と分かった場合に追加する。

## 本プロジェクトの仮説

| 仮説 | 検証する比較 | 改善が見られない場合 |
|---|---|---|
| 整理した記憶で同じ誤りの再発が減る | 原ログ検索 vs 整理した記憶＋原ログ検索 | 原ログ検索を採用し、記憶工程は見送る |
| 根拠確認が誤った記憶の継承を減らす | 整理前ノート vs 根拠照合後の記憶 | 検証手順や対象を見直す |
| 練習による確認が汎化に役立つ | 整理のみ vs 整理＋練習 | 練習を追加しない |

これらは未検証の仮説であり、両記事がこの環境での効果を証明したものではない。研究の性能値を本プロジェクトの期待改善率へ移し替えない。

## 関連する読書ノート

- [Google Sleepの既存ノート](https://github.com/moruku36/independent-tech-research-notes/blob/main/surveys/llm-infrastructure/2026-google-sleep-continual-learning.ja.md)
- [Anthropicの既存ノート](https://github.com/moruku36/independent-tech-research-notes/blob/main/surveys/llm-infrastructure/2026-anthropic-agent-memory-components.ja.md)
- [Raw-RAGの比較ノート](https://github.com/moruku36/independent-tech-research-notes/blob/main/surveys/llm-infrastructure/2026-raw-rag-agentic-memory.ja.md)
