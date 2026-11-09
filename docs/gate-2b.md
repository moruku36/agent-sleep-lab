# Gate 2B, first slice: receipt contracts and current policy

**English** | [日本語](gate-2b.ja.md) | [Home](../README.md)

Status: **first slice locally accepted on macOS arm64 / Python 3.13.18: 152 tests passed (110 existing + 42 new).** A fresh installed wheel passed receipt/policy checks outside the checkout. Publication/merge/CI are separate observations; see the [acceptance record](../reports/gate-2b-progress.md) and [live pull requests](https://github.com/moruku36/agent-sleep-lab/pulls). **Gate 2B as a whole remains incomplete. There is no active memory or adoption writer.**

## Implemented

- Strict, versioned packaged contracts for `agent-sleep-verification-receipt/1`, `agent-sleep-evaluation-receipt/1` and `agent-sleep-control-policy/1`, mirrored in repository `schemas/`. Bounded artifacts, strict JSON parsing, cross-field checks and exact identifier/hash/time/purpose/partition matching. Legacy schemas/CLI are unchanged. Internal canonical encoding is not RFC 8785.
- `runtime_artifacts.py`: validation/encoding and separately configured simulated `VerifierBoundary`, `EvaluatorBoundary`, `ControlBoundary`. Claims cannot supply boundary identity/version/time. Permitted method/protocol name+version pairs come from the boundary. This is not authentication or a truth verifier.
- `runtime_store.py`: explicit store format v2, immutable receipt registration, exact ID/hash resolution, persisted policy revisions with expected-current CAS, additive exclusions and `eligibility_failures`.

## Storage and upgrade

[ADR 0005](decisions/0005-runtime-store-extension.md) defines v2 as Gate 2A tables plus `receipts` and `policy_revisions`. Fresh files are created as v2. `RuntimeStore` refuses v1 until explicitly upgraded with `upgrade_store_v1_to_v2`; v1 APIs refuse v2. Upgrade adds empty tables and preserves evidence/source/lineage bytes. It is not a legacy-memory migration.

Opening v2 and upgrading v1 compare tables, indexes and triggers against exact supported DDL created in a schema-only in-memory reference. Missing/replaced triggers, column drift, foreign/unknown versions and unexpected application objects fail closed. This is compatibility/inconsistency checking, not protection against a coordinated database forger. Partial extension failure rolls back to v1; temporary synthetic upgrade/reopen checks have run, not production migration or power-loss acceptance.

Runtime evidence, receipts and policy read through the **same store connection**. The schema-only reference connection never reads runtime data. A later writer can use these helpers inside one `BEGIN IMMEDIATE` transaction; a helper called standalone does not promise a stable cross-call snapshot. Another connection cannot change policy while that transaction holds the write lock. No adoption transaction exists yet.

## Receipt and policy semantics

- Registration methods accept configured boundary objects separately from claims. Verification registration binds current stored evidence hashes/scope/integrity; evaluation registration records a fixture assertion, not a checked candidate adoption result.
- Resolve only by receipt kind, ID and exact SHA-256. Corrupt bytes or inconsistent stored identity columns fail closed. Re-registering the same claim preserves original issue time/hash; it does not refresh validity. Different content conflicts.
- Policy is append-only, outside memory snapshots. `expected_revision=0` initializes; subsequent writes require the current revision and assign `n+1`. Reopen never resets it. Missing/corrupt policy fails closed. Exclusions may only grow in this slice.
- Eligibility rechecks receipt memory hash/scope, configured verifier/method, confirmed outcome, issue time/expiry, evidence plus ancestors/root, current authorization revision, accepted purpose/partition and exclusions. Read failures stop the check. All evidence remains synthetic.
- An empty failure tuple is only a point-in-time fixture binding/policy result. It does not verify memory text/kind, authenticate a caller, grant permissions or activate memory. Evaluation matching and preference/hypothesis rules remain the future writer's responsibility.

## Executed checks

`.venv/bin/python tests/run_tests.py` passed **152 tests**. The 42 additions cover contracts, forged claim identity, receipt resolution/tampering, current exclusions/expiry/authorization, policy CAS/reopen, one-connection locking, v1/v2 schema guards, preserved evidence and upgrade rollback. These are independent-connection/sequential-policy checks, not cross-process adoption races.

The wheel was installed in a fresh environment. [check_runtime_installed.py](../tools/check_runtime_installed.py), invoked outside the checkout, checked all new packaged schemas, explicit upgrade, capture, verification/evaluation registration, resolution, policy CAS, ancestor exclusion and reopen. Gate 1 and 2A installed checks also passed. CI includes the runtime helper on Python 3.11/3.13; read actual workflow results before claiming CI success.

## Pending

Operation/candidate/source-manifest/committed-operation contracts, parent-based candidate construction, memory-kind rules, exact evaluation acceptance, active pointer, operation-ID/digest durability/replay and atomic adoption. Concurrent adoption initialization/writers, process-crash and ACK-loss acceptance are unimplemented. Gate 3 retrieval/rollback/deletion and full SLP-01–12 acceptance remain pending. No writable CLI, real adapter/provider, schedule, production data or performance claim.
