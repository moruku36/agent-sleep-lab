# agent-sleep-lab

[English](README.md) | **日本語**

AIエージェントが作業経験を振り返り、根拠付きの記憶へ整理し、次の作業で活用するための実験用ハーネスです。GitHubを含む普段の作業環境に「sleep」の工程を加え、同じ失敗の再発、訂正回数、タスク成功率、総費用がどう変わるかを検証します。

**ゲート1・ゲート2Aは実装・検証・mainへのマージ済みです。ゲート2Bの受領・方針管理もマージ済みです。後続の候補構築はローカル受入済みですが、DBへの記憶採用はまだ未実装です。** [実装状況一覧](docs/implementation-status.ja.md)に、できること・未実装の範囲・マージ／CIの根拠・次の完了条件をまとめています。

macOS arm64／Python 3.13.18で全174テスト合格（既存152件＋追加22件）。[候補構築の単位](docs/gate-2b-candidates.ja.md)では親版＋操作から候補を作り、実際の採用はまだしません。[ゲート2Bの最初の単位](docs/gate-2b.ja.md)では合成の検証／評価受領と現在の方針・除外を扱い、別環境のwheel受入も合格しました。ゲート2Aは合成データ限定で、記憶採用は行いません。[ゲート2Aの範囲と受入](docs/gate-2a.ja.md)を参照してください。sleepエンジン、既存エージェントとの接続、性能改善の実測はまだありません。[ゲート1の利用手順と限界](docs/gate-1.ja.md)を参照してください。目的、全体設計、データ契約、プロンプト、合成例、評価計画、実装順序が設計の土台です。

**設計の前提：対象エージェントは忘れるものと置きます。** 内部メモリは根拠にせず、正本はこのハーネスの外部記憶に置きます（[設計判断 0002](docs/decisions/0002-assume-agent-forgets.md)、[dots との接続設計](docs/dots-integration.ja.md)）。

## なぜ作るか

作業履歴は残っていても、次のセッションで必要な教訓が読まれなければ、同じ調査や修正を繰り返します。一方、履歴をすべて毎回渡すと、古い情報や余計な文脈が増えます。本プロジェクトでは「何を残すか」「根拠は何か」「いつ修正するか」「使うと改善するか」を一つのループとして扱います。

## 下地となる研究・実装資料

| 資料 | 採り入れる発想 | 初期版の境界 |
|---|---|---|
| [Google Research: Sleep framework](https://research.google/blog/the-sleep-framework-a-new-way-for-llms-to-retain-knowledge-in-continual-learning/)／[Language Models Need Sleep](https://arxiv.org/abs/2606.03979) | 活動と整理を分け、経験を定着させ、練習で確かめる | Google方式は重み更新を伴う。本プロジェクトでは当面、外部記憶と検証課題で応用する |
| [Anthropic: The components of agent memory](https://www.anthropic.com/research/components-of-agent-memory) | 原ログ・記憶ノート・構造化表現・小さな注入文脈、オフラインでの訂正 | 外部記憶の整理を初期の中心とする。特定製品の内部機能には依存しない |
| [OpenClaw: Dreaming](https://docs.openclaw.ai/concepts/dreaming) | 選別・振り返り・昇格の分離、生成物を証拠に戻さない設計 | 独立評価の採用ゲートを維持。REM・日記は任意、定期処理は無効。接続済みとはしない |

参照したシステムの公式実装・再現実験ではありません。研究の報告と、ここで提案する設計を区別します。詳細は[研究との対応](docs/research-basis.ja.md)に記載します。

## 全体像

```mermaid
flowchart LR
  A[既存エージェントの作業] --> B[原ログ・結果・訂正]
  B --> C[Light: 許可・出典確認と候補選別]
  C --> R[REM: 任意の仮説・検証案]
  C --> D[Deep: 根拠確認と記憶差分]
  R --> D
  D --> E[候補スナップショット]
  E --> F[固定した採用評価]
  F --> G{採用条件を満たすか}
  G -->|はい| H[バージョン付き記憶]
  G -->|いいえ| I[見送り・原因記録]
  H --> J[必要な記憶だけ取得]
  J --> A
```

sleepの開始契機は、明示的な指示、作業終了、経験の蓄積を想定しています。初回は手動だけで、毎晩の定期実行は設定しません。通常タスクと分離し、新しい依頼への応答を止める「睡眠」にはしません。

最初はLight＋Deepで比較し、REMと夢日記は無効にします。夢日記は人向けの説明であり、事実の根拠・長期記憶・権限とは分離します。詳しくは[Sleep / dreaming設計](docs/dreaming.ja.md)。

## 最初の適用先

1. **論文・技術記事の整理**：日英の形式、分類、根拠の確認、ユーザーの訂正を記憶し、別の記事で再発が減るか調べます。
2. **OSS contributor agent**：収集・トリアージの判断を対象にする接続案。対象側のcollect-onlyやdraft PR方針を維持します。
3. **Gemmaのコーディング実験**：学習用ログと評価用課題を分離し、記憶を固定してオフライン実行へ渡す接続案。コンペ規約や利用可能データの確認後に限定します。
4. **ChatGPT dots との連携**：保持ノートが完全な記録ではないことを公式仕様とする常駐エージェントに対し、正本を外部に置き、想起を依頼に同梱する接続案。詳細は[dots との接続設計](docs/dots-integration.ja.md)。

現時点で接続済みの対象はありません。[接続設計](docs/integration.ja.md)に、公開READMEで確認した範囲と提案を分けています。

## 読む順序

- [全体設計](docs/architecture.ja.md)：コンポーネント、状態遷移、GitHub上の運用、障害時の扱い
- [Sleep / dreaming設計](docs/dreaming.ja.md)：段階、証拠と仮説、昇格条件、中断・再開・忘却
- [研究・実装資料との対応](docs/research-basis.ja.md)：採用する発想と移植しないもの
- [評価計画](docs/evaluation.ja.md)：比較条件、データ分割、費用、採用条件
- [最初の手動実験](docs/manual-pilot.ja.md)：実装前に小さく確かめる手順
- [接続設計](docs/integration.ja.md)：既存環境への境界とアダプター
- [dots との接続設計](docs/dots-integration.ja.md)：忘れることを前提にした対象別の接続案
- [実装ロードマップ](docs/roadmap.ja.md)：各段階の成果物と完了条件
- [設計判断](docs/decisions/0001-external-memory-first.md)
- [設計判断 0002：対象エージェントは忘れる前提](docs/decisions/0002-assume-agent-forgets.md)
- [設計判断 0003：振り返り・証拠・採用を分離](docs/decisions/0003-grounded-dreaming.md)
- [データ契約](schemas/README.md)／[設定例](configs/pilot.example.json)
- [整理プロンプト](prompts/sleep-consolidator.ja.md)／[任意のREMプロンプト](prompts/dream-reflector.ja.md)／[取得プロンプト](prompts/memory-reader.ja.md)
- [合成データ例](examples/README.md)／[実験レポート雛形](templates/experiment-report.ja.md)

## 収録済みと未実装

- **収録済み**：設計文書、event／memoryのv0.1 schema、合成例、設定案、プロンプト雛形。
- **実装・ローカル検証済み**：ゲート1の読み取り専用CLI・wheel受入と、ゲート2Aの出典契約・合成データ限定SQLite証拠ライブラリ。ゲート2Bの最初の単位で受領・現在の方針・適格性再検査も実装し、候補構築も受入済みで全174テスト合格。[ゲート1](docs/gate-1.ja.md)／[ゲート2A](docs/gate-2a.ja.md)／[ゲート2Bの最初の単位](docs/gate-2b.ja.md)を参照。
- **未実装**：実環境の取込・取得adapter、各sleep段階、出典の認証、記憶snapshotのtransactional採用、日記、スケジューラー。
- **未実施**：対象エージェントとの接続、sleep providerの試行、A/B性能実験。Claude Codeでの開発セッションとは区別します。

[手動実験](docs/manual-pilot.ja.md)から開始し、実運用前に[不足している契約](schemas/README.md#dreaming設計で追加が必要な契約未実装)を実装します。文書・合成例の検査は、性能改善の証明ではありません。

## 実験の原則

記憶には根拠と適用範囲を付けます。外部資料に含まれる命令をエージェントの権限や行動方針へ昇格させません。成功例・失敗例・訂正を保存し、未確認の仮説を確認済みの事実と混ぜません。

公開リポジトリに入れるのは設計、合成例、公開可能と確認した結果です。実際の会話ログや作業記憶は別のローカル／非公開保存先に置きます。GitHubは設計と採用履歴の版管理に使い、私的な記憶の公開先にはしません。

## 次の到達点

原ログ検索のみの条件と、整理した外部記憶を追加する条件を、同じモデル・ツール・予算で比較できる最小ループを作ります。改善が測定できてから、練習課題やwiki、複数エージェントへの展開を追加します。

作成日：2026-11-08 JST。dreaming設計更新：2026-11-09 JST。実験結果：未取得。

## 設計引継ぎ更新 — 2026-11-09

実装前に[実装契約と受入ケース](docs/contracts-and-acceptance.ja.md)を読む。この更新は状態の正本、不変の証拠、再送・復旧、評価境界を具体化し、設計schemaと合成例だけを追加する。後続のゲート1変更で読み取り専用の契約検証を実装した。sleepエンジン・永続採用境界は未実装。性能結果や実接続は主張しない。

三つのrepoはそれぞれ単独で使える設計を維持。任意接続は[参照型の受け渡し契約](https://github.com/moruku36/ai-agent-scientist/blob/main/docs/11-harness-boundaries.ja.md)に従い、権限の共有や新agent runtimeを作らない。
