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

[PR #27](https://github.com/moruku36/agent-sleep-lab/pull/27) is **MERGED** by the
owner at `93ddb1a070c6ffdee65cd0809eea5c8ae68203c5`, source
`442b7ea1b4f67c878d67599a42bde6864604810b`. GitHub confirmed the merge at
2026-11-10T15:50:40Z and PR CI success on Python 3.11 and 3.13. It merged worker input validation and loader
contract tests, not a working integration checker.

## Current development branch

`feat/oss-offline-parent-checker`, based on the PR #27 merge above.

- Added the stdlib [parent checker/consumer](../src/agent_sleep_lab/oss_offline_parent.py).
  Read-only, bounded git calls check the explicit repository root, local origin
  claim, pinned commit and all eleven source hashes. Source bytes come from Git
  objects, never mutable worktree files; the target checkout is not written.
- Only the built-in synthetic task and bounded canonical synthetic experience
  reference bytes are accepted. A fresh `python -I -B` worker runs once with
  temporary cwd, minimal environment, no shell, timeout and bounded I/O.
  The parent checks output protocol and source/task/reference/notes bindings.
- The journal-compatible consumer returns an unreviewed receipt; injected worker
  commands are explicitly labelled stand-ins. No output establishes verified
  delivery, semantic memory use, adoption or improvement.
- **Actual pinned-source offline execution has now passed once**, after coordinator
  review. The local repository contained commit
  `e40b39c6258ac5a4446c38246bdfd7f5dc5dbf7b`; all eleven Git blobs matched
  the embedded SHA-256 pins. The real collection/digest/temporary-ledger path
  produced five expected outcomes: candidate, low-score skip, pending LLM,
  duplicate skip and infrastructure error, with one decision still pending.
- The reference came from actual retrieval from an empty synthetic adoption store:
  zero records and no active snapshot. The five returned decisions were then
  captured through `CollectOnlyBridge` in that temporary synthetic store.
  No memory, adoption or verifier/evaluator receipt was created.
- This confirms pinned target code can run on synthetic inputs and its decisions
  can cross the capture contract; it does **not** demonstrate adopted-memory use.
  Reference bytes reach `Target.notes`, unused semantically with `llm=None`.
  The acceptance script/artifact are local coordinator evidence, not a portable
  regression or production deployment.
- Remaining: bridge/journal/consumer end-to-end orchestration, reconciling the
  journal's larger reference cap with the worker's 32,768-byte cap, bundle
  key-set drift coverage and store-origin binding in the general consumer,
  independent guard-boundary tests, nonempty eligible-memory use and real-data
  authorization. Guard code is not a sandbox for hostile Python. Local origin
  is mutable, not authenticated identity; hostile Git configuration is not tested.
- Claude Code completed this revision successfully: coordinator terminal receipt
  reports `is_error=false`, `terminal_reason=completed`, canonical model
  `claude-fable-5-2`, provider `firstParty`, no permission denials or subagents.
  No fallback model was used. The coordinator read both READMEs and the architecture/
  evaluation design before implementation; the coding worker did not read all four.
- PR #27's strict input/loader contracts remain part of the merged baseline,
  with 21 stand-in unit cases. They are distinct from this branch's real offline
  acceptance and ten new parent contract cases.

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

- **286 unique regression cases / one full local invocation passed in 14.081 s**
  on Python 3.13.18, including ten new parent-checker cases and the prior 21
  worker cases. New regressions use stand-in sources/git responses/processes;
  they do not require the target checkout or make network/model calls.
- Separate local acceptance: one real pinned-worker invocation, five synthetic
  decisions captured, zero adopted memories and zero verifier/evaluator receipts.
  Worker output SHA-256:
  `fb0503a72112677b5610a5471f378578539d1dc43c4906704c94ca51ef8266af`.
  This was not counted as a regression case or repeated during regression.
- Documentation: **362 relative file links / 76 Markdown files passed**;
  anchors and remote URLs are not checked. Whitespace diff check passed.
  Feature CI not run.
- Historical PR #27 local verification: 276 cases / one invocation in 13.446 s,
  364 relative links / 76 Markdown files. PR #26: 255 cases / one invocation
  in 13.415 s, 362 relative links / 76 Markdown files. These are historical,
  not executions in this trial.
- Guard boundary denial behavior, journal end-to-end dispatch, real-data use,
  five-task real A/B and live-model performance improvement remain unverified.

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
