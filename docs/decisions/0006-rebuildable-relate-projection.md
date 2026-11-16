# ADR 0006: Rebuildable Relate projection behind an isolated experiment

- Date: 2026-11-17 JST
- Decision: recommended architecture for the Relate experiment; implementation is separate.
- Current availability and execution evidence: [implementation status](../implementation-status.md).
- Design: [English](../relate-memory-design.md) / [日本語](../relate-memory-design.ja.md).

## Context

ADR 0002 puts continuity outside a forgetful target agent. SQLite already binds
evidence, policy, receipts, adoption and recovery. Replacing that authority for a
short hackathon would combine a storage migration with a retrieval experiment.
Relate's graph can instead connect tasks, memory versions, evidence, corrections
and observed use while retaining existing eligibility rules.

## Decision

Choose SQLite authority plus a rebuildable Relate projection over full migration
or a visualization-only export. The experiment owns optional dependencies, config,
fixtures, tests and output in experiments/relate-memory/. Core imports no Relate
code, gains no mandatory dependency and keeps its existing database format.

Start with synthetic AdoptionStore data, one scope per bounded generation,
full rebuilds, a single graph-owning process/thread and explicit invocation.
A versioned manifest binds canonical head/policy, source and relation hashes.
There is no cross-store atomicity claim. Revalidate current canonical eligibility
and explanation paths before serving a new experiment bundle.

The new read/export bridge must preserve existing transaction and verification
checks; the current capped lexical bundle is not silently treated as a full
snapshot. Any additive core read port is a separate compatibility-preserving change.
PublicDocumentStore integration, incremental outbox, vectors and remote serving
are deferred. A standalone frozen viewer is a reduced-scope fallback, not evidence
of graph-enhanced recall.

## Consequences

Stopping the experiment restores existing retrieval without restoring an old
SQLite database. Projection loss is recoverable from authorized canonical data.
Stale/failed graph reads may fall back explicitly to SQLite; failed canonical
checks must never fall back to graph content.
Revocation invalidates graph generations and derived output as well as recall.
Unknown runtime capabilities and event-rule discrepancies remain documented
confirmation items. No production deployment, license change or submission is
implied by merging this design.
