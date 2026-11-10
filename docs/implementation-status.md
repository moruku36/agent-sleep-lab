# Implementation status

**English** | [日本語](implementation-status.ja.md) | [Home](../README.md)

## Current assessment — 2026-11-11

**Provisional initial-version completion: 30–35%. The former 50% estimate is withdrawn.**
100% means capture → adoption → retrieval → Light/Deep → comparison evaluation →
one existing-agent integration. REM, diary and wider rollout are excluded.
File/test counts and prepared interfaces do not increase this estimate.
This page and its Japanese translation are the ONLY current status authority;
dated gate reports are historical evidence.

## Verified merged baseline

[PR #23](https://github.com/moruku36/agent-sleep-lab/pull/23) is **MERGED** at
`025e32314efd246dd5b04b3476fa5b2865287a3c`; source
`087f2a3da8e4188a70a7a84d50d1a8d4eb14e1dc`.
The owner merged it on 2026-11-10. Read-only GitHub queries verified the merge
and successful [main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42798899032).
[PR CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42796639749)
passed all 241 unique cases on each of Python 3.11 and 3.13 (482 case
executions / two matrix invocations), 339 relative file links and wheel build.
No paid API calls occur in CI.

[PR #24](https://github.com/moruku36/agent-sleep-lab/pull/24) is also **MERGED** at
`2117e96fcad631f69422541b6a6dbad9c6c025ed`, source
`ab05819d253d15ed7e3dc733f52efd4b034df604`. The owner completed the merge after
the dedicated merge tool stopped. Both checks in
[PR CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42801027617)
and the [main workflow](https://github.com/moruku36/agent-sleep-lab/actions/runs/42801229632)
succeeded. This adds the synthetic collect-only bridge, not a deployed agent.

[PR #25](https://github.com/moruku36/agent-sleep-lab/pull/25) is **MERGED** at
`ccb06aa4bdb1defef8fc8564e818522b650fd59a`, source
`9387f1fef1565f3edcf94740e22d97f7187ac41f`; GitHub reports the merge at
2026-11-10T10:54:59Z. Its reference dispatch journal is part of this baseline.

Merged foundation: synthetic evidence/provenance, policy and receipt libraries,
transactional adoption, scoped retrieval, rollback/logical forgetting; body-bound
v2 Light/Deep proposals and generated candidate claims; explicit runtime CLI;
MiMo adapter, durable checkpoints, identical A/B rejection, diagnostic
non-comparability, manual handoff and stopped-worker recovery.
Generated candidates are not independently verified or adopted automatically.
This is not production authentication, physical purge or a deployed agent connection.

[PR #26](https://github.com/moruku36/agent-sleep-lab/pull/26) is **MERGED** at
`9a36ee6dca4569ea2fe1d32dd42969ea9a62c6c3`, source
`37439d00d95a4f74d5225a3dc2aab27fdf3c658c`. A GitHub read confirmed the merge at
2026-11-10T15:34:08Z; its CI result is not recorded here. It merged the partial offline worker as a
preserved draft, not a working integration checker.

## Current development branch

`feat/oss-offline-worker-contract`, based on the PR #26 merge above.
The worker is still an **incomplete draft**, not an operational integration checker.

- Hardened input validation in the partial
  [offline worker](../src/agent_sleep_lab/oss_offline_worker.py): exact payload keys,
  bounded lowercase hex, per-field byte caps, strict JSON (duplicate keys, non-finite
  numbers, BOM and invalid UTF-8 rejected), the exact synthetic experience
  reference-bundle key set with record-count and snapshot checks, and built-in
  synthetic task bytes only.
- Loading rechecks source hashes immediately before compiling, uses the reviewed
  order instead of mapping order, compiles every source before executing any,
  refuses a process where those module names already exist, and no longer leaks the
  worker's `__future__` flags into pinned code.
- Added **21 passing [contract tests](../tests/test_oss_offline_worker.py)** for
  validation and loader unit behavior using test-authored stand-in sources;
  they never run target code.
- Three levels remain distinct: **syntax/import and unit behavior** pass the
  regression below; **actual target integration** (`run()`, guards, pinned target
  sources) remains unexecuted and unverified.
- The parent checker, target checkout/commit verification, bridge/journal wiring
  and end-to-end run are NOT implemented. The embedded source pins have not been
  independently verified. The bundle key set is a local copy of the retrieval
  contract with no drift test; canonical bundle bytes and store origin are not
  checked. Do not use this draft on real data.
- Guard code is not a sandbox for hostile Python; it has not passed boundary tests.
  Reference bytes are assigned to target notes, which triage with `llm=None` does
  not use semantically. No memory benefit or deployed connection is demonstrated.
- This revision was written in Claude Code. The coordinator received a successful
  terminal result (`is_error=false`, `terminal_reason=completed`) naming canonical
  model `claude-fable-5-2` (Fable 5.2), provider `firstParty`, with no permission
  denials or subagents. No fallback model was used. The earlier PR #26 attempt
  requested Codex CLI `gpt-6.1-sol` / `xhigh` and timed out without a model receipt.

Already merged in PR #25:

- The [reference dispatch journal](reference-use.md) freezes bounded task/reference
  bytes and identities, records durable intent before dispatch, uses CAS, refuses
  retry of unknown outcomes and rechecks context before/after dispatch.
- Returned output is hash-bound, but consumer receipts remain unreviewed;
  `delivery_and_use_verified` is always false. Accounting is not semantic-use proof.

Already merged in PR #24:

- Added an opt-in [OSS Contributor collect-only bridge](oss-bridge.md) for the
  existing agent's `TriageDecision` dictionary contract.
- Capture preserves decisions and any model rationale as untrusted observations,
  not verified issue facts. It creates no memory, verifier/evaluator receipt or
  adoption. Pending and failure states stay observations.
- Read-only context uses current-policy adopted-memory retrieval with fixed scope,
  byte limits and exclusions. No target ledger, scoring, configuration, scheduler,
  patch/PR path or production host is changed.
- This is **synthetic offline wiring**, not real-data ingestion or proof of
  delivery/use by the existing agent. Real operational capture needs a separate
  non-synthetic retention/authorization contract; do not relabel real logs.

## Current branch verification

- **276 unique cases / one full local invocation, all passed in 13.446 s**,
  with the existing Python 3.13.18 verification environment. This includes
  21 new worker unit/contract cases. No installs or paid harness inference.
- Documentation: **364 relative file links / 76 Markdown files passed**;
  anchors and remote URLs are not checked. Feature CI is not run.
- Historical, from the PR #26 branch before these edits: 255 unique existing
  regression cases / one invocation passed in 13.415 s on Python 3.13.18, and
  362 relative file links / 76 Markdown files passed. Those runs did not exercise
  the worker and are not verification of this branch.
- Worker input validation and stand-in loader behavior are verified only at the
  unit level. Actual `run()`, guards, target-source execution and end-to-end
  integration remain unverified.
- PR #25's earlier local result (255 cases, 13.588 s) and PR #24's result
  (247 cases, 12.183 s) are historical, not executions in this trial.
- Actual five-task A/B and live-model performance improvement remain unverified.

## Genuine remaining work

1. Resolve the MiMo execution approval/binding failure and obtain a real
   provider/model receipt. The owner approved the saved review command, but the
   unchanged native `ask=always` submission was again denied before execution:
   approval could not safely bind. No alternate route or model was attempted.
   An earlier design request timed out without receipt; its usage/cost is unknown.
2. Run the prepared five-task real-response comparison with applicable caller
   budget, independently accepted experience memories and a frozen evaluator.
   [Fictional development tasks](../examples/paper-pilot/README.md) are preparation,
   not an independent holdout. Exact-match fixture scoring is not scientific
   paper-quality proof.
3. Connect ONE existing agent and verify actual capture/retrieval use. Offline
   bridge contracts and manual handoff drafts are preparation only. Real-data
   boundaries and actual delivery/use verification remain open. The new local
   dispatch journal supplies accounting only, not authenticated use evidence.
4. Relevant raw ranking, physical purge and broader production fault acceptance
   remain open; none is established by passing offline tests.

Runtime contracts and commands: [English](runtime-guide.md) / [日本語](runtime-guide.ja.md).
The MiMo CLI lacks per-call max-token control: post-generation byte rejection
is NOT a hard token or monetary limit; unknown outcomes may have incurred cost.
