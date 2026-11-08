# ADR 0001: Start with external memory around existing agents

- Date: 2026-11-08
- Status: accepted for the initial design; implementation pending.

## Context

The project aims to test sleep-time consolidation in the owner's existing GitHub and AI-agent workflows. Google's Sleep framework updates model weights. Anthropic's article concerns external memory retained across sessions. These are different intervention levels.

## Decision

Start with external evidence-backed memory, explicit snapshots, retrieval, and held-out evaluation. Add adapters around existing agents rather than migrating them to a new runtime. Preserve their execution budgets and publication policies.

Keep real logs and private memories outside the public repository. Version public design and sanitized experimental reports through PRs. Do not configure a recurring schedule in the initial version.

## Consequences

The first pilot can run without training infrastructure. Any measured improvement is a workflow result, not evidence that model weights improved. Retrieval alone is a required baseline. Maintenance costs, stale memories, and incorrect consolidation must be measured.

A standalone durable agent runtime, including eve as a candidate, can be evaluated in a later ADR if needed. Weight updates require a separate research plan and cannot be described as implemented by editing memory files.
