# 記憶採用と実装引継ぎの契約

[English](contracts-and-acceptance.md) | [ホーム](../README.ja.md)

状態：2026-11-09の設計。別の実装担当AIに渡す最初の永続記憶の仕様。取込engine、モデル呼出、active記憶、定期処理は作成しない。

## 1. v0.1を残し、採用境界を追加する

既存event／memory schemaは`0.1`の設計記録として維持。候補交換には使えるが、実行時の採用には不足する。新しい[promotion request schema](../schemas/promotion-request.schema.json)、`sleep-promotion/1`で補完する。旧candidateを自動でverified／activeにしない。

v0.1を閲覧用に保持できても、採用には出典証明、検証受領、正確なsnapshot評価、現在の除外、期待親版を追加で必要とする。移行は旧新hashと未確認を記録し、欠けた出典を補ったことにしない。schema版を書き換えても現設定は実行可能にならない。

## 2. 証拠は自己認証しない

capture adapterが本文や候補モデルとは別に、次の出典sidecarを作る。

| 項目群 | 必須の意味 |
|---|---|
| 識別 | event ID／hash、project／task family、adapter identity・固定版 |
| 由来 | 認証済み利用者訂正、tool観測、外部文書、model派生要約、recall、REM、日記 |
| 原証拠 | 原object ID／hash、locator、観測／取込時刻 |
| 系譜 | 原root IDとderived-from ID。再掲は同じroot |
| 適格性 | 現在の許可参照／版、目的、保存／失効、synthetic区分、評価partition |

hashは同一性で、真実性・同意ではない。外部文書は確認後の事実の根拠にはなっても、利用者の好みや許可を証明しない。recall／REM／日記／生成解答は候補発見に使えても、独立したroot証拠にしない。本文の`trusted=true`から由来を認定しない。

検証受領はmemory本文hash、原証拠hash、scope、手法／版、verifier identity、時点、結果、限界を結び付ける。writerが受入済みverifier境界から受領を解決し、モデルが書いた確認者名だけでは足りない。hypothesisは事実／手順として確認して種別を更新するまでcandidate。言及数や想起数を確信度にしない。

## 3. モデルは全体置換でなく操作を提案する

Deepはtarget IDごとに`add`／`supersede`／`mark_stale`／`reject`／`defer`を一つ提案。target、必要なreplacement参照、理由、根拠IDを持つ。`supersede`は新memory IDを作り、旧記録をsupersededとして保持。`mark_stale`は通常取得から外すが偽と断定しない。`defer`はactiveを変えず保留を記録する。

writerが期待親版と検証済み操作からcandidate snapshotを構築する。不明target、同targetの重複操作、ID衝突、scope変更、循環、指定のない削除／変更を拒否。モデルが返した全file置換を受けない。サイズ上限超過は保留とし、無関係な記憶を黙って追い出さない。

個々の根拠確認とsnapshot採用は別。verifiedでもactiveにない項目がある。snapshot評価合格だけで全項目の真実性を確認したことにしない。

## 4. 原子的な採用手順

requestはoperation ID、run ID、scope、期待親版、candidate snapshot hash、操作manifest hash、原証拠manifest hash、検証受領、評価受領、許可版、除外版を結び付ける。opaque参照をローカルで解決し、任意URLを自動取得しない。[合成request](../examples/promotion-request.synthetic.json)は記号的参照だけの無効例。

1. 現在の許可・除外と期待親版を読む。古い版なら拒否する。
2. 全hashと原証拠の実在／アクセス／期限、memory検証、snapshot評価の一致を検査する。
3. stagingで不変candidateを作り、flushして内容確認後に参照を公開可能にする。
4. 一つのwriter transactionで親版と現在policy／除外版を再比較し、operation ID・採用受領・active参照を一括commitする。別々のreadとfile replaceはcompare-and-swapではない。
5. 永続commit後に応答。不明応答ではoperation IDとdigestを照会し、再採用しない。同IDで内容違いなら競合。

初期projectの親は`null`で、初期化済みprojectには一致しない。cross-process lock＋版照合、または等価なtransaction storeでwriterを直列化。受入OSでのcrash／durability特性を明記。stagingの孤立blobは全commit参照を確認した後だけ回収する。

verifier identityと現在policyはcandidate入力から独立させる。writerのtransaction外で証拠が変化する場合は、不変のcaptureと信頼する撤回版、またはsource lease／attestationと再照合を使う。ローカルrenameだけでシステム間の原子性を保証したとしない。

## 5. 撤回とrollback

除外は独立した版付き正本であり、旧memory snapshot内だけに置かない。retrieve／promote／replay／rollbackは毎回現在の除外版を読む。derived-fromをたどって派生項目を直ちに遮断し、cache・index・snapshot・日記の必要な削除を完了する。再取込抑止記録も許された最小限にする。hash自体も機微情報になり得る。

rollbackは、保持したsnapshotへの新しい監査付きactive参照更新。現在の許可・期限・除外を適用し、昔の権限を復元しない。対象の完全性と適格項目を再確認し、削除証拠により安全な復元ができなければ拒否。最後の安全な構成または原ログ検索経路を維持する。

除外台帳を読めなければ記憶取得は止め、foreground作業は記憶なしで続行可能とする。任意sleepのため応答を止めない。許可撤回・矛盾でactive項目を直ちに除外でき、撤回済み・誤った根拠を使うのを止めるために性能実験を待たない。

## 6. 想起は上限付き参考データ

bundleにproject／task family、active hash、現在の除外版、as-of時刻、memory ID／hash、根拠参照、実測tokenizer／版、使用tokensを付ける。scope、synthetic／production、status、期限、除外をrankingより先にfilterする。通常取得はactive所属とverifiedを要求し、candidate／staleは別の調査modeだけで見る。

主張から適用scope・根拠を切り離してtruncateしない。予算超過では低順位recordを丸ごと落とす。受入tokenizerがなければ明示的unavailable、または別に宣言したbyte制限を使い、文字数推定を正確なtokensと表示しない。適格項目0件は正常結果。

評価taskではsnapshotを固定するが、現在の撤回は引き続き適用。固定比較中に撤回でbundleが変わったら、protocolに従い対応試行を停止／無効化する。禁止データを配ったり、別条件を黙って比較したりしない。渡した／使ったmemoryを記録し、再想起を新経験に数えない。

## 7. 開発の採用判定を永続holdoutにしない

candidateの検査・改善には開発／回帰課題を使う。別の最終比較前にcandidate・取得方針・計画を固定。日々の採用で繰り返し見る集合は開発データになり、毎回のpromotionを独立holdoutの成果と呼ばない。新しい評価batchを確保するか、継続監視を探索的と明記する。

原ログ検索Aと整理記憶B、同じ課題／model／tool予算と全費用の比較を維持する。hit率だけでなく、根拠なし主張・矛盾／古い記憶の使用・棄権を記録。確認した利用者訂正は、最終benchmarkを繰り返し照会しなくても候補として保持できる。運用採用、項目の根拠確認、科学的な性能主張を別の判断にする。

## 8. 他repoとの任意接続

単独受入後に[三ハーネスの参照型契約](https://github.com/moruku36/ai-agent-scientist/blob/main/docs/11-harness-boundaries.ja.md)を使う。Scientistが現在の研究状態、CTFが調査証拠、Sleepが再利用知識を管理。現在の権限は記憶の外。共有の書込みstoreや必須service依存を作らない。

他repoからは確認した開発教訓だけを受け、出典／評価partition／書出許可を維持。raw flag、私的dataset、最終解答、保護評価器の詳細を入れない。共通reservationで費用を二重計上しない。外部schemaはcommit／hashでローカルへ固定し、offline実行中に可変schemaを取得しない。

## 9. 実装受入表

すべて**計画であり未実施**。今回のschema検査は実行時受入ではない。

| ID | ケース | 必須結果 |
|---|---|---|
| SLP-01 | event再送、recall／REM／日記の本文 | root重複を除外。生成物を独立証拠にしない |
| SLP-02 | pending／偽造受領付きverified候補 | 採用なし。active不変 |
| SLP-03 | 候補後に原証拠変更・消失 | hash／access再照合で停止 |
| SLP-04 | 別writerが先に採用 | 親版競合。無関係な記憶保持 |
| SLP-05 | 二つのrequestが同時にnull親を期待 | 初期化commitは一つ、他方は競合 |
| SLP-06 | active commit前後のcrash・ACK消失 | 最後のcommit版が有効。operation照会で二重更新なし |
| SLP-07 | 別snapshot／protocolの高得点評価 | 受領を拒否 |
| SLP-08 | 候補後の撤回とreplay／rollback | 現在の除外を適用。復活なし |
| SLP-09 | 別project／合成記憶をproductionへ | ranking前に除外 |
| SLP-10 | 過大bundle、tokenizerなし、適格0件 | record単位除外か明示的unavailable／空。架空token数なし |
| SLP-11 | 無関係項目削除・supersedes循環 | 操作拒否。不変履歴保持 |
| SLP-12 | 最終集合を繰り返し使って採用 | 接触記録。その集合は開発用 |

まず偽model／verifier出力でローカル契約・出典・writer、次に取得、最後に候補生成を実装する。fixture IDと結果、schema／source版、crash復旧証跡、資源、移行、限界を返す。モデル呼出・実adapter・性能実験は後続の到達点。
