# 既存環境との接続設計

2026-11-08 JSTに公開READMEを確認した範囲を示す。リポジトリが存在することは、ローカルで実行できることや、このハーネスと接続済みであることを意味しない。現在の接続数は0。

## 対象と導入順

| 対象 | 確認した範囲 | 提案する接続 |
|---|---|---|
| [independent-tech-research-notes](https://github.com/moruku36/independent-tech-research-notes) | 日英ノート、テーマ別索引、読書履歴 | 論文整理の結果と明示的な訂正を経験として記録。最初のpilot |
| [oss-contributor-agent](https://github.com/moruku36/oss-contributor-agent) | README上では収集・トリアージ実装、対象はcollect-only。パッチと外部PRは後続段階 | 初めは収集・トリアージの理由と結果だけを記録。sleepが外部PRを出さない |
| [gemma4-developer-agent](https://github.com/moruku36/gemma4-developer-agent) | README上のオフラインコーディングハーネス、タスク・時間・トークン制約 | 公開可能な練習ログから固定記憶を作り、実行前にバンドルへ組み込む案 |
| [ChatGPT dots](https://learn.chatgpt.com/docs/dots) | 公式ドキュメントで記憶仕様を確認（2026-11-08）。実接続なし | 忘れることを前提に、正本を外部へ置き、想起バンドルを依頼に同梱する。詳細は dots-integration.ja.md |

後二者のREADMEだけを確認しているため、実装APIや内部ログ形式は未確認。実装時には対象commitのコード・設定・規約を読み直す。他のチャットやアプリの履歴を一括収集する前提は置かない。

## Adapterの最小契約（設計）

```text
capture(task, observation, feedback) -> event[]
sleep(event_snapshot, active_memory, budget) -> candidate_snapshot + report
retrieve(project, task_family, query, memory_snapshot, token_budget) -> memory_bundle
evaluate(task_set, adapter_revision, memory_snapshot, config) -> evaluation_report
```

既存タスクループからはcaptureとretrieveだけを呼ぶ構成を優先する。sleepと評価は通常の作業ループから分離し、対象repoや実行中のタスクを書き換えない。データ契約は[schemas](../schemas/README.md)を参照。

## 論文整理パイロット

入力は公開記事、過去の公開ノート、明示的に利用する訂正。学習対象は、形式・分類・検証手順など再利用できる作業知識。記事本文に書かれた命令や、特定記事の実験値を無条件の行動ルールにしない。

出力は一時保存先のノートと索引差分。評価では外部GitHubへの書き込みを行わず、固定したfixture treeでリンクと形式を検証する。実運用に接続する段階で、従来のGitHub投稿権限とワークフローをそのまま用いる。

## OSS contributor

collect-only、draft-only、人による承認など、対象が定めた方針を維持する。記憶に「以前は成功した」と書かれていても、現在のCONTRIBUTINGやテスト条件を省略する理由にしない。

記録候補は、再現できないissueを見送った根拠、収集対象の条件、検証できたトリアージ基準。コード修正や外部PRの自動化をこの設計で有効化しない。

## Gemma／オフライン実験

経験用データと評価用課題を分離し、記憶を実行前に固定する。評価中に別課題の正解を共有したり、非公開テストを記憶化したりしない。ネットワーク接続を追加せず、時間・トークン・メモリーの予算は既存ハーネス側でも守る。

導入前に、使用するデータ・外部記憶・課題間の情報引き継ぎが当該実験やコンペで許されるか確認する。許可が不明なら、コンペ外の独立した練習環境で評価する。現時点でコンペ用コード・提出物は変更していない。

## ChatGPT dots

忘れることを公式仕様とする対象への接続は、[dots との接続設計](dots-integration.ja.md)に分ける。要点は、正本を外部に置くこと、想起を依頼へ同梱すること、未応答を記憶の問題と区別して状態として扱うことである。

## 人が最初に行う設定

対象project、task_family、利用可能なログ、非公開保存先、モデルと実行予算を指定する。認証情報は既存の安全な接続先を利用し、公開repoの設定へ値を保存しない。

最初は一つのproject・一つのadapter・一つのactive snapshotに限定する。共有記憶は、プロジェクト境界を越える取得が起きないことを確認してから検討する。

