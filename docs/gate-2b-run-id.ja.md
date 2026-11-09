# run ID監査連携

## テスト集計の訂正 — 2026-11-10 マージ準備

以前の「13項目・3回」には[PR #10のCI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42712205113)が漏れていました。ログで旧writer版の3項目・1回・0.235秒の合格を確認。実際は**累計16項目・4回実行**（中核7＋既存PR CI3＋プロセス3＋run ID3）です。承認上限は13で、集計漏れによる超過を後付け承認とは扱いません。確認中に追加テストは実行していません。下記に残る当時の累計はこの訂正で上書きされます。新run ID PRは重点3項目を1回実行するため、PR作成前に**追加3項目、累計19まで**の明示承認が必要です。CI回避・省略や試行枠のリセットはしません。

writer中核のPR #10はマージ済み（`629560858b5aef5423d75d90a71df99b6eec65d3`）。未マージなのは後続run ID／プロセス検証の追加分です。最新mainとのmerge-treeでは競合なし。全体進捗は約35%のままです。


[English](gate-2b-run-id.md) | **日本語** | [現在の採用API](gate-2b-adoption.ja.md)

2026-11-10に実装・ローカル重点検証を実施し、3項目が1回で合格しました。feature branchの成果で、未マージ・新CI未実施です。Muse Wonderから設計助言を受け、実装と検証は別途行いました。初期版全体の目安は約35%（30〜40%程度）です。

## 契約

旧request/1・receipt/1と保存済みbytes/hashを固定し、全既存項目に必須run_idを追加したrequest/2・receipt/2を別schemaとして追加します。run_idは既存IDと同じ1〜128文字のASCII規則とし、空白除去・正規化・過去分の補完をしません。

request hashにrun_idが含まれ、writerがreceiptへそのまま複写し、照合時も一致を確認します。manifestは従来通りrequest hashを通じて結び付けます。run_idは**呼出側が指定した監査ラベル**であり、実在run・認証・権限・評価の所属を証明しません。登録済みrunの照合は将来の別機能です。

## 書込み・再送

- builderは明示run_idを必須としてv2を生成。新規操作はv2だけを受理します。
- canonicalな入力／payloadを検査し、同じtransaction内で先に既存operation IDを照合します。
- 既存v1の完全一致再送は元のreceipt/1を返すだけ。履歴の再生成・hash変更・run ID後付け・head更新・現在許可の復活はしません。
- 同じoperation IDでrun_idや版を変えれば競合です。ID空間をrunごとに分割しません。
- 未登録operationのv1は書込み前に拒否。未知の版も拒否します。
- reject/deferだけの監査操作も従来契約を維持し、v2のrun_id付き履歴とoutcome audit_onlyを保存します。評価不要・head初期化／変更なし。Museの「監査操作を別契約へ分離」という案は既存仕様に合わないため採りません。
- 現在方針・親・原証拠の照合と一括commitは変更しません。

## 保存・実装箇所

現行v3 DDLはpayload版を固定せず、bytes/hashを保存するためDB移行やrun_id列追加は不要です。user_versionは3、過去行は不変。旧アプリはv2を読めないためライブラリ更新は必要です。

runtime_artifacts.pyにrequest／receipt各2版だけの厳密なdispatcherを追加し、adoption_candidates.pyでbuilder／receiptをv2化、adoption_store.pyで新規版検査前の旧再送照合とrun_id／版ペア一致を実装します。公開schemaとpackage内schemaを揃えます。schema IDを任意のファイルパスやURLとして扱わず、他artifactの検査を緩めません。

## 重点3項目（1回実行・全合格）

1. 旧契約に従って直接保存した合成v1履歴を新コードで再openし、除外後も旧bytes/hashを保持した完全一致再送になり、headも変わらない。
2. v2でrun Aの採用・受領結合が成立し、同じoperation IDのrun Bへの変更が競合し、重複やhead変更がない。
3. 新規v1を無書込みで拒否し、run_id付きv2のdeferは評価なし・履歴だけを保存。v1/v2履歴を混在して読める。

所有者の明示承認で同じ試行の上限を10→13項目へ増枠し、`.venv/bin/python tests/run_tests.py --limit 3 test_adoption_run_id.RunIdTests`を実行。0.239秒で3項目合格、累計13項目・3回実行です。再実行・CI・全件回帰・matrixなしで、枠は再び使い切りました。先のwriter7項目・プロセス3項目は今回コードでは再実行せず履歴として扱います。v1は直接保存したfixtureで、旧binaryからの移行受入ではありません。版不正・受領破損などの追加受入、package／プロセス再検証は残ります。[正確な受入記録](../reports/gate-2b-run-id-acceptance.md)。
