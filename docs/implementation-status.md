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

[PR #28](https://github.com/moruku36/agent-sleep-lab/pull/28) is **MERGED** at
`709e7642be3de65f83abd76e5337357829450aa5`, source
`6a3bba2c53158053583ff86dab56da87c4a60027`. GitHub confirmed the merge at
2026-11-10T16:07:42Z and PR CI success on Python 3.11 and 3.13.
It merged the bounded parent checker and ten stand-in contract cases. A separate
local acceptance ran the pinned target code once with an empty synthetic reference
and captured five synthetic outcomes; it did not exercise the dispatch journal.

[PR #29](https://github.com/moruku36/agent-sleep-lab/pull/29) is **MERGED** at
`85300ee064b6a9621119c5748f6c8267e240d030`, source
`9a7e3b8f25268d81503aa8bba91f5feb29d5647c`. GitHub confirmed the merge at
2026-11-10T17:54:44Z; PR CI passed on Python 3.11 and 3.13.

[PR #30](https://github.com/moruku36/agent-sleep-lab/pull/30) is **MERGED** at
`9f281875925dd66a90b09c07af1562e3cdae3beb`, source
`9d0cbb69dae3943becdbf7d886b4df488cb600dd`. GitHub confirmed the merge at
2026-11-10T18:11:11Z; both PR checks and
[main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42872601554)
passed. It merged six selected guard acceptance cases and accurate limitation
documentation, not guard behavior hardening.

## Current development branch

`feat/oss-paired-outcome-journal`, based on owner-merged
[PR #32](https://github.com/moruku36/agent-sleep-lab/pull/32) at
`46a1e585e580275aef003c72bc74f08c9be09b52` (source
`96ba94bb25d71089a5f6abdd8cd14926e42ddb97`). GitHub confirmed MERGED and
successful Python 3.11 / 3.13 PR CI checks.

- Added a separate [paired-outcome journal](../src/agent_sleep_lab/oss_paired_outcome.py)
  consuming actual captured OSS request artifacts, not replacement task prompts.
  Registration validates the capture, source/task/reference hashes, current-policy
  context and caller-supplied worker labels, then freezes both exact requests,
  original reference bytes, retrieval/bridge identity and equal per-arm byte bounds.
  Artifacts and caller-controlled store/summary labels are not authenticated authority.
- Each arm commits intent before one fake dispatch and commits its reply before
  the next arm. Close/reopen can continue an unstarted second arm; saved replies
  replay without redispatch. Unknown outcomes permanently stop the plan.
  A changed/unavailable context prevents remaining dispatches; context is rechecked
  after replies and on report, withholding stale reply bodies.
- Private SQLite journal has a separate application ID/schema, explicit full-sync
  settings, foreign-database refusal and saved-reply integrity checks.
  This assumes one driver per plan and is not a cross-store atomic transaction.
- **Fake-only execution:** only an explicitly supplied local fixture provider is
  supported. Replies are synthetic bytes, not parsed target verdicts or real model
  receipts. Usage/cost stay unavailable; byte caps are not generation-token or
  monetary caps. No live provider, CLI or evaluator was added.
- [Eight new regression cases](../tests/test_oss_paired_outcome.py) cover byte-exact
  Unicode request binding/provenance, durable continuation/replay, unknown outcomes,
  policy revocation before/after replies, malformed bindings/size bounds,
  unavailable context, database identity/durability and reply corruption.
  All **317 unique local cases passed in one invocation** (17.497 s, Python 3.13).
- Separate acceptance captured a nonempty Japanese reference through the actual
  pinned OSS judge/prompt, then passed those exact request bytes to the fake journal.
  One arm completed, the journal closed/reopened, the other completed; a third run
  replayed both, with two total fake calls. Current exclusion withheld both saved
  reply bodies. Preparation/fake execution wrote nothing to the adoption store.
  External provider calls, model verdicts and live usage/cost measurements: zero.
  Store adoption/verifier/evaluator data were explicitly test-authored fixtures.
- Worker provenance: explicitly requested `claude-fable-5-2`, but the invocation
  timed out at 300 s after saving the module and six cases. No normal-completion
  or resolved-model receipt was returned; no worker retry/substitution. Coordinator
  reviewed and hardened saved code, added two regression cases and verified it.
- Remaining: bounded live-provider wiring with current-context checks, real model
  identity/usage receipts, target verdict parsing, a frozen independent evaluator,
  paired cost accounting and effect measurement. This is offline execution plumbing,
  not semantic-memory-use or performance evidence. Known guard gaps remain open.

## Merged PR #32 adopted-reference preparation

Historical branch `feat/oss-adopted-reference-preparation`, based on merged PR #31.
**Locally verified:** all 309 unique regression cases passed in one invocation
(Python 3.13, 15.290 s). PR CI is reported separately. No paid/live evaluation inference.

- Reference canonical validation now requires retrieval's own byte form
  (sorted keys, compact, unescaped UTF-8) through one stdlib helper,
  `canonical_reference()`, in the
  [prompt-capture worker](../src/agent_sleep_lab/oss_prompt_capture_worker.py)
  and the shared [parent payload builder](../src/agent_sleep_lab/oss_offline_parent.py).
  ASCII-only bundles are byte-identical to before. Escaped, re-spaced, BOM,
  duplicate-key, invalid UTF-8, lone-surrogate and oversized bytes are refused.
  The prompt framing boundary additionally refuses data frame markers. Strict JSON, the 32,768-byte / 256-record caps and the
  exact reference SHA-256 are unchanged; worker protocol OUTPUT stays canonical ASCII.
- [Three new integration cases](../tests/test_oss_adopted_reference.py) use a
  temporary adoption store whose verifier/evaluator receipts and adoptions are
  **test-authored fixtures**, plus a labelled stand-in worker. They cover a
  nonempty eligible Unicode reference framed byte-exact in the reference arm
  only, A/B comparability, current-policy exclusion, mismatched scope, no store
  mutation during preparation and fail-closed malformed/non-canonical bytes.
- Not claimed: store-origin authentication, semantic memory use, a model
  verdict or any performance result. `OfflinePipeline` still requires the
  ASCII-canonical subset. Known filesystem guard gaps remain open.
- Actual pinned-source acceptance passed with one Japanese synthetic memory from
  a temporary adoption store (test-authored adoption and verifier/evaluator fixtures).
  The exact claim appears only in the reference prompt: 3,079 UTF-8 bytes vs 962
  baseline bytes. A second fresh worker after policy exclusion retrieved zero records
  and omitted the claim. Each worker called the real pinned judge/prompt twice;
  preparation performed zero store writes, provider calls, responses or verdicts.
- Worker provenance: normal completion receipt confirms `claude-fable-5-2`
  (`terminal_reason=completed`, `is_error=false`); no fallback. Coordinator reviewed
  the saved changes, corrected one test boundary assumption and ran verification.
- Remaining: bounded explicit live-provider executor and real provider/model receipts;
  durable paired outcome/cost accounting and frozen evaluator.

## Merged PR #31 prompt contract

Historical development branch `feat/oss-reference-prompt-contract`, based on
PR #30 and merged in PR #31 (merge `c8b6ccc`, source `c61cbb1`).
GitHub confirmed MERGED and both Python 3.11 / 3.13 PR CI checks succeeded.
Owner priority is implementing memory-use and comparable execution before
measurement. **No paid or live measurement has been run.**

- Added a separate [prompt-capture parent](../src/agent_sleep_lab/oss_prompt_capture.py)
  and [stdlib worker](../src/agent_sleep_lab/oss_prompt_capture_worker.py); old
  worker/pipeline protocols stay unchanged. Existing preflight freezes the same
  eleven reviewed blobs, then a fresh guarded process drives the real pinned
  `OpenAITriager.judge → triage_prompt` path for the built-in borderline issue.
- Both arms share the issue, actual default score/reasons, mock model and request
  settings. Baseline has no project notes; reference arm inserts one explicit
  untrusted-data frame containing the exact bounded reference bundle.
  Parent recomputes request/prompt hashes and verifies that the two prompts differ
  by only that contiguous insertion, with equal non-prompt request fields.
- An injected local transport captures the requests and raises the pinned
  `LLMTriageError`. It never sends a request, returns a response or fabricates
  a verdict. Endpoint/model/credential are explicit inert fixture labels;
  environment credentials are not consulted and header values are not exported.
- `prepare_from_bridge()` obtains an existing explicit bridge's scoped reference
  under current policy, with worker byte/record caps and pinned repository/commit.
  Store origin stays caller-controlled/unauthenticated. Artifact preparation is not
  dispatch authorization; a later executor must revalidate current context.
- **Actual pinned-source acceptance passed once**: issue #3, actual score 0.5,
  two calls each to the pinned judge/prompt function, two captured requests,
  zero provider calls/responses/verdicts, zero adoptions/verifier/evaluator receipts.
  Reference came from an empty temporary synthetic store (zero records).
  Baseline prompt was 962 UTF-8 bytes and reference prompt 1,960 bytes.
  This verifies reference-data placement in an actual request path, not semantic
  use of an adopted memory. The full collection pipeline remains unchanged.
- [Five new contract cases](../tests/test_oss_prompt_capture.py) use stand-ins
  and cover exact framing, binding/label rejection, A/B equivalence, the no-response
  transport and preflight/stand-in labels. They are not real-model evaluations.
- Worker provenance: explicitly requested `claude-fable-5-2`, but the invocation
  timed out at 300 seconds after saving two modules. No successful completion or
  resolved-model receipt was returned; do not claim a successful Fable run.
  Read-only process reconciliation found only an unrelated Claude process over a
  day old. No worker retry/substitution was started. Coordinator reviewed the
  saved modules, wrote/verified tests and actual acceptance, and updated status.
- Remaining: nonempty independently eligible memory integration; bounded explicit
  live-provider executor and real provider/model receipts; durable paired outcome/
  cost accounting and frozen evaluator. At PR #31 the capture path accepted only
  the ASCII-canonical bundle subset (addressed and locally verified on the current branch).
  Prompt framing is not proof of prompt-injection immunity or authenticated origin.

## Merged guard-verification baseline

The six guard cases cover selected socket/process/environment/cwd/write-open/
SQLite/resource checks in fresh children. They do **not** establish a hostile-code
sandbox. The separate side-effect-free event probe found `os.remove`, `os.rename`,
`os.mkdir`, `os.link`, `os.symlink`, `os.chmod`, `os.truncate` unhandled.
No corresponding external mutation was executed. These gaps and path/dir-fd
hardening remain open; this branch does not change runtime guard behavior.

## Merged PR #29 pipeline

Historical development branch `feat/oss-offline-journal-pipeline`, merged in PR #29.

- Added [OfflinePipeline](../src/agent_sleep_lab/oss_offline_pipeline.py):
  bridge retrieval → durable reference journal → parent checker → saved decisions
  → capture. Bridge repository/commit must match the built-in pinned task.
  Reference budget is at most the worker's 32,768 bytes and 256 records.
- A canonical contract binds retrieval, target path, launch configuration and
  capture timestamps/session/authorization into the journal consumer version
  before dispatch. Changed configuration under the same use ID conflicts.
  The bounded consumer output persists the contract, checker summary and
  hash-bound returned decisions before any capture.
- Capture resumes only from saved output. Deterministic event IDs and the existing
  store's byte-identical replay allow recovery after partial capture without
  executing the worker again. Unknown, invalid receipt and invalidated outcomes
  are never re-dispatched or captured as success. Current context is rechecked
  before/between/after capture, and the capture boundary checks authorization
  even on replay. Already captured observations are not rolled back when policy
  changes; remaining capture stops and reports partial observations.
- Added read-only `ReferenceUseJournal.context_unchanged()`; no journal schema
  change, migration, new database or automatic retry mechanism.
- **Separate actual pinned-worker pipeline acceptance passed**: an empty reference
  from a temporary synthetic store, one real worker invocation, interruption
  before capture #3, journal reopen, then two replayed and three newly captured
  observations. A further call replayed all five with total worker invocations
  still one. Outcomes were candidate, low-score skip, pending LLM, duplicate skip
  and infrastructure error. No adopted memory or verifier/evaluator receipt exists.
- [Nine integrated regression cases](../tests/test_oss_offline_pipeline.py) use
  real temporary synthetic stores/journals and a mocked checker, not target code.
  They cover replay, partial recovery, contract conflicts, unknown result,
  changed context, current capture authorization, caps, mid-capture policy change
  and oversized output. Mocked results stay explicitly labelled stand-ins.
- Development provenance: Claude Code's terminal metadata identifies
  `claude-fable-5-2` / `firstParty`, but the run **did not complete normally**:
  `is_error=true`, `terminal_reason=api_error`, HTTP 429
  `usage_limit_reached`. It saved pipeline code and the journal accessor only.
  The coordinator reviewed the partial code, added the nine acceptance tests and
  per-capture context checks, and completed verification/status updates.
  No alternative coding worker/model was started.
- This is synthetic offline orchestration, not production integration or
  authenticated delivery/use. The receipt remains unreviewed self-report and
  `delivery_and_use_verified` stays false. Empty reference bytes reach
  `Target.notes`; triage with `llm=None` does not use them semantically.
- Remaining: nonempty eligible-memory use, broader guard-boundary coverage/hardening,
  bundle-key drift/store-origin binding, real-data authorization and real comparison
  evaluation. Capture/journal/store are not one cross-database transaction.
  The explicitly supplied store remains caller-controlled, not authenticated;
  capture recovery requires the same surviving evidence store. Local origin URL
  is mutable and guard code is not a sandbox for hostile Python.
  Actual acceptance script/artifact remain local coordinator evidence, not a
  portable checked-in real-target regression.

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

- `feat/oss-adopted-reference-preparation`: **nothing executed yet.** The three
  new cases, full regression, documentation check and pinned-source acceptance
  are pending with the coordinator. Figures below are PR #31 history.
- **306 unique regression cases / one full invocation passed in 15.327 s** on the
  existing Python 3.13.18 environment. Includes five new prompt-capture cases.
  Earlier focused five-case run: four passed / one fixture error; corrected the
  stand-in source paths to match required trace names, then the affected one case
  passed. **312 case executions / three invocations** total in this trial.
- Separate actual acceptance: one fresh prompt-capture worker, two captured
  requests through pinned judge/prompt code, no external calls or model verdicts,
  and empty eligible-reference data. Not counted as regression cases.
  Worker-output SHA-256:
  `2d26697d97af0cf4277582b77155fefcf72febdb4d2e0a651d800bee734acc02`.
- Documentation: **370 relative file links / 76 Markdown files passed**;
  anchors and remote URLs excluded. Whitespace diff check passed.
  Feature CI not run.
- Historical PR #30 verification: 301 cases / one invocation in 15.011 s and
  earlier six focused cases (307 executions/two invocations), 366 relative
  links / 76 Markdown files. Its seven-event diagnostic was not a regression case.
  Historical PR #29 verification: 295 cases plus eight earlier focused cases,
  and one real empty-reference pipeline recovery acceptance. None was rerun here.
- Nonempty adopted-memory semantic use, live comparison/evaluation and the
  known filesystem mutation guard gaps remain unverified/unfixed.

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
