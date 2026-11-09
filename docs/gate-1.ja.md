# ゲート1：オフライン契約検証

[English](gate-1.md) | [ホーム](../README.ja.md)

状態：macOS arm64／CPython 3.13.18でローカル受入合格。[受入レポート](../reports/gate-1-progress.md)に実行結果と限界を記録しています。GitHub公開とCIの状態は別途照合が必要です。

## 範囲

event JSONL、memory JSONの単一object／配列、promotion requestの単一objectを読み取る検証CLIです。repo内のDraft-07／2020-12 schemaの同梱コピーを使い、外部schemaの解決を拒否します。schemaのdialect URIは識別子で、ダウンロード指示ではありません。

verifierの認証、opaqueな証拠・受領参照の照会、現在の権限・除外確認、記憶採用は行いません。合成promotion例は構造上有効でも採用可能ではありません。永続writer、取込／取得adapter、sleep用model呼出、定期処理、性能実験は対象外です。SLP-01〜12の実行時受入は未実施です。

## 開発環境と使い方

Python 3.11以上が必要で、開発用は3.13.18に固定しています。[公式uv](https://docs.astral.sh/uv/getting-started/installation/)（ローカルでは0.13.7で確認）を用い、システムPythonは置き換えません。

```sh
uv python install 3.13.18 --no-bin
uv venv --python 3.13.18 .venv
uv pip install --python .venv/bin/python --require-hashes -r requirements-dev.lock
uv pip install --python .venv/bin/python --no-deps -e .
.venv/bin/python tools/check_environment.py
.venv/bin/python tests/run_tests.py
.venv/bin/python tools/check_docs.py
.venv/bin/agent-sleep-lab schemas
.venv/bin/agent-sleep-lab validate events examples/events.synthetic.jsonl
.venv/bin/agent-sleep-lab validate memory examples/memory.candidates.synthetic.json --format json
.venv/bin/agent-sleep-lab validate promotion examples/promotion-request.synthetic.json
```

`requirements.txt`は直接の実行時依存の固定で、推移依存のlockではありません。`requirements-dev.txt`には指定の[OpenAI公式Python SDK](https://github.com/openai/openai-python) 3.48.0を開発用として追加しました。`requirements-dev.lock`はmacOS arm64／Python 3.13で解決した開発依存と配布hashを記録し、全環境での受入合格は主張しません。上の確認にはAPI呼出も認証情報も不要です。CLIの実行時依存にOpenAI SDKは含めず、このゲートからproviderを呼びません。

終了コードは`0`＝有効（警告ありを含む）、`1`＝内容不正、`2`＝引数・入力読取・schema読込のエラー。既定はtext出力で、`--format json`でJSONの検証結果を選べます。`--max-diagnostics`は表示件数上限（既定50、範囲1〜1000）。読取エラーはJSON modeでもstderrへ出ます。

## 実装した検査

- 厳密UTF-8／JSON：BOM、重複key、孤立surrogate、NaN／Infinity／float overflow、不正構文、過深nestを拒否。巨大整数は対応interpreter既定の桁数上限で制限します。
- 契約版、必須・余分なfield、型、RFC3339日時形式。UTCへの正規化は行いません。
- 入力内整合性：event／memory IDの同一内容再掲は警告、異なる内容はエラー。自己訂正・自己supersede、未確認verified、verified hypothesisを拒否。ただし出典検証やverifier認証ではありません。
- 通常fileだけを上限付きで読取。file 8 MiB、event一行1 MiB、10,000 record、container 64段、recordあたりschemaエラー10件＋省略通知。
- event JSONLは物理改行区切りで空行はエラー。空file／空memory配列は警告で、採用やsleep成功を表しません。

## wheel受入

```sh
uv build --wheel --out-dir dist
uv venv --python 3.13.18 .venv-wheel
uv pip install --python .venv-wheel/bin/python dist/agent_sleep_lab-0.1.0.dev0-py3-none-any.whl
```

その後、絶対pathで`.venv-wheel/bin/python tools/check_installed.py /absolute/checkout/path`をcheckout外の作業directoryから起動します。ローカルでは合成例3種類、同梱schema読込、内容不正の終了1、存在しないfileの終了2が合格しました。helperはsource treeをimportしていないことも確認します。

Linux／Python 3.11・3.13向けに同じ契約・wheel検査のCIを定義しました。その環境での合格はGitHubの実際のrunを参照してください。検査合格は性能改善や記憶採用の証明ではありません。
