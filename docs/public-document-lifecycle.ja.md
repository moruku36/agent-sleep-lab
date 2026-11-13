# 公開文書1件のlifecycle

[English](public-document-lifecycle.md) | **日本語** | [実装状況](implementation-status.ja.md)

既存の合成provenance・RuntimeStore・取得・CollectOnlyBridgeを緩めず、
**別の版付きライブラリ／専用SQLite store**で公開文書1件を扱います。
取得、provider client、自動dispatch、timer、有料model接続はありません。
テストは架空の公開byteと注入したoffline consumerだけです。

## 信頼境界と現在許可

[public_document_runtime.py](../src/agent_sleep_lab/public_document_runtime.py)の契約は
`agent-sleep-public-document/1`です。`PublicDocumentStore.create`は新規fileを排他的に作り、
通常のconstructorは既存fileだけを開きます。合成storeの移行／代用はしません。

原文／model出力の外で、control・quotation verifier・mechanical evaluator・
semantic reviewerの4つの異なる`Authority(identity, version)`を設定します。
consumerは別identity／version／runtime permission／入出力byte上限を持ちます。
これは**信頼するhost内の役割分離で、認証・OS隔離・DBやPythonを操作できるコードからの
防御ではありません**。providerに制御／review handleやDB操作権限を渡しません。
設定は永続化して再open時にも照合します。組込み先のネイティブ承認制御は維持します。

controlの`approve`は、別途確認した
[PublicDocumentApproval](public-source-intake.ja.md)、正確なstaging artifact hash、
origin task、expected generationを束縛します。現在のrevision・URL・原文hash・scope・
許可／失効時刻・artifact hash・originを保存し、全本文APIが自分で現在controlを解決します。
古い許可objectの再送ではruntimeアクセスを認可できません。
revision更新には現在generationと同じ許可refが必要で、受入後の更新は旧派生物を失効させます。
撤回はgenerationを増やし、purge_pending／deletedから再許可はできません。

受入は既存`recheck_public_document`を再利用し、全本文アクセスで現在の除外・
`now < expires_at`・受入generation・原文と全管理派生物のhashを検査します。
時計はtimezone付きの信頼するhost時計です。staging／受入の許可はmodel・agent実行・
有料利用・公開・policyの許可ではなく、consumer permissionは別の明示設定です。

## 明示API経路

1. 外部で取得／reviewした原文を既存`prepare_public_document`で準備します。
   非公開storeを独立役割設定で作り、controlでexact artifactを許可して`admit`します。
2. `propose_excerpt(proposal_id=..., quotation=...)`で不変の**未検証**案を保存します。
   出典付き引用だけで、好み／policy／抽象的推論へ昇格しません。`read_proposal`と
   `candidate_snapshot`は読取り専用で受領を作りません。
3. 別設定verifierの`issue`は正確な原文引用だけを決定的に検査して候補hashを束縛します。
   真偽・抽象化品質・性能・意味的有用性の検証ではありません。
4. 別evaluatorの`issue`がexact candidate snapshot／parent／検証受領を固定した機械的
   protocolで確認します。task性能の合格判定ではありません。
5. `adopt`でoperation ID、expected parent／generationと両受領を指定します。
   登録受領・役割／版・protocol・hash・期限・現在controlを再検査し、追記型snapshot、
   memory、採用受領、operation、headを同じtransactionでcommitします。
   途中失敗は全てrollbackし、同一IDの別内容やCAS不一致は拒否します。
6. **originとは異なるtask ID・同じproject／task family**で`retrieve`または
   `prepare_request`します。引用と出典を含むrecord全体でbyte上限を適用し、
   一つも入らなければ拒否します。要求はgeneration、snapshot、task、入力／reference hash、
   consumer identity／version／permission／上限を固定します。
7. 別の明示`dispatch`がconsumer呼出し**前**に`dispatch_outcome_unknown`を永続化し、
   呼出し直前／応答後に現在controlを再検査します。
   `invoke(exact_request_bytes, observe_input)`は実入力境界で同一byteを
   `observe_input`へ渡してから利用する契約です。未観測／別byteではreturnedになりません。
   callbackの有効性判定・観測transaction全体・呼出しcloseは同じlockで直列化します。
   進入済みの観測完了を待ってcloseし、待機中／遅延callbackはclose後に拒否します。
   観測書込みとreturnedへの遷移には永続statusがunknownであることも必要で、
   古い観測からreturned受領を上書きしません。正常応答／例外終了の両方に適用します。
8. `execution_receipt`／`read_result`で結果を確認します。
   別設定のsemantic reviewerだけがexact request／result hashに束縛した独立の意味的利用判定を
   `record`できます。review前に`read_request`／`read_result`で同じbyteを確認できます。

[実行可能な架空例のテスト](../tests/test_public_document_runtime.py)と
[詳細API契約](public-document-lifecycle.md)を参照してください。
provider出力から権威的受領を自動作成する経路はありません。

## 結果不明と観測の区別

準備済み・実入力観測・応答済みは別状態です。consumerの利用自己申告、引用、
語彙一致は意味的reviewへ昇格しません。別reviewerの判断もhost assertionであり、
人間の本人認証・科学的性能比較・一般的な学習効果の証明ではありません。

crash／例外・未観測入力・不正な応答はunknownのままで、有効な結果を返しません。
自動再試行・返金・restartでの再送はありません。exact requestのbyte／hashは
request ID・generation・snapshot出典を保持し、**実効inputのno-retry identityとは分離**します。
専用store／control generation内で、schema・target task・scope・task-input hash・
実際にpackingしたreference hash（出典込み）・consumer identity／version／permission／
byte上限全体を同一性の根拠にします。request IDやsnapshot履歴だけでは実行枠は増えません。
同じ引用の再採用や、packingで選ばれないrecordの追加でheadが変わっても、
同じ実効inputのunknown実行を再試行できません。
同じwriter lock内で既存の全attemptの保存requestと比較するので、修正前のintentも対象です。
exact provenance列の移行や要求byteの変更はせず、既存attemptの要求本文欠落もfail-closedです。
unknown以外の既存attemptにも同じ再試行防止を適用します。
実効task／input／referenceが異なる明示認可済みの新規実行は別作業で、
旧unknownの復旧や解決には数えません。
出力上限は応答後のbyte検査で、remote側の生成token／請求上限ではありません。
採用operationのexact replayは現在controlのsweepを行い、内容なし履歴と
「現在適格性を主張しない」表示だけを返します。headや適格性を復活させません。

## 管理対象の削除と限界

source／evidence、proposal、memory、snapshot、request、resultを専用DBでinventory化します。
期限・撤回・整合性／generation不一致でまず除外を`purge_pending`として永続化します。
`purge`は本文、許可URL／body、origin task、review／dispatch派生物を
SQLite secure_delete・DELETE journal・VACUUMで除去し、圧縮成功後だけ`deleted`にします。
途中失敗はpendingのままで、論理忘却を物理削除と呼びません。
再open後の明示purge／アクセス時cleanupで続行できます。
最小の内容なしhash／generation、設定identity、hashだけのoperation履歴は
再受入抑止とexact replayのため残します。無関係なbundle／fileは辿らず、削除しません。

期限／整合性は明示`sweep`またはアクセス時に検査します。
**停止中のprogramは期限時刻の削除を実施できません**。scheduleは作りません。
管理SQLite内容の除去であり、SSD、filesystem snapshot、backup、他者が複製したjournalや
任意exportの安全消去を保証しません。呼出し前のstaging file、Python buffer、
consumerの複製、remote要求／応答はinventory外で、host側に別の削除責任があります。
実行中の撤回は渡したbyteを回収できませんが、local再読取りを拒否／purgeし、
戻った結果を利用不可にします。

実公開文書・既存の私的bundle・元の不明準備・provider・有料model・実agentは使いません。
実環境受入、公開文書Light／Deep、費用計測、独立した性能reviewは別です。
検証結果の正本は[実装状況](implementation-status.ja.md)だけです。
