# 実モデルによる開発用の部分計測

[English](live-development-measurement.md) | [実装状況](implementation-status.ja.md)

## 計測するもの

指定モデルのadapterに、呼出しごとの記録を追加しました。

- `request_bytes`: シリアライズされた要求本文のUTF-8バイト数。
- `cli_prompt_bytes`: 固定指示・非信頼データの注意書き・本文を含むCLI引数のUTF-8バイト数。
- `transport_elapsed_ns`: 単調増加時計で測ったtransport呼出し前後の時間。
  CLI起動・認証解決・プロバイダ処理・CLI終了処理を含みます。
- 従来の応答バイト数・ハッシュ・取得できた会計観測。

時間は**CLIプロセス全体の経過時間**です。モデル単体の遅延、最初のトークンまでの時間、
トークン数ではありません。バイト数には未知の通信形式・隠れたsystem文・課金対象の推論等を
含めません。応答バイト上限は生成後の検査で、トークン・金額上限ではありません。
テストtransportの時間は実測モデルの証拠にしません。

失敗・応答却下でも時間を残し、既存Light／Deepと比較journalで保持します。
結果不明の再送・回復処理は変えません。使用量・実費の欠落はゼロではなく未取得です。
認証情報の直接利用やホスト・モデル・経路・既定設定の変更はありません。

## 2026-11-13の開発用プロトコル

基点はオーナーがマージした[PR #50](https://github.com/moruku36/agent-sleep-lab/pull/50)、
merge `d90e3036c6440e34901a65659fe1096057f110f8`です。
前の「会計対応まで比較を一切行わない」という条件を限定し、
トークン・請求額の受入れとは分けて、既存の有料開発許可で**応答・バイト・時間だけを部分計測**します。

1. 既存の[架空5タスク](../examples/paper-pilot/tasks.json)、別保管の語句充足rubric、
   モデル・上限を推論前に固定します。
2. 本文と現storeに束縛したLight／Deepを各1回だけ実行します。
   今回のDeepは原文を一字一句引用する**抽出的**候補です。抽象的な統合の品質証明ではありません。
3. 生成器とは別の決定的検証が原文一致・来歴・pending状態・現束縛を確認し、
   通常の候補評価・atomic writerで採用します。同じ運用者による別機構の検証で、
   **外部の独立レビューや非合成データの受入れではありません**。
4. A/Bに同一の完全なrawを渡し、Bだけに採用済みmemoryを追加します。
   上限は同一、順序はAB/BA交互、各タスク各arm1回、10枠すべてを分母に残します。
5. 固定した語句・要素充足基準で応答をスクリーニングし、原応答も確認用に保存します。
   fake応答の完全一致点ではありませんが、意味品質・独立holdout・統計的改善の証明でもありません。

最大12呼出し（sleep2＋task10）、再送・fallback・追加接続probeなし。
task要求16,384bytes／応答1,024bytes、sleep各stage応答2,048bytes。
CLIには呼出しごとのtoken／金額hard capがありません。
intentと既存journalを使い、未知の結果・古い呼出しを再送しません。
新しい合成storeは、以前の不明結果・準備済み実公開文書とは別です。

現CLIはlocal・Gateway双方のJSONでusageを省くため、token・通貨・全phaseの請求実費は未取得です。
セッション全体の費用を個々のlocal one-shotへ割り当てることもしません。別経路の実行はありません。

非公開bundleは1日で期限切れ、bundle・派生物の手動削除義務があります。
自動削除timerは設置していません。原応答・詳細rubric・許可ID・journalは公開しません。

## 観測

新しい実MiMo呼出しは**2件**です。本文束縛Light／Deepが各1回、登録済みlocal経路で返り、
provider／model／fallbackなしを照合しました。Lightは2eventを選び、Deepは原文一致の候補2件を返しました。

| 段階 | 要求bytes | CLI prompt bytes | 応答bytes | CLI経過秒 |
|---|---:|---:|---:|---:|
| Light | 2,495 | 2,643 | 47 | 12.986 |
| Deep | 2,537 | 3,020 | 471 | 9.766 |
| 合計 | 5,032 | 5,663 | 518 | 22.752 |

両受領ともusage／last-call usageはabsent、costはnullです。token・請求額の結果ではありません。
各stage1標本なので遅延benchmarkとも呼びません。

その後、local preparerは**最初のreceipt登録前**に失敗しました。
私的callerの小数秒付きISO期限がreceipt schemaの文字数上限を超えたためです。
Deepの原応答は有効のまま保存されています。coordinatorの
`trusted_preparation_failed`は残し、状態をリセットしません。
日時を整形した別の有限local準備コマンドはネイティブ実行承認待ちです。
既存副作用を照合してから保存済み候補を通常のverifier／evaluator／writerへ渡すもので、
追加model呼出しはありません。**pendingで、実行・成功は未確認です**。
ツール待機はtimeoutしましたが、公式承認照会では元の要求がまだpendingでした。
local準備のintent・完了artifactも未観測です。未dispatchの断定や再発行はせず、元の要求を照合します。
schemaや権限制限は緩めていません。
別途の外部SQLite読取りはhostのstate-directory policyで拒否され、コピー・別経路の読取りはしていません。

採用と10枠A/Bは**未実施**です。task／rubricの選択は固定しましたが、
実行可能な比較planと10要求の登録はまだです。部分観測で、実環境の全受入ではありません。
[本文を含まない集計](measurements/2026-11-13-live-development.json)。

offline検証は、focused 3件／1起動が0.005秒で合格し、その後の全回帰451件／1起動も
34.812秒で合格しました。**local 454ケース実行／test 2起動**です。
実モデル呼出しとは別で、PR CIも別記録です。現在の正本は[実装状況](implementation-status.ja.md)です。
