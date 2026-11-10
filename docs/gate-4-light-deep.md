# Gate 4A: manual offline Light/Deep slice

> Historical gate specification. [日本語要約](gate-4-light-deep.ja.md). Current capabilities, merge state and verification evidence live only in [implementation status](implementation-status.md); old test limits and pre-merge labels below are dated history, not current instructions.

## Gate 4A acceptance — 2026-11-10

[PR #17](https://github.com/moruku36/agent-sleep-lab/pull/17) remains unmerged.
Head `a5d64acb294186c840fee7222be5f000661940e2`;
[CI42772057834](https://github.com/moruku36/agent-sleep-lab/actions/runs/42772057834)
passed **5 new cases / 1 invocation, 0.197 s**, plus wheel build, Ubuntu / Python 3.13.18.
Local execution: zero. This trial totals 5 case executions / 1 invocation.
Documentation-only follow-up does not trigger duplicate CI.
The accepted synthetic capture→Light→Deep→independent receipts→adoption→retrieval
slice justifies an overall initial-version estimate of **35–40%**.
Production integration, comparison evaluation and broader fault acceptance remain incomplete.


Status: implemented on the feature branch; **five focused CI cases passed**.
Overall initial-version estimate remains **35–40% after focused acceptance**.
This is a synthetic library, not a live sleep agent or performance result.

## Public API and boundaries

`SleepCoordinator` uses its own private SQLite database (do not pass the
evidence-store path). `bind` registers a local run label against exact scope,
ordered event ID/hash references, parent hash, configuration and limits. It
rejects a changed binding without mutating the existing run. This local registry
is neither authentication nor integration of capture authorization with use policy.
Call bind with the intended inputs on reopening; inspect alone does not authenticate
an input. Callers own configuration, file permissions and trusted callbacks.

`advance` executes one stage, only with the included `FakeProvider`.
Light selects bounded input IDs. Deep proposes explicit add operations referring
only to Light-selected evidence. The first slice does not generate arbitrary memory
claims or implement supersede/mark_stale/reject/defer. Provider claims of verification,
receipts, policy or operation identity are forbidden fields. FakeProvider is an
offline test seam, not a sandbox for arbitrary Python subclasses.

A locally configured `trusted_preparer(operation_id, run_id, binding, proposal)`
builds memory bytes, source and operation manifests, the candidate and independent
verification/evaluation receipts through existing interfaces. This is privileged
host code, never generated code or a provider callback. It returns exact writer
kwargs; the coordinator checks run/scope/parent, proposed operations and evidence
event hashes before persisting the handoff. Full source/provenance hashes, current
policy, receipt acceptance and parent CAS remain enforced by AdoptionStore.
The synthetic acceptance fixture uses the existing trusted test verifier/evaluator;
its passed fixture receipt is NOT an A/B performance result.

`adopt` first resolves the immutable operation ID, then uses the existing writer's
exact-replay validation. Even a resolved ID is not enough to skip exact request-byte
checks. The full payload is persisted before the first write; after lost ACK it
is reused, never reconstructed. Current-policy retrieval remains a separate read.

## Lifecycle and accounting

`light → deep → ready → preparing → handoff → adopted`

- Run binding and checkpoints are durable SQLite writes, with FULL synchronous mode.
- Every provider call is preceded by a committed CAS reservation. Calls, serialized
  input bytes, reserved output bytes and actual returned output bytes are recorded.
  Reservations are conservative and never refunded. These are bytes, not tokens,
  currency or measurements of paid inference.
- A completed Light checkpoint is reused on reopen. Each advance has a state CAS;
  another caller cannot dispatch the same stage from that checkpoint.
- Budget shortage becomes `incomplete(provider_budget_exhausted)` before dispatch.
- Invalid/oversized/non-byte output becomes failed; a provider exception becomes
  incomplete with unknown outcome. Neither retries.
- An empty valid proposal becomes `no_change`: **no proposed writes**, not a claim
  that there was no useful knowledge or that an evaluation passed.
- Process death in an in-flight provider stage stays in-flight. After confirming
  the old worker stopped, the local caller may explicitly call
  `recover_stopped_provider` to mark unknown/incomplete; it never replays the call.
  There is no time-based lease or automatic recovery.
- Death during trusted preparation remains `preparing` and cannot replay preparation
  automatically. Manual receipt/artifact reconciliation is pending.
- Writer exceptions retain `handoff` for read-first reconciliation with the exact
  stored payload. A deterministic writer rejection is not labeled adopted.
- Runtime databases are private and are not publication artifacts. Existing logical
  forgetting does not physically purge this separate run database.

## Acceptance plan and remaining scope

Five explicitly named new cases in one PR-only CI invocation:
full fixture capture→Light→Deep→trusted verification/evaluation→adoption→retrieval
including lost-ACK reconciliation; completed-Light reopen; changed run binding;
budget stop; forged provider verification rejection. No local duplicate invocation
or default ten-case regression. Gate 3's historical 23 executions / 5 invocations
are a different exhausted trial and are not rerun or reset here.

Crash/process-kill, concurrency, no-change, malformed JSON, preparation interruption
and non-null parent scenarios have not received dedicated runtime acceptance in
this five-case selection. Historical tests remain, but are not claimed as current
coverage. This partial slice does not close broader fault acceptance, frozen retrieval,
delivered-memory logging, exclusion capacity/cleanup, physical purge, capture/use
policy integration, evaluation-contact logging, A/B comparison or one existing-agent
integration. REM, diary, live provider adapters and schedules are disabled/absent.
