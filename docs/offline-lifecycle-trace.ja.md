# Offline合成素材 → 採用 → 利用 → 撤回

[English](offline-lifecycle-trace.md) | **日本語** | [初回手順](first-run.ja.md)

既存fixtureの**ソースwalkthrough**です。新規live操作・状況報告・本番接続ではなく、
実文書を取得しません。組込みdemoの`temporary_state_removed`は一時store cleanupであり、
**許可撤回や管理本文purgeの証拠ではありません**。

## 最小の再現入口

runtime依存がinstall済みのcheckoutで使う明示入口：

```sh
PYTHONPATH=src python tests/run_tests.py test_public_document_runtime.PublicDocumentRuntimeTests.test_managed_text_purge_crash_recovery_and_unrelated_bundle_untouched
```

**合成1ケース／1起動**であり、module全件ではありません。
今回は入口を文書化しただけで**実行していません**。今回のlocal4ケース枠はtext表示に使い、
PR CIの4ケースもtext表示だけで、このlifecycle fixtureを選択しません。
CIへ追加せず、残枠なしで実行しません。
まず[既存fixture](../tests/test_public_document_runtime.py)を読みます。
新規一時directory・固定2030年時計・架空`example.test`識別子・offline注入callbackのみです。
URLはmetadataでfetchしません。fixtureのrole objectは本番認証ではありません。

## 操作と確認点

| 段階 | 既存source操作 | 確認点 |
|---|---|---|
| 素材 | `setUp`、`admit`で架空本文と許可を構築、generation 0→1で承認しartifact受入 | hash・scope・期限が結合。本文内の敵対命令はdataのまま |
| 案・受領 | `adopt`で架空天文台の正午開館文を引用し、別verifierと機械evaluatorが受領を発行 | 案は自己認証しない。この最小範囲にはLight／Deepやmodel不要 |
| 原子的採用 | `store.adopt`へ`EMPTY_HEAD`、generation 1、operation ID、両受領 | exact binding・親版検査。fixture受領は科学的有用性ではない |
| 別task利用 | `prepare`→`prepare_request`→`dispatch(..., invoke=returning)` | originは“origin”、targetは“different”。採用参照がcallbackへ届く。observe／返却は独立意味reviewではない |
| 撤回前 | `store.inventory` | source_evidence・proposal・memory・snapshot・request・resultの6種類 |
| 撤回失敗 | compaction失敗を意図的注入し`control.withdraw(expected_generation=1)` | 例外と`purge_pending`。試行だけで削除済みにしない |
| 回復 | 同じstoreをreopenし`purge` | deleted、managed_records=0、内容なしoperation_count=1 |
| 削除範囲 | DB本文・WAL／journal・無関係fileを確認 | 架空本文・task・result・URIがDBに残らず、WAL／journalなし、無関係bundleは不変 |

同じfixtureの`test_observed_and_returned_are_not_independent_semantic_use`は、
hash結合の独立reviewを別に説明します。暗黙実行しません。
callback本文の`consumer_used=true`／`semantic_use_confirmed=true`は意味利用の証拠ではありません。
本traceは性能改善・実agent受入・費用実測・remote／backup消去を示しません。
内容なしno-retry識別子を再試行目的でresetしません。

public-document libraryは合成CLI demoとは別storeです。host接続は
[lifecycle](public-document-lifecycle.ja.md)と[model境界](public-document-model.ja.md)を読みます。
このoffline入口は実data・model・API・export・公開の権限を与えません。
