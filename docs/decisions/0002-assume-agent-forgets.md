# ADR 0002: Assume the target agent forgets

- Date: 2026-11-08
- Status: accepted for design; implementation pending.

## Context

Some target agents keep internal memory that is explicitly incomplete and cannot be inspected or edited from outside. For ChatGPT dots, the official documentation states that a dot's notes are not a full transcript, that a new task does not automatically inherit the whole conversation, and that individual memory entries cannot be viewed or corrected externally. The service has also had recorded incidents in which dots did not respond at all.

A workflow that assumes the agent remembers will silently depend on behavior the operator cannot verify. Forgetting, non-response, and stale internal notes then surface as unexplained rework.

## Decision

The harness's external memory is the source of truth. The target agent's internal memory is treated as an unverified cache: useful when present, never a basis for correctness.

Continuity is delivered from outside. Each task request carries a short recall bundle: the decisions that apply (with provenance), a current state snapshot with its timestamp, the relevant verified memories within the injection budget, and pointers to the sources of truth.

Requests carry unique keys and an explicit pending state, so non-response is tracked as its own condition rather than mistaken for forgetting, and retries do not duplicate work. Tasks are scoped units; continuity does not depend on one long thread surviving.

## Consequences

Re-asking about settled decisions and repeating past mistakes become measurable workflow failures, not agent mysteries. The cost shifts to preparing recall bundles and state snapshots, which must be measured like any other memory maintenance cost.

Reset-style recovery on the agent side stays a human, last-resort action outside the harness. The design for the dots target is recorded in [docs/dots-integration.ja.md](../dots-integration.ja.md).
