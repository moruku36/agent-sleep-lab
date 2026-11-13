# Runtime guide

**English** | [日本語](runtime-guide.ja.md) | [Current status](implementation-status.md)

Command contracts do not establish successful paid inference or an existing
agent integration. Except for the self-contained `demo`, use an existing synthetic v3 adoption store
with independently configured boundaries, policy and registered receipts. The
CLI refuses missing stores and journal/store path collisions; it never initializes
permissions or registers verification/evaluation receipts for a model.

For existing OSS durable pairs/cohorts, `oss-cost-report --manifest local/report.json`
is an explicit offline reader with no execution options. See the
[read-only CLI, manifest and SQLite limits](oss-cost-accounting.md#read-only-cli-and-input-manifest).

## Built-in offline demo

```sh
agent-sleep-lab demo
```

The command accepts only `--help`; caller data, file paths, stores, output paths,
manifests and provider/live options are rejected before execution. It uses only
built-in synthetic catalog observations and scripted replies. No network,
subprocess, live provider, credential lookup, fallback, schedule or existing-agent
execution is part of this route. Current verification is recorded only in
[implementation status](implementation-status.md).

Each invocation creates a fresh temporary directory containing three separate
SQLite stores for evidence/adoption, sleep and comparison. Its capture boundaries
and policy are local fixtures; existing stores and permissions are not inputs.
Connections close and temporary state is removed on success or failure. A fixed
fixture clock (`2026-11-12T00:00:00Z`) precedes the evidence authorization expiry
(`2026-11-13T00:00:00Z`); these dates do not grant real-world permission. The JSON
report is printed only after successful completion and cleanup, with
`temporary_state_removed:true`. Errors return exit 2 without a success report.

The successful path has the following counts. They describe fixture operations,
not live-model calls or independently accepted performance results.

| Operation | Count |
|---|---:|
| Captured experience events | 2 |
| Scripted Light / Deep calls | 1 / 1 |
| Materialized pending candidates | 1 |
| Local source-equality verification / registered verification receipt | 1 / 1 |
| Local snapshot evaluation / checks / registered evaluation receipt | 1 / 4 / 1 |
| Normal atomic adoption | 1 |
| Eligible memories in retrieval | 1 |
| Paired tasks / scripted task calls / separate evaluator calls | 2 / 4 / 4 |

Deep emits an unverified candidate with its generated claim. A separate trusted
fixture preparer checks exact equality to captured source text, unchanged evidence
binding, the generated claim and the candidate snapshot. It registers receipts
through the normal verifier/evaluator APIs; providers never issue them. The normal
atomic writer rechecks parent, policy, evidence and receipt hashes before adoption.
This local fixture check is distinct from independent scientific verification.

Comparison freezes the adopted snapshot, policy and exact context. A contains both
independently selected raw events, including the event not cited by the memory;
B contains the identical whole raw prefix plus the one adopted memory. Both pairs
must have distinct request bytes and no dropped records. Task order is AB then BA,
with equal per-arm limits and no reply-history sharing. `comparison.frozen_context`,
the frozen membership lists, report and audit expose context/plan hashes, packed
request hashes and per-arm membership/status for inspection.

Sleep is bounded to 2 calls, 32,768 cumulative input bytes, 4,096 reserved output
bytes, 2,048 output bytes per stage and 2 candidates. Each comparison arm has
2 calls, 16,384 request bytes per call and 128 reply bytes per call. Retrieval is
bounded to 16,384 bytes and 1 memory; raw selection scans at most 2 events and
selects at most 2. The report records actual sleep stages/calls and input/output
bytes, plus comparison calls/input bytes and evaluator calls. Byte bounds are not
token or monetary caps.

The evaluator-only answer mapping is separate from sleep evidence, tasks, caller
config and provider requests. Both arms receive the same fixed scripted reply;
exact-match scores test wiring rather than semantic memory use. Reported costs
retain synthetic-zero or unavailable labels, with no measured savings. REM,
diary, real-agent delivery/use, live-model verification, independent holdout and
performance improvement are outside this demo.

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

## Offline comparison preparation

```sh
agent-sleep-lab compare-prepare --store-config private/store.json --manifest private/comparison.json --journal private/comparison.sqlite --model xiaomi/mimo-v2.6-pro
```

This explicit offline operation freezes and inspects the existing independent-raw
A/B plan before constructing any provider. `--model` is required and accepts only
`xiaomi/mimo-v2.6-pro` or `fake-model-1`; it binds a label, without paid execution.
There are no agent, provider, live, dispatch, rubric-key or execution options.

Use the **same private manifest and separate journal as `compare`**, described
below: `plan_id`, 1–5 unique `{task_id,prompt}` tasks, `retrieval`,
`evaluator_identity`, and optional `budget`/`config` with the existing defaults.
Unknown contract fields, duplicate JSON keys, invalid budgets and database aliases
(including hardlinks) are refused. Manifest/store-config files are bounded to
1 MiB; retrieval `max_bytes` is at most 1 MiB, `scan_limit` at most 1,024 and
`max_raw` at most 64. Existing retrieval/packing caps still apply. Caller `config`
is opaque metadata, not operating policy or execution options.

The adoption store is opened with `read_only=True` / SQLite query-only controls.
Only the separate existing `ComparisonStore` journal is written: frozen context,
plan and evaluation contact; no verification/adoption receipts or arm dispatches
are created. The journal contains private frozen source/request text: keep it
outside public artifacts. Identical reopens preserve plan bytes and execution
states. Changed bindings, stale current context, absent eligible memory and
identical A/B requests fail closed. Unknown intent remains unknown, without
resend or status changes.

The bounded JSON output contains plan/config/taskset/context/policy/snapshot and
evaluator hashes, model, identical per-arm caps, AB/BA order, request hash/length/
status, existing membership-hash audit and current validity. It omits source,
prompt, query, reply and answer-key text. Each B must include consolidated memory
after the same complete raw prefix as A. **Five tasks fix all ten planned arm
slots** (five per arm); missing, failed or unknown outcomes never shrink this
denominator. Reply bytes are checked **after generation**, not token or monetary
caps. Usage/cost measurements remain unavailable, including MiMo; no zero-cost,
performance or completed-acceptance claim follows.

The additive `input_volume` field makes planned input growth explicit:

- `pairs` is ordered by zero-based `task_index`, not AB/BA dispatch position.
  Each pair reports `a_request_bytes`, `b_request_bytes`, `delta_bytes` (B−A)
  and `delta_percent` (100 × (B−A) / A).
- `totals` sums A and B separately, adds `combined_request_bytes` (A+B),
  and calculates the difference and percentage from those totals, **not the mean
  of pair percentages**. Percentages round half-up to two decimal places;
  exact integer byte counts are authoritative.
- `task_pairs` and `total_arms` include every planned slot, regardless of
  execution status. This measures one planned traversal, not actual sends,
  retries or whole-pipeline consumption. Arm identities and positive integer
  lengths must form exactly one A and one B for each frozen task.
- `basis: "planned_serialized_utf8_json_request_bytes"` means the length of
  the exact hash-checked serialized request. The existing packer uses ASCII
  Unicode escapes (`ensure_ascii=True`); its output is also valid UTF-8.
  These are not original text/file sizes, provider/system-wrapper bytes, actual
  transmitted bytes, tokens or money. Extra input is not evidence of equal-context
  fairness, quality improvement or savings.

Preparation reads only evaluator identity and its protocol hash, never an answer
key. Later, the existing explicit `compare --provider script` (for `fake-model-1`)
or `--provider mimo --agent ...` route can consume the same manifest/journal with
a separate `--rubric` matching that hash. Model/budget/task bindings must match.
Current validity is a read-time observation, not dispatch authorization or an
atomic cross-database guarantee. Account/approval binding, target-host restrictions,
real responses, total measured costs and independent acceptance remain unresolved;
preparation does not resolve or bypass them.

## Read-only saved comparison inspection

```sh
agent-sleep-lab compare-inspect --store-config private/store.json --journal private/comparison.sqlite --plan-id my-comparison
```

Use this after preparation, interruption or execution to inspect an **existing**
independent-raw plan with 1–5 pairs. Unlike `compare-prepare`, it never creates a
plan or evaluation contact. Unlike `compare` and its report method, it never
runs/retries a provider, evaluates a reply or persists invalidation/recovery.
Only `--store-config`, `--journal` and `--plan-id` are accepted; no manifest,
rubric, provider, model or execution options are needed or accepted.

Both databases open in SQLite read-only/query-only mode. Missing, empty, foreign,
aliased (including hardlinked), corrupt or unsupported journals fail without
initialization/migration. Saved context, plan and request hashes/membership are
checked. The journal is read within one transaction. Evidence-store eligibility
is a separate current observation, not an atomic cross-database guarantee.
Normal SQLite read locks and WAL/SHM sidecars may still be required.

JSON preserves the saved `status` even when context has expired, been revoked or
changed; `current_validity.valid:false` reports that mismatch without rewriting
the journal. This read-time flag is not dispatch authorization, origin
authentication or completed acceptance. Invalid integrity fails with exit 2 and
a fixed diagnostic; an inspected partial/stale plan exits 0, **not** a run-success
verdict. An already-invalidated plan stays invalidated even if current context
matches again.

- `outcomes.A/B` keeps the full planned denominator and counts
  `planned_not_dispatched`, `dispatch_intent_outcome_unknown`, `replied`,
  `completed`, `timeout`, `missing` and `invalid` separately. Unknown intent
  never becomes a failure or permission to resend. A reply is not a scored outcome.
- `arms` gives task index, arm, dispatch position, request hash/bytes, saved status,
  known-outcome flag and existing 0/1 score (null until completed).
  `evaluator_pass` counts saved passes; `all_outcomes_scored` is true only when
  every planned slot is completed. Scores remain synthetic exact-match rubric
  results, even for a real-model response; these are not verified model receipts.
- `input_volume` uses the same planned serialized-byte definition and all-slot
  denominator as preparation, regardless of completion.
- No prompt, query, original evidence/memory, reply, free-text reason or raw
  provider receipt is returned. Keep identifiers and hashes private as appropriate;
  the output is not an automatic publication allowlist.
- Usage and measured cost remain unavailable (not zero); `comparison` and
  `performance_claim` remain null. No adoption or live-acceptance claim is issued.

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
