# 公開文書の明示的モデル接続

[English](public-document-model.md) | **日本語** | [Lifecycle](public-document-lifecycle.ja.md)

任意library `public_document_model.py` は、既存の登録済みOpenClaw経路で
`xiaomi/mimo-v2.6-pro`を明示選択します。pure saved-output protocolと合成runtimeは
変更しません。fetch、fallback、retry、自動stage連結・採用・agent loopはありません。

現在の検証・release準備は[実装状況](implementation-status.ja.md)だけを参照してください。
本書はlibrary契約であり、公開済み・性能受入の主張ではありません。libraryのみなのは意図的で、
許可・stage提出・独立review・採用・別consumer選択はhostが担います。新CLI・自動連結はありません。
[構成図](architecture-overview.ja.md)と[文書索引](index.ja.md)から関連契約へ進めます。

## 呼出し契約

英語版の実行例は両言語共通APIです。`InvocationPermission`には、呼出し側が独立に
選んだrequest SHA-256、登録agent、paid callの明示許可、費用不明の受容、
prompt byte上限（最大131072）、timeout（1〜120秒）を渡します。文書やモデル出力は
許可になりません。このobject自体は認証済み承認受領ではありません。

新たにownerが許可し公開・秘密情報reviewを終えた文書1件を、新しい隔離
PublicDocumentStoreへ既存lifecycle契約で受け入れます。旧合成pilotのstore・report・
結果不明executionは使いません。役割を分離し、privateなmetadata sidecarを1つ作り、
以後すべての呼出しで同じpathを保持します。

1. `prepare_sleep(**preparation)`でLight requestを固定します。
2. request hashに束縛した独立permissionを渡し、`invoke_stage(stage="light", ...)`
   を1回呼びます。返却bytesを`submit_light_result`へ渡します。
3. 空選択なら終了。Deep requestが返った場合だけ、そのhashの新たなpermissionと
   exact Light replyを渡して`invoke_stage(stage="deep", ...)`を1回呼びます。
4. 返却Deep bytesを`submit_deep_result`へ渡します。未検証提案であり採用ではありません。

最大2回の新規モデル呼出しです。submission失敗や返却後のcrashでも再呼出しせず停止します。
既定ではrunnerはsubmission前のraw replyを永続化しません。以下の任意quarantineも
上限内の返却済みprotocol不正だけを対象とし、crash時の消失を防ぐ保証ではありません。
raw replyをrepoへexportしません。

## 任意のLight task／rubric context

`public_document_sleep.SelectionContext(task=..., rubric=..., max_bytes=2048)`を
`prepare_sleep(..., selection_context=...)`へ明示指定できます。taskとrubricのexact UTF-8
合計は非空で、正の上限（最大**8192 byte**）以内とします。canonical要求全体にも
`SleepLimits.max_request_bytes`を適用し、切捨てません。review済み公開開発task用に限定し、
私的本文・認証情報・評価解答・独立holdout用rubricを含めません。Sleepへ公開したcontextは
開発入力であり、独立holdoutの証拠にはなりません。

Lightの任意`selection_context`は`task`・`rubric`・`max_bytes`・`untrusted:true`・
`authority:false`だけを持ちます。原文unitの選別用dataで、原証拠・許可・review・採用の
権限ではありません。Deepには選択原文unitだけを渡し、context自体は除き、exact Light
要求hashを通して束縛します。context本文は上限・role・有料呼出し許可・retry identity・
対象側の実行制約を変更できません。

省略または`None`では従来の要求／prompt byteを維持します。contextを追加・変更すると
canonical要求hashが変わり、旧要求のpermissionは予約／dispatch前に拒否されます。
同sleep IDのcontext変更は競合し、再openと現在controlによる再構築でも元contextを保持します。
contextは管理要求本文として同じpurgeで削除します。

exact instruction＋requestのpromptも固定する場合は、`public_document_model`の
`build_stage_prompt(request=request_bytes, stage="light")`のSHA-256を
`InvocationPermission(..., prompt_sha256=...)`へ指定します。既存caller向けの既定値は
`None`です。request hashの許可とprompt byte上限は常に必要で、指定したprompt hashは
予約前に照合します。実際の送信promptも常にhash照合し、hash／byte数だけを記録します。
prompt固定は独立権限や追加試行の許可ではありません。

## 拒否応答の任意managed quarantine

`invoke_stage(..., quarantine_max_bytes=N)`で拒否raw replyの保持を明示選択できます。
既定`None`では拒否byteを保存しません。`N`は正の整数で最大**65536**、かつ準備した
reply上限以下です。確認済みtransport envelopeから返却されたtextがstrict Light／Deep
protocolで拒否された場合だけ保存します。quarantine上限超過は全体を見送り、切捨てません。
transport envelope不正・結果不明・crash、返却前の生成後output上限拒否は保存対象外です。
byte上限はtoken／金額上限ではありません。

adapterは`store.quarantine_sleep_result(sleep_id=..., stage=...,
expected_request_sha256=..., result_bytes=..., max_bytes=N)`を使います。
offline callerも保存応答の拒否後に同APIを明示利用できます。現在control・原文・parent・
要求を再確認し、strictな拒否を独立に再検査します。上限はreply上限以下（store最大512 KiB）
です。有効または既に受理した応答はquarantineへ入れません。
**store内の各stageにつき不変raw replyを1件だけ**と、小さい内容なし拒否recordを1件保存します。
exact replayは冪等、異なる要求／raw replyはinventoryを増やさず競合します。
2件の書込みは一括commitまたはrollbackです。

kind `sleep_rejected_reply`・`sleep_rejection`は既存content inventory・完全性検査・
期限／撤回除外・`purge_pending`・secure-delete・compactionの対象です。
新table・migration・raw出力sidecarは追加しません。
明示診断read `read_sleep_quarantine(sleep_id=..., stage=...,
expected_request_sha256=...)`は元の束縛が現在も有効な場合だけ拒否byteを返し、
proposalへ変換しません。保存済みquarantineは同exact要求のsubmitを終端拒否し、
修正済み保存応答でも置換できません。不正Deepからproposal・review・採用・consumer結果は
**一切作りません**。verifier／adoption／consumer境界は変更しません。

Sleep例外の内容なし`.code`は`invalid_json`・`protocol_fields`・`binding_mismatch`・
`source_selection`・旧`invalid_excerpt`・`authority_claim`・`excerpt_source_mismatch`・
`quotation_bound`・`quotation_not_exact`・`duplicate_excerpt`・`byte_limit`・`item_limit`・`invalid_context`と
既定`invalid_protocol`です。構造が正しいDeep itemは、権威flag・source束縛・引用byte上限・
原文完全一致・重複引用の順で最初の失敗を返します。不正field／textはprotocol分類で、
部分的proposal listは返しません。storeのquarantine拒否は`quarantine_bound`／`quarantined`、
通常lifecycle拒否は`lifecycle_rejected`、transportは`transport_rejected`／
`transport_outcome_unknown`です。raw出力・敵対的key・例外本文を例外／log／受領へ
転記しません。sidecarには`error_category`と`quarantine_status`だけを追加します。
後者は`disabled`・`skipped_bound`・`saved_untrusted`・`not_saved`で、`not_saved`は
除外・不変slot競合・保存失敗などを表し、保持成功とは主張しません。

quarantineは永続stage予約を払い戻しません。context・sleep ID・request・parent・
quarantine選択を変えても再dispatchできません。purgeは管理quarantineを除去しますが、
別metadataのno-retry tombstoneは保持します。caller buffer／export・provider複製・backup・
停止中の期限削除は管理削除保証の対象外です。保持byteはuntrusted診断dataであり、
独立した検証／採用受領ではありません。

## 観測・結果不明の停止

sidecarはtransport前に同期commitでUNKNOWNを予約します。keyは正規化store path、
文書artifact hash、generation、stageに束縛されます。sleep ID・parent・requestを変えても
同じstageを再送できません。成功済みも再送不可。同一sidecarの並行予約も一方だけです。
sidecar削除・置換、storeの移動・複製、generation変更は回復方法や再送許可ではありません。
これは協調的なlocal保護で、認証済みglobal exactly-once保証ではありません。

prepared requestと実際のCLI promptのhash・byte数を保存し、送信直前にも照合します。
既存providerはmodel/provider、fallbackなしのenvelope、output byte、単調時計のCLI全体時間
を確認します。その後strict parserでreplyを確認します。`transport_receipt`にresponse
hash/bytes、usage/costの可用性を記録します。欠測はゼロではありません。
transport wrapperは下位adapterでは正直にinjectedと表示されますが、prompt照合後に
既存CLIだけを呼びます。fake testはlive実証ではありません。

byte上限はtoken・金額上限ではなく、outputは生成後検査です。CLI promptはlocal process
metadataに見える可能性があります。認証情報・既定model・host設定は変更しません。
予約直前とsubmission時にstore controlを再確認しますが、remote providerとの分散transaction
ではありません。送信と競合した撤回は既送信bytesを取り戻せません。

## 独立review・採用・別task・削除

Deep結果は未検証引用だけです。設定済みverifierによる原文照合、別evaluatorによる
exact candidate/parentのsnapshot受領、現在のgeneration/parentを照合する明示的採用は別操作です。
モデル応答・transport観測をreview受領へ昇格しません。引用一致は有用性や性能の証明ではありません。

採用後のみ別target taskへの取得を準備し、既存dispatch境界で設定済みconsumerを明示呼出しします。
入力観測・返却・独立semantic review・性能評価は別です。このadapterは実行しません。

metadata sidecarはstoreのmanaged deletion外です。prompt/replyは含めませんがhash・費用・
時間metadataを含むため、hostがアクセスと保持を管理しno-retry tombstoneを維持します。
source期限だけを理由に削除しません。store purgeではCLI/provider側copy・process観測・
backup・caller exportは削除できません。timerや自動cleanupは追加しません。
