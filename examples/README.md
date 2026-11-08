# 合成例

このフォルダは設計説明用の架空データ。実ユーザーの会話、モデル実行ログ、実験成績ではない。

- [events.synthetic.jsonl](events.synthetic.jsonl)：課題→失敗→訂正→成功の4イベント。
- [memory.candidates.synthetic.json](memory.candidates.synthetic.json)：その経験から作る記憶候補の形。

fixture:// URIは上記イベントのsource_uriと対応する説明用の識別子。インターネット上の取得先ではない。別途の会話ファイルをダウンロードする必要はない。

記憶はcandidate／pendingのまま。実装済みの抽出器が生成した結果でも、性能向上の証拠でもない。

## 期待する確認

訂正がsynthetic-event-002の失敗を指すこと、候補が訂正と成功例の両方を参照すること、synthetic-paper-curationの範囲にとどまることを確認する。

異常系fixtureとして、根拠ID不在、他projectの参照、期限切れ、同じIDの内容違い、外部命令を含む記事、競合する訂正を追加する予定。Phase 1以降の実装テストに使う。
