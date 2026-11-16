# Connected Recall

[English](README.md) | **日本語** | [既存core](../../README.ja.md)

忘れるagentが、必要な記憶・訂正・根拠を関係から辿るためのRelate拡張案です。
実装・検証の現在地は[実装状況](../../docs/implementation-status.ja.md#relate-experiment)に集約します。

## Relateを使う理由

SQLiteを正本に残し、Relateでtask・対象entity・記憶版・原証拠・出所・置換・利用を結びます。
関係探索で想起候補と理由pathを作り、本文は現在のSQLite検査を通して返します。
永続化は .rl ファイルを第一候補とし、固定Python bindingで使えなければdirectory形式へ縮退します。
作成・commit・close・reopenの受入前に対応済みとは書きません。
[具体的なモデルと手順](../../docs/relate-memory-design.ja.md)／[ADR](../../docs/decisions/0006-rebuildable-relate-projection.md)。

## 実装担当AIへの引継ぎ

この文書は設計の引継ぎであり、実装済みpackageの導入手順ではありません。
このdirectoryに、別のpyproject.toml、固定依存、src/asl_connected_recall/、
configs/、tests/、合成fixtures/を順に追加してください。詳細な配置と完了条件は設計書に従います。
root packageの必須依存や既定CLIへRelateを組み込まず、まず一つの固定core版を扱うread bridgeを作ります。

rebuild／inspect／compareは将来の操作名です。動作確認前に実行可能なcommandとして案内しないでください。
受入後、この節を確認済みOS・Python・Relate版と、正確なinstall・再構築・再open・探索・比較手順へ置き換えます。
公開成果物は submission/manifest.json に実際のpathとhashを記録し、
予定の submission/connected-recall.rl または完全なstore directoryを同梱します。
公開storeはreview済み合成fixtureからだけ生成し、private出力は .state/ に置きます。

## 切り戻しと提出

別venv・別graph所有process・別feature commitで進めます。
この実験を停止すれば既存SQLite取得へ戻れ、core DBの復元は不要です。
[固定基点](BASELINE.md)へコードを戻すことと、現在DBを古いcopyで上書きすることを混同しません。
既存開発は継続し、実験撤退のために共有mainをresetしないでください。

[再利用・AI利用の開示](REUSE.md)を提出時に更新します。応募適格性・配点の不一致、
12月12日11時JSTの締切は設計書を参照してください。
topic relate、合成の永続store、再現手順、短い動画は実装後に確認します。
現状の設計資料を動作する作品として提出せず、UNLICENSEDの既存コードへ勝手にライセンスを付与しません。
