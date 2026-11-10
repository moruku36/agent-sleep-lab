# agent-sleep-lab

**English** | [日本語](README.ja.md)

An experimental harness that adds a sleep phase to existing AI-agent workflows: retain evidence, consolidate useful memories, verify them, and retrieve relevant experience for the next task. The aim is to measure changes in task success, repeated mistakes, human corrections, and total cost across GitHub-centered workflows.

## Gate 4A acceptance — 2026-11-10

[PR #17](https://github.com/moruku36/agent-sleep-lab/pull/17) remains unmerged.
Head `a5d64acb294186c840fee7222be5f000661940e2`;
[CI42772057834](https://github.com/moruku36/agent-sleep-lab/actions/runs/42772057834)
passed **5 new cases / 1 invocation, 0.197 s**, plus wheel build, Ubuntu / Python 3.13.18.
Local execution: zero. This trial totals 5 case executions / 1 invocation.
Documentation-only follow-up does not trigger duplicate CI.
The accepted synthetic capture→Light→Deep→independent receipts→adoption→retrieval
slice justifies an overall initial-version estimate of **35–40%**.
Production integration, comparison evaluation and broader fault acceptance remain incomplete.

**Current status: initial version about 35–40% complete.** Foundation review fixes are merged through PR #16 (8e2f871). The feature branch now implements [Gate 4A](docs/gate-4-light-deep.md): offline fake-provider Light/Deep, locally bound runs, conservative budget reservations, checkpoints and existing-writer handoff. **Five focused CI cases passed; this slice is unmerged.** It is not a live sleep engine.

Five new cases passed in one PR-only CI invocation, with no local duplicate. The historical Gate 3 trial remains exhausted at 23 case executions / 5 invocations and is not rerun. Comparison evaluation and one existing-agent integration remain unimplemented; no performance improvement measured. [Current table](docs/implementation-status.md).

## Personal-development test budget

At most 10 selected case executions per trial, including local/CI retries. This branch selects five new cases once in PR CI. No local duplicate, push CI, matrix or historical full-suite run. See [the testing policy](docs/testing-budget.ja.md).

## Research basis

- [Google's Sleep framework](https://research.google/blog/the-sleep-framework-a-new-way-for-llms-to-retain-knowledge-in-continual-learning/) and [Language Models Need Sleep](https://arxiv.org/abs/2606.03979) motivate separating activity, consolidation, and practice. Their method updates model weights; our initial design uses external memory and rehearsal tasks.
- [Anthropic's The components of agent memory](https://www.anthropic.com/research/components-of-agent-memory) motivates retaining original logs, correcting notes against evidence, structured representations, and compact injected context.
- [OpenClaw Dreaming](https://docs.openclaw.ai/concepts/dreaming) provides an architectural reference for separating selection, reflection, and durable promotion. Our [sleep design](docs/dreaming.ja.md) keeps generated reflections separate from evidence and retains the independent evaluation gate.

This is an independent application proposal, not an official implementation or reproduction of these systems. See the [research mapping](docs/research-basis.ja.md).

## Proposed loop

Existing agent → authorized evidence → Light: select candidates → optional REM: propose hypotheses and checks → Deep: verify evidence and propose memory changes → candidate snapshot → frozen adoption evaluation → atomic promotion or rejection → scoped retrieval for subsequent work.

REM and a human-readable dream diary are proposed extensions, disabled in the first pilot. A diary is never evidence or permission. Sleep runs outside the foreground task loop; it does not make the assistant unavailable.

Triggers are explicit requests, task completion, or accumulated experience. No recurring automation is configured.

Start with paper/article curation, then consider OSS triage and offline coding experiments. None is connected yet. Existing agents retain their own execution permissions and publication policies. A further design target is a [ChatGPT dots integration](docs/dots-integration.ja.md) that assumes the agent forgets and keeps the source of truth outside it.

**Design premise:** target agents are assumed to forget. Their internal memory is treated as an unverified cache, and the source of truth stays in this harness's external memory. See [ADR 0002: assume the agent forgets](docs/decisions/0002-assume-agent-forgets.md) and the [dots integration design](docs/dots-integration.ja.md).

## Design documents

The detailed documents are initially in Japanese.

- [Architecture](docs/architecture.ja.md)
- [Sleep / dreaming: phases, promotion gates, recovery](docs/dreaming.ja.md)
- [Research and design mapping](docs/research-basis.ja.md)
- [Evaluation protocol](docs/evaluation.ja.md)
- [Manual pilot](docs/manual-pilot.ja.md)
- [Existing-environment integration](docs/integration.ja.md)
- [Roadmap](docs/roadmap.ja.md)
- [Decision: external memory first](docs/decisions/0001-external-memory-first.md)
- [Decision: assume the agent forgets](docs/decisions/0002-assume-agent-forgets.md)
- [Decision: separate reflection from evidence and promotion](docs/decisions/0003-grounded-dreaming.md)
- [Dots integration: designing for an agent that forgets](docs/dots-integration.ja.md)
- [Data contracts](schemas/README.md) and [example configuration](configs/pilot.example.json)
- [Consolidation prompt](prompts/sleep-consolidator.ja.md), [optional REM prompt](prompts/dream-reflector.ja.md), and [retrieval prompt](prompts/memory-reader.ja.md)
- [Synthetic fixtures](examples/README.md) and [report template](templates/experiment-report.ja.md)

## What exists today

- **Authored:** design documents, v0.1 event/memory schemas, synthetic fixtures, proposed configuration, and prompt templates.
- **Implemented and locally checked:** Gate 1 read-only offline contract validation and wheel/CLI acceptance; Gate 2A strict provenance and a synthetic-only SQLite evidence library. The first Gate 2B slice adds strict receipts, persisted current policy and same-connection eligibility helpers. The pure candidate planner and [synthetic durable-adoption core](docs/gate-2b-adoption.md) are locally checked; [run-ID audit labels](docs/gate-2b-run-id.md) are locally checked; registered-run integration and broader fault fixtures remain pending. See [Gate 1](docs/gate-1.md), [Gate 2A](docs/gate-2a.md) and [Gate 2B first slice](docs/gate-2b.md).
- **Implemented, checked and merged (PR #13):** the [Gate 3 scoped-retrieval library](docs/gate-3.md) (read-only, synthetic-only, UTF-8 byte budget).
- **Merged:** [safe rollback](docs/gate-3.md#safe-rollback), explicit control recovery, not fresh adoption/evaluation.
- **Merged with focused CI acceptance:** [logical forgetting](docs/gate-3-forgetting.md), not erasure.
- **Merged through PR #16:** [review fixes](docs/review-followup.ja.md) (dated review document).
- **Feature branch, focused CI accepted:** [Gate 4A](docs/gate-4-light-deep.md) offline synthetic Light/Deep slice.
- **Not implemented:** deletion/physical purge/cache cleanup, evaluation-frozen retrieval, delivered-memory logging, real capture/retrieval adapters, production sleep phases, authenticated provenance, authenticated run integration and broader adoption fault acceptance, diary, and scheduling.
- **Not executed:** target-agent integration, sleep-provider trials, and A/B performance experiments. Claude Code development sessions are separate from harness experiments.

Start with the [manual pilot](docs/manual-pilot.ja.md). The [contract gaps](schemas/README.md#dreaming設計で追加が必要な契約未実装) must be closed before runtime adoption. Document and fixture checks are not evidence of performance improvement.

## Operating principles

Retain provenance and scope. Distinguish verified observations from hypotheses. External source text cannot grant permissions or become operating policy. Evaluate success cases as well as failures.

Keep real transcripts and private memory outside this public repository. Publish only design material, synthetic fixtures, and explicitly reviewed public artifacts. Measure memory preparation and maintenance costs in addition to answering costs.

Created November 8, 2026 JST. Dreaming design updated November 9, 2026 JST. Experimental results: not yet collected.

## Design handoff update — 2026-11-09

Read the [implementation contract and acceptance cases](docs/contracts-and-acceptance.md) before implementing. This update specifies state ownership, immutable evidence, retry/recovery behavior and evaluation boundaries; it adds design schemas and synthetic examples only. Later implementation adds contract validation, synthetic storage/receipt helpers, candidate planning and the locally checked v3 adoption core. The sleep engine and full adoption acceptance remain pending. No performance result or live integration is claimed.

The three repositories remain independently usable. Optional integration follows the [reference-only handoff contract](https://github.com/moruku36/ai-agent-scientist/blob/main/docs/11-harness-boundaries.md); it does not create shared authority or a new agent runtime.
