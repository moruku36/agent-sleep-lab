# Gate 2B durable-adoption core

**English** | [日本語](gate-2b-adoption.ja.md) | [Status](implementation-status.md)

Implemented and locally checked on 2026-11-10. This is a **synthetic-only library milestone**, not full Gate 2B/SLP acceptance, a production deployment, or a retrieval adapter.

## APIs and storage

`agent_sleep_lab.adoption_store.AdoptionStore` extends the v2 runtime API using v3 storage. Supply the capture boundary plus separately configured `VerifierBoundary`, `EvaluatorBoundary` and a pinned `evaluation_protocol=(name, version, config_sha256)`. These are local simulations, not authentication.

Fresh files are created as v3. Existing v2 files are refused until an explicit `upgrade_store_v2_to_v3(path)`; v1 requires the existing explicit v1→v2 step first. The upgrade verifies exact supported DDL and atomically adds empty tables/triggers without rewriting evidence, receipts or policies. Legacy v1/v2 store classes refuse v3.

`commit_adoption(request_bytes=..., manifest_bytes=..., source_manifest_bytes=..., memory_bytes=...)` uses one `BEGIN IMMEDIATE` transaction to:

1. Bind the exact canonical request to submitted manifest/source hashes and raw memory bytes.
2. Reconcile operation ID before any attempt to reapply a historical operation. Identical requests return original receipt bytes; conflicting content is refused.
3. Compare the current policy revision and scope head, load the immutable parent and derive globally used IDs from the append-only memory table.
4. Construct the candidate using the existing pure builder. Resolve the registered evaluation by ID/hash and bind candidate, parent, operations, source, scope, trusted evaluator and pinned protocol/config hash. Require complete, passed, time-valid results.
5. For **every active member**, including carried members, recheck memory bytes/kind/expiry, registered verifier, evidence hashes, all ancestors, current authorizations/partitions/purposes and exclusions. Bind new source evidence to the registered receipt. Preference root origins must be user corrections; hypotheses cannot activate.
6. Persist immutable memory/snapshot bytes, request/manifest/source and committed receipt journal bytes, and update the scope head together. Return only after commit.

Audit-only reject/defer operations need no evaluation, write a journal entry and do not initialize or move a head. Historical global IDs refer to previously adopted memory records; merely deferred proposals do not reserve an adopted-memory ID.

`resolve_operation(operation_id)` is read-only reconciliation for acknowledgement loss. `current_snapshot(scope)` returns **historical metadata only**, never a currently eligible retrieval bundle. Replay can succeed after exclusion without changing the head or the current policy; it is not permission to reuse the memory.

## Current acceptance

Seven selected synthetic cases, **one local invocation, seven executions total**:

- Commit/reopen/replay, original receipt preservation, conflicting request and non-revival after exclusion.
- Audit-only scope remains uninitialized.
- Two connections propose the same null parent: the second stale commit is refused.
- Carried member excluded under the latest policy causes rollback.
- A registered evaluation with the wrong pinned configuration hash is refused.
- Injected failure at the final head write rolls back memory, snapshot and journal.
- Explicit v2→v3 upgrade preserves evidence and policy.

Command: `.venv/bin/python tests/run_tests.py --limit 7 test_adoption_store.AdoptionTests`. Result: seven passed on Python 3.13.18/macOS arm64. No full-suite, wheel-runtime, or matrix test was run. Three executions remain in the ten-case trial cap; default future PR CI selects only three affected cases. Do not rerun these seven just because CI or a session changes.

## Publication and remaining work

Branch: `feat/gate-2b-durable-adoption`, based on candidate-planning PR #9 head `31353d17035394840856283ad932c8005d120133`. PR #9 was observed OPEN before this development; this milestone is not merged and has no new PR/CI result. Commit/push receipts are recorded separately; a branch name is not delivery evidence.

Full Gate 2B still needs run-ID audit association with a versioned request contract, broader source/receipt corruption and preference-root fixtures, actual simultaneous multi-process contention and process exits before/after commit/ACK loss. SQL rollback and reopen are not process-crash, power-loss or network-filesystem durability evidence. Immutable SQLite hashes detect inconsistency, not coordinated forgery by a database owner.

Present-time retrieval/filtering, rollback/deletion semantics, Light/Deep coordinator, evaluation runner, one-agent integration, real adapters/authentication and measured performance remain pending. Overall initial-version progress is estimated at about **30% (roughly 25–35%)**, not measured from test counts and not a claim of performance improvement.
