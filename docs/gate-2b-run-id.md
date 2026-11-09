# Versioned run-ID audit binding

**English** | [日本語](gate-2b-run-id.ja.md) | [Current adoption API](gate-2b-adoption.md)

Status: implemented and locally checked on 2026-11-10; three selected cases passed once. Local feature-branch changes are not merged and no new CI was run. Muse Wonder supplied design advice through a successful explicit `meta/muse-wonder-1.0` call; implementation and checks were separately performed. Overall initial-version completion is about 35% (roughly 30–40%).

## Contract decision

Keep request/1 and committed receipt/1 schemas, stored bytes and hashes unchanged. Add separate strict `agent-sleep-adoption-request/2` and `agent-sleep-committed-operation-receipt/2` schemas, each with all existing fields plus required `run_id`. Use the existing bounded ASCII ID rule: `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`. Do not trim, normalize or manufacture a legacy run ID.

The v2 request digest binds run_id. The writer copies it into receipt/2 and reconciliation verifies exact equality. Receipt/2 retains the existing fields; manifests remain transitively bound through request_sha256 rather than inventing redundant unvalidated fields.

run_id is a **caller-supplied audit label**, not registered identity, authorization, a run registry entry or proof that evaluation belongs to a trusted run. Full run registration and coordinator audit remain later work.

## Write/replay policy

- New builder calls require an explicit run_id and emit v2. New operations must use v2; unknown versions fail closed.
- Validate submitted canonical bytes and payload bindings, then resolve the global operation ID within the existing transaction.
- Exact legacy request/1 replay returns the original stored receipt/1 unchanged. No rewriting/backfill, new head update or renewed current permission.
- Same operation ID with another run_id, another payload or a v1/v2 conversion conflicts. The operation namespace stays global, not keyed by (run_id, operation_id).
- A new v1 operation is rejected after replay lookup. Old pure codecs remain available for historical inspection; no implicit emission of a v1 write by the main builder.
- Audit-only reject/defer **keeps the existing journal protocol**, now with request/2 and receipt/2 and run_id. It requires no evaluation and must not create/move a head. Receipt outcome audit_only is never adoption evidence. This corrects the incompatible portion of the model advice.
- Current policy/parent/evidence checks and atomic memory/snapshot/journal/head commit are unchanged.

## Storage and codec changes

The current v3 DDL stores generic blobs/digests and does not constrain payload schema identifiers. No run_id column or schema migration is needed for this additive payload change. Keep database user_version 3 and all immutable rows unchanged. Old applications still cannot read v2 payloads; updated library code is required. A future indexed run query would need a separately reviewed migration.

Implement a bounded strict version dispatcher for only the two request/receipt versions; do not let untrusted schema IDs become filesystem paths or remote URLs. Retain artifact kind/semantic checks and byte-canonical verification, with explicit version-selected schema validators. Version pairs must match (request/1 -> receipt/1; request/2 -> receipt/2). Do not broaden unrelated artifact schemas.

Affected code: runtime_artifacts.py (version dispatch and packaged schema checks), adoption_candidates.py (builder/receipt fields), adoption_store.py (legacy replay before new-write policy and reconciliation bindings), top-level and packaged schemas, and narrowly selected synthetic fixture callers.

## Three selected acceptance cases — passed once

1. **Legacy journal preservation:** a manually seeded, frozen-contract synthetic v1 journal/head is reopened with new code; exact replay returns original request/receipt bytes and hashes without head movement, even after current exclusion. No invented run_id.
2. **v2 identity conflict:** one v2 commit with run_id A succeeds and binds run_id in receipt; changing only run_id to B for the same operation ID is rejected with unchanged journal/head and no duplicate.
3. **Audit-only/version gate:** new v1 operation is rejected without writes; v2 defer with a run_id commits only the journal, no evaluation/head/snapshot. Historical v1 and new v2 entries remain readable together.

Owner approved a specific increase from 10 to 13 total executions. Command: `.venv/bin/python tests/run_tests.py --limit 3 test_adoption_run_id.RunIdTests`. Result: three passed in one invocation (0.239 s); same writer trial totals 13 case executions in three invocations. No retries, CI, full suite or matrix. Budget exhausted again. Earlier seven writer and three process cases were not rerun on this code and remain historical results. The v1 fixture is manually seeded, not a previously installed binary upgrade test. Malformed-version/receipt-corruption expansion and old-binary/package/crash reruns remain unexecuted. [Acceptance record](../reports/gate-2b-run-id-acceptance.md).
