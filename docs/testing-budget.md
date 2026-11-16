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

For the isolated Relate design/directory change, the four existing selections in
`test_packaging_and_examples` check unchanged dependency declarations, the core
entry point/package data, identical packaged schemas and synthetic promotion
remaining proposal-only. These are core compatibility checks, not Relate runtime
acceptance. Local work uses documentation review/checking only; one PR CI
invocation reserves four case executions. Main push remains static-only.
Each test method is one case; internal assertions are not extra unittest cases.
Re-select affected cases when a later change targets another contract; do not
accumulate previous selections.

Keep dated reports and historical tests intact. Their large counts, former
matrices and old runner commands describe past acceptance, not current instructions.
No automatic rerun follows a failure: reconcile the outcome and remaining budget
first. Specific extra cases need a justified budget increase, not a full-suite default.
Live experiments require their own explicit authority; regression limits are not
model/token/currency caps.
