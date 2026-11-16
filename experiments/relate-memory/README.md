# Connected Recall

**English** | [日本語](README.ja.md) | [Core](../../README.md)

A proposed Relate extension that helps a forgetful agent find relevant memories,
follow corrections and explain the evidence path behind a recall bundle.
For current implementation and verification, see the
[single status authority](../../docs/implementation-status.md#relate-experiment).

## How Relate fits

SQLite remains canonical. Relate is a rebuildable relationship index used for
bounded traversal, candidate selection and explanation. Prefer a persistent .rl
file; use a directory store if the pinned Python binding requires it. This mode
choice must be confirmed by persistence/reopen acceptance before release.

The graph connects tasks, entities, memory versions, evidence, source versions,
supersession and observed use. The canonical store rechecks eligibility before
any content reaches a bundle. See the [design](../../docs/relate-memory-design.md)
and [decision](../../docs/decisions/0006-rebuildable-relate-projection.md).

## Implementation handoff

This is a design handoff, not an installation guide for a working Relate package.
Do not invent commands or results. Implement in this directory in the order
specified by the design, keeping the root package dependency-free of Relate.

Planned package name: asl-connected-recall; module: asl_connected_recall.
Add its own pyproject.toml, pinned dependency manifest, src/, configs/, tests/ and
synthetic fixtures/. First support a fixed core commit through one read bridge.
Expose explicit rebuild, inspect and compare operations only after they work.
The root agent-sleep-lab command remains the existing entry point.

Before claiming judge readiness, replace this handoff section with tested OS /
Python / Relate versions and exact install, rebuild, reopen, inspect and compare
commands. Record the actual artifact paths and hashes in submission/manifest.json.
Planned public store path: submission/connected-recall.rl (or a documented complete
store directory). That artifact does not exist merely because this path is listed.
Generate it only from reviewed synthetic fixtures. Keep private output in .state/.

## Isolation and rollback

Use a separate virtual environment and graph-owning process. No core migration,
mandatory dependency, automatic model call or scheduler. Stop this extension to
return to existing SQLite retrieval; do not overwrite canonical data.
The [baseline](BASELINE.md) preserves the starting code revision. Isolated feature
commits can be reverted while retaining unrelated core development.

## Submission preparation

[Reuse and AI disclosure](REUSE.md) distinguishes prior core code from new work.
The design records the event-rule questions and the December 12, 11:00 JST deadline.
Before submission, verify the relate repository topic, judge-readable synthetic
store, working instructions and a short demonstration. Do not submit this design
as a working graph integration. No license change is made here.
