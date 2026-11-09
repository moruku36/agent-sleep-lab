# Implementation status

**English** | [日本語](implementation-status.ja.md) | [Home](../README.md)

Last updated: 2026-11-10 JST. **Gate 1, Gate 2A and Gate 2B receipt/policy helpers are merged into main. Subsequent pure candidate planning is locally accepted: 174 combined tests passed. Database adoption remains unimplemented.**

Use this page to see what works today. Future plans in the [roadmap](roadmap.ja.md), executed gate acceptance, and performance experiments are separate claims.

## Test-budget policy (2026-11-10 owner update)

Future trials execute at most 10 selected cases total, counting local/CI/retries. Default is 3 concise cases, and PR-only CI has one Python 3.13 job with 3 cases; full-suite, duplicate push/PR and multi-version runs are no longer automatic. The 174-case result below is historical acceptance of the candidate implementation, not a claim of rerunning all cases on this policy commit. [Details](testing-budget.ja.md).

## Overall progress estimate

Approximately **25% (a rough 20–30% range)** of the initial end-to-end version: capture → adoption → retrieval → Light/Deep → comparative evaluation → one existing-agent integration. Optional REM, diary and wider rollout are excluded. This is a scope-based judgment, not a calculation from files/tests or a measured performance improvement. Validation, storage, receipts and candidate planning exist; the adoption writer, retrieval, coordinator, evaluation runner and integration still represent most remaining work.

## Capability overview

| Capability | Status | Boundary |
|---|---|---|
| Event, memory and promotion-request validation | Implemented, checked, merged | Read-only offline CLI; valid structure is not evidence of truth or permission to adopt |
| Provenance sidecar and original evidence storage | Implemented, checked, merged | Synthetic-only SQLite library; atomic event/source/provenance capture |
| Replay, conflicting IDs and root deduplication | Implemented, checked, merged | Byte-identical replay, conflict rejection, generated artifacts cannot become independent roots |
| Stored evidence integrity checks | Implemented, checked, merged | Hashes, source presence and expiry; descendant capture also checks ancestors against configured current authorization revisions and evaluation partition |
| Verification/evaluation receipts and current control policy | Implemented, checked, merged | [First Gate 2B slice](gate-2b.md); 42 new tests, 152 combined, fresh installed-wheel checks passed |
| Candidate snapshot from parent + operations | Implemented and locally accepted | [Pure planning](gate-2b-candidates.md); 22 new tests, 174 combined; no database write/adoption |
| Memory adoption and active-version updates | **Not implemented: next, Gate 2B** | Requires trusted-boundary receipts, current policy/exclusions, expected parent and operation IDs |
| Retrieval, revocation and rollback | Not implemented: planned Gate 3 | Scoped bounded bundles and non-resurrection under current exclusions |
| Light/Deep candidate generation | Not implemented: planned Gate 4 | Manual coordinator with fake providers and recovery checks first |
| Paper-curation A/B evaluation | Not implemented or executed: planned Gate 5 | Runner must retain all trials, failures and costs; no measured improvement |
| Existing-agent integration | Not implemented or executed: planned Gate 6 | One target only after standalone acceptance |
| REM, diary and recurring execution | Outside the initial slice / not implemented | No scheduled automation or background service configured |

## Merged deliverables and evidence

### Gate 1: read-only contract validation CLI

- [PR #5](https://github.com/moruku36/agent-sleep-lab/pull/5) merged. Main merge commit: `dcc7dac2cba8e5437695d49ef42a1903bef68760`.
- Strict JSON parsing, packaged local schema validation, bounded diagnostics, CLI exit codes and package acceptance.
- **87 tests passed** locally at that gate; isolated installed-wheel CLI/schema checks ran outside the checkout.
- [Successful main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42654863953).
- [Usage](gate-1.md) / [detailed acceptance record](../reports/gate-1-progress.md).

### Gate 2A: provenance contract and synthetic-only evidence store

- [PR #6](https://github.com/moruku36/agent-sleep-lab/pull/6) merged. Main merge commit: `88bd44ca9c884d906bb76bf019e7f515eea6af71`.
- `agent-sleep-provenance/1`, atomic SQLite capture, replay/conflict handling, lineage and integrity checking.
- **110 tests passed in total (87 existing + 23 new)** locally. Do not add the earlier 87 to 110 as separate tests.
- Fresh installed-wheel checks outside the checkout covered schema equality, capture/replay, lineage, connection reopen and read-only verification; Gate 1 CLI acceptance also passed.
- Python **3.11/3.13** CI passed. [Successful post-merge main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42679309578) corresponds to the merge commit above.
- [Scope and usage](gate-2a.md) / [detailed acceptance record](../reports/gate-2a-progress.md) / [storage decision](decisions/0004-local-evidence-store.md).

Acceptance reports preserve observations made at each gate. This page also summarizes later publication, merge and CI observations. Passing tests are not independent security certification or evidence of performance improvement.

### Gate 2B first slice: registered receipts and current policy

- [PR #8](https://github.com/moruku36/agent-sleep-lab/pull/8) is merged; merge commit `a43301ff28f50ccaeb4975162c17e3d8410b38ab`. [Post-merge main CI passed](https://github.com/moruku36/agent-sleep-lab/actions/runs/42702164583).
- Runtime implementation commit: `55dbb9f06d790e31c193faa479f24cc4d16b7ec0`. Later status-only commits do not expand the implementation scope.
- **152 combined tests passed (110 prior + 42 new)**; fresh installed-wheel receipt/policy/explicit-upgrade checks and existing CLI/evidence checks passed outside the checkout.
- [Observed CI success on the implementation commit](https://github.com/moruku36/agent-sleep-lab/actions/runs/42701391859), Python 3.11/3.13. See the PR for checks on any later documentation commit.
- [Scope](gate-2b.md) / [acceptance and remaining limits](../reports/gate-2b-progress.md). Active memory/adoption is still not implemented.

### Subsequent slice: pure candidate planning

- [Scope](gate-2b-candidates.md) / [acceptance](../reports/gate-2b-candidates-progress.md): five contracts and deterministic parent+operation candidate construction.
- 174 tests (152 prior + 22 new) and fresh outside-checkout installed-wheel checks passed. Publication/merge are recorded separately in the acceptance record and live PR.
- Candidate `active` labels and receipt-format builders are not actual activation or proof of commit. The atomic writer remains pending.

## Next: remaining Gate 2B acceptance targets (not executed)

The first receipt/policy runtime slice and three schemas are locally accepted: 152 tests (110 prior + 42 new) and fresh installed-wheel checks passed. Review fixes cover exact schema recognition, malformed boundary inputs and receipt replay integrity. See [the acceptance record](../reports/gate-2b-progress.md) and [live PRs](https://github.com/moruku36/agent-sleep-lab/pulls) for publication/merge/CI evidence. The acceptance targets below are for the remaining full Gate 2B; memory adoption is not available.

1. Resolve verification/evaluation receipts through separately configured simulated boundaries, not candidate-asserted identity. Bind receipts to exact memory/snapshot bytes, evidence, scope, method and protocol hashes.
2. Integrate the accepted pure candidate builder with the writer's trusted current parent and full ID history; reject unrelated omissions, unknown targets, ID collisions, cycles and scope changes.
3. Recheck current authorization/exclusions, original evidence and ancestors, expiry and expected parent in the same SQLite transaction as active adoption.
4. Commit operation ID, request digest, adoption receipt and active reference together; resolve lost acknowledgements through durable operation lookup.
5. Exercise forged/mismatched receipts, source change/loss, concurrent null-parent initialization, competing writers, process exits before/after commit and ACK loss with synthetic fixtures.

The [implementation contract and SLP-01–12 cases](contracts-and-acceptance.md) remain the acceptance basis; full SLP acceptance is pending. Gate 2A connection reopen/SQL rollback is not Gate 2B process-crash or power-loss acceptance. Promotion-time exclusion checks alone do not complete Gate 3 retrieval, rollback or deletion behavior.

## Current limits

- Capture is a locally configured boundary simulation, not authenticated users/adapters. Hashes do not prove truth or consent.
- `get()` is raw lookup; `verify()` checks stored integrity/expiry, not current revocation or adoption eligibility.
- No active memory, sleep provider integration, production adapters or performance experiments. Real transcripts, credentials and private memory stay outside this public repository.
- Process-crash, power-loss and network-filesystem durability acceptance has not been executed.

## Keeping this current

Update this page, its Japanese counterpart and README at meaningful implementation milestones. Distinguish designed, implemented, executed, pushed and merged, linking the exact PR/commit, CI and acceptance record. Keep incomplete work and genuine waits explicit; plans are not completed features.
