# ADR 0003: Separate reflection from evidence and promotion

- Date: 2026-11-09
- Status: accepted for design; runtime and experiments pending.
- Reference: [OpenClaw Dreaming](https://docs.openclaw.ai/concepts/dreaming), read 2026-11-09 JST. This is an architectural reference, not a dependency or a reproduction claim.

## Context

External memory needs a way to discover reusable lessons without converting generated reflections into facts. The existing design already separates evidence verification from held-out evaluation and assumes target agents forget. Adding a dreaming stage must preserve those boundaries.

## Decision

Use one bounded sleep run with Light (selection), optional REM (hypotheses and proposed checks), and Deep (validated memory-operation proposals). Keep the first A/B pilot to Light plus Deep. Test REM as a separate intervention only after that baseline works.

The harness, not the generating model, validates provenance, scope, evidence freshness, permitted operations, budgets, and the parent snapshot. Verification changes a memory's status; evaluation and an atomic parent check govern activation. Never turn a memory into permission to act.

Keep any human-readable diary outside the evidence and normal retrieval paths. Preserve references to original observations rather than counting recycled model output as new evidence. No automatic schedule, provider connection, public diary, or target-agent memory mutation is enabled by this design.

## Consequences

The approach adds explicit run-state and provenance contracts before runtime adoption. A failed proposal leaves the previous active snapshot intact. Deletion exclusions apply to retrieval, promotion, replay, and rollback. Component costs and failure reasons must remain visible.

Do not copy another system's defaults or score thresholds without validation. Do not require multiple occurrences for every explicit correction. Defer free-form whole-memory rewrites, automatic compaction, and production scheduling. See the [execution design](../dreaming.ja.md) and [evaluation plan](../evaluation.ja.md).
