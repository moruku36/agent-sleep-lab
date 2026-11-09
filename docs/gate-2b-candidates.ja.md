# ゲート2B・第2単位：候補snapshotの構築

[English](gate-2b-candidates.md) | [ホーム](../README.ja.md)

**状態：ローカル受入済み。全174テスト（既存152件＋追加22件）と別環境wheel検証が合格です。** 今回はDBに触れない純粋な候補構築ライブラリで、**記憶の採用commit・active参照の更新・現在の適格性判定はまだ行いません。** [受入記録](../reports/gate-2b-candidates-progress.md)と[実際のPR](https://github.com/moruku36/agent-sleep-lab/pulls)で公開状態を区別します。

## 実装したもの

操作manifest、原証拠manifest、候補snapshot、採用request、採用受領の**形式**の5種類の厳密なschemaを追加しました。package側にも同一コピーを同梱し、旧schema・CLIは変更していません。storeへの登録や旧requestの自動移行はしません。

`adoption_candidates.py`は、渡された親版と操作から候補を構築し、requestと受領形式のbytes／digestを作ります。関数名に`committed`が含まれていても、**返されたbytesは実際のcommitの証拠ではありません。** 将来のwriterが永続transaction後にだけ正式な受領として公開するための形式です。

## 操作の意味

- `add`：新しいIDを追加。候補snapshot内の`active`表示であり、実際のactive記憶にはなりません。
- `supersede`：activeな対象を履歴として保持し、新IDの後継へ置換。無関係な記憶は残します。
- `mark_stale`：削除せずstale化。偽と断定しません。
- `reject`／`defer`：未採用の提案に対する監査用情報で、既存memberを消しません。これだけのrunでは新snapshot・評価を作らず、未初期化scopeも初期化しません。
- 重複target、未知／非activeな対象、ID再利用、scope変更、hash・原証拠の不一致、証拠ID重複、supersedes不整合、サイズ超過を拒否します。無関係な記憶の省略や暗黙の追い出しはしません。

符号化は内部用のsorted-key compact ASCII JSONで、RFC 8785ではありません。操作は規定順、memberはID順。上限は操作／原証拠entryが64、memberが256、entry当たり証拠参照32、artifact当たり256KiBです。ID履歴は呼出側から`known_ids`で渡すため、DB全体での一意性をここで保証したことにはなりません。

## まだ行わないこと

現在のactive親版の解決、許可・除外のCAS、検証／評価受領の実解決、祖先を含む原証拠の照合、採用transaction、永続operation ID照会・再送、run IDとの監査上の関連付け、採用受領の保存は未実装です。新requestは方針の統合版を使い、旧requestの許可版／除外版を黙って同一視しません。移行・writerへの組込みは後続です。

新しい記憶の形式・期限・種別は検査しますが、引継いだ全memberの現在の適格性はwriterが再確認する必要があります。hypothesisはactive候補にできず、preferenceのrootにuser correctionを要求する純粋な規則もありますが、実出典への結び付けはまだしません。評価参照があるだけではsnapshot・protocol・結果の一致は検証されません。

今回の原証拠manifestは追加／置換する記憶だけを扱います。任意の入力を採用許可としたり、この単位でSLP全体やクラッシュ／応答消失を受入済みにしたりしません。

## 実行した確認

`.venv/bin/python tests/run_tests.py`で174件合格。初回に1件あったscope fixtureの不整合を修正し、重複証拠・受領の方針版／日時も補強しました。決定的な構築、操作ごとの意味、履歴保持、ID競合、親版・scope・期限・種別・過大候補の拒否等を確認しています。

新wheelを別環境へ入れ、[候補構築の検証](../tools/check_candidates_installed.py)をcheckout外から実行。schema同梱、追加・置換と履歴、request・受領形式のhash結合が合格しました。ここでの参照は記号的な合成データで、登録済み証拠ではありません。既存CLI・証拠ストア・受領／方針のwheel検証も合格。Python 3.11／3.13のCIへ追加していますが、実際の結果は別途確認します。
