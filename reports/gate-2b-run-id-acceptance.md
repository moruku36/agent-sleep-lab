# Run-ID binding acceptance — 2026-11-10 JST

Synthetic-only local library milestone, not authenticated run registration or completed Gate 2B.
Branch feat/gate-2b-durable-adoption; prior pushed base61253e314a96a9d1dd9c967dcf80dbd1c679c0e5. These continuation changes are not yet committed/pushed at record creation; no PR/merge/CI. Publication evidence is recorded separately in the private handoff/final response.

## Implementation

- Separate strict request/2 and committed receipt/2 schemas require bounded ASCII run_id; public and packaged copies added. v1 schema bytes unchanged.
- Fixed allowlist dispatch selects only v1/v2 validators and preserves canonical-byte checks and existing semantic rules. No arbitrary schema paths/URLs.
- Main request builder requires explicit run_id and emits v2; receipt builder copies it and emits matching version. Label is not registered identity/authorization or verified evaluation-run association.
- Writer resolves existing global operation ID first: exact legacy replay returns original receipt; changed content/run conflicts. New v1 operations rejected before adoption writes. Reconciliation checks version pairing and run_id equality.
- Audit-only keeps existing journal protocol and no-head/no-evaluation semantics. No DB migration, v3DDL/user_version unchanged.

## Executed acceptance

Owner explicitly increased the SAME writer trial cap from10 to13. Exactly3 selected cases in ONE invocation:
.venv/bin/python tests/run_tests.py --limit 3 test_adoption_run_id.RunIdTests

Result: 3 passed in0.239s. Prior7 + prior3process + current3 =13case executions, three invocations. No reruns, CI, full suite, matrix or wheel install checks. Budget exhausted; no extra execution without applicable specific approval. Earlier10 results remain historical, not current-code regression evidence.

1. Manually seeded frozen-contract v1 adopted journal/head; reopen after exclusion; exact replay preserves stored bytes/hash/receipt/head/policy and v3header, no fabricated run_id.
2. v2 active request/receipt bind run-A; change only label to run-B for same global operation ID conflicts, no extra rows/head change.
3. Newv1 audit-only request refused without journal write; seeded historicalv1 audit and newv2 audit coexist; no memory/snapshot/head/evaluation, reopen and legacy replay preserve both receipts.

## Limits and next work

The historical fixture is explicitly constructed from the v1wire/DDL contract, not a previously installed old application upgrade. Unknown-version/missing-label/receipt-corruption cases, broader source/root fixtures, installed-wheel and process tests on this code were NOT executed.
Run registration/coordinator audit, present-time retrieval, rollback/deletion, Light/Deep, comparative evaluation and one existing-agent integration remain. Overall scope estimate ~35% (rough30–40%), not test-count-derived or measured improvement.

Muse Wonder returned public design advice successfully. Main agent rejected incompatible advice to separate audit-only into another protocol; accepted existing semantics and reviewed code independently of that advice.
