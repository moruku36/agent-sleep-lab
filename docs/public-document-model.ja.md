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
runnerはsubmission前のraw replyを永続化しないため、その隙間のcrashでは失う可能性があります。
raw replyをrepoへexportしません。

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
