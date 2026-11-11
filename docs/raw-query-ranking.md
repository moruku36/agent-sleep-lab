# Opt-in raw query ranking contract

[Current status](implementation-status.md) / [日本語の実装状況](implementation-status.ja.md)

`RawBaselineComparison` and `select_raw_evidence` in
[raw_baseline.py](../src/agent_sleep_lab/raw_baseline.py) accept
`raw_order="query_overlap_descending"` with the existing `query` argument.
Omitting it, or explicitly choosing `"event_id_ascending"`, preserves the default
event-ID selection, rules, serialized plan/context bytes and saved-plan replay.
No existing plan is migrated. A query alone still affects only memory retrieval.

The existing file-based `compare` manifest passes these options inside `retrieval`:

```json
{
  "scope": {"project": "p", "task_family": "t"},
  "max_bytes": 32768,
  "query": "dataset licence 記憶整理",
  "raw_order": "query_overlap_descending",
  "scan_limit": 256,
  "max_raw": 16
}
```

This fragment is the `retrieval` object, not the complete manifest. The existing
tasks, budget and evaluator identity remain required; answer keys stay in the
separate local rubric. This adds no command, provider, network or dispatch route.
The existing `--provider script` path uses synthetic replies.

The order must be one of the two exact strings. Ranked order requires a valid
UTF-8 string of 1–1,024 characters with at least one lexical term. Unknown orders,
missing queries, other types, lone surrogates, whitespace/punctuation-only queries
and overlong queries are refused before selection. Unicode-equivalent queries
still have distinct exact-byte identities and conflict on plan reuse.

Algorithm `raw_source_summary_bilingual_overlap`, version `1`, reuses
`retrieval._terms`: NFKC, casefold, punctuation-separated words, and Japanese
character unigrams plus overlapping bigrams. For each independently eligible row,
the integer score is the size of the intersection between distinct query terms
and the union of terms from stored UTF-8 source text and the event's `summary`
value. Repetition earns no extra score. Other event values, field names, IDs,
hashes, provenance and request framing do not contribute. Evaluator answers are
not ranking inputs; holdout and generated-answer origins remain ineligible.
Evidence prose is reference data and cannot grant permission or change policy.

All independently eligible rows are ranked by descending score, then ascending
event ID, **before** `max_raw` and whole-record request-byte packing. Zero-overlap
rows remain eligible, counted and ordered; they can be included after positive
matches. Memory retrieval keeps its existing zero-score exclusion. Both arms
receive the exact same ranked raw whole-record prefix under equal per-arm byte
and call limits; B may append eligible memories only after that raw prefix.

The existing exact scope, partition, independent-origin, current policy,
authorization, expiry, integrity and full ancestry checks remain in force.
The raw scan counts all evidence rows in the scope, including other partitions
and ineligible origins, and fails if it exceeds `scan_limit` (default 256,
effective maximum 1,024). The comparison's `max_raw` remains 1–64 (default 16);
the lower-level selector retains its existing 1–256 bound. Corrupt, missing or
oversized scans fail closed, including corruption in capped-out rows. No partial
selection is frozen. Existing request/reply byte ceilings are not token or money caps.

Only ranked plans add `rules.ranking`: algorithm/version, Unicode database
version, exact query and UTF-8 SHA-256, sorted normalized query terms and scored
fields. Existing rules also bind order, scan/raw caps, origins, partition and
memory retrieval settings. The context and plan hash bind these rules; report
and ranked audit expose them. Changes to order, exact query, algorithm/version,
Unicode database or settings conflict on saved-plan reuse. Identical reuse
returns frozen bytes without rescanning; execution and report still recheck the
current context. Every eligible row's event/source/provenance hashes contribute
to the eligible-set digest, including zero-score and capped-out rows. Any change
invalidates current context and stops further dispatch without refreshing the
plan or resending completed/unknown arms.

This is a bounded synthetic lexical contract, without semantic relevance,
morphological analysis, fairness or improvement evidence. `complete_raw_baseline`
remains false and fairness/performance claims remain null. Raw scan, memory
retrieval and later checks remain separate reads; the existing race between a
check and dispatch remains. Current verification and merge state are recorded
only in the two implementation-status pages.
