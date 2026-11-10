# OSS Contributorのcollect-only連携

[English](oss-bridge.md) | **日本語** | [接続設計](integration.ja.md)

## 境界

`CollectOnlyBridge`は既存OSS Contributorの
`src/collector/digest.py`にある`TriageDecision`を
`dataclasses.asdict`した辞書を受け付けます。呼出側が実際のagent commit、
対象repository、Sleep Labのproject／task_familyを固定します。
commitは呼出側の申告であり、認証済みの出自ではありません。

今回は明示的に接続する**合成データのオフラインadapter**です。
本番接続済みではありません。既存ストアのsynthetic-only契約を保ち、
実運用ログをsyntheticと偽って渡してはいけません。実ログの保存・保持期間・
利用許可は別契約が必要です。本番ledger、設定、timer、remote hostは変更しません。

## 記録と取得

[英語版の呼出例](oss-bridge.md)を参照してください。
既存の`AdoptionStore`とcapture authorizationを明示的に渡します。
暗黙の初期化や許可拡張は行いません。pending／infra_errorを含む現在の6状態は
判定の観測であり、タスク成功を意味しません。

記録元は上限内の判定辞書で、LLMの理由も未信頼データとして保持します。
`tool_observation`は「その判定を観測した」という根拠に限定し、
issueの事実やモデルの理由が正しいと認めるものではありません。
検証／評価受領、記憶、採用、patch、PRは作りません。
同じ入力の再送は既存capture境界でreplayし、同じevent IDの内容変更は拒否します。

`reference_context(query=..., max_bytes=...)`は現在policy・根拠・受領・除外を
再確認し、固定scopeの採用済み記憶だけを返します。空は正常です。
予算単位はUTF-8 byteでtokenではありません。返したbyteは明示的な参考データ枠で
扱い、現在の指示・対象policy・権限を置き換えません。

対象のscore、閾値、pending状態、ledger、collect-only gateは変更しません。
adapterは受信側を実行しないため、bundle生成を配信・利用確認とは呼びません。

任意の[受け渡しjournal](reference-use.ja.md)で固定byteと明示的なローカルconsumer呼出しを
記録できます。返答は未確認で、配信・利用の検証済み証明ではありません。

## 検証と残作業

合成fixtureで記録／replay、未信頼の理由、実データ拒否、対象repo不一致、
不正入力、authorization不一致、採用済み記憶取得、scope分離、
現在の除外、policy未設定を検査します。実モデルや本番運用の検証ではありません。
最新の結果は[実装状況](implementation-status.ja.md)に記録します。

既存agent一つの接続完了とするには、利用可能な固定記憶bundleを実際の対象実行が
受け取り、使用した結果を記録できることと、実ログのcapture／利用契約が必要です。
オフラインテストの合格で本番接続を自動有効化しません。
