# Documentation

**English** | [日本語](index.ja.md) | [Home](../README.md)

Use [implementation status](implementation-status.md) for current capabilities,
merge/verification evidence and open gaps. Design pages describe contracts or
proposals; dated reports describe their tested versions, not current instructions.

## Run and integrate

| Goal | Guide |
|---|---|
| Try the synthetic, no-model walkthrough | [Built-in offline demo](runtime-guide.md#built-in-offline-demo) |
| Invoke sleep, review, adoption, retrieval or comparison explicitly | [Runtime guide](runtime-guide.md) |
| Stage reviewed public bytes without admitting them to a runtime store | [Public-source intake](public-source-intake.md) |
| Use the separate one-document store and its review/deletion/consumer boundaries | [Public-document lifecycle](public-document-lifecycle.md) |
| Prepare paired OSS inputs offline from adopted synthetic memories, without sending | [OSS request preparation](oss-prepare.md) |
| Account for a predeclared synthetic multi-task cohort, not live/holdout evidence | [Fixture cohort](oss-fixture-cohort.md) |
| Select an issue and inspect forced-judge provenance separately from the default v1 route | [Selected-issue offline probe](oss-selected-issue-probe.md) |
| Understand target-agent restrictions and the forgetful-agent assumption | [Integration boundaries (日本語)](integration.ja.md), [target-agent design (日本語)](dots-integration.ja.md) |

Public fixtures remain synthetic. A non-sensitive trial summary does not authorize
publishing its inputs/outputs or feeding real data into synthetic-only interfaces.
Native execution, test, publication and offline restrictions still apply to adapters.

## Design and evaluation

Keeping a transcript is not the same as learning from it. The experiment asks
what to retain, how to ground or revise it, and whether reuse improves outcomes
and total cost.

- [Architecture overview](architecture-overview.md): diagrams, source-module map and store boundaries.
- [Detailed architecture (日本語)](architecture.ja.md) and [contracts / acceptance](contracts-and-acceptance.md).
- [Schemas](../schemas/README.md) and [synthetic examples](../examples/README.md).
- [Evaluation design (日本語)](evaluation.ja.md), [research handoff](gate-4e-research-handoff.md) and [roadmap (日本語)](roadmap.ja.md).
- [Research basis (日本語)](research-basis.ja.md), [Sleep / dreaming design (日本語)](dreaming.ja.md) and [external-memory decision](decisions/0001-external-memory-first.md).

The initial-version target is capture → adoption → retrieval → Light/Deep → paired
evaluation → one existing-agent integration. REM, diary, schedules and wider
rollout are optional later work, not required parts of the quick start.

Background includes Google's [Sleep framework](https://research.google/blog/the-sleep-framework-a-new-way-for-llms-to-retain-knowledge-in-continual-learning/),
Anthropic's [components of agent memory](https://www.anthropic.com/research/components-of-agent-memory)
and OpenClaw [Dreaming](https://docs.openclaw.ai/concepts/dreaming).
This repository is not an official implementation or reproduction of those systems.

## Reports, not operating instructions

- [2026-11-12 public-source trial](public-source-trial-2026-11-12.md): a separate local, unmerged extension; publication of the report does not publish that runtime path.
- [2026-11-13 partial live development measurements](live-development-measurement.md): byte/time observations, incomplete acceptance and accounting limitations.
- Other dated gate reports are historical evidence. Consult [current status](implementation-status.md) before using them to infer available capabilities.

## Development checks

After installing from the repository as shown in the [quick start](../README.md#quick-start):

```sh
.venv/bin/python tests/run_tests.py
.venv/bin/python tools/check_docs.py
```

The regression runner deduplicates imported fixture aliases by test ID; explicit
affected test names can be supplied during repair. PR and main CI run Python 3.11
and 3.13 regression, relative documentation file links and wheel build, with no
paid model calls. The documentation checker does not validate anchors or external
URLs. See [repository instructions](../AGENTS.md) and [test policy (日本語)](testing-budget.ja.md).

## License

[Package metadata](../pyproject.toml) declares **UNLICENSED**; no open-source license is granted.
