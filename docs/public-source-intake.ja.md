# 公開文書の取込み前ステージング

[English](public-source-intake.md) | **日本語** | [ランタイム手順](runtime-guide.ja.md)

**確認済みの公開文書1件**を非公開の実データartifactへ準備するライブラリです。
既存の証拠／採用storeへの取込みやagent接続ではありません。取得・ファイル検索・
秘密情報の自動検査・モデル呼出し・受領登録・公開は行いません。
既存の合成限定capture／取得／採用は変更しません。

## 明示的な境界

信頼する呼出し側が公開可否と秘密情報を確認した後、原文とは別に
`PublicDocumentApproval`を設定します。正確なHTTPS URL、UTF-8原文
1〜65,536 byteのSHA-256、project／task family、許可参照・版、許可時刻と
有限の期限を束縛します。URLの認証部分・query・fragmentや不適切な制御文字は拒否します。
URL形式は公開元の証明やSSRF防御ではなく、このmoduleは取得自体を行いません。

目的は`public_document_consolidation`、保持は`until_expiry`のみです。
期限切れ・撤回時は呼出し側が非公開のstaging bundle全体と全派生物を削除します。
これは記録する義務で、**timer・ファイル削除・安全消去の実装ではありません**。
私的会話・認証情報・個人記憶・評価の解答には使いません。返されたartifactは公開せず、
公開repoのテスト入力は合成のままにします。

許可objectは呼出し側のローカル設定です。認証・同意の発見・著作権の確認・
自動匿名化の証明ではありません。原文中の命令は権限にならず、モデルや原文が
作った許可を信頼してはいけません。

## ライブラリAPI

明示的な非公開callerから
[public_source_intake.py](../src/agent_sleep_lab/public_source_intake.py)を使います。

1. 取得済み原文byte、正確なURL、event ID、scope、観測／取込時刻、
   別設定の現在許可とtimezone付き現在時刻を`prepare_public_document(...)`へ渡します。
2. 戻り値のcanonical bytesは公開checkout外へ保管します。原文を変更せず、
   `synthetic:false`と`state:staged_not_admitted`を記録します。
   モデル送信や採用の許可は付与しません。
3. 内容を含まないhash／byte確認には`intake_summary(artifact)`を使います。
   原文・URL・許可参照は返しません。summaryを権限検証に使わないでください。
4. 後の利用ごとに
   `recheck_public_document(artifact, approval=current_approval, now=current_time)`
   で再検査します。欠落／撤回・版変更・期限切れ・不一致の許可、原文／metadata改変、
   非canonical artifactは拒否します。

古い許可objectを渡されたことをAPIだけで知ることはできません。
接続側が実際の最新許可を解決し、撤回・削除を実施する責任を持ちます。
CLI・暗黙の初期化・schema移行・合成への偽装・verifier登録・有料送信はありません。

## 検証と残る受入

[behavior 6件](../tests/test_public_source_intake.py)は架空データだけを使い、
原文byte保存、命令文のデータ扱い、内容なし出力、別許可／URL／hash／scope、
撤回／期限／版／時刻、確認assertion、サイズ、改変、従来の合成限定拒否を確認します。
実行結果の正本は[実装状況](implementation-status.ja.md)です。

別の[公開文書1件のlifecycleライブラリ](public-document-lifecycle.ja.md)が、永続化した
現在control、受入、管理削除、独立した引用／機械的受領、採用、明示consumer境界を実装します。
staging単体はそれらを実行しません。local検証と残る実環境受入は
[実装状況](implementation-status.ja.md)を参照してください。
どちらも未公開の試用拡張を検索・復元・取込みしていません。
