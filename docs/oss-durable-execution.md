# Durable OSS prompt execution

[Current status](implementation-status.md) | [日本語の状況](implementation-status.ja.md)

## Separate driver

[ExecutionJournal](../src/agent_sleep_lab/oss_execution_journal.py) connects the
[exact-prompt adapter](oss-exact-prompt-adapter.md) to durable paired execution.
The old [fake-only journal](../src/agent_sleep_lab/oss_paired_outcome.py), its
provider restriction, labels and schema are unchanged.

Create a new private journal with an absolute path and `initialize=True`.
Reopening an existing journal does not require that flag. Existing databases are
inspected read-only first; application ID, version and exact schema must match.
Unrecognized files are refused without a write. This is a controlled local
path, not authentication of a database or a filesystem sandbox.

`register(plan_id, adapter=..., live_transport=False, **capture_options)` reuses
the capture/summary/reference/bridge validation and bounds of
`oss_paired_outcome.build_binding`. It freezes the full validated capture plus
adapter version, registered agent, requested model, actual transport provenance,
live selection and limits. Reusing an ID with a different binding is refused.
Synthetic **task/source fixtures** and injected **execution transport** labels
are kept separate; injected tests are never reported as a live model run.

The selected adapter's input-byte bound must cover the journal's input bound.
Both adapter construction opt-ins remain required. A CLI-backed adapter additionally
requires `live_transport=True` at registration and execution. These are caller
choices, **not owner approval or spending authorization**; existing external
controls still apply. CI and the regression suite use only injected transports.

## Execution and recovery

`run(plan_id, bridge, adapter, live_transport=False, limit=1 or 2)`:

1. Verify frozen binding, bridge and selected adapter identity/limits.
2. Inspect saved bodies and receipts for integrity. Recover any unclosed intent
   as an unknown outcome and permanently stop the plan, even with a fresh adapter.
3. Check current reference context (ignoring only retrieval read time) before
   every pending arm; failure/unavailability permanently prevents further calls.
4. Commit one unique arm intent in a short immediate SQLite transaction.
5. Release the transaction, then make one adapter call. Never hold a DB lock
   across model transport; never automatically retry an exception or invalid reply.
6. Verify reply/allowlisted receipt bindings, then recheck current context.
   If revoked, store hash/length/status only. Otherwise commit reply and sanitized
   receipt with their hashes before the next arm can start.

`report(plan_id, bridge)` rechecks context and integrity without making calls.
Previously completed bodies **and receipt details** are withheld when context
has changed or is unavailable. Saved bodies remain in private SQLite: withholding
is not physical erasure. Interrupted intents are reported stopped immediately;
`run` persists the recovery transition. Complete plans replay without dispatch.

An insufficient remaining adapter-instance budget is rejected before any intent.
A fresh instance may continue only an arm that has never had an intent.
Replacing an adapter must never retry an interrupted or terminal arm.

## Limits and non-claims

- One driver per plan is assumed. Unique intent reservation prevents duplicate
  calls; overlapping drivers conservatively halt the plan and may discard a reply.
  This is not distributed coordination or a lease/recovery service.
- Full-sync SQLite transactions protect journal transitions. Current reference
  retrieval and journal writes are **not a cross-store atomic transaction**.
- Source/worker/store labels are caller-controlled, not authenticated authority.
- Usage/cost remain unavailable; byte bounds are not generation-token or monetary
  caps. Subprocess output is buffered before post-output validation.
- Execution replies remain raw text, not evaluator/adoption authority. Optional
  [strict verdict parsing and frozen fixture scoring](oss-verdict-evaluation.md)
  now attach a separate report-time result to predeclared manifests; plans without
  one remain unscored. Synthetic scoring is not live effect evidence.
  No live inference, paid effect evaluation, CLI command, default-model change,
  new credentials, schedules or merge occurs in these tests.

[Eight regression cases](../tests/test_oss_execution_journal.py) cover restart/
replay, interruption, revocation before/after reply, foreign DB refusal, frozen
bindings and receipt corruption, oversized output/concurrent drivers and opt-in/
instance-budget boundaries. All capture/adoption and process results are
test-authored stand-ins. A live model/evaluator remains unverified.
