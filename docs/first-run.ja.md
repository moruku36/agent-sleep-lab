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

## 実際の公開文書試用へ進む場合

これは**別library／store経路**です。demo optionや新しい自動CLIではありません。
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
