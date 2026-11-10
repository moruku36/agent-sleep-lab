# Gate 3 rollback slice — implementation and planned acceptance

Date: 2026-11-10 JST. Branch: `feat/gate-3-safe-rollback`, based on main `9e3d1107f96034b61a812ab2a5abb1c95ef5eaba` (verified owner-merged PR #13). Initial-version progress remains approximately 40% until focused acceptance is verified. This report is the pre-CI record; live PR checks supply later execution evidence.

## Implementation and review

Synthetic-only explicit control recovery to a retained previously adopted snapshot, not fresh candidate adoption or an evaluation/performance claim. New canonical rollback request/receipt version1 with separate allowlisted schemas. Existing adoption-v1/v2 schemas remain unchanged. The v3 DB layout is unchanged: rollback journal entries hold request/receipt bytes and strictly empty adoption-manifest/source columns. Old binaries cannot read the new row kind; no downgrade guarantee.

One writer transaction resolves operation identity, checks expected current head and policy revision, verifies retained target bytes/scope and its original committed adoption receipt, revalidates every active target memory against present expiry, registered verification receipts, evidence/ancestors, authorizations and exclusions, then atomically writes audit receipt and head. Any failure refuses the whole target without filtering or rewriting history. Exact replay only returns original receipt, even after later head/policy changes. A reused ID with different payload conflicts. Current permissions never come from an old snapshot.

Main-agent review added explicit original-adoption-receipt proof (orphan snapshot rejected), strengthened replay after a later successful adoption, and included adoption-v2 replay while the rollback head is current. Historical source bytes remain unchanged. The target-receipt lookup currently scans the local journal; no production-scale performance claim.

## Exactly three focused CI methods (not yet executed)

1. Scope-bound successful rollback, refusal of cross-scope and orphan targets, unchanged original memory/snapshot/journal bytes, original adoption-v2 exact replay, retrieval of restored head and subsequent normal adoption.
2. Present revocation rejects the whole target with head/history unchanged; a smaller fully eligible historical target is explicitly restorable; excluded memory cannot be revived later.
3. Stale-head/policy conflicts, ACK-loss resolution across reopen, exact rollback replay after a later successful adoption and later revocation, ID conflict with unchanged current head/history.

`tests/run_tests.py --list --limit 3` selects exactly these methods and executed **zero test bodies**. Public/package copies of both new schemas match. Relative documentation links:238 passed before final prose-only publication wording adjustments; anchors not checked. Whitespace check passed at review.

## Budget and delivery

SAME Gate3 trial: PR13 local4cases/1invocation plus CI3cases/1invocation =7executions/2invocations used. Rollback has0executions at this commit. Remaining3 are reserved for ONE existing PR-only CI run on Python3.13; it will reach10executions/3invocations, exhausted. No local rollback tests, fullsuite, matrix, installed-wheel runtime checks, duplicate push/PR CI or reruns. The earlier writer trial19/5 is historical/exhausted, not reset. If acceptance fails, further tests require an explicit budget increase after diagnosis; no automatic rerun.

## Remaining limits

No current rerun of legacy-v1 binary migration, full historical regression, all corrupt-journal/expiry paths, rollback-specific injected late-write failure or crash/power-loss durability. Existing synthetic process acceptance is dated adoption evidence, not rollback fault acceptance. Run ID is an audit label, not run registration or caller authentication.

Deletion/physical purge/cache cleanup, evaluation-snapshot freezing, delivered-memory logging, full Gate2B registration/fault acceptance, Light/Deep coordinator, comparison evaluation and one existing-agent integration remain pending. No real transcripts, private memory, credentials, live provider calls, production actions or recurring jobs were added.
