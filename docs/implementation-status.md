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

`feat/oss-fixture-cohort`, based on owner-merged
[PR #36](https://github.com/moruku36/agent-sleep-lab/pull/36) at
`6e4018c8393103c6f3da362fa409814a61571a3a`. GitHub verified MERGED and
[main CI success](https://github.com/moruku36/agent-sleep-lab/actions/runs/42916818253)
at that exact commit.

- Added a separate [frozen synthetic fixture cohort registry](oss-fixture-cohort.md).
  Two to five unique task identities, exact plan/manifest pins and comparable
  settings are committed before any member intent. A short journal reservation
  excludes competing intent writers; membership cannot be rebound.
- Read-only reports keep every registered task in the denominator. Unknown,
  missing, withheld, corrupt or unsupported outcomes prevent overall means and
  paired difference. Invalid completed verdicts score zero without retry.
  Reports contain no reply bodies, rationale or answer labels.
- All **352 unique regression cases / one invocation passed** locally on
  Python 3.13.18 (24.123 s), including 13 new cohort cases. Feature CI is pending.
  These use injected replies and stand-in captures; the actual pinned capture
  worker still selects only issue #3. No real multi-task target acceptance.
- Development worker: after automatic review refusal and explicit owner approval,
  the unchanged Codex CLI request was submitted through native one-time approval.
  Local execution metadata confirms provider `openai`, model `gpt-6.1-sol` and
  effort `xhigh`. The outer tool timed out at 600 s; no final-message file or
  normal-completion receipt was obtained and no matching worker process remained.
  Draft changes were preserved, independently reviewed and tested by the
  coordinator. No retry, substitute model or API worker call; development usage
  and cost are unknown.
- Unmerged work: no live inference, paid runtime measurement, independent
  evaluation dataset, confidence interval, rationale-quality scoring, cost
  schema, adoption, target changes or merge. This is descriptive synthetic
  development-fixture accounting, not performance evidence.
  Initial-version completion remains provisional **30–35%**.

## Merged PR #36 strict fixture evaluation

Historical branch `feat/oss-verdict-evaluation`, based on owner-merged
[PR #35](https://github.com/moruku36/agent-sleep-lab/pull/35) at
`7dc833f14034087b1559eb6ffcef71cf2675e582` (source
`c9d7d5e18723ee7858972a9bb3d99013bcb31e27`). GitHub confirmed MERGED and
successful Python 3.11 / 3.13 PR checks.

- Added a [strict verdict parser and frozen fixture evaluator](../src/agent_sleep_lab/oss_verdict_evaluation.py).
  This is an explicitly stricter subset of the pinned OSS parser, not a claim of
  identical permissive semantics. Only whole JSON with boolean accept and
  nonempty bounded text rationale is accepted; duplicate keys, coercion, prose,
  nonfinite/surrogate data and extra fields fail with sanitized codes.
- Optional manifest freezes the caller-declared synthetic label, task hash and
  issue number, evaluator/parser/strict-JSON implementation hashes, target-source
  hash and fixed criterion in the execution plan before any intent. Labels never
  reach the provider prompt. Posthoc changes/attachment to an unscored plan conflict.
  Existing unscored plans need no schema migration and remain unscored.
- Report-time evaluation distinguishes parsed decisions, invalid verdict failures
  and incomplete/unknown arms. Invalid completed outputs score zero without retry;
  missing/unknown arms never create a paired difference. Current-context revocation
  withholds parsed rationales and scores. Code/criterion mismatch prevents silent
  rescoring. A single-fixture difference is not scientific effect evidence.
- [Eight new regression cases](../tests/test_oss_verdict_evaluation.py).
  Full local regression: **339 unique cases / one invocation passed** (Python 3.13,
  18.845 s). Following strict-JSON and issue-binding improvements, related checks
  passed: 8 cases (1.168 s) then 16 cases (2.725 s).
  Total: 363 regression case executions / three invocations, 339 unique cases.
- Separate offline acceptance used actual pinned source/captured prompts and only
  injected replies. Three target-parser samples: one compatible strict verdict
  and two intentionally stricter refusals. Actual capture → first saved reply →
  reopen → second reply → stable replay → policy withholding passed with two
  mock calls per acceptance. Two acceptance invocations (before/after issue binding);
  six differential sample executions / two end-to-end fixture runs in total.
  Manufactured fixture differences, not model verdicts/performance.
- Worker provenance: one Muse Wonder review request was attempted with explicit
  `meta/muse-wonder-1.0`, but the tool timed out at 270 s. No response, normal
  completion, resolved-model or cost receipt was obtained; no matching process
  remained on read-only inspection, which does not establish remote outcome.
  No retry/substitution. Coordinator continued authorized implementation/review
  and verification; this is not a successful Muse development receipt.
- [Contract and limitations](oss-verdict-evaluation.md): no live/runtime inference,
  paid effect measurement, adoption, target mutation, default/auth/schedule or merge.
  Labels are unauthenticated synthetic fixtures; rationale quality is not verified.
  Remaining: justified independent dataset, broader aggregation, live verification
  under spending controls, usage/cost schema and actual paired effect measurement.
  Provisional initial-version completion remains **30–35%**.

## Merged PR #35 durable execution journal

Historical branch `feat/oss-durable-prompt-execution`, based on owner-merged
[PR #34](https://github.com/moruku36/agent-sleep-lab/pull/34) at
`4492cb05a5aa057b1905753834bd0bcbb0d84f81` (source
`c7071b43e30f95f0b3a7b59b9720f50048b0fbec`). GitHub confirmed MERGED and
successful Python 3.11 / 3.13 PR checks.

- Added a separate [durable execution journal](../src/agent_sleep_lab/oss_execution_journal.py)
  connecting validated captures to the exact-prompt adapter. Full capture,
  source/task/reference/arm hashes, bridge, adapter/agent/model/transport and
  limits are frozen. Existing IDs cannot be rebound to changed execution settings.
  Synthetic task provenance is distinct from injected/CLI execution provenance.
- Intent commits before each call; response and sanitized hash-bound receipt
  commit before the next arm. Close/reopen continues only unstarted arms and
  replays complete pairs without dispatch. Unclosed intents, unknown outcomes,
  invalid outputs or receipt mismatches halt the plan; fresh adapters cannot retry.
- Current context is checked before/after calls and on report. Revoked replies
  store only hash/length/status. Already saved bodies and receipt details are
  withheld from reports after context changes/unavailability (not physically erased).
- Own application ID/version/exact schema, explicit initialization, read-only
  foreign-DB inspection, full-sync writes and short immediate transactions.
  No DB lock spans transport. One driver per plan remains the contract;
  overlapping drivers conservatively stop instead of duplicating a call.
  There is no cross-store atomicity or authenticated store/worker origin.
- [Eight new mock-only cases](../tests/test_oss_execution_journal.py). All
  **331 unique local cases passed in one invocation** (Python 3.13, 18.842 s).
  After explicitly closing the read-only probe, its one affected case passed
  (0.108 s): 332 local case executions / two invocations, not 332 unique cases.
  Tests use test-authored captures/adoptions and injected CLI envelopes only.
- Worker receipt: `ok=true`, provider `meta`, model `muse-wonder-1.0`,
  no fallback attempts; one development design review. Coordinator implemented
  and verified the reviewed design. Worker suggestions are not authorization:
  live selection flags do not supply owner approval or change external controls.
- [API and limitations](oss-durable-execution.md): old fake journal/type restriction
  unchanged; no live inference, actual target acceptance, paid effect measurement,
  new CLI entry point, credentials, defaults, schedules or merge. Usage/cost remain
  unavailable; byte bounds are not token/financial caps.
  Remaining: live verification under separate spending approval, target verdict
  parsing, frozen independent evaluator, paired usage/cost and effect comparison.
  Provisional initial-version progress remains **30–35%**.

## Merged PR #34 exact-prompt adapter

Historical branch `feat/oss-registered-mimo-adapter`, based on owner-merged
[PR #33](https://github.com/moruku36/agent-sleep-lab/pull/33) at
`19c7e39440f4b938ba95250e212a5fce01d0f8c3` (source
`76e5b026762c5cd646fe2c92630405e09e6d4a1a`). GitHub confirmed MERGED and
successful Python 3.11 / 3.13 PR checks.

- Added a separate [exact-prompt adapter](../src/agent_sleep_lab/oss_mimo_adapter.py)
  for explicit registered MiMo calls. It validates the entire captured artifact,
  pins/source/task/reference/request/prompt hashes and A/B relation before reserving
  a call. The exact selected user text is forwarded with no instruction wrapper.
  This is not HTTP wire replay; original URL/headers/model/settings are not forwarded.
- Literal paid/uncapped-generation opt-ins, 1–2 calls, timeout at most 120 seconds,
  captured request/envelope/post-generation byte bounds, strict CLI model/provider/
  no-fallback/text-output checks and sanitized hash-bound receipts.
  Usage/cost remain unavailable; no supported usage/cost schema or financial cap.
- [Six mock-only cases](../tests/test_oss_mimo_adapter.py) cover exact Unicode
  forwarding, opt-ins/budgets, capture rejection, invalid/fallback/oversized replies,
  timeout/interruption stops and sanitized missing usage/cost. Full local regression:
  **323 unique cases / one executed invocation passed**, Python 3.13, 17.043 s.
  An earlier system-Python 3.9 launch stopped at imports (missing dependencies);
  no test cases executed in that launch.
- Worker receipt: normal completion confirms provider `meta`, model
  `muse-wonder-1.0`, `ok=true`, no fallback attempts. Coordinator reviewed the
  untrusted proposal and corrected its fictional envelope, opt-in/budget validation,
  capture binding and failure handling. No further worker invocation.
- [Contract and limitations](oss-exact-prompt-adapter.md): stop/budget are
  **in-memory per instance**, not a durable live journal. No current-policy executor,
  live paired-journal integration, actual OSS acceptance or live evaluation has
  been run for this change. All runtime adapter calls were injected mocks.
  The prior paired journal remains fake-only with unchanged schema/type restrictions.
  Next: durable context-aware live execution, target verdict parsing, frozen
  evaluator and paired usage/cost/effect measurement. Initial progress stays 30–35%.

## Merged PR #33 offline paired-outcome journal

Historical branch `feat/oss-paired-outcome-journal`, based on owner-merged
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
