# Gate 2B second slice: pure candidate planning

**English** | [日本語](gate-2b-candidates.ja.md) | [Home](../README.md)

Status: locally accepted on macOS arm64 / Python 3.13.18: **174 combined tests passed (152 prior + 22 new)** and fresh installed-wheel checks passed outside the checkout. This is a pure, offline planning library. **It does not write a database, commit an adoption, activate memory or establish current eligibility.** See the [acceptance report](../reports/gate-2b-candidates-progress.md) for executed scope and [live PRs](https://github.com/moruku36/agent-sleep-lab/pulls) for delivery state.

## Implemented

Five strict packaged runtime contracts: operation manifest, source manifest, candidate snapshot, adoption request and committed-operation receipt **format**. All have mirrored repository schemas. Legacy v0.1 and `sleep-promotion/1` contracts/CLI are unchanged. These helpers do not register artifacts in a store or migrate legacy proposals.

`agent_sleep_lab.adoption_candidates` provides:

- `build_candidate`: validate canonical artifact bytes, check parent bytes/hash/scope, construct a candidate from operations and proposed memory bytes. No caller-supplied full replacement is accepted.
- `build_adoption_request`: bind operation ID, constructed candidate hash, parent, operation/source hashes, expected single policy revision and evaluation reference.
- `build_committed_receipt`: format proposed receipt bytes/digest with request/policy consistency and an aware timestamp. **Despite the format name, returning these bytes is not evidence that anything committed.** Only a future writer may persist/acknowledge that result after a real transaction.
- `evidence_origin_failures`: pure kind rules over caller-supplied root-origin labels. It does not discover or authenticate origins.

## Operation semantics

- `add`: new ID, no supersedes; candidate member becomes `active` within the **proposed snapshot only**.
- `supersede`: new ID points to exactly one active target; retain old member/hash as superseded and add its successor. Untouched members are preserved.
- `mark_stale`: retain the member/history, mark it stale rather than false. Only active targets are permitted.
- `reject` / `defer`: audit-only for proposed non-member IDs, never remove existing members. A run containing only these has `changed=False` and no new snapshot/evaluation; no initialization occurs.
- Duplicate touched IDs, unknown/inactive targets, scope changes, missing/extra memory bytes, hash/source mismatches, repeated evidence IDs, inconsistent supersedes and oversize candidates fail closed. No silent eviction. A caller supplies `known_ids` for historical/global reuse checks; database-wide uniqueness is **not** proven here.

Artifact encoding is internal sorted-key compact ASCII JSON, not RFC 8785. Operations must be canonically ordered; snapshot members sort by ID. Maximums: 64 operations/source entries, 256 members, 32 evidence references per source entry, 256 KiB per artifact. Excess history is rejected, not dropped. Raw memory bytes retain their exact hash identity; legacy memory validation and expiry/kind checks apply to new items. The source manifest covers new add/supersede memories only; carried-forward evidence must still be rechecked by the future writer.

## Boundaries still pending

The parent is supplied by the caller, not resolved from a trusted active pointer. No database transaction, current policy CAS, verifier/evaluation resolution, full-source integrity/authorization recheck, durable global-ID reservation, operation replay, run-ID audit association or committed receipt storage exists. The combined policy revision is intentionally distinct from legacy separate authorization/exclusion fields; adoption integration/mapping is pending. Candidate `active` labels and formatted receipts confer no permission or truth.

Hypotheses cannot be proposed as active. Preference roots must be user-correction labels under the pure rule, but binding those labels to trusted stored provenance remains pending. Merely including an evaluation receipt reference does not check its actual snapshot/protocol/config/result. No SLP runtime adoption case or crash/ACK-loss acceptance is complete from this slice.

## Executed checks

`.venv/bin/python tests/run_tests.py`: **174 passed**. Tests cover deterministic construction, parent/hash/canonical bytes, all operation types, preservation/history, duplicate/unknown/reused IDs, memory/source/scope/expiry/kind constraints, no eviction, snapshot cycles, request/receipt shape and time/policy consistency.

A fresh wheel passed [check_candidates_installed.py](../tools/check_candidates_installed.py) outside the checkout: all runtime schemas, deterministic add/supersede/history and request/receipt-format binding. References in that helper are symbolic synthetic data, not registered evidence. The existing CLI, evidence and receipt/policy wheel helpers also passed. The original CI included this helper on Python 3.11/3.13. The later [owner test-budget policy](testing-budget.ja.md) replaces automatic full/matrix/wheel-acceptance runs with 3 selected cases on PRs/Python 3.13. The 174-case and installed-wheel results here are historical acceptance of the implementation, not repeated on every subsequent commit.
