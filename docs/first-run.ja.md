# 初回手順：offline demoを理解する

[English](first-run.md) | **日本語** | [ホーム](../README.ja.md)

本書は手順であり、状況の別正本ではありません。能力・確認結果・未完事項は
[実装状況](implementation-status.ja.md)を参照してください。

## installと実行

Python **3.11以上**を用意し、local checkoutで実行します。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/agent-sleep-lab demo --format text
```

installはbuild toolや依存packageをdownloadする場合があり、完全offlineとは限りません。
依存を含めてinstall済みなら、demo runtimeにnetwork・認証情報・実モデルは不要です。
demoにOpenClawアカウントは要りません。installに失敗したらPython版とpackageの取得可否を
確認し、有料providerへ切り替えて解決しようとしないでください。

詳細な機械可読reportは、従来どおり既定のJSONで取得できます。

```sh
.venv/bin/agent-sleep-lab demo
.venv/bin/agent-sleep-lab demo --format json
```

textは同じ台本walkthroughの任意表示で、別の実行経路ではありません。
利用者data・既存store・provider・出力file指定は受け付けません。
[demoの完全な契約](runtime-guide.ja.md#組込みオフラインdemo)も参照してください。

## 結果の読み方

capture → 台本Light／Deep → 未検証candidate → 別のlocal fixture検証／評価 →
原子的採用 → 取得 → 対応比較の順に読みます。
fixtureはevent 2件、candidate／採用記憶1件、課題2組です。
台本呼出しは**実モデル呼出しではなく**、完全一致点数は配線確認であり、
意味的な有用性や一般的な改善の測定ではありません。

JSONでは`status`・`synthetic_only`・`calls`・`adoption`・`retrieval`・
`comparison`を確認します。実provider／既存agent接続／性能主張のflagはfalseです。
textも同じ境界を要約します。hash・固定membership・群ごとの詳細が必要ならJSONを使います。
`temporary_state_removed:true`は接続を閉じて3つの使い捨てSQLite storeを削除した後だけ
出ます。成功しても再利用用記憶は残らず、既存agentも接続しません。
通常の成功・失敗経路ではcleanupしますが、強制終了やhost障害時まで保証しません。
errorは成功reportなしのexit 2です。診断を読み、途中出力を採用成功に変えたり、
結果不明のlive操作を再試行したりしません。

demoの回数・UTF-8 byte上限は生成token・通貨上限ではありません。
synthetic-zero／unavailableは実測の節約額ではありません。

## 実試用前にofflineで撤回まで追う

[最小の合成採用→利用→撤回trace](offline-lifecycle-trace.ja.md)を読みます。
既存1ケースfixtureを再利用し、操作・確認点とpurge失敗／回復まで示します。
demoの一時cleanupは許可撤回ではありません。入口の文書化で自動実行はせず、実行には別の残枠が必要です。

## 実際の公開文書試用へ進む場合

これは**別の永続store経路**で、demo optionではありません。明示的なoffline command
`agent-sleep-lab public-document`（下記）がありますが、自動連結・model呼出し・network・
schedule・agent接続はありません。model利用は別のlibrary adapterのままです。
host接続を作る前に[lifecycle](public-document-lifecycle.ja.md)と
[モデル接続](public-document-model.ja.md)を読みます。

| 順序 | hostが明示的に担当すること |
|---|---|
| 1. 準備 | exactな公開byte・scope・許可・期限をreviewし、新規専用libraryへ1文書を受入。同じno-retry sidecarを保持 |
| 2. Light／Deep | 上限付き各stageを別々に許可。Lightが空なら終了。応答は未検証案のみ |
| 3. 独立review | 原文／候補のexact bindingを照合し、verifierとsnapshot evaluatorの受領を別に登録 |
| 4. 採用 | 現在の親版・policy・scope・期限を検査する原子的writerを使う。provider出力の自己認証は禁止 |
| 5. 別task利用 | 適格な採用参照を取得し、consumer dispatchと意味利用reviewを別に行う |
| 6. 撤回／期限／削除 | アクセス停止と管理本文／派生物のpurgeを明示実行。内容なしのno-retry tombstoneを保持。remote複製・backupは保証外 |

原文・task context・生成文はuntrusted dataで、許可ではありません。
held-outの解答／rubricをLight contextへ入れません。
拒否応答の保持は既定無効です。任意quarantineは上限付き管理contentであり、
拒否応答logや再試行の権限ではありません。

### 永続store1つの日常利用（offline command）

以下はすべて`--store`でstoreを指定します。storeとその親directoryを作るのは`init`だけで、
他は**既存**storeを開き、無ければ拒否します。model呼出し・network・再試行はありません。

```sh
agent-sleep-lab public-document init --store lib/store.sqlite --roles roles.json
agent-sleep-lab public-document approve --store lib/store.sqlite \
  --identity CONTROL_ID --identity-version 1 --approval approval.json \
  --artifact staged.json --origin-task ORIGIN --expected-generation 0
agent-sleep-lab public-document admit --store lib/store.sqlite --artifact staged.json
agent-sleep-lab public-document propose --store lib/store.sqlite \
  --proposal-id p1 --quotation-file quote.txt
agent-sleep-lab public-document verify --store lib/store.sqlite \
  --identity VERIFIER_ID --identity-version 1 --proposal-id p1 --expires-at WHEN
agent-sleep-lab public-document evaluate --store lib/store.sqlite \
  --identity EVALUATOR_ID --identity-version 1 --proposal-id p1 \
  --expected-parent HEAD --verification-receipt V --expires-at WHEN
agent-sleep-lab public-document adopt --store lib/store.sqlite --operation-id op1 \
  --proposal-id p1 --expected-parent HEAD --expected-generation N \
  --verification-receipt V --evaluation-receipt E
agent-sleep-lab public-document retrieve --store lib/store.sqlite --target-task OTHER \
  --project P --task-family F --max-bytes 2048
```

- **roleはhostが用意します。** `roles.json`に、互いに異なる4 authority（control・verifier・
  evaluator・semantic reviewer）とconsumer設定1つ（ここではdispatchしません）を書きます。
  role付きactionは`--identity`／`--identity-version`を1組だけ受け取り、libraryが保存済み設定と
  照合します。この文字列は**認証ではなく**、秘密でも別人の証明でもありません。roleを自動選択しません。
- **許可は別操作です。** `approval.json`は、exactな準備済みartifact
  （[公開文書staging](public-source-intake.ja.md)）に対してhostがreview済みの許可です。
  `approve`は渡されたfileを登録するだけで、ownerの許可を作ったり、review・推定したりしません。
  schemaが正しいfileは、そのbyteをownerが許可した証拠ではありません。
- **受領は機械的な確認です。** `verify`と`evaluate`は、指定した1つのrole identityに対して
  libraryの機械的な受領を登録するだけで、意味の判断はしません。`verify`はexactな引用一致、`evaluate`は候補snapshotの機械的検査で、
  `adopt`は両方と現在の親版（`status`の`head_sha256`。新規storeは`[]`のhash）・generationが必要です。
  合格は事実の真偽・意味的な有用性・性能の証明ではありません。provider出力は受領を発行しません。
- **取得は利用ではありません。** 同じ許可scopeの*別*taskへ、`--max-bytes`内でrecord全体を
  untrusted dataとして返すだけです。consumerを呼ばず、利用の実証にもなりません。
  `propose`のfileはbyteそのまま使うため、末尾の改行を足さないでください。

#### 読みやすい表示と次の操作

日常commandはすべて`--format text`で、状態・件数・受領または取得した参照と、
次の操作案内を表示できます。既定および`--format json`の詳細JSON形式は維持します。
同じ1回の操作結果を整形するだけで、追加dispatchやstore読取りはありません。
動的な値は端末制御文字も含めJSON escapeします。表示ラベルは英語です。

```sh
agent-sleep-lab public-document status --store lib/store.sqlite --format text
agent-sleep-lab public-document cleanup-preview --store lib/store.sqlite --format text
```

`Stored state`は保存された状態、`Access eligibility`は期限による利用可否、
`Adopted head present`は採用済みの版があるかを示します。`Approval window`（許可期間）、
`Scope`（範囲）、`Managed records`（管理件数）を確認してから次の操作を選びます。
取得時も上記の別task向けcommandに`--format text`を足すと、未信頼の引用と出典を表示します。
採用・取得・削除は自動では行いません。storeのpathは出力・記憶されないので自分で保持します。
表示形式を変えるだけのために、書込み操作を再実行しないでください。

#### status・preview・cleanup

`status`と`cleanup-preview`はstoreをread-onlyで、1つのread transactionの中で開くため、
途中で別のclientが撤回しても1回の出力は整合した単一のsnapshotです。期限切れ処理も含め何も変更せず、
文書本文・URI・参照名・role名を出しません。保存状態（`empty`・`approved`・`purge_pending`・
`deleted`）、実効`access`（`approval_not_yet_valid`・`approval_expired`・
`approved_not_admitted`・`admitted_in_window`・`suppressed_purge_pending`・
`suppressed_deleted`）、cleanup状態を分けて示します。期限ちょうどでは保存状態が
`approved`のままでも`access`は`approval_expired`です。`integrity`は常に`not_assessed`で、
previewはmetadataのみを見て、受入済みbyteや派生物を検査しないため、`cleanup`が行い得る
処理をすべて予測できず、`admitted_in_window`は後の取得成功の約束でもありません。除外後の原因は`unknown`
（storeは理由を記録しません）。`deleted`はこのlibraryの管理purge完了で、fileや
forensicな消去ではありません。

副作用がないと保証されるのは`status`と`cleanup-preview`だけです。`cleanup`は明示的な
期限／integrityのsweepで、保留中purgeも完了させます。approvalが現在有効か、管理byteが
無傷かを検査し、有効で無傷の期間内dataは残しますが、検査に失敗したdataは除外・purgeします。
有効なcontentを消すには`--purge`か`--exclude-only`を明示する`withdraw`を使います。
管理contentを読む他の変更系action（`verify`・`evaluate`・`adopt`・`retrieve`など）も同じguardを
通り、失敗時は拒否する前に除外・purgeします。`withdraw`はまず`--expected-generation`に対する
自分自身の除外を確認し、その後に（`--purge`のとき）別段階のpurgeを試みます。別のclientが先に
撤回していた場合、古いcompare-and-setは拒否（終了code 2）で、自分で確認していない除外を
報告することはありません。操作記録・内容なしのno-retry tombstone・外部export／backupは保持され、
保証の対象外です。

**終了code。** `0`：完了、または対象なし。`1`：実行したが未完了。`purge_pending_incomplete`は
除外はcommit済みで物理purgeが終わっていない状態（まず`status`を確認し、同じstoreで`cleanup`を選択）、
`failed_state_unchanged`は除外前のerror、`purge_attempted_state_unconfirmed`は最終状態を読み戻せなかった
状態です。`2`：拒否または失敗で、そのcallが完了した影響を確認していません。
0以外の後は、何かを繰り返す前に`status`で保存された状態を確認してください。
purge例外後も撤回commandは新しいmetadata snapshotを読み、実際に観測できたときだけ
`deleted`、読み戻せなければ`unconfirmed`を表示します。遅い例外では
`managed_purge_completed`を観測できても終了code 1を維持します。別clientが削除を完了した
可能性もあるため、自分のcallが削除を実行した証拠とはしません。撤回を繰り返さないでください。

#### 任意の最小metrics

既定は無効で、**新規作成専用**です。`--metrics-out FILE`は、store操作の前に、既存directory内で
FILEを排他的（no-follow・mode 0600）に作成し、その同じfile handleで後に1回だけ上限付きで書きます。
既存のpath（store・SQLiteのsidecar／journal・export・hardlink／symlink・directory）や親の不在は、
操作の前に終了code 2で拒否し、追記・切詰め・削除・作成はしません。親directoryは同時に差し替えられない
と信頼しており、他のprocessが先に同名を作った場合も拒否されます。1行にはaction・結果・経過ms・
管理record数または参照byte数・`model_calls: 0`・`cost: null`（`cost_state:
unavailable_not_measured`）だけを書きます。予約したfileは、操作や書込みが失敗しても（空のまま）残ります。
操作後のmetrics書込み失敗は警告を出しますが、操作の結果や終了codeは変えません。
**metricsを得るために操作を繰り返さないでください。** 費用不明はゼロではなく、節約額は測りません。
fileは回転も削除もされないため自分で消します。metricsは配線のlocal観測で、有用性・性能ではありません。

### live呼出しの前に費用を確認

adapterは送信前に回数を予約し、prompt／入力／返答byteとtransport時間を制限します。
**出力byteは生成後に検査**するため、生成前のmax-tokenや厳密な金額capは未実装です。
必要なaccount制御は別途確立します。hard capの追加は別実装であり、文書の切替ではありません。

usage／costは、実際に選んだadapterと返却envelopeが供給した観測だけを保持します。
欠測は不明であり**ゼロではありません**。見積もり・未照合billingは請求書ではありません。
全費用にはreview・採用・取得・別task実行・保守も含みます。
失敗・拒否・timeout・UNKNOWNでも課金される可能性があり、不明終了を自動retryしたり、
予約をresetしたりしません。

実モデルが「未試用」という意味ではありません。
[2026-11-12試用](public-source-trial-2026-11-12.ja.md)と、実装状況にある限定README-library
観測は実在します。ただし一般的改善・PR56のlive受入・全費用削減・常駐agent loopの証明ではありません。
