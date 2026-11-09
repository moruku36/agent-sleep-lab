# Gate 2B first-slice acceptance — 2026-11-10 JST

Status: **first receipt/policy slice locally accepted**, macOS arm64 / CPython 3.13.18. **Full Gate 2B adoption is NOT complete.** Publication, merge and Linux CI are separate observations; consult the [feature branch](https://github.com/moruku36/agent-sleep-lab/tree/feat/gate-2b-adoption-boundary) and [live PRs](https://github.com/moruku36/agent-sleep-lab/pulls) for delivery state.

Published implementation commit: `55dbb9f06d790e31c193faa479f24cc4d16b7ec0`, [PR #8](https://github.com/moruku36/agent-sleep-lab/pull/8). Implementation-commit [CI run 42701391859](https://github.com/moruku36/agent-sleep-lab/actions/runs/42701391859) passed Python 3.11/3.13. Later status-link commits have their own checks; current merge state is recorded by the live PR.

## Delivered

Three strict runtime artifact schemas mirrored in repository/package; simulated verifier/evaluator/control boundary stamping; immutable receipt registration and exact ID/hash resolution; independent persisted policy with expected-current CAS, consecutive revisions and additive exclusions; evidence/ancestor/current-policy eligibility rechecks on the same store connection; explicit SQLite v1-to-v2 extension without evidence rewriting.

## Executed acceptance

- Initial full suite: **146 tests passed** (110 prior + 36 authored with Claude). After review corrections and six meaningful regression additions, **152 tests passed** (110 prior + 42 new). These are successive snapshots, not 298 distinct tests.
- Review fixes: exact supported table/index/trigger definitions before upgrade/open; rollback of a deliberately interrupted extension; exact purpose/partition formats including trailing-newline rejection; stable boundary rejection for malformed method/protocol types; receipt replay rejects inconsistent identity columns. All new regressions passed. No unchanged repeat regression after that final source/test snapshot.
- Built wheel, installed in fresh `.venv-wheel-gate2b` with runtime dependencies only. From outside the checkout, `tools/check_runtime_installed.py` passed schema byte equality, explicit v1 upgrade and unchanged evidence, v2 capture, verification/evaluation registration and resolution, policy CAS, ancestor-root exclusion and reopen. Gate 1 CLI and Gate 2A evidence installed checks also passed on this wheel.
- Final documentation check passed: 152 relative file links exist (anchors not checked). Whitespace checks passed. CI includes normal tests/docs plus all three installed-wheel helpers on Python 3.11 and 3.13; actual CI results must be observed, not inferred from workflow configuration.
- All database operations used synthetic temporary directories. No real transcript, credential, production source, model API client or memory adoption was used by the product.

## Development attribution and lifecycle

Claude Code `claude-sonnet-5-5` saved the initial runtime modules, schemas, helper and 36 test methods. Its bounded invocation ended at the outer 600-second tool timeout without a final successful Claude response; the implementation process was confirmed absent. The main agent reviewed saved code, supplied the six focused review regressions and corresponding corrections, installed-wheel helper, CI and bilingual progress/usage/decision documentation. This is reviewed saved output, not a claimed successful terminal Claude run or independent security certification.

The module-form test invocation could not be safely approval-bound and did not execute. After the owner agreed to the repository's already-existing explicit-file test entry, normal file-bound execution succeeded. No execution-policy/security/allowlist change, host switch or platform-code patch was required. No result from an unrelated timed-out advisory API call was used as evidence.

## Limits and remaining implementation

Boundaries are local simulations, not identity authentication, truth verification or consent. A database writer can forge rows and hashes together. Schema checks reject unsupported definitions but do not attest the entire environment/import graph. Re-registering a receipt preserves its original issue time; it does not renew validity. Policy revisions combine authorization/exclusions for this slice; wiring them into future promotion request revisions remains pending.

Eligibility is a point-in-time binding/policy check for caller-provided memory ID/hash, not verification of memory bytes/kind. Evaluation registration does not check a candidate or grant adoption. Missing/corrupt policy fails closed; exclusions can only grow. Explicit upgrade changes supported API format from v1 to v2; no automatic migration or production upgrade was executed.

Still pending: operation/candidate/source-manifest/committed-operation contracts, expected-parent candidate construction, kind rules, exact evaluation acceptance, active pointer, operation-ID/digest replay and atomic adoption. Current same-connection lock and sequential CAS checks do not establish cross-process adoption, crash/ACK-loss or power-loss acceptance. Gate 3 retrieval/rollback/deletion, full SLP acceptance, real provider/agent integration, scheduling and performance measurement remain pending.

[English usage](../docs/gate-2b.md) / [日本語](../docs/gate-2b.ja.md) / [Storage extension ADR](../docs/decisions/0005-runtime-store-extension.md).
