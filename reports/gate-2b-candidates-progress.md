# Gate 2B candidate-planning acceptance — 2026-11-10 JST

Status: **pure planning slice locally accepted**, macOS arm64 / Python 3.13.18. No database writer, adoption commit or active memory. Publication/merge/CI are separate observations; see the [working branch](https://github.com/moruku36/agent-sleep-lab/tree/feat/gate-2b-atomic-adoption) and live PR state.

## Baseline

Owner merged PR8. GitHub confirmed MERGED at 2026-11-09T21:24:13Z, merge commit a43301ff28f50ccaeb4975162c17e3d8410b38ab. Post-merge main CI42702164583 passed. This slice branches from that immutable baseline; the old PR8 merge-tool stop is no longer a pending merge.

## Implemented and checked

- Five strict runtime schemas mirrored in package/repository: operation/source manifests, candidate snapshot, adoption request and committed-receipt format. A format is not an adoption receipt from a real transaction.
- Pure parent+operation construction, canonical identities, deterministic ordering, add/supersede/stale/audit-only reject/defer semantics and preserved unrelated/history members. Caller-supplied known-ID checks, memory/source/expiry/kind/scope rules, no silent eviction and request/receipt builders. Database-backed authority is explicitly absent.
- First full suite ran172tests with1error: a cross-scope-parent test accidentally used a memory from the original scope. Corrected that fixture. Review added rejection for duplicate memory evidence and inconsistent receipt policy/naive time, with2regression methods. Final suite: **174passed (152prior+22new)**. No unchanged repeat local regression after final code.
- Fresh wheel installed in `.venv-wheel-candidates`. Outside checkout, the new candidate helper passed packaged schema equality, add/supersede/history and request/receipt-format hash binding. Existing Gate1CLI, Gate2Aevidence and first2Breceipt/policy helpers passed on the same wheel.
- Final local documentation check passed183relative file links (anchors not checked); whitespace checks passed.
- CI now includes the candidate helper on Python3.11/3.13; actual workflow results are separate. Synthetic fixture references do not prove source existence, verifier identity, evaluation quality or consent.

## Attribution and limits

Claude Code Sonnet5.5 saved the contracts/planner/original20test methods. Its retained-session call returned is_error=true, terminal_reason=api_error, status429 usage_limit_reached, despite a success-like subtype; no successful terminal completion is claimed. Main agent reviewed saved output, corrected the scope fixture, added two focused regressions/corrections and supplied installed-wheel acceptance/CI/bilingual documentation. No further implementation-model call or automatic retry was made after the limit.

Pending: trusted current-parent resolution; exact verification/evaluation/provenance checks of all candidate members; policy/parent recheck with active pointer and durable operation digest/receipt in oneSQLitetransaction; global-ID reservation; run-ID audit association and legacy revision mapping; replay and no-resurrection; process concurrency/crash/ACK-loss fixtures. No new DB schema/version, production migration, retrieval, model-provider integration, schedule or performance claim. Full2B/SLP acceptance remains pending.

[English scope](../docs/gate-2b-candidates.md) / [日本語](../docs/gate-2b-candidates.ja.md).
