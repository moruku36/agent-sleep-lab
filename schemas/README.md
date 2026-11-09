# データ契約 v0.1

状態：schemaは設計契約。JSON Schemaと合成例を収録する。読み取り専用の[ゲート1検証CLI](../docs/gate-1.ja.md)はmacOS arm64／Python 3.13.18で87件のテストとwheel・CLIのローカル受入に合格。永続化・記憶採用は未実装。

CLIの入力内整合性検査は、同一IDの再掲／競合、自己訂正・自己supersede、verifiedの確認情報、verified hypothesisの拒否まで。保存先全体の一意性、参照実在、出典・issuer認証、現在の許可・除外、採用条件は確認しない。

- [event.schema.json](event.schema.json)：一つの観測・成功・失敗・訂正。JSONLの各行に適用。
- [memory.schema.json](memory.schema.json)：再利用する一つの記憶。配列の場合は各要素に適用。

日時はUTCのRFC 3339形式で保存し、表示時にJSTへ変換する。projectとtask_familyの組が取得範囲。別projectへの移植は自動で行わない。

## Schema外で検証する制約

JSONの形だけで根拠の正しさや参照整合性は保証できない。実装では次を検証する。

1. event_id、memory_idは保存先で一意。重複取り込みは内容が同じ場合だけ無視し、内容違いなら競合として止める。
2. corrects_event_idとevidence.event_idが実在し、許可された範囲で参照できる。
3. source_uriとlocatorの証拠が存在し、取り込み時の内容hashと一致する。URIは外部ネットワークへ自動アクセスする指示ではない。
4. verifiedにはverification.result=confirmedと空でないverifierが必要。hypothesisは検証されるまでcandidateにとどめる。
5. stale／superseded／rejectedは通常取得から除外する。valid_untilが過ぎたverifiedも取得時点でstale扱いにする。
6. supersedesが循環せず、置き換え先と置き換え元の履歴を保存する。
7. syntheticな証拠に基づく記憶は実運用の記憶へ混ぜない。例のcandidateをそのままactiveへ入れない。

## Dreaming設計で追加が必要な契約（未実装）

v0.1のJSON Schemaは形の検査に限られ、以下の安全性を保証しない。実装開始前に別schemaと移行方針を追加する。現在の合成例に存在しないフィールドが、既に実行時に強制されるとは扱わない。

- **出典**：adapterが確認したorigin・発信者の同定根拠・session種別・利用許可とその確認時点／版・source内容hash・取り込み時点。本文が自己申告したtrust値は使わない。
- **生成物の由来**：原event、想起の再掲、モデルの要約、REM、日記を区別する。派生元IDを持ち、独立証拠の重複計上を防ぐ。
- **run manifest**：run_id・重複判定キー・入力／親snapshot・構成とprompt版・段階状態・チェックポイント・使用量・中断理由。
- **操作案**：add / supersede / mark_stale / reject / defer、対象memory ID・根拠ID・expected_parent。モデルに任意ファイルの置換権限を持たせない。
- **削除・失効**：派生先と再取り込みの抑止記録。現在の許可・除外方針を既存データにも再適用する。通常取得・採用・履歴再生・rollbackすべてで除外する。
- **採用記録**：証拠の直前再確認、評価結果、親版照合、操作ID、書込み結果。記憶のverificationとrunのpromotionを分ける。

[設計上の必須条件](../docs/dreaming.ja.md)はschemaだけでなく、書込み側と取得側の振る舞いとして検証する。

## Snapshot manifest（実装予定）

snapshot_id、parent_snapshot_id、作成日時、schema/config/adapter/modelの版、入力event ID一覧と内容hash、memory一覧とhash、評価report ID、採用判定を保存する。snapshot_idは正規化したmanifest本文（ID自身を除く）のSHA-256から作る予定。

active.jsonの更新時には親snapshot_idを照合する。構造化manifestの正規化は三ハーネス契約のRFC 8785 JCSを用い、自身のID・hash・署名を除く。原artifactは保存bytesのSHA-256。既存v0.1の不足情報を自動補完せず、新しい採用契約と明示的移行で扱う。

## 採用requestの追加契約

[promotion-request.schema.json](promotion-request.schema.json)（`sleep-promotion/1`）はv0.1を変更せず、候補snapshot・操作・原証拠・検証・評価の参照と、期待親版・許可版・除外版を要求する。[合成例](../examples/promotion-request.synthetic.json)はproposal_only=trueで、0埋めhashは未解決の記号。実在する証拠や採用許可ではない。

schema合格だけでwriterが採用してはならない。proposal_only、synthetic／production境界、実参照の存在／hash／issuer、scope、現行policy、transaction、循環を[仕様](../docs/contracts-and-acceptance.ja.md)どおり検証する。未対応版は拒否し、migrationは旧新hashと未確認事項を記録。既存v0.1のverified自己申告を信頼しない。
