# Implementation status

**English** | [日本語](implementation-status.ja.md) | [Home](../README.md)

## Current assessment — 2026-11-10

**Provisional initial-version completion: 30–35%. The former 50% estimate is withdrawn.**
100% means capture → adoption → retrieval → Light/Deep → comparison evaluation →
one existing-agent integration. REM, diary and wider rollout are excluded.
File/test counts and prepared interfaces do not increase this estimate.
This page and its Japanese translation are the ONLY current status authority;
other gate specifications and acceptance reports are dated history.

## Verified merged baseline

[PR #22](https://github.com/moruku36/agent-sleep-lab/pull/22) (Gate 4E) IS MERGED
at `68a6536a8017ac4f76b2cede3693cbbeb220dcee`, not untested/unmerged as the old
landing page said. Source `ce723d0c36a5603acc41fae164e321396e046697`;
[CI42789603739](https://github.com/moruku36/agent-sleep-lab/actions/runs/42789603739)
passed five handoff cases once (1.702 s), wheel success. Earlier Gate 4A–4D are
merged through PR #17/#19/#20/#21. These focused historical results do NOT establish
a full regression result or live-model quality improvement.

Merged foundation: synthetic evidence/provenance, policy and receipt libraries,
transactional adoption, scoped retrieval, rollback/logical forgetting; fake
Light/Deep checkpoints; paired comparison/contact tracking; source-matched and
independent bounded raw contexts; manual draft handoff journal. This is not
production authentication, physical purge, or a connected existing agent.

## Review-fix branch (implemented, not yet merged)

Branch: `fix/runtime-provider-and-comparison`, based on PR #22 merge above.
Review claims were checked against source; the external reviewer's 253-case
run is NOT reported as our own verification.

| Finding | Implemented correction | Verification / remaining limit |
|---|---|---|
| ID-only Light/Deep | Body/hash-bound v2, current eligible evidence from store, generated claim, unverified candidate materialization, preparation cannot substitute prose | Offline contract/CLI cases pass; actual API response unverified |
| Fake-only transport | Explicit registered `xiaomi/mimo-v2.6-pro` adapter; no credential extraction, shell or retry, model/fallback receipt checks | First design call timed out without receipt; later implementation-review command denied by execution controls. No successful MiMo receipt in this trial |
| Identical A/B inputs | Reject before registration/dispatch; explicit diagnostic mode never yields comparison statistics | Tight-budget/no-memory regressions assert rejection; audit prefixes retained |
| Narrow CI | All unique regressions on PR and main, Python 3.11/3.13, all Markdown file links, wheel | Workflow configured; remote checks are not yet claimed passed |
| Scattered stale docs | README language/overview first, single current-status authority, permanent-only AGENTS, roadmap/architecture corrected, Gate 4 Japanese summaries | File links checked; translated Gate summaries are summaries, not full word-for-word translations |
| No runtime entry | Explicit sleep/status/adopt/retrieve/compare CLI, bounded file input and existing boundary configuration | Script sleep/reopen, independent prepared adoption→retrieval and foreign-journal rejection pass |
| Interrupted preparation | Explicit stopped-worker recovery to incomplete/unknown, never callback replay | Offline crash/recovery case passes |
| Query score-zero memories | Omit lexical score-zero records for effective query terms | Updated retrieval regression passes; no-query listing remains |
| Hard-coded research target | Required caller repository and immutable 40-hex commit | Historical tests explicitly configure their fixture target |

## Current verification

- Full regression: **240 unique cases in one invocation, 239 passed, one environment
  failure**, 11.825 s. Installed jsonschema 4.26.0 differs from repository pin
  4.23.0. The original environment was not changed; the pin assertion was not
  skipped or weakened. A clean isolated environment creation was denied by host
  execution controls. CI installs project pins on supported Python versions.
- Newly added runtime/transport/CLI cases: **13 cases, one focused invocation,
  all passed**, 0.532 s. Earlier affected sets: 23/1 and 28/1 passed after repairs.
  These are recorded executions, not a ten-case budget reset. A test-module syntax
  error was fixed before its test bodies ran.
- Documentation: **339 relative file links / 72 Markdown files passed**; anchors
  and remote URLs are not checked. Subsequent check receipts belong to PR checks
  or private development logs; do not infer an unrun CI result from this page.
- Original baseline full run: 227 unique cases (imported fixture aliases deduplicated),
  two failures/four errors. Behavioral failures were corrected; dependency-pin
  mismatch remains local. That snapshot selected 240. A subsequent receipt-reopen
  regression brings the final selection to 241; the final affected 19-case run
  passed once (0.557 s). Final full verification belongs to PR/main CI.
- Paid API calls in CI: zero. Actual five-task A/B execution: NOT performed.
  [Five fictional development tasks](../examples/paper-pilot/README.md) prepared;
  not an independent holdout, measured result, or adopted memory.

## Genuine remaining work

1. Resolve the explicit MiMo execution approval/binding failure and obtain a real
   provider/model receipt. Do not silently substitute another model or retry an
   uncertain call. This trial's actual API cost/usage remains unknown.
2. Run the prepared five-task real-response comparison with the caller's applicable
   budget, independently accepted experience memories and a frozen evaluator.
   Current exact-match rubric scoring alone is not scientific paper-quality proof.
3. Connect ONE existing agent and verify actual capture/retrieval use; manual
   handoff drafts are preparation only. Relevant raw ranking, delivered-memory
   logging, physical purge and broader production fault acceptance remain open.

Runtime contracts and commands: [English](runtime-guide.md) / [日本語](runtime-guide.ja.md).
The MiMo CLI lacks per-call max-token control: post-generation byte rejection
is NOT a hard token or monetary limit; unknown outcomes may have incurred cost.
