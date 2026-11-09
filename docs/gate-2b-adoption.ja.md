# ゲート2B：採用writerの中核

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

## 今回の確認

**重点7項目・ローカル1回実行・合計7項目合格**。全件テスト・matrix・wheel実行検証は行っていません。

1. 採用→再open→同一再送、元の受領保持、異なるrequestの競合、除外の非解除。
2. 監査だけならscopeは未初期化のまま。
3. 2接続が同じnull親を提案し、後から古い親で採用する側は拒否。
4. 持ち越す記憶が現在の除外対象なら全体rollback。
5. 登録済みでも固定評価設定hashが異なる受領は拒否。
6. 最終head書込みの失敗で記憶・snapshot・履歴すべてrollback。
7. 明示v2→v3移行で原証拠・方針を維持。

コマンド：`.venv/bin/python tests/run_tests.py --limit 7 test_adoption_store.AdoptionTests`。Python 3.13.18／macOS arm64で合格。試行上限10項目の残りは3項目で、将来のPR用CI既定も関係する3項目だけにします。セッション変更を理由に7項目を再実行しません。

## 公開状態と残る範囲

作業branch：`feat/gate-2b-durable-adoption`。候補構築PR #9のhead `31353d17035394840856283ad932c8005d120133`を土台にしています。開始時点でPR #9はOPEN。今回の成果も未マージで、新PR・CI結果はありません。commit／pushの根拠は別記録で照合し、branch名だけで公開済みとは扱いません。

2B全体では、run IDを結び付ける版付きrequest契約、追加の証拠／受領破損・preference root検査、実際の同時複数プロセス、commit前後の強制終了・応答消失検査が残ります。SQL rollback・再openはプロセスクラッシュ・電源断・ネットワークFS耐久性の検証ではありません。hashもDB所有者による協調的改ざんを認証するものではありません。

現在方針を適用した取得、rollback／削除、Light/Deep、比較評価runner、既存agent1つへの接続、実環境adapter／認証・性能実験はこれからです。初期版全体の目安は**約30%前後（25〜35%程度）**。テスト件数からの算出や性能改善率ではありません。
