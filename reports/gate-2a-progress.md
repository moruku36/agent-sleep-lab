# Gate 2A acceptance — 2026-11-10 JST

Status: **local acceptance passed** on macOS arm64 / CPython 3.13.18. Publication and Linux CI outcomes are separate observations; consult the feature PR and actual workflow runs.

## Delivered

- Strict locally packaged `agent-sleep-provenance/1` sidecar: event/source SHA-256, scope, fixed adapter identity/version, origin, lineage, timestamps, authorization reference/revision/purpose/retention/expiry and synthetic/evaluation partition.
- Synthetic-only library API for atomic event/source/provenance capture on standard-library SQLite; byte-identical replay, conflicting-ID rejection, independent-root/source deduplication, append-only triggers and read-only integrity lookup.
- Before adding descendants, the same write transaction checks all transitive ancestors/root for integrity, source presence, expiry, configured current authorization revision and evaluation partition. Existing corrupt records cannot be reported as successful replay.
- Storage ADR, bilingual usage/status docs, 23 new contract/behavior tests, and installed-wheel evidence acceptance helper. Existing Gate 1 CLI contracts and pinned dependencies are unchanged.

## Executed checks

- `.venv/bin/python tests/run_tests.py`: **110 tests passed** (87 existing + 23 new). Includes independent-connection races, partial-write SQL-failure rollback, connection reopen, corrupted/missing evidence, generated/root boundaries, scope/partition, expiry, current configured authorization revisions, strict fields/versions and unchanged CLI contracts.
- Final source/test blob hashes matched the tested snapshot after the development session ended; no unnecessary unchanged test rerun.
- Built the wheel, installed it into a fresh non-editable environment, and invoked both acceptance helpers from outside the checkout. New helper passed packaged provenance byte equality, synthetic capture/replay, lineage/root dedupe, connection reopen and read-only integrity verification. Existing helper passed all three CLI fixture kinds and error exits.
- Documentation check passed: 104 relative file links exist (anchors not checked).
- All databases and source records used in checks are synthetic, temporary and outside the repository. No real transcript, credentials or API clients were used.

## Development-session outcome

Implementation and tests were authored with Claude Code `claude-sonnet-5-5`. The initial bounded call timed out after saving code; its process was confirmed stopped, then the same retained project conversation was continued for targeted review fixes/tests/docs rather than relaunching the original task. That continuation saved the required artifacts but ended with `usage_limit_reached` (429), not a successful terminal result. No quota retry or model substitution was used. The main agent independently reviewed and executed the saved artifacts and finished acceptance/status documentation.

## Limits / next slice

- This is a local capture-boundary simulation, not authenticated provenance or proof of truth/consent. Database write access can rewrite both bytes and hashes; integrity checking detects inconsistency, not coordinated forgery.
- `get` is raw lookup. `verify` checks local stored integrity/expiry, not current caller permissions or revocation. Counts are stored independent roots, not confidence or currently eligible memories.
- Internal sidecar JSON encoding is not RFC 8785 JCS. No cross-harness snapshot canonicalization claim.
- Connection reopen and injected SQL rollback are **not** process-crash, power-loss, cross-process adoption or filesystem durability acceptance. Network/shared-filesystem use is unsupported. The successful wheel build retains the previously recorded setuptools license-table deprecation warning.
- No writable CLI, active-memory pointer, promotion, trusted verifier/evaluation receipts, exclusion ledger, retrieval, provider API, production adapter, migration or scheduler. Full SLP-01–12 runtime acceptance remains pending; these are partial evidence-store checks only.
- Next: Gate 2B trusted receipts/current exclusion policy and transactional adoption boundary with explicit failure/recovery tests. No remaining gate is implicitly complete from these results.

[English usage](../docs/gate-2a.md) / [日本語](../docs/gate-2a.ja.md) / [Storage ADR](../docs/decisions/0004-local-evidence-store.md).
