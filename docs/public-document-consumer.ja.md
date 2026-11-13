# 公開文書の明示的な後続consumer

[English](public-document-consumer.md) | **日本語**

保存済みの別task向けrequestを、明示的なMiMo呼出し1回へ接続するlibrary adapterです。
request作成・文書取得・採用・意味review・合成runtime変更は行いません。
検証状況の唯一の正本は[実装状況](implementation-status.ja.md)です。
本手順はこのhelper自体のlive検証済み主張ではありません。

## hostからの呼出し

受入・独立した引用／機械的review・採用後、
[lifecycle](public-document-lifecycle.ja.md)に従って
`store.prepare_request(..., consumer=configured_consumer)`を実行します。
保存済みrequestの完全なbyte、scope、現在許可、host権限を別途確認してから呼びます。

```python
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.public_document_model import InvocationPermission, inspect_journal
from agent_sleep_lab.public_document_consumer import invoke_consumer

request = store.read_request(request_id)
permission = InvocationPermission(
    request_sha256=sha256_hex(request),
    agent=registered_agent,             # hostの明示設定
    allow_paid_call=True,              # 独立したhost承認がある場合だけ
    accept_unknown_cost=True,
    max_prompt_bytes=32768,
    timeout_seconds=60,
)
receipt, metadata = invoke_consumer(
    store=store, request_id=request_id, consumer=configured_consumer,
    journal_path=preserved_private_sidecar_path, permission=permission,
)
result = store.read_result(request_id)   # 管理本文。暗黙にexportしない
observations = inspect_journal(preserved_private_sidecar_path)
```

許可は凍結された`InvocationPermission`型に限り、文書／modelの指示は許可ではありません。
consumerはstore設定と完全一致が必要です。request／consumer入力は65,536 byte以内、
出力上限は1〜65,536 byte、prompt許可はUTF-8で1〜131,072 byte、
timeoutは整数1〜120秒です。modelは`xiaomi/mimo-v2.6-pro`固定、
最大1呼出しでfallback・自動retryはありません。
byteやCLI経過時間はtoken／金額上限やprovider latencyではありません。
生成後の出力検査で生成料金は制限できません。会計未観測はゼロでなく不明です。

## 永続化と境界

予約前に保存request・hash許可・consumer設定・現在generation／head・byte上限・
同一requestの既実行を照合し、provider初期化でagent／timeoutを検査します。
事前確認は将来の権限保証ではありません。`store.dispatch`が再確認し、
ID改名を含む実質同一requestの実行拒否の正本であり続けます。

別SQLite sidecarはstage adapterと同じ本文なしの`calls` schemaを使い、
storeのcanonical path・consumer stage・request hashから一意keyを作ります。
FULL synchronousでUNKNOWNをcommitしてからdispatch／transportへ入ります。
同じsidecarをprocess／再起動を越えて保持してください。並行予約で2回目は呼べません。
別sidecarも本storeの実質同一性gateを迂回しません。retry目的で予約を削除／resetしません。

実transport入口でCLI argv全体・完全なprompt・timeout・subprocess optionを確認し、
`subprocess.run`直前に`observe_input(exact_request)`を呼びます。
準備／読出し時に観測を捏造しません。これはlocal境界観測でremote認証ではありません。
入れ子provider receiptは意図的に`injected_transport_not_live_verified`と記録し、
envelopeのlabelだけでlive認証済みに昇格しません。

戻り値はdispatch receiptと本文なしmetadataです。生応答は管理result経路に保存します。
finallyでprovider観測・経過時間・不明会計を可能な範囲で記録し、
例外文字列・原文・prompt・生応答はsidecarへ保存しません。
予約後の例外はtransport前の拒否でも保守的なUNKNOWN／retry禁止です。
crash時は最初のUNKNOWNだけが残り得ます。再送せず証拠を確認します。

応答後の許可撤回／現在制御確認はstoreが担当し、providerの応答だけでは管理resultを
利用可能にしません。`semantic_use`は`not_reviewed`のままです。
意味reviewは別host操作で、consumerが自己認定しません。
本文なしのretry禁止metadataを保持し、管理本文と別途作った派生物はlifecycleの削除条件に従います。
timer・自動cleanup・認証変更・常駐実行は追加しません。
