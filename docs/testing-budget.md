# Development testing policy

**English** | [日本語](testing-budget.ja.md) | [Home](../README.md)

The owner's 2026-11-13 personal-development policy in [AGENTS](../AGENTS.md)
supersedes the 2026-11-10 exhaustive-regression override. Normally select 3–5
change-relevant cases, at most **10 case executions per development trial** across
local runs, CI, retries and all subagents. A narrower task allocation still applies.
Never reset an exhausted or UNKNOWN reservation by renaming a trial.

## Select before executing

Use explicit full method names with `python tests/run_tests.py <names>`.
Do not use its historical no-name discovery default, or a class/module containing
more cases than allocated. `--list <names>` loads and lists selected cases without
executing their bodies; it is not a regression result. Report executed cases and
invocation counts separately. Documentation-only reversible edits normally need
review and `python tools/check_docs.py`, not regressions.

## What CI actually runs

[Workflow](../.github/workflows/gate-1.yml), Python 3.13 only:

| Event | Static checks | Regression |
|---|---|---|
| Pull request | AST parsing without imports; Markdown relative file links | Install pinned runtime dependencies; exactly four explicit cases, one invocation |
| Push to main | Same static checks | No dependency install or cases |

No version matrix, wheel checks, full suite, demo command, or paid/model/API calls
are hidden in static checks. Link checking does not validate anchors/external URLs.
PR creation, updates and reruns can each consume four more executions: reserve
them before publication; authorization and reservations belong in the trial ledger.

The current four selections are the existing `test_demo_text.DemoTextTests`
methods: JSON serialization compatibility; single-result text without additional
dispatch; invalid-format rejection before execution; failure exit and temporary
state cleanup. Each test method is one case; its internal assertions and scripted
fixture calls are not extra unittest cases or live-model calls. Re-select four
affected cases when a later change targets another contract; do not accumulate
previous selections.

Keep dated reports and historical tests intact. Their large counts, former
matrices and old runner commands describe past acceptance, not current instructions.
No automatic rerun follows a failure: reconcile the outcome and remaining budget
first. Specific extra cases need a justified budget increase, not a full-suite default.
Live experiments require their own explicit authority; regression limits are not
model/token/currency caps.
