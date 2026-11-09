# ゲート2B：採用writerの中核

## テスト集計の訂正 — 2026-11-10 マージ準備

以前の「13項目・3回」には[PR #10のCI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42712205113)が漏れていました。ログで旧writer版の3項目・1回・0.235秒の合格を確認。実際は**累計16項目・4回実行**（中核7＋既存PR CI3＋プロセス3＋run ID3）です。承認上限は13で、集計漏れによる超過を後付け承認とは扱いません。確認中に追加テストは実行していません。下記に残る当時の累計はこの訂正で上書きされます。新run ID PRは重点3項目を1回実行するため、PR作成前に**追加3項目、累計19まで**の明示承認が必要です。CI回避・省略や試行枠のリセットはしません。

writer中核のPR #10はマージ済み（`629560858b5aef5423d75d90a71df99b6eec65d3`）。未マージなのは後続run ID／プロセス検証の追加分です。最新mainとのmerge-treeでは競合なし。全体進捗は約35%のままです。


[English](gate-2b-adoption.md) | **日本語** | [実装状況](implementation-status.ja.md)

2026-11-10に実装・ローカル重点検証を実施。**合成データ限定のライブラリ成果**であり、2B全体・SLP受入・本番導入・取得adapterの完成ではありません。

## できること

`agent_sleep_lab.adoption_store.AdoptionStore`はv3形式を使用します。取込境界と独立した検証／評価の模擬境界、固定した評価protocol名・版・設定hashを渡します。認証機能ではありません。

既存v2は自動移行せず、`upgrade_store_v2_to_v3(path)`で明示移行します。既存の証拠・受領・方針は書き換えません。DDL照合と追加は単一transactionです。v1は先に既存の明示v1→v2移行が必要です。

`commit_adoption`は、request・操作／出典manifest・記憶bytesを受け取り、同じSQLite接続の`BEGIN IMMEDIATE`内で次を行います。

- operation IDとrequest digestを照合。同じ内容の再送は元の採用受領を返すだけで、再採用しない。異なる内容は競合。
- 現在の方針版・期待親版を照合し、保存済み親と全採用記憶ID履歴から候補を構築。
- 登録済み評価受領をID/hashで解決し、候補・親・操作・出典・scope・独立評価境界・固定protocol設定に結び付ける。完全な合格と有効期限が必要。
- 持ち越すactive記憶も含め、bytes・期限・検証受領・原証拠・全祖先・現在の許可／除外を再検査。新規出典のhashも受領と照合。preferenceのrootはすべて利用者訂正でなければならず、hypothesisは採用しない。
- 記憶・snapshot・request／manifest／採用受領の履歴・active参照を一括保存。COMMIT後にのみ応答。

reject/deferだけなら評価不要で、履歴だけを残し、現在版を初期化・変更しません。採用済み記憶IDは全scopeで再使用不可ですが、単にdeferした提案IDは採用済みIDとして予約しません。

`resolve_operation`は応答消失時の結果照会です。`current_snapshot`は**過去のsnapshotメタデータ**で、現在利用可能な記憶bundleではありません。除外後に元の採用結果を照会できても、現在の除外を解除したり再採用したりはしません。

## 過去の中核受入（run ID v2追加前）

**重点7項目・ローカル1回実行・合計7項目合格**。全件テスト・matrix・wheel実行検証は行っていません。

1. 採用→再open→同一再送、元の受領保持、異なるrequestの競合、除外の非解除。
2. 監査だけならscopeは未初期化のまま。
3. 2接続が同じnull親を提案し、後から古い親で採用する側は拒否。
4. 持ち越す記憶が現在の除外対象なら全体rollback。
5. 登録済みでも固定評価設定hashが異なる受領は拒否。
6. 最終head書込みの失敗で記憶・snapshot・履歴すべてrollback。
7. 明示v2→v3移行で原証拠・方針を維持。

コマンド：`.venv/bin/python tests/run_tests.py --limit 7 test_adoption_store.AdoptionTests`。Python 3.13.18／macOS arm64で合格。続行で下記の追加3項目を1回実行し、同じ試行は計10項目・2回実行で上限到達です。追加の許可なしにローカル／CIを再実行せず、自動CIが走るPRも作成しません。

### プロセス検証の続行

run ID v2追加前に追加3項目を1回実行し、0.579秒で全件合格。head保存後・COMMIT直前のSIGKILL、COMMIT後・応答前のSIGKILL、2つのspawnプロセスによるnull親競合を確認しました。pipeと上限付き待機を使うテスト限定の同期で、本番hookは追加していません。[正確な結果・限界](../reports/gate-2b-process-acceptance.md)。当時は同じ試行で計10項目・2回実行。後述の明示増枠後は計13項目です。プロセス3項目はv2追加コードでは再実行していません。新PR・CIなし。公開根拠は別途記録します。

## 版付きrun ID結合

[run ID結合](gate-2b-run-id.ja.md)を実装。request/2・receipt/2に監査ラベルを結び付け、旧履歴の完全一致再送を維持します。明示増枠により追加3項目を1回・0.239秒で合格、累計13項目・3回実行で上限到達。先の10項目は今回再実行していない履歴です。新PR・CIなし。Muse Wonderの助言から既存契約に合わない監査操作の変更案は採用していません。

## 公開状態と残る範囲

作業branch：`feat/gate-2b-durable-adoption`。候補構築PR #9のhead `31353d17035394840856283ad932c8005d120133`を土台にしています。開始時点でPR #9はOPENでしたが、最新の読取り確認ではMERGED（merge commit `122fed26305a5d039de3d14b5c42633811b8affc`）。後続writer／run ID連携の成果は未マージで、新PR・CI結果はありません。commit／pushの根拠は別記録で照合し、branch名だけで公開済みとは扱いません。

2B全体では、監査ラベルを超える登録runの照合、追加の証拠／受領破損・preference root検査、上記の過去3項目以外のクラッシュ境界が残ります。プロセス強制終了の検証は電源断・ネットワークFS耐久性の検証ではありません。hashもDB所有者による協調的改ざんを認証するものではありません。

現在方針を適用した取得、rollback／削除、Light/Deep、比較評価runner、既存agent1つへの接続、実環境adapter／認証・性能実験はこれからです。初期版全体の目安は**約35%前後（30〜40%程度）**。テスト件数からの算出や性能改善率ではありません。
