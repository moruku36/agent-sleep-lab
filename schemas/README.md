# データ契約 v0.1

状態：設計。JSON Schemaと合成例を収録する。検証CLIと永続化実装はまだない。

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

## Snapshot manifest（実装予定）

snapshot_id、parent_snapshot_id、作成日時、schema/config/adapter/modelの版、入力event ID一覧と内容hash、memory一覧とhash、評価report ID、採用判定を保存する。snapshot_idは正規化したmanifest本文（ID自身を除く）のSHA-256から作る予定。

active.jsonの更新時には親snapshot_idを照合する。manifestの細部と正規化方式はPhase 1で固定し、それまではスキーマ互換性を保証しない。
