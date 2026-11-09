# ゲート2A：出典契約とローカル証拠store

[English](gate-2a.md) | [ホーム](../README.ja.md)

状態：**macOS arm64／Python 3.13.18でローカル受入合格。追加23件を含む全110テストが合格しました。** 作成したwheelを別環境へinstallし、checkout外から証拠storeとゲート1 CLIの確認も合格しました。GitHub CIと公開状態は別途確認します。[受入レポート](../reports/gate-2a-progress.md)を参照。ゲート1（読み取り専用検証CLI）は変更していません。この範囲はPythonライブラリのみで、書込みCLI、active参照、記憶採用、取得、verifier／評価連携、定期処理、model呼出、移行は含みません。

設計根拠：[ADR 0004](decisions/0004-local-evidence-store.md)、[契約 §2](contracts-and-acceptance.ja.md)。

## 機能

`agent_sleep_lab.provenance`が厳密なsidecar schema `agent-sleep-provenance/1`を定義します（同梱の`provenance.schema.json`。repositoryの`schemas/`にも同一bytes）。`agent_sleep_lab.evidence_store`がevent本文bytes、原source bytes、付与済み出典をSQLiteに保存します。

以下はAPIの概略です。`ev`・`src`・`claim`は準備済みの合成入力で、DBの親directoryも事前作成が必要です。完結した実行fixtureは[wheel受入helper](../tools/check_evidence_installed.py)を参照してください。

```python
from agent_sleep_lab.provenance import CaptureBoundary
from agent_sleep_lab.evidence_store import EvidenceStore, ReadOnlyEvidenceStore

boundary = CaptureBoundary(                       # 取込対象とは別に設定
    adapter_id="synthetic-adapter", adapter_version="1.0.0",
    allowed_origins=frozenset({"tool_observation", "recall"}),
    authorizations={"auth-1": 1},                 # 許可参照 -> 現行版
)
path = "/tmp/asl-demo/evidence.sqlite3"  # 事前に親directoryを作成
with EvidenceStore(path, boundary) as store:
    result = store.capture(event_bytes=ev, source_bytes=src, claim=claim)  # created | replayed
    report = store.verify(result.event_id)        # IntegrityReport(ok, failures)
with ReadOnlyEvidenceStore(path) as reader:
    stored = reader.get("e-1")                    # 取込APIなし。get自体は検証しない
```

- `capture`は原子的です。新規は`created`、byte同一（boundaryのadapter識別を含む）で既存記録が`verify`に合格すれば`replayed`。既存記録が壊れていれば`storage.corrupt_existing`、同じidで内容が違えば`conflict.event_id`です。
- `get`、`list_event_ids`、`independent_root_count(project, task_family)`、`verify`、`verify_all`、`close`。
- `claim`は`adapter`を含まない出典JSONで、adapterはboundaryが付与します（claim側に含めると拒否）。event本文から由来、adapter、許可、系譜は読みません。`event_id`、scope、`synthetic`をclaimと照合するだけです。
- エラーは安定した`.code`を持つ`EvidenceError`の派生：`ContractViolation`、`BoundaryViolation`、`LineageViolation`、`ConflictError`、`NotFoundError`、`StorageError`。

## 強制する規則

- synthetic限定：非syntheticのclaim／eventはfail closed（`synthetic.required`）。
- 未知のschema版、余分／欠落field、不正なRFC 3339時刻、`observed_at`＞`captured_at`、不正な識別子は拒否。
- claimのscopeはeventおよび親のscopeと一致し、origin・scope・許可（参照、**現行**版、期限）はboundaryが許す範囲に限る。
- 独立originは自分がroot。生成origin（`model_derived_summary`、`recall`、`rem`、`diary`、`generated_answer`）は保存済み記録から派生させ、rootに数えない。同scopeで同じsource bytesの二つ目のrootは`conflict.duplicate_root_source`。
- 子孫を追加する前に、同一transaction内でroot含む全祖先を再検証：hash一致、source bytes存在、期限内、現行許可版、同じ評価partition。満たさなければ何も書かない。
- 一記録につきroot一つ。複数root系譜は未対応。

## 限界

boundaryはローカルの模擬で認証ではありません。hashはbytesの同一性であり真実性・同意の証明ではなく、DBファイルを書ける者は行とhashを同時に偽造できます。除外／撤回台帳、採用、クラッシュ・電源断の受入、ネットワークfile system対応はありません。`canonical_json`は内部符号化でRFC 8785 JCSではありません。`user_correction`はboundaryが主張するラベルで、認証済み利用者ではありません。

## 実施した受入

```sh
.venv/bin/python tests/run_tests.py          # tests/test_evidence_store.pyを含む
.venv/bin/python tools/check_docs.py
```

`tests/test_evidence_store.py`は一時的な合成ディレクトリだけを使用し、全体110件が合格しました。再起動テストは接続のclose／再openで、OS再起動やprocess crashではありません。read-onlyの`get`は生のlookup、`verify`は保存内容の整合性と期限を調べるだけで、現行の取込boundary／撤回状態は参照せず、現在の権限・適格性を認定しません。

作成したwheelを`.venv-wheel-gate2a`へinstallし、checkout外から[check_evidence_installed.py](../tools/check_evidence_installed.py)を実行。同梱schema bytes、capture／replay、派生系譜とroot重複排除、再open・read-only検証が合格しました。固定の合成fixture時刻であり、現行の許可を表しません。実capture／API呼出は行っていません。
