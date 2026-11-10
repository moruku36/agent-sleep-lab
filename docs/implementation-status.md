# Implementation status

**English** | [日本語](implementation-status.ja.md) | [Home](../README.md)

Last updated: 2026-11-10 JST. **Gate 1, Gate 2A, the Gate 2B receipt/policy helpers, pure candidate planning (PR #9), the synthetic durable-adoption core (PR #10) and the later run-ID/process additions (PR #11) are all MERGED; PR #12 merged documentation only** (PR #10, #11 and #12 merge states verified by fresh GitHub reads; PR #10 merge commit `629560858b5aef5423d75d90a71df99b6eec65d3`). **Full Gate 2B acceptance is not complete** (trusted run registration and broader fault fixtures remain). The old writer trial is closed: its final total was **19 case executions in 5 invocations, budget exhausted**. **Gate 3 scoped retrieval is MERGED ([PR #13](https://github.com/moruku36/agent-sleep-lab/pull/13), `9e3d1107f96034b61a812ab2a5abb1c95ef5eaba`; 4 local + 3 CI cases passed before merge, CI at head `90b3d9e`). A synthetic rollback slice is implemented but UNEXECUTED on `feat/gate-3-safe-rollback` (awaiting its limited CI; not merged); overall initial-version progress stays about 40% until its single 3-case PR CI run verifies it.** Deletion, evaluation-frozen retrieval, delivered-memory logging, full Gate 2B acceptance, Light/Deep, comparison evaluation and the adapter are pending.

## Test-count history (dated, 2026-11-10) — superseded by the final total above

An earlier 13-case/three-invocation total omitted [PR #10 CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42712205113) (three cases, once, 0.235 s, older writer commit). The reconciled count at that time was 16 cases in four invocations (7 local core + 3 prior PR CI + 3 local process + 3 local run-ID); the owner-approved cap then was 13, so that was a reporting/budget overrun, not retroactive permission. The run-ID PR CI took the old writer trial to the final **19 executions in 5 invocations**. Earlier "unmerged" and "pending approval" wording in older records below is historical.

Use this page to see what works today. Future plans in the [roadmap](roadmap.ja.md), executed gate acceptance, and performance experiments are separate claims.

## Test-budget policy (2026-11-10 owner update)

Future trials execute at most 10 selected cases total, counting local/CI/retries. Default is 3 concise cases, and PR-only CI has one Python 3.13 job with 3 cases; full-suite, duplicate push/PR and multi-version runs are no longer automatic. The 174-case result below is historical acceptance of the candidate implementation, not a claim of rerunning all cases on this policy commit. [Details](testing-budget.ja.md).

## Overall progress estimate

Approximately **40% (a rough 35–45% range)** of the initial end-to-end version: capture → adoption → retrieval → Light/Deep → comparative evaluation → one existing-agent integration. Optional REM, diary and wider rollout are excluded. This is a scope-based judgment, not a calculation from files/tests or a measured performance improvement. Validation, storage, receipts, candidate planning and the synthetic adoption core exist. Versioned audit labels and selected process boundaries are locally checked; registered-run integration, broader writer faults, full Gate 3 acceptance (including frozen evaluation retrieval), rollback/deletion, coordinator, evaluation runner and integration remain. Basic current-policy bounded retrieval is merged with focused acceptance; that was the last increase. The unexecuted rollback slice adds nothing to the estimate until its CI run is verified. The figure reflects delivered, verified capability, not test or file counts.

## Capability overview

| Capability | Status | Boundary |
|---|---|---|
| Event, memory and promotion-request validation | Implemented, checked, merged | Read-only offline CLI; valid structure is not evidence of truth or permission to adopt |
| Provenance sidecar and original evidence storage | Implemented, checked, merged | Synthetic-only SQLite library; atomic event/source/provenance capture |
| Replay, conflicting IDs and root deduplication | Implemented, checked, merged | Byte-identical replay, conflict rejection, generated artifacts cannot become independent roots |
| Stored evidence integrity checks | Implemented, checked, merged | Hashes, source presence and expiry; descendant capture also checks ancestors against configured current authorization revisions and evaluation partition |
| Verification/evaluation receipts and current control policy | Implemented, checked, merged | [First Gate 2B slice](gate-2b.md); 42 new tests, 152 combined, fresh installed-wheel checks passed |
| Candidate snapshot from parent + operations | Implemented, locally accepted, merged via PR #9 | [Pure planning](gate-2b-candidates.md); 22 new tests, 174 combined; no database write/adoption |
| Memory adoption and active-version updates | Synthetic core implemented, locally checked, merged (PR #10, #11) | [v3 writer](gate-2b-adoption.md); atomic journal/head, current receipts/policy and exact replay; versioned audit labels checked; registered-run integration/broader faults pending (full Gate 2B not complete) |
| Scoped retrieval (read-only library) | Implemented, locally checked, **merged (PR #13)** | [Gate 3 slice](gate-3.md); 4 local cases (0.782 s) and 3 CI cases at head `90b3d9e` passed before merge; UTF-8 byte budget, no tokenizer; evaluation-frozen retrieval and delivered-memory logging pending |
| Rollback (explicit control recovery) | **Implemented, UNEXECUTED**; branch `feat/gate-3-safe-rollback`, pending limited CI | [Gate 3 rollback](gate-3.md#safe-rollback-unexecuted-until-ci); restore a retained snapshot of the same scope with a new operation ID, CAS on head and policy, whole-or-nothing current revalidation; not a fresh adoption or evaluation claim; 3 cases reserved for one PR CI run |
| Deletion / physical purge / cache cleanup | Not implemented | Non-resurrection under current exclusions in retrieval/adoption/rollback is by recheck only; no physical deletion or index/cache cleanup |
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
- [Scope](gate-2b.md) / [acceptance and remaining limits](../reports/gate-2b-progress.md). That historical slice did not implement adoption; the subsequent v3 core is described below.

### Subsequent slice: pure candidate planning

- [Scope](gate-2b-candidates.md) / [acceptance](../reports/gate-2b-candidates-progress.md): five contracts and deterministic parent+operation candidate construction.
- 174 tests (152 prior + 22 new) and fresh outside-checkout installed-wheel checks passed. Publication/merge are recorded separately in the acceptance record and live PR.
- Candidate `active` labels and receipt-format builders are not actual activation or proof of commit. The subsequent atomic-writer core is now locally checked; full Gate 2B acceptance remains pending.

## Latest slice: Gate 3 safe rollback (implemented, UNEXECUTED)

[Rollback contract](gate-3.md#safe-rollback-unexecuted-until-ci): `AdoptionStore.commit_rollback` restores a retained, previously adopted snapshot of the same exact scope in one `BEGIN IMMEDIATE` transaction, with a new operation ID, explicit run audit label, expected head and expected policy revision. Every active target member is revalidated under the current authorization, expiry and exclusions; any failure refuses the whole rollback and leaves head and history unchanged. The rollback request digest and receipt are stored in the same transaction as the head so ACK loss resolves through operation lookup; exact replay returns the historical receipt and a same-ID different payload conflicts. New versioned artifacts `agent-sleep-rollback-request/1` / `-receipt/1`; adoption v1/v2 artifacts and replay are unchanged; no storage migration (v3 tables reused). **Rollback is control recovery, not fresh candidate adoption, and makes no performance or evaluation claim.** Three focused cases exist in `tests/test_rollback.py`; **none has been run**. They are the default of `tests/run_tests.py` and are reserved for one PR CI invocation. Not implemented: deletion/purge/cache cleanup, evaluation-frozen retrieval, delivered-memory logging, full Gate 2B acceptance, Light/Deep, comparison evaluation, adapter.

## Previous milestone: Gate 3 basic scoped retrieval (merged, PR #13)

[Gate 3 API and limits](gate-3.md): a read-only, synthetic-only library over `AdoptionStore` with one same-connection read transaction, current-policy/ancestor rechecks before ranking, fail-closed integrity handling, and an explicit UTF-8 byte budget. Dated observations: 4 selected local cases passed once (0.782 s) and 3 PR CI cases passed at head `90b3d9e`; PR #13 is merged. Same-trial accounting: **7 case executions / 2 invocations of 10 used**; the remaining 3 are reserved for the rollback PR CI run. The earlier writer trial (19 cases / 5 invocations) is historical and exhausted. See the [acceptance record](../reports/gate-3-retrieval-progress.md).

## Previous milestone: synthetic durable-adoption core (merged)

PR #9 is MERGED (`122fed26305a5d039de3d14b5c42633811b8affc`, `2026-11-09T22:19:24Z`). PR #10, #11 and documentation-only #12 are MERGED per fresh GitHub reads. The text below is the dated record from the feature-branch period; its "unmerged" and cap statements are historical.

[Scope, APIs and exact acceptance](gate-2b-adoption.md). Branch `feat/gate-2b-durable-adoption`, based on PR #9 head `31353d17035394840856283ad932c8005d120133`. Seven selected tests, one invocation, seven executions, all passed. No CI/wheel-runtime/full-suite rerun. A continuation passed three process cases once (SIGKILL before COMMIT, SIGKILL after COMMIT/before ACK, two spawned contenders); this trial now totals ten executions in two invocations and has no remaining test budget. The later [run-ID binding slice](gate-2b-run-id.md) passed three cases once (0.239 s), after explicit owner increase to 13 total. Cumulative trial: thirteen executions in three invocations, budget exhausted. Earlier ten cases were not rerun on this code. No new PR, merge or CI; feature-branch publication evidence is recorded separately. Muse Wonder supplied design advice; the implementation and local checks were separately reviewed/executed. This does not establish model coding-performance equivalence.

## Remaining Gate 2B acceptance targets

The first receipt/policy runtime slice and three schemas are locally accepted: 152 tests (110 prior + 42 new) and fresh installed-wheel checks passed. Review fixes cover exact schema recognition, malformed boundary inputs and receipt replay integrity. See [the acceptance record](../reports/gate-2b-progress.md) and [live PRs](https://github.com/moruku36/agent-sleep-lab/pulls) for publication/merge/CI evidence. Items 1–4 below are now implemented in the synthetic v3 core with focused acceptance; full Gate 2B is not complete. Versioned run-ID audit labels now have focused acceptance; trusted run registration and broader source/receipt/root and process-crash/ACK fixtures remain.

1. Resolve verification/evaluation receipts through separately configured simulated boundaries, not candidate-asserted identity. Bind receipts to exact memory/snapshot bytes, evidence, scope, method and protocol hashes.
2. Integrate the accepted pure candidate builder with the writer's trusted current parent and full ID history; reject unrelated omissions, unknown targets, ID collisions, cycles and scope changes.
3. Recheck current authorization/exclusions, original evidence and ancestors, expiry and expected parent in the same SQLite transaction as active adoption.
4. Commit operation ID, request digest, adoption receipt and active reference together; resolve lost acknowledgements through durable operation lookup.
5. Exercise forged/mismatched receipts, source change/loss, concurrent null-parent initialization, competing writers, process exits before/after commit and ACK loss with synthetic fixtures.

The [implementation contract and SLP-01–12 cases](contracts-and-acceptance.md) remain the acceptance basis; full SLP acceptance is pending. Gate 2A connection reopen/SQL rollback is not Gate 2B process-crash or power-loss acceptance. Promotion-time exclusion checks alone do not complete Gate 3 retrieval, rollback or deletion behavior.

## Current limits

- Capture is a locally configured boundary simulation, not authenticated users/adapters. Hashes do not prove truth or consent.
- `get()` is raw lookup; `verify()` checks stored integrity/expiry, not current revocation or adoption eligibility.
- Synthetic adoption is a library capability. The Gate 3 retrieval library is merged with focused synthetic acceptance, and the rollback writer is unexecuted; neither is live-agent integration. No sleep provider integration, production adapters or performance experiments. Real transcripts, credentials and private memory stay outside this public repository.
- Three local process-crash/concurrency cases passed; broader crash points, power-loss and network-filesystem durability remain unverified.

## Keeping this current

Update this page, its Japanese counterpart and README at meaningful implementation milestones. Distinguish designed, implemented, executed, pushed and merged, linking the exact PR/commit, CI and acceptance record. Keep incomplete work and genuine waits explicit; plans are not completed features.
