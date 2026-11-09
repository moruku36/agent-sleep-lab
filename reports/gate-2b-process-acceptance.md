# Gate 2B process acceptance — 2026-11-10

Synthetic temporary SQLite databases only. Runtime code and v3 contracts unchanged.
Continuation of the existing writer trial, not a new test budget.

Command: `.venv/bin/python tests/run_tests.py --limit 3 test_adoption_process.AdoptionProcessTests`
Result: 3 cases passed, one invocation, 0.579 seconds. Prior 7 + current 3 = 10 case executions in two invocations. No retries, CI, full suite or matrix. Budget exhausted.

- Spawned writer: signal parent in SQLite trace just before COMMIT, with in_transaction true after all adoption writes; parent SIGKILLs child. Reopen: no memory/snapshot/journal/head rows; evidence/policy retained; same request can commit once.
- Spawned writer: test-only context wrapper signals after actual COMMIT (in_transaction false) but before commit_adoption returns. Parent SIGKILLs child, receiving no adoption acknowledgement. Reopen resolves original receipt; exact replay returns it without changing head or row counts.
- Two spawned writers open separate connections and wait at a pipe start gate. Both receive release signals for independently prepared null-parent proposals. Exactly one commits, the other gets parent conflict; losing operation absent, winner receipt/head/member bound and exactly one row per adoption table.

Bounded pipe polls/joins and cleanup kill/join only test-owned children. No sleeps, production hooks, network, model calls or real memories. This demonstrates selected local process exits and competing proposals, not every OS interleaving, power loss or network filesystem durability.

Local continuation on feat/gate-2b-durable-adoption, base 61253e314a96a9d1dd9c967dcf80dbd1c679c0e5; not committed/pushed/merged, no new PR/CI. Prior merged milestones are unchanged.
Full run-ID association, broader corruption/root/fault fixtures, present-time retrieval and later sleep/evaluation/integration work remain. Overall initial-version estimate remains approximately 30%.
