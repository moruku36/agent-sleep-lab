# Runtime guide

**English** | [日本語](runtime-guide.ja.md) | [Current status](implementation-status.md)

These are implemented commands, not claims that paid inference or an existing
agent integration has succeeded. Use an existing synthetic v3 adoption store
with independently configured boundaries, policy and registered receipts. The
CLI refuses missing stores and journal/store path collisions; it never initializes
permissions or registers verification/evaluation receipts for a model.

For existing OSS durable pairs/cohorts, `oss-cost-report --manifest local/report.json`
is an explicit offline reader with no execution options. See the
[read-only CLI, manifest and SQLite limits](oss-cost-accounting.md#read-only-cli-and-input-manifest).

## Explicit store configuration

Copy [runtime-store.example.json](../configs/runtime-store.example.json) to a
PRIVATE file and set its existing store path and actual configured boundary IDs,
accepted methods/protocol and protocol hash. These are local simulation identities,
not credentials or authentication. Do not put an API key in this file. It is not
loaded as Python code. Paths resolve from the current working directory.

## Sleep and generated candidates

```sh
agent-sleep-lab sleep --store-config private/store.json --manifest configs/sleep.example.json --journal private/sleep.sqlite --provider script --replies configs/sleep-replies.example.json
agent-sleep-lab sleep-status --journal private/sleep.sqlite --run-id sleep-public-fixture-1
```

The explicit run manifest binds scope, selected event IDs, limits, caller config
and candidate observation time. Evidence TEXT and event/source/provenance hashes
come from current eligible store data, never an unchecked model reference. Live
policy/head/evidence checks run before dispatch AND after return. Deep must emit
only `op`, `memory_id`, selected `event_ids` and generated `claim`. Materialized
memories preserve this prose and remain unverified candidates. The preparer must
not substitute different prose; existing independent verifier/evaluator and
atomic adoption remain mandatory. Legacy version-1 ID-only runs are fake-only.

To explicitly select paid inference instead of scripted replies:

```sh
agent-sleep-lab sleep --store-config private/store.json --manifest configs/sleep.example.json --journal private/sleep.sqlite --provider mimo --agent YOUR_REGISTERED_AGENT
```

The adapter invokes the registered OpenClaw account with fixed
`xiaomi/mimo-v2.6-pro`, not a key read from disk/environment by this package.
It validates provider/model/no-fallback receipts, reserves calls BEFORE dispatch,
uses argv without a shell, has a 120-second transport timeout and NEVER retries.
Sleep allows at most two stage calls. Input/request and output byte bounds are
not token bounds: **the CLI exposes no per-call max-token setting; output bytes
are checked AFTER generation, so there is no hard monetary/token ceiling**.
Unknown failures may have incurred cost. Use only with the caller's explicit
paid-use authorization and applicable account budget. No paid calls in CI.

Interrupted provider intent is not replayed. After confirming the old worker is
stopped, `recover_stopped_provider(run_id)` or
`recover_stopped_preparation(run_id)` explicitly marks the outcome incomplete and
unknown. Preparation recovery never re-executes the trusted callback. Reconcile
any independently registered artifacts/receipts before a separate new operation.

## Adoption and retrieval

```sh
agent-sleep-lab adopt --store-config private/store.json --manifest private/prepared-adoption.json
agent-sleep-lab retrieve --store-config private/store.json --manifest configs/retrieve.example.json
```

Adoption takes the existing writer kwargs serialized as hex strings:
`request_bytes`, `manifest_bytes`, `source_manifest_bytes` and a
`memory_bytes` ID→hex map. Obtain these from independent trusted preparation,
not provider-supplied receipt claims. The atomic writer checks the exact parent,
current policy, evidence and registered verification/evaluation receipts. The
CLI does not bypass any boundary or auto-adopt generated prose. Retrieval uses
current eligibility and excludes lexical score-zero items for nonempty query
terms; no-query listing is still supported.

## Paired comparison

```sh
agent-sleep-lab compare --store-config private/store.json --manifest private/comparison.json --journal private/comparison.sqlite --provider mimo --agent YOUR_REGISTERED_AGENT --rubric private/exact-match-rubric.json
```

The manifest contains `plan_id`, 1–5 `tasks` ({task_id,prompt}),
`retrieval` (scope,max_bytes and optional query/caps), `budget` (calls per
arm, request_bytes, reply_bytes), `config` and `evaluator_identity`
(name,version,protocol_sha256). The separate rubric maps task IDs to exact
expected reply strings. Its canonical-JSON SHA256 must match protocol_sha256;
answers are never placed in provider requests. A mechanical exact-match fixture
score is not independent paper-quality assessment. Synthetic rubric results are
labelled as such even when responses come from a real provider.

Raw evidence defaults to event-ID order even when `retrieval.query` is set.
Explicit `retrieval.raw_order: "query_overlap_descending"` opts into bounded
bilingual query ranking before raw caps and byte packing, retaining zero-overlap
rows. See the [API and manifest contract](raw-query-ranking.md) for validation,
frozen ranking identity and saved-plan compatibility. Both arms share the same
raw prefix; this does not establish fairness or improvement.

A/B use identical per-arm limits and alternating order. If any packed A/B inputs
are identical, planning FAILS before registration/dispatch. Reduce raw context
or increase the request cap. Library `diagnostic_only=True` permits byte/audit
inspection, but reports `comparable:false` and `comparison:null`. It is not a
performance trial. Entire records and the strict raw-prefix audit are preserved.
Receipts and unknown outcomes persist in the private journal; resume skips
completed arms and never repeats an intent with unknown outcome. MiMo cost is
reported unavailable, not synthetic zero. No savings/performance claim follows.

The [five-task development fixture](../examples/paper-pilot/README.md) is preparation
for a real-response run, not a completed experiment or an independent holdout.
Research handoff targets now require explicit repository + immutable 40-hex
commit; no production target is hard-coded in the library.
