# 参考記憶の受け渡し記録

[English](reference-use.md) | **日本語** | [OSS bridge](oss-bridge.ja.md)

## 記録するもの

`ReferenceUseJournal`は上限付きのtaskとscope付き参考bundleの実byte・hash、
呼出側が固定したconsumer ID／version、対象repo／agent commit、
検索queryとbyte／record上限を、**別の非公開SQLite journal**に保存します。
journalや出力を公開repoへ入れません。

明示的に渡した信頼できるローカルcallableをuse IDごとに最大1回呼びます。
plugin読込み、認証、モデルclient作成、メッセージ送信、定期処理は行いません。
consumerが行う操作には呼出側の既存権限が必要で、task／記憶文は権限になりません。
[英語版の実行例](reference-use.md)はオフラインfixtureです。

## 状態と再実行防止

- `prepared`：固定済み、未dispatch。
- `dispatch_outcome_unknown`：consumer呼出し**前**に永続化した実行意図。
- `received_unreviewed`：task／参考hashが一致する返答を保存。自己申告の未確認受領。
- `invalid_receipt_unreviewed`：返答形式／hashが不一致。再実行しない。
- `invalidated`：現在の参考文脈が変化、または確認不能。

例外、プロセス停止、ACK不明はunknownのままです。再open、再prepare、再dispatchで
consumerを再実行しません。timeoutによるリセット、復旧時の再送、予約返却はありません。
use IDの一意制約とSQLite CASで同時接続の二重呼出しを防ぎます。
consumerの副作用とSQLiteを一つのtransactionにはできず、完了のexactly-onceは主張しません。

taskは1〜65,536 byte、参考bundleは全体で最大262,144 byte、
出力は最大65,536 byteです。出力の生成後検査であり、consumerの実行時間、
メモリー、token、費用を制限するsandboxではありません。

## 現在policyと限界

dispatch前に現在policyで再取得し、固定文脈と比較します。
読取り時刻`as_of`だけを比較対象から除き、policy、snapshot、record、除外、
scope、予算は維持します。返答後にも確認し、変化していれば有効な返答は保持しつつ
invalidatedにします。再確認ができない場合も停止扱いです。

事前確認からconsumerの実操作までの競合時間は消えません。
consumer側でも必要な実行境界で現在policyを守る必要があります。
対象ledger、権限、採用、採点は変更しません。

hash付き返答は**consumerの未確認自己申告**であって、記憶を実際に推論へ使ったことや
品質改善の証明ではありません。statusは常に`delivery_and_use_verified=False`です。
返答を証拠・検証・評価・採用へ自動昇格せず、既存agent連携完了とも扱いません。
実agent実行と配信／利用の独立確認は未完です。元bridgeのsynthetic-only制約も維持します。

## 検証

合成回帰で再open／再dispatch、結果不明、停止後の意図、実行前後のpolicy変更、
不正受領、identity不一致、同時dispatch、別DB拒否、binding破損を検査します。
実行済みの結果は[実装状況](implementation-status.ja.md)を参照してください。
