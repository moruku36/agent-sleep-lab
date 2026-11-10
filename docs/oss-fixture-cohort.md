# Frozen synthetic fixture cohorts

[Current status](implementation-status.md) | [日本語の状況](implementation-status.ja.md)

## Contract and registration

[CohortRegistry](../src/agent_sleep_lab/oss_fixture_cohort.py) stores a separate
local SQLite registry, with its own application ID, version and exact schema.
An absolute private path and explicit `initialize=True` are required for a new
registry. Foreign/changed schemas are refused before writes; there is no migration.
No execution, inference, adoption or publication method belongs to the registry.

First register every required plan in the existing
[ExecutionJournal](oss-durable-execution.md), with its pre-frozen
[fixture manifest](oss-verdict-evaluation.md). Read each member's exact pins using
`member_identity(journal, plan_id, bridge)`, then call:

```python
registry.register("synthetic-cohort-v1", journal=journal,
                  members=members, bridges=bridges_by_plan_id)
report = registry.report("synthetic-cohort-v1", journal=journal,
                         bridges=bridges_by_plan_id)
```

`members` is an explicit list of two to five dictionaries, each with **exactly**
`plan_id`, `binding_sha256`, `manifest_sha256`, `task_sha256`, and `issue_number`.
IDs are bounded to 128 ASCII characters; hashes are lowercase SHA-256. The task
hash identifies the whole built-in fixture suite, so the issue number (1–5) is
also part of task identity. Duplicate plans or tasks are rejected, even when a
task has a different plan ID or answer label. No real task importer is supplied.
The five built-in issues remain synthetic development fixtures, never an
independent holdout or independent evidence.

All member plans must already exist with exact matching pins, valid current
manifests and current reference contexts. A new cohort is refused if **any**
member has any arm intent/outcome row or is stopped. A short `BEGIN IMMEDIATE`
reservation on the execution journal excludes intent writers while the separate
registry transaction commits the complete cohort. It writes no journal data
and spans no transport. This enforces registration timing for cooperative journal
writers without changing the execution protocol or adding a dispatch method.

Membership is sorted by issue number and immutable. Exact registration replay
under an existing ID returns the same contract, including after execution;
creating a new cohort after execution is refused. Changed pins, membership or
comparison settings under an existing ID conflict. Registry documents have an
8,192-byte cap, exact JSON fields/types, canonical encoding and an integrity hash.
The frozen document contains only protocol, cohort ID, fixed
`synthetic_development_fixture` partition, registered-task count, member pins and
comparison-settings hash. It contains no prompts, reference text or answer labels.

## Comparability and reporting

Comparison settings must match conservatively across all members: execution
protocol/kind, adapter/model/transport and limits, source suite and commit,
worker provenance, bridge scope, retrieval settings, exact reference/context,
non-prompt request fields, capture comparability and evaluator settings (including
dataset ID and implementation/dependency hashes). Only issue identity, task
prompt and fixture answer may vary. Full binding/manifest hashes pin those bytes
too. Model/provider labels retain the journal's provenance limitations; injected
transport results are not live model receipts.

Aggregation reads a journal snapshot through its existing current-context and
integrity-checked reports. It writes neither database, recovers no intent and
dispatches/retries nothing. Reports allowlist identity pins, execution/evaluation
statuses and numeric scores/counts. Reply bodies, parsed verdict decisions,
rationales, answer labels and transport receipts are never copied into them.

- The denominator is always `registered_tasks`, including every incomplete task.
- Invalid **completed** verdicts score zero and count as failures, with explicit
  invalid-verdict counts. They do not trigger a retry or shrink the cohort.
- Missing/unstarted/unknown outcomes, missing plans/bridges, withheld context,
  changed identities/settings, integrity failures or unavailable evaluator
  versions remain explicit incomplete task rows with unavailable scores.
- `observed_successes` and `scored_tasks` describe available arm scores only.
  They are not success rates over a reduced denominator. Both `mean_score` values
  and overall `reference_minus_baseline` stay null unless **all** registered tasks
  have comparable, complete pairs. Missing scores are never zero-imputed.
- A complete cohort reports the mean task-level reference-minus-baseline score
  difference, including zero scores for invalid completed verdicts. This is a
  descriptive fixture calculation, never an adoption or scientific performance
  claim. Usage/cost remain `unavailable`, never zero.

Each report rechecks each supplied plan's bridge and current reference context;
revocation/unavailability withholds that plan's saved scores. Unclosed intents
remain unknown; only the original executor can persist its existing terminal
recovery behavior. Saved outcomes replay without additional provider calls.

## Boundaries and coordinator checks

The registry is local integrity/accounting, not database/store-origin
authentication, physical erasure, distributed coordination, or a cross-store
policy transaction. Cooperative SQLite writers obey the reservation; direct file
tampering is outside this timing guarantee. A policy change after a context read
can race reporting, as with the underlying journal. Distinct cohorts must not be
pooled as independent samples of these same fixtures.

The actual pinned capture worker still selects the one borderline issue (#3).
The [cohort regression source](../tests/test_oss_fixture_cohort.py) uses explicitly
labelled stand-in captures for other built-in issues; it does not broaden that
worker or establish real five-task execution. Parser/evaluator implementation
bytes, execution protocol, provider limits and no-retry behavior are unchanged.
There is no confidence interval, rationale-quality scoring, independent dataset,
live-model verification or total-cost measurement here.

The coordinator reviewed the preserved worker draft and ran all 352 unique
regression cases in one invocation on Python 3.13.18: passed in 24.123 s,
including 13 new cohort cases. These are mock/stand-in behavior checks, not live
model or actual multi-task target acceptance. Current publication and CI status
remain in the implementation-status pages.
