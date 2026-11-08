# agent-sleep-lab

**English** | [日本語](README.ja.md)

An experimental harness that adds a sleep phase to existing AI-agent workflows: retain evidence, consolidate useful memories, verify them, and retrieve relevant experience for the next task. The aim is to measure changes in task success, repeated mistakes, human corrections, and total cost across GitHub-centered workflows.

**Status: design and experiment preparation. There is no runtime, connected adapter, or measured performance improvement yet.** This initial version provides architecture, data contracts, prompts, synthetic fixtures, evaluation criteria, and an implementation roadmap.

## Research basis

- [Google's Sleep framework](https://research.google/blog/the-sleep-framework-a-new-way-for-llms-to-retain-knowledge-in-continual-learning/) and [Language Models Need Sleep](https://arxiv.org/abs/2606.03979) motivate separating activity, consolidation, and practice. Their method updates model weights; our initial design uses external memory and rehearsal tasks.
- [Anthropic's The components of agent memory](https://www.anthropic.com/research/components-of-agent-memory) motivates retaining original logs, correcting notes against evidence, structured representations, and compact injected context.

This is an independent application proposal, not an official implementation or reproduction of either method. See the [research mapping](docs/research-basis.ja.md).

## Proposed loop

Existing agent → logs/results/corrections → memory candidates → evidence checks and consolidation → candidate snapshot → held-out evaluation → versioned promotion or rejection → relevant memory retrieval for subsequent work.

Triggers are explicit requests, task completion, or accumulated experience. No recurring automation is configured.

Start with paper/article curation, then consider OSS triage and offline coding experiments. None is connected yet. Existing agents retain their own execution permissions and publication policies. A further design target is a ChatGPT dots integration that assumes the agent forgets and keeps the source of truth outside it (docs/dots-integration.ja.md).

## Design documents

The detailed documents are initially in Japanese.

- [Architecture](docs/architecture.ja.md)
- [Evaluation protocol](docs/evaluation.ja.md)
- [Manual pilot](docs/manual-pilot.ja.md)
- [Existing-environment integration](docs/integration.ja.md)
- [Roadmap](docs/roadmap.ja.md)
- [Decision: external memory first](docs/decisions/0001-external-memory-first.md)
- [Decision: assume the agent forgets](docs/decisions/0002-assume-agent-forgets.md)
- [Dots integration: designing for an agent that forgets](docs/dots-integration.ja.md)
- [Data contracts](schemas/README.md) and [example configuration](configs/pilot.example.json)
- [Consolidation prompt](prompts/sleep-consolidator.ja.md) and [retrieval prompt](prompts/memory-reader.ja.md)
- [Synthetic fixtures](examples/README.md) and [report template](templates/experiment-report.ja.md)

## Operating principles

Retain provenance and scope. Distinguish verified observations from hypotheses. External source text cannot grant permissions or become operating policy. Evaluate success cases as well as failures.

Keep real transcripts and private memory outside this public repository. Publish only design material, synthetic fixtures, and explicitly reviewed public artifacts. Measure memory preparation and maintenance costs in addition to answering costs.

Created November 8, 2026 JST. Experimental results: not yet collected.

