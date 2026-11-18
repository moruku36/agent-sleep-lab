# 公開情報1件 → 別タスクで出典付き取得

[English・コピー用コマンド](minimal-public-item-recipe.md) | **日本語**

既存CLIだけの最短手順です。今回実行済みの試験や本番接続ではありません。
既にインストール済み・レビュー済みの環境が前提です。追加インストール、
モデル呼び出し、Light/Deep、機能追加は行いません。

## 1件の例と準備

Google公式Gemma PyTorch READMEの一文：
> This is the official PyTorch implementation of Gemma models.

[固定版の公式出典](https://raw.githubusercontent.com/google/gemma_pytorch/014acb7ac4563a5f77c76d7ff98f31b568c16508/README.md)
を2026-11-18T00:48:29.956Zに読み、一文の存在を確認しました。
Gemma利用規約・大会公式ルールではありません。規約ページ取得はリダイレクト
上限で失敗しており、大会資格・採点・Windows動作は確認していません。

新しい専用の非公開作業ディレクトリに、正確な公開バイト列の
`source.txt`、その正確な部分文字列の`quote.txt`、ホストが別途確認した
`approval.json`、設定済み役割の`roles.json`を準備します。
一文だけ保存した場合のSHA256はその一文のバイト列のハッシュであり、
README全体のハッシュとは異なります。引用末尾の改行に注意してください。

承認はURL・正確なハッシュ・用途・scope・有限の有効期限を束縛し、
公開性と秘密情報の確認を実際に行ってから与えます。この文書は承認を発行しません。
URLの認証情報・query・fragmentは禁止のままです。役割IDは認証ではなく、
control/verifier/evaluator/semantic_reviewerとconsumerを区別して設定します。

## タスクAとタスクB

英語版のコマンドを1つずつ実行します：
`stage → init → approve → admit → propose → verify → evaluate → adopt`。
初期parentは正確な`[]`のSHA256、承認前generationは0、承認後は1です。
この値は既存storeへ流用しません。検証・評価の期限は承認期間内に設定し、
各終了コードとJSONを確認します。失敗時にファイルの存在だけで成功扱いしたり、
同じ書込みを無条件に再試行しません。

タスクA（`task-A-save`）を終了し、新しいshell/processのタスクB
（`task-B-identify-implementation`）から、同じ専用SQLiteパスを明示して
`retrieve`します。scopeは同じ`gemma-reading/public-docs`です。
CLI呼出し自体も別プロセスですが、実際のプロセス境界・結果・タスクIDが
記録されなければ「今回2プロセス実証済み」とは呼びません。

出典は取得結果の`quotation/source_uri/source_sha256/artifact_sha256`、
snapshotは採用結果の`head_sha256`を使います。取得日時は実行時に別途記録し、
観測・capture日時はstaged.jsonから保持します。取得reference自体に日時や
snapshot欄があるとは説明しません。今回は取得結果・採用receipt未生成です。

## 残る手作業

公開情報の入手・規約と大会ルールの別確認、承認・役割・TTL設定、引用選択、
receipt確認、storeパス・タスクID・出典日付・snapshotの引継ぎ、タスクBでの
引用利用と意味の確認、撤回・期限後のcleanup、staging/export等の削除です。
`retrieve`は参照取得のみ（consumer未実行）。機械的な検証・評価は真実性、
人間認証、有用性・精度向上の証明ではありません。

停止中のプロセスは期限到達時に削除できません。期限は後続アクセスを止め、
明示的cleanupが管理対象をpurgeします。管理外の入力・出力・バックアップは別途
保持方針に従って削除します。不明呼出しの再試行防止情報はリセットしません。
所要時間短縮・精度・ベンチマーク・自動採用・自動権限の主張はありません。
