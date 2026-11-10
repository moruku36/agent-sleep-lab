# 回帰テスト方針

[ホーム](../README.ja.md) | [実装状況](implementation-status.ja.md)

所有者の2026-11-10 18:37 JSTのレビュー修正依頼により、Sleep Labの旧「1試行10件以下」を撤廃しました。PRおよびmainのCIで全件回帰を実行します。過去の上限と実行数は当時の履歴であり、現在の実行制限ではありません。

```sh
python -m pip install .
python tests/run_tests.py
python tools/check_docs.py
# 修正箇所の確認だけを先に行う場合
python tests/run_tests.py test_runtime_review
# 実行せず全選択IDを確認
python tests/run_tests.py --list
```

runnerは全test_*.pyを探索し、同一unittest IDを重複排除します。fixtureとしてimportされたTestCase aliasを二重実行しません。実行したケース数と呼出し回数は分けて報告し、外部レビューの253件などを自分の実行結果として数えません。

CIはPython 3.11／3.13、PRイベントとmainへのpushを対象にします。feature pushとPRの二重起動は避けますが、mainマージ時の回帰は意図した再確認です。全Markdownの相対ファイルリンク（anchor対象外）とwheelビルドも確認します。有料モデルAPIはCIから呼びません。

失敗時は原因を直し、まず関係するケースだけを再実行します。全件の繰返しは修正・新たな懸念があるときに限定します。依存pinの不一致をテスト省略や期待値の変更で隠しません。実API試行の費用・時間・回数上限は回帰テスト方針とは別です。
