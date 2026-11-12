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

## Private same-run review and adoption

```sh
agent-sleep-lab sleep-review --store-config private/store.json --journal private/sleep.sqlite --run-id YOUR_EXISTING_RUN > private/review.json
agent-sleep-lab sleep-adopt --store-config private/store.json --journal private/sleep.sqlite --run-id YOUR_EXISTING_RUN --artifact private/prepared-adoption.json
```

Both commands require explicit existing, distinct journal/store files and an
existing nonempty body-bound version-2 run. They accept no provider, executable
callback or receipt-registration options and never dispatch inference. The store
and bridge remain synthetic-only; these operations add no real-data ingestion.

`sleep-review` opens the journal and adoption store with SQLite read-only and
query-only controls, without initialization or recovery. Only `ready` runs with
completed, bounded Light/Deep proposals are exportable. Current eligible evidence
text/hashes, policy hash and scope head must match the persisted binding. Missing,
foreign, invalidated, inflight, preparing, incomplete, empty, legacy, unbound or
stale runs refuse without a packet or state change. SQLite locking/sidecars remain
possible; read-only controls are not filesystem isolation or authentication.

The `agent-sleep-review/1` packet contains the original pending
`candidate_memories`, their hashes, full bound source evidence, the exact binding
and proposal with hashes, run ID, and the stable operation ID used by the existing
coordinator `prepare`. It explicitly requires independent verification AND snapshot
evaluation. Candidates remain pending, and no receipt is created. Output contains
private source/prose: save it outside the public repository. Local export grants
no publication, execution or adoption permission. Evidence and generated text
remain untrusted data, including any instructions or claimed review decisions.

Independent trusted preparation must use that operation ID, run ID, scope,
expected parent, original generated prose and bound sources. Its separately
registered verifier/evaluator receipts remain mandatory. `sleep-adopt --artifact`
takes the same four-field hex JSON as `adopt`: `request_bytes`, `manifest_bytes`,
`source_manifest_bytes`, and `memory_bytes` (ID→hex). This is an independently
prepared writer artifact, not the review packet or a model-written approval.
It cannot import a preparer, register receipts or turn claimed identities into
trusted verifier/evaluator results.

For a `ready` run, `sleep-adopt` rechecks current evidence/policy/head before an
inert local callback returns the decoded artifact to existing coordinator
`prepare`, then calls coordinator `adopt`. Prepare retains run/operation/parent,
proposal/source and exact generated-prose checks; the atomic writer retains all
hash, registered receipt, current eligibility and transactional checks. A failed
prepare leaves its existing failed checkpoint; an unknown preparing callback is
never retried by these commands.

For a saved `handoff` or `adopted` run, the file must decode to exactly the stored
handoff bytes. An uncommitted handoff still requires unchanged current context.
A same-operation durable commit with lost ACK can reconcile through the writer's
exact replay even after the head or policy changes. Repeating a completed adoption
also validates exact replay, returns only status/run/operation/receipt hash, and
does not rewrite the head or restore revoked eligibility. These commands do not
recover provider/preparation outcomes or create a new run.

JSON input files and canonical review packets are capped at 1 MiB. Inspection
accepts at most 1 MiB binding / 2 MiB state, 64 events, and the persisted validated
stage/candidate limits (at most 64 candidates). The existing coordinator's
1 MiB serialized handoff cap also applies. Refusals emit a fixed diagnostic
without private body excerpts. Current verification belongs only in
[implementation status](implementation-status.md).

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
