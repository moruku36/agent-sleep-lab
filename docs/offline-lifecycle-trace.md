# Offline synthetic material → adoption → use → withdrawal

**English** | [日本語](offline-lifecycle-trace.ja.md) | [First run](first-run.md)

This is a **source walkthrough of an existing fixture**, not a new live operation,
status claim or production integration. No real document is fetched. It complements
the built-in demo: `temporary_state_removed` means disposable-store cleanup,
**not** authorization withdrawal or managed-content purge.

## Minimum reproducible entrypoint

From the checkout with runtime dependencies already installed:

```sh
PYTHONPATH=src python tests/run_tests.py test_public_document_runtime.PublicDocumentRuntimeTests.test_managed_text_purge_crash_recovery_and_unrelated_bundle_untouched
```

This selects **one synthetic case / one invocation**, not the whole module.
It is documented here but **not executed in this follow-up**: its four-case local
allocation is spent on text presentation; the four-case PR CI selects only those
presentation cases, not this lifecycle fixture.
Do not append this command to CI or run it without a remaining allocation.
Read [the fixture](../tests/test_public_document_runtime.py) without execution first.
It uses a fresh temporary directory, a fixed 2030 fixture clock, fictional
`example.test` source identity, and an injected offline callback; the URL is
metadata, never a fetch. Fixture role objects are not production authentication.

## Operations and verification points

| Step | Existing source operation | What to inspect |
|---|---|---|
| Material | `setUp`, `admit`: prepare exact fictional bytes and approval; approve generation 0 → 1, admit artifact | Source hash/scope/expiry bound; hostile instruction in source remains data |
| Proposal and receipts | `adopt`: quote “Fictional observatory opens at noon.”; separately issue verifier and mechanical evaluator receipts | Proposal is not its own verification; no Light/Deep or model required in this minimum slice |
| Atomic adoption | `store.adopt` with `EMPTY_HEAD`, generation 1, operation ID and both receipts | Exact bindings and parent checks gate the writer; fixture receipts do not establish scientific usefulness |
| Different-task use | `prepare` → `prepare_request`, then `dispatch(..., invoke=returning)` | Origin task “origin” differs from target “different”; packed adopted reference reaches injected callback; `observe` and returned bytes are observations, not independent semantic review |
| Before withdrawal | `store.inventory` | Exactly source_evidence, proposal, memory, snapshot, request, result are managed |
| Withdrawal failure | `control.withdraw(expected_generation=1)` with deliberately injected compaction failure | Exception and `purge_pending`: never claim deletion from the withdrawal attempt |
| Recovery | Reopen same store, `purge` | Audit state deleted; managed_records = 0; content-free operation_count = 1 |
| Scope of deletion | Check database bytes, WAL/journal paths, unrelated file | Fixture source/task/result/URI absent from database; no WAL/journal; unrelated bundle unchanged |

The same fixture's `test_observed_and_returned_are_not_independent_semantic_use`
separately illustrates hash-bound independent review; do not run it implicitly.
The callback's `consumer_used=true` and `semantic_use_confirmed=true` text is not
trusted evidence of semantic use. Neither this trace nor its assertions establish
performance improvement, actual-agent acceptance, measured costs or remote/backup
erasure. Content-free no-retry identity must not be reset to obtain a retry.

The public-document lifecycle is a separate store from the synthetic CLI demo.
For a host integration, read [lifecycle](public-document-lifecycle.md) and
[model boundary](public-document-model.md); this offline entrypoint grants no
authority for real data, models, APIs, exports or publication.
