# Implementation status

**English** | [日本語](implementation-status.ja.md) | [Home](../README.md)

## Current assessment — 2026-11-13

**Acceptance first; no supported completion percentage.** The 2026-11-12 owner
review tracks four capabilities below. The initial target remains capture →
adoption → retrieval → Light/Deep → comparison evaluation → one existing-agent
integration; REM, diary and wider rollout are excluded. File/test counts and
prepared interfaces are not completed acceptance.
This page and its Japanese translation are the ONLY current status authority;
dated gate reports are historical evidence.

Fresh GitHub reads confirmed [PR #47](https://github.com/moruku36/agent-sleep-lab/pull/47)
owner-merged at `82729e8dff6ce5b3967fd406490a058c5f265b70` on 2026-11-13.
Its exact-head [PR CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/43347223453)
succeeded. That baseline includes planned input-volume reporting.
[PR #48](https://github.com/moruku36/agent-sleep-lab/pull/48) is also owner-merged
at `2ab948bebbdcdf14d4ffeca0a2a071cf1db16af8`. Its exact-head
[CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/43350754976) passed
435 cases on each Python version, documentation and wheel checks.
That baseline adds read-only comparison inspection. This follow-up retains
provider accounting observations; it does not publish the separate trial code from
[PR #46](https://github.com/moruku36/agent-sleep-lab/pull/46).
Prior `feat/live-acceptance-path` commit `1e636d8` remains preserved elsewhere;
its prior PR creation is **UNKNOWN**, not reissued here.

| Capability | Code | Offline verification | Live acceptance | Gap | Next action | Evidence |
|---|---|---|---|---|---|---|
| Record / independent verification / atomic adoption / retrieval / withdrawal / restore | Synthetic-store path implemented | Historical baseline regression; current results below | Not performed | Real-data boundary and operational acceptance | Define one authorized real-data boundary | Existing store/writer/retrieval contracts |
| Real-model Light/Deep → independent adoption → retrieval | Body-bound generation and separate verifier/writer implemented; prior same-run CLI branch preserved separately | Existing contracts; no new model call | Not performed | MiMo absent from the current agent catalog; unresolved execution binding and real candidate verification | After binding resolution, one bounded receipt call within total budget | [Runtime guide](runtime-guide.md), prior branch noted above |
| Fixed five-task paper A/B, missing outcomes and costs | Existing plan/journal, preparation/volume/inspection; provider accounting retention | Baseline and new accounting contracts below | Not performed | Ten real outcomes, live-emitted usage, currency and all-phase billed costs | Restore the supported MiMo capability before any live run | [Preparation](runtime-guide.md#offline-comparison-preparation), [contracts](../tests/test_compare_prepare_cli.py) |
| One real-agent capture → retrieval on another task → input / execution | Synthetic bridge and offline handoff only | Existing synthetic integration contracts | Not performed | Real-data permission, retention/deletion/scope/secrets contract and tracked actual use | Scope explicit public-source capture acceptance for Kurotchi | Existing bridge and execution journal; no real-agent receipt |

Paid-use consent was already received; missing generic consent is not the blocker.
The saved host-binding denial and unknown outcomes remain unresolved. Preparation
does not replay them or change host/account controls.

## Direct validation preflight and accounting retention — 2026-11-13

Owner asked Kurotchi itself to validate, without workers. A read-only catalog
inspect for `xiaomi/mimo-v2.6-pro` returned **Model not found** for the configured
agent. This is not an inference, an approval rejection, proof of globally missing
credentials, or proof the historical binding was repaired. Live calls: **0**.
The five-pair worksheet is not a frozen executable comparison or scored result.

- Implemented [provider accounting retention](runtime-guide.md#provider-accounting-observations)
  in the existing paper-pilot adapter: allowlisted aggregate/last-call token and
  recorded cost metadata, availability and billing provenance. Missing/default
  zeros, unavailable usage and malformed values never become invented metrics.
  No currency, prices, monetary totals or savings are inferred.
- Existing Light/Deep checkpoints and A/B provider-receipt journals retain these
  observations across reopen, including on rejected post-generation output.
  This changes no schema, permissions, synthetic-only gates, dispatch, model,
  verification or adoption policy. The separate OSS adapter/inspector stay unchanged.
- Seven new [offline behavior cases](../tests/test_provider_usage.py) passed in
  one focused invocation (0.052s). Full regression passed **442 unique cases /
  one invocation** (36.809s), using existing Python 3.13.18 and pinned dependencies:
  **449 verified local case executions / two invocations**. The full run includes
  a clearer unverified-billing label introduced after the focused run.
  Earlier unknown/denied operations are not retried or reset.
- Direct coordinator review and injected transports are not independent review
  or live acceptance. Current PR Python 3.11/3.13 CI is a separate check record.
  The reviewed public CLI contract may be newer than the installed CLI; actual
  emission and provider billing are still unverified.
- Remaining: supported MiMo capability/binding restoration by the infrastructure
  owner; established currency and all-phase billed-cost coverage; a separately
  reviewed real-data boundary with explicit source/scope/purpose/retention/deletion
  and actual later-task input/use receipts. No private trial code was searched or
  reconstructed, and real data was not relabelled synthetic.

## Read-only saved comparison inspection — PR #48 merged baseline

- Added [compare-inspect](runtime-guide.md#read-only-saved-comparison-inspection)
  over existing independent-raw journals, without initialization, plan/contact
  registration, provider/evaluator calls, reply reads, raw receipt export or
  state mutation. Both databases use SQLite read-only/query-only controls;
  journal inspection uses one read transaction.
- Preserves planned per-arm denominators, every saved arm state and existing 0/1
  fixture scores. Reuses the hash/membership audit and planned-byte projection.
  Stale/revoked context returns a separate false validity observation without
  invalidating or recovering the saved plan. No origin authentication,
  measured cost, performance conclusion or live acceptance is established.
- Six new [behavior cases](../tests/test_compare_inspect_cli.py) cover no-write
  guarantees/privacy, mixed unknown/partial states, a complete scripted run,
  changed/revoked eligibility, corruption refusal and strict existing-file/CLI
  gates. Local execution has **no verified result**: one six-case attempt timed
  out without a completion receipt (0–6 executions unknown; scoped process
  subsequently absent). A later log-retaining command was refused before
  execution by native approval binding, not by automatic risk review.
  No further local test command was submitted after that refusal.
- Code/documents were reviewed directly by the coordinator, without workers.
  Normal PR CI supplies full Python 3.11/3.13 regression, documentation links
  and wheel checks; its current result is a separate PR check record.
  These checks do not exercise a live model or a real-agent connection.

## Planned input-volume reporting — PR #47 merged baseline

- Implemented additive `input_volume` in existing
  [compare-prepare](runtime-guide.md#offline-comparison-preparation): exact planned
  serialized request bytes for each A/B pair, totals, B−A and percentage growth.
  Identity-based pairing validates every frozen task; all planned slots remain
  counted even with missing/unknown outcomes. Totals use the ratio of sums,
  with half-up percentage rounding to two decimals.
- Only reporting and identity validation change. Frozen plans/hashes, journal
  schema, statuses and explicit dispatch/adoption boundaries are unchanged.
  No provider, evaluator, answer key, live inference or real-data path is added.
  Byte growth is not token usage, measured money or evidence of benefit.
- Four new [behavior cases](../tests/test_compare_prepare_volume.py) passed in
  one focused invocation (0.443s). Full regression passed **429 unique cases /
  one invocation** (36.025s), using retained Python 3.13.18 and project-pinned
  dependencies: **433 verified case executions / two local invocations**.
  A prior four-case attempt returned no completion receipt after a tool timeout;
  its executions are unknown (0–4), excluded from those verified totals.
- The local figures above are not independent approval or live acceptance.
  The subsequently verified exact-head PR CI succeeded, including Python
  3.11/3.13 regression, documentation and wheel checks; PR #47 is owner-merged
  as recorded above. These later gates do not complete live acceptance.

## Local public-source trial — 2026-11-12

The [dated trial report](public-source-trial-2026-11-12.md) records one completed
public-document capture → actual model generation → separate source-grounding
review → atomic adoption → retrieval → use on a different task. This used the
merged baseline plus a **local, uncommitted/unmerged extension**, not the merged
synthetic CLI. No runtime implementation is published by this documentation change.

One predeclared paired example scored raw-only 7/8 and raw-plus-memory 8/8.
Input increased by 4,072 bytes; usage and cost were unavailable. One pair is not
general performance evidence. The extension passed 436 local regression cases,
not the documentation branch's test count. Exact version, artifact hashes,
comparison limits and test accounting are in the report.

Current acceptance remains limited: no automated Light/Deep provider run, permanent
agent connection, paid MiMo execution or five-task acceptance was completed.
Publication/review of the local implementation and a supported agent connection
remain separate next steps. The historical host-binding blockers below were not
resolved or retried by this trial.

### Documentation-only update checks

This change touches six Markdown files and publishes no runtime code or private
trial artifacts. Its local regression passed **425 unique cases in one invocation**
(13.517s, Python 3.12.14); 521 relative file links across 88 Markdown files passed.
Existing README destinations were retained. These counts are separate from the
436-case local-extension trial above. GitHub checks for this documentation commit
remain a separate CI record.

## PR #45: predispatch comparison preparation (history)

- Added explicit [compare-prepare](runtime-guide.md#offline-comparison-preparation):
  same bounded comparison manifest, separate journal and finite model choice;
  adoption store opened read-only. Only frozen context/plan/evaluation contact
  are written. No provider/evaluator is constructed, no answer key is read and
  no execution status is changed. Unknown intent remains unknown.
- Returns hashes, caps, fixed planned denominator/order and existing membership
  audit; requires the same A raw prefix in B plus eligible consolidated memory
  and a fresh current-context check. Existing explicit `compare` can later use
  the same frozen plan with its separate rubric and matching model route.
- Seven new [offline behavior tests](../tests/test_compare_prepare_cli.py) passed
  in one focused invocation (0.980s). Full regression then passed **425 unique
  cases in one invocation** (34.600s), using existing Python 3.13 and pinned
  dependencies. Total: 432 case executions / two local test invocations.
  Documentation validation passed 513 relative file links across 86 Markdown
  files; whitespace check passed. PR Python 3.11/3.13 CI and wheel validation
  are separate, not yet accepted here.
- The selected Codex draft invocation reached its 600-second outer timeout;
  no final completion receipt was recovered and the scoped process was absent.
  The coordinator reviewed/completed and tested the saved draft without replay.
  Coordinator review is not independent approval. No live inference or
  independent acceptance occurred. Reply byte caps are post-generation, not
  token/money caps; MiMo costs stay unavailable. This is preparation, not live
  recovery, real Light/Deep or real-agent ingestion.

## Verified merged baseline

[PR #23](https://github.com/moruku36/agent-sleep-lab/pull/23) is **MERGED** at
`025e32314efd246dd5b04b3476fa5b2865287a3c`; source
`087f2a3da8e4188a70a7a84d50d1a8d4eb14e1dc`.
The owner merged it on 2026-11-10. Read-only GitHub queries verified the merge
and successful [main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42798899032).
[PR CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42796639749)
passed all 241 unique cases on each of Python 3.11 and 3.13 (482 case
executions / two matrix invocations), 339 relative file links and wheel build.
No paid API calls occur in CI.

[PR #24](https://github.com/moruku36/agent-sleep-lab/pull/24) is also **MERGED** at
`2117e96fcad631f69422541b6a6dbad9c6c025ed`, source
`ab05819d253d15ed7e3dc733f52efd4b034df604`. The owner completed the merge after
the dedicated merge tool stopped. Both checks in
[PR CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42801027617)
and the [main workflow](https://github.com/moruku36/agent-sleep-lab/actions/runs/42801229632)
succeeded. This adds the synthetic collect-only bridge, not a deployed agent.

[PR #25](https://github.com/moruku36/agent-sleep-lab/pull/25) is **MERGED** at
`ccb06aa4bdb1defef8fc8564e818522b650fd59a`, source
`9387f1fef1565f3edcf94740e22d97f7187ac41f`; GitHub reports the merge at
2026-11-10T10:54:59Z. Its reference dispatch journal is part of this baseline.

Merged foundation: synthetic evidence/provenance, policy and receipt libraries,
transactional adoption, scoped retrieval, rollback/logical forgetting; body-bound
v2 Light/Deep proposals and generated candidate claims; explicit runtime CLI;
MiMo adapter, durable checkpoints, identical A/B rejection, diagnostic
non-comparability, manual handoff and stopped-worker recovery.
Generated candidates are not independently verified or adopted automatically.
This is not production authentication, physical purge or a deployed agent connection.

[PR #26](https://github.com/moruku36/agent-sleep-lab/pull/26) is **MERGED** at
`9a36ee6dca4569ea2fe1d32dd42969ea9a62c6c3`, source
`37439d00d95a4f74d5225a3dc2aab27fdf3c658c`. A GitHub read confirmed the merge at
2026-11-10T15:34:08Z; its CI result is not recorded here. It merged the partial offline worker as a
preserved draft, not a working integration checker.

[PR #27](https://github.com/moruku36/agent-sleep-lab/pull/27) is **MERGED** by the
owner at `93ddb1a070c6ffdee65cd0809eea5c8ae68203c5`, source
`442b7ea1b4f67c878d67599a42bde6864604810b`. GitHub confirmed the merge at
2026-11-10T15:50:40Z and PR CI success on Python 3.11 and 3.13. It merged worker input validation and loader
contract tests, not a working integration checker.

[PR #28](https://github.com/moruku36/agent-sleep-lab/pull/28) is **MERGED** at
`709e7642be3de65f83abd76e5337357829450aa5`, source
`6a3bba2c53158053583ff86dab56da87c4a60027`. GitHub confirmed the merge at
2026-11-10T16:07:42Z and PR CI success on Python 3.11 and 3.13.
It merged the bounded parent checker and ten stand-in contract cases. A separate
local acceptance ran the pinned target code once with an empty synthetic reference
and captured five synthetic outcomes; it did not exercise the dispatch journal.

[PR #29](https://github.com/moruku36/agent-sleep-lab/pull/29) is **MERGED** at
`85300ee064b6a9621119c5748f6c8267e240d030`, source
`9a7e3b8f25268d81503aa8bba91f5feb29d5647c`. GitHub confirmed the merge at
2026-11-10T17:54:44Z; PR CI passed on Python 3.11 and 3.13.

[PR #30](https://github.com/moruku36/agent-sleep-lab/pull/30) is **MERGED** at
`9f281875925dd66a90b09c07af1562e3cdae3beb`, source
`9d0cbb69dae3943becdbf7d886b4df488cb600dd`. GitHub confirmed the merge at
2026-11-10T18:11:11Z; both PR checks and
[main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42872601554)
passed. It merged six selected guard acceptance cases and accurate limitation
documentation, not guard behavior hardening.

[PR #39](https://github.com/moruku36/agent-sleep-lab/pull/39) is **MERGED** at
`5cea9e224f8bfc306735c400b9cd358db7c0ac9f`. A fresh read-only GitHub query
confirmed the merge at 2026-11-11T01:59:18Z. This is historical baseline evidence.

[PR #40](https://github.com/moruku36/agent-sleep-lab/pull/40) is **owner-merged** at
`29fef5ad19239e53ce3e07684b2c30e0cc2d1623`. A fresh read-only GitHub query
confirmed the merge at 2026-11-11T03:04:33Z and successful Python 3.11/3.13
[main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42950289146)
for that exact commit. That was the raw-ranking gate's baseline.

[PR #41](https://github.com/moruku36/agent-sleep-lab/pull/41) is **owner-merged**
at `e2d525242511cd2c8b46626ce1ab96477a85dd2d`. Fresh read-only GitHub queries
confirmed its merge at 2026-11-11T03:57:26Z and successful Python 3.11/3.13
[main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/42956077100)
for that exact commit. That was the read-only cost-report gate's baseline.

[PR #42](https://github.com/moruku36/agent-sleep-lab/pull/42) is **owner-merged**
at `791e8f540db0b4ca549ffec79a96925e907e804b`, the baseline for this demo draft.
A coordinator GitHub query confirmed MERGED at 2026-11-11T04:35:30Z with
that exact merge commit. The cost-report checks below are historical.

## Current local gate — read-only OSS preparation

[PR #43](https://github.com/moruku36/agent-sleep-lab/pull/43) is owner-merged at
`736988a0cb243da9c263ce28232ec5f44d0e3ea7` (2026-11-11T23:00:41Z),
independently confirmed with GitHub metadata. Its
[PR CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/43116115784)
and exact-merge [main CI](https://github.com/moruku36/agent-sleep-lab/actions/runs/43116437958)
succeeded. The demo figures below are historical, not this gate's checks.

- Added [oss-prepare](oss-prepare.md), an explicit strict manifest/store-config
  CLI. Existing adopted synthetic experience records are read under current policy
  with read-only/query-only SQLite. Empty returned bundles refuse before target
  execution; a post-worker fresh retrieval rejects changed or expired context.
  Existing pinned source, byte-exact framing and output validation remain enforced.
- Shared unchanged configuration validators were extracted to
  `oss_read_config.py`, preserving cost-report imports while keeping execution
  journal/provider/adapter imports out of preparation. No injected worker,
  provider, transport, capture/adoption or dispatch options are exposed.
- [Seven unique contract cases](../tests/test_oss_prepare_cli.py) passed in one
  focused invocation (0.693 s), with real temporary adopted stores and explicitly
  labelled stand-in workers. Full regression passed **418 unique cases / one
  invocation, 34.432 s**: **425 case executions / two local regression invocations**.
- Documentation: **503 relative file links / 86 Markdown files passed**;
  anchors/external URLs excluded. Whitespace checks passed.
- Separate coordinator acceptance passed **one case / one invocation** against
  actual pinned OSS Contributor source at
  `e40b39c6258ac5a4446c38246bdfd7f5dc5dbf7b`, with one test-authored adopted
  synthetic memory, one built-in capture worker, two actual judge/prompt calls,
  962-byte baseline and 3,047-byte reference prompts. Model calls and store
  mutations were zero. This acceptance is separate from the regression counts.
- The selected Codex `gpt-6.1-sol`/`xhigh` invocation timed out after 600 seconds,
  saving the production draft but no tests/docs. Its process ended; no complete
  resolved-model/completion receipt was returned, and it was not replayed.
  The coordinator reviewed the draft, completed tests/docs and verified it.
- Local checks establish usable offline request preparation, not real operational
  capture, authenticated delivery, semantic memory use or improvement. Raw synthetic
  memory/request payloads appear in output and are not a publication allowlist.
  No paid inference, configuration/authentication changes or merge were performed.
  Feature PR CI is a separate gate; real acceptance remains outstanding.

## Historical PR #43 local gate

### Built-in synthetic offline demo — prior local verification

- Saved `agent-sleep-lab demo`, its [runtime contract](runtime-guide.md#built-in-offline-demo)
  and [eight unique contract cases](../tests/test_offline_demo.py). It accepts no
  caller data/store/provider options and uses three disposable temporary SQLite
  stores with built-in synthetic data, fixed clocks and bounded scripted providers.
- The chain captures two events, calls Light and Deep once each, materializes one
  pending candidate, checks exact source equality and registers one verification
  receipt plus one four-check snapshot evaluation receipt through normal APIs.
  The existing atomic writer performs one adoption, and retrieval returns one
  eligible memory. No provider issues receipts or bypasses production gates.
- Two paired tasks freeze the adopted snapshot/policy, both independent raw
  events and one memory. A contains the whole raw prefix; B adds the memory.
  Four scripted task calls and four separate evaluator calls use AB then BA
  order, equal per-arm limits and distinct requests without dropped records.
  Expected answers stay outside provider requests. Output exposes actual
  stage/call/byte counts, frozen context and hash-bound membership audits.
- Initial focused verification reported **8 case executions / one invocation:
  2 passed, 3 failed, 3 errored**. The shared blocker was the invalid
  `until_expiry` authorization with a null expiry. The fixture now supplies a
  real expiry after its fixed clock. The tautological snapshot assertion was
  replaced by adopted-snapshot, policy, frozen-context/plan hash and completed
  per-arm membership checks; assertions and production gates remain enforced.
- Repair verification passed **all 8 unique affected cases / one invocation,
  0.919 s**. Including the initial failed run, the demo gate has **16 case
  executions / two focused invocations** so far. This is local synthetic contract
  verification, not independent acceptance. Documentation validation passed
  **489 relative file links / 84 Markdown files** in one checker invocation;
  anchors and external URLs were excluded. Whitespace checks passed.
  Coordinator full regression then passed **411 unique cases / one invocation,
  33.853 s**: **427 case executions / three local invocations** including both
  focused runs. This verifies the synthetic chain, not real-agent acceptance.
  At that local checkpoint Python 3.11/3.13 PR CI and wheel were pending;
  both subsequently passed, as recorded above.
  The local offline wheel command was denied before execution by approval binding;
  no alternate local build route was attempted.
- No live inference, install, merge or external permission/configuration change
  was used. Feature publication and a review PR are authorized; GitHub PR checks
  remain the authority for the published commit. Temporary-state cleanup, failure
  handling, answer exclusion and refusal of live/provider dispatch are covered
  by the affected cases. Scripted exact-match scores do not establish semantic
  memory use, real-agent integration, billing, holdout quality or improvement.
  Real acceptance remains outstanding.

## Merged development gates (historical checks)

### PR #42 offline read-only OSS cost-report CLI — prior local verification

The following figures predate the owner merge in PR #42. They are baseline
history, not demo verification or authorization for new publication.

- Saved `oss-cost-report` and its [strict manifest/API contract](oss-cost-accounting.md),
  with explicit pair/cohort IDs, per-plan bridge identities, existing file paths
  and optional exact canonical observation bytes. Output reuses only the existing
  accounting allowlist and current-policy/integrity checks; no provider or write options.
- Saved opt-in SQLite read-only/query-only modes for AdoptionStore, ExecutionJournal
  and CohortRegistry, with early write-method refusal, no initialization/migration,
  path-alias refusal and unchanged default writer/saved contracts. SQLite locking
  and sidecars remain possible; this is not filesystem isolation or authentication.
- Saved [synthetic regression sources](../tests/test_oss_cost_report_cli.py) for
  pair/cohort output, full denominator and unknown/invalid/withheld outcomes,
  canonical/stale observations, missing/empty/foreign/aliased databases, zero
  execution/adoption effects, early refusal, WAL policy visibility and writer compatibility.
  Fixture helpers are reused without inherited/imported test-case duplication.
- Coordinator verification passed **12 new unique cases / one focused invocation,
  2.399 s**, then **403 unique regression cases / one invocation, 30.601 s** on
  Python 3.13.18: **415 case executions / two local invocations** in this gate.
  **479 relative file links / 84 Markdown files passed**; anchors and external
  URLs were excluded. Whitespace checks passed. No new gate CI or local Python
  3.11 result is claimed. Tests use synthetic stores and injected replies only.
- Before that historical verification, the duplicate journal precheck was removed
  so exact-type validation still precedes foreign-method access; a regression
  assertion covers that boundary. These checks established neither a full agent
  integration nor live/billing verification or performance improvement.

### PR #41 opt-in independent raw query ranking — prior local verification

The following records the raw-ranking gate before its owner merge in PR #41.
Its verification/publication authorization does not apply to the demo gate.

The [ranking contract](raw-query-ranking.md) and
[implementation](../src/agent_sleep_lab/raw_baseline.py) add explicit
`raw_order="query_overlap_descending"` to the independent raw comparison API and
existing file-based compare manifest. The default event-ID path retains its rules,
saved context/plan bytes and replay behavior; there is no migration or new dispatch route.

- The existing bounded bilingual NFKC/casefold/Japanese terms score stored source
  text and event summary values only. All independently eligible rows are ranked
  before `max_raw` and byte packing, by overlap descending with event-ID ties.
  Zero-overlap rows remain in the eligible denominator. Scope, partition, origin,
  policy, expiry, integrity, ancestry and scan bounds remain unchanged and fail closed.
- Ranked rules freeze algorithm/version, Unicode database version, exact query/hash,
  normalized terms and scored fields alongside existing settings. Order/query or
  ranking-setting changes conflict on reuse. All eligible source hashes, including
  capped-out rows, remain bound; current-context changes invalidate without redispatch.
  A/B retain the same raw whole-record prefix and equal byte/call limits; B may
  append eligible memories. Report and ranked audit retain the frozen rules.
- Ten new synthetic test case sources are saved across
  [raw baseline tests](../tests/test_raw_baseline.py) and
  [runtime CLI tests](../tests/test_runtime_cli.py), reusing fixture methods without
  imported-case duplication. They cover ordering/ties/zeros, Unicode/Japanese,
  cap selection, validation, metadata/answer exclusion, eligibility/corruption/scan
  refusal, frozen replay/conflicts, capped-out change invalidation and A/B/audit membership.
- Coordinator verification passed **10 new unique cases / one focused invocation,
  1.354 s**, then **391 unique regression cases / one invocation, 28.049 s** on
  Python 3.13.18: **401 case executions / two local invocations** in this gate.
  **472 relative file links / 84 Markdown files passed**; anchors/external URLs
  were excluded. Whitespace checks passed. This gate has no new CI or local
  Python 3.11 result. The tests use synthetic stores, rubric data and fake replies.
- The requested Codex CLI completed normally with exit 0 and a final-message
  artifact; execution metadata confirms `gpt-6.1-sol` / `xhigh`. Static review and
  coordinator review found no remaining source/contract blocker. Before execution,
  one test initialization assertion was corrected to inspect the absence of an
  adapter table rather than query that nonexistent table. The default path retains
  its previous serialized fields; tests cover default/explicit-order replay, not
  a separately retained pre-change binary artifact.
- Read-only GitHub queries and local fetch/worktree preparation were used. Original
  checkouts and unrelated edits were preserved. No live runtime/evaluation provider
  calls, paid effect measurement, settings/credential changes, merge or schedules
  occurred. The owner authorized this feature branch and review PR publication;
  merge requires separate approval. GitHub PR checks are the authority for the
  published commit. No fairness, semantic relevance or improvement evidence is claimed;
  real acceptance remains outstanding.

### Merged PR #40 offline-worker filesystem audit hardening

The following local checks and implementation provenance predate owner merge
at `29fef5ad19239e53ce3e07684b2c30e0cc2d1623`. That filesystem-guard worktree
started at main `5cea9e2`; its publication authorization was specific to that
gate and does not authorize publication of this raw-ranking gate. These results
are historical evidence, not verification of the new ranking code.

- The [filesystem audit contract](oss-offline-filesystem-guards.md) describes
  shared `install_guards` hardening: remove/rmdir/mkdir, rename/replace, hardlink,
  symlink target/destination, chmod/chown/utime/truncate/flags/xattrs, write-open
  flags and the designated SQLite connection path. Both affected endpoints are
  checked. Descriptor paths and non-default audited directory descriptors are
  refused, along with relative/ambiguous mutation paths and symlink components.
- Absolute in-temp scratch and the ledger remain allowed by contract, including
  the reviewed ledger's existing-parent mkdir attempt. Prompt capture reuses the
  same guards before loading sources. The stdlib-only worker, target pin,
  payloads and source/task/reference hash contracts are unchanged.
- Added [disposable-child regression sources](../tests/test_oss_offline_guards.py)
  with temporary synthetic sentinels, outside content/metadata preservation,
  both endpoints, bytes/path-like paths, relative/ambiguous paths, symlinks,
  descriptors/dir-fd, write flags, scratch/ledger and prompt-capture reuse.
  Platform-specific metadata and malformed-event checks are side-effect-free
  audit probes; the capture reuse case uses a stand-in payload/loader.
- Coordinator verification passed **17 focused unique cases / one invocation,
  0.408 s**, then **381 unique regression cases / one invocation, 27.043 s** on
  Python 3.13.18. This increment adds eleven cases and totals **398 case
  executions / two local invocations**. No Python 3.11 or new CI result is claimed.
  The full run includes existing pinned synthetic captures with injected replies;
  these are not live-model or production evaluations. **459 relative file links /
  83 Markdown files passed**; anchors and external URLs were excluded.
  Whitespace validation passed.
- The requested Codex CLI completed normally with exit 0 and a final-message
  artifact. Execution metadata confirms `gpt-6.1-sol` / `xhigh`. Independent static
  review and coordinator review confirmed the narrow existing-root mkdir exception
  needed by the pinned ledger, while other root mutations remain denied.
- No runtime/evaluation provider calls, paid effect measurement, target changes,
  settings or credential changes, merge or schedules occurred. Read-only
  GitHub queries and local fetch/worktree preparation were used; original checkouts
  and unrelated dependency edits were left untouched. Publication is limited to
  this feature branch and its review PR. This is reviewed-code guard
  hardening, not full isolation of hostile Python, native code, inherited descriptors,
  unaudited syscalls, hardlink aliases or filesystem races. Real acceptance remains outstanding.

### Merged PR #39 offline OSS cost accounting

`feat/oss-usage-accounting` starts at the local merge commit for
[PR #38](https://github.com/moruku36/agent-sleep-lab/pull/38),
`85b7dfceda509d0005295b3aa019dd7ae3dea147`; that gate recorded a GitHub read
confirming the merge. The following local verification and worker results were
recorded before PR #39 merged at `5cea9e224f8bfc306735c400b9cd358db7c0ac9f`.
These dated counts and timings are historical; current-gate verification is above.
GitHub PR checks remain the authority for feature CI.

- The [offline accounting contract](oss-cost-accounting.md) adds a strict
  caller-owned JSON artifact and a report for durable pairs and frozen cohorts.
  Artifacts pin the frozen binding or cohort and exact report snapshot, including
  cohort member execution hashes. Replay checks current policy and integrity.
- Reports retain both arms of all registered tasks and all seven cost stages.
  Missing usage and cost remain null. Currency is explicit and sums use exact
  decimal arithmetic. Observation evidence hashes are caller-supplied and
  unverified. The registered OpenClaw CLI still supplies no usage or cost in
  `model.run`. No measured billing, monetary cap or performance claim follows.
- [Seven new cases](../tests/test_oss_cost_accounting.py) and existing contracts
  passed independent coordinator verification: **370 unique regression cases /
  one invocation**, Python 3.13.18, 26.989 s. Earlier focused verification passed
  nine cases, then one affected case: **380 case executions / three invocations**
  in this increment. Tests use synthetic accounting, temporary stores and injected
  replies. **451 relative file links / 82 Markdown files passed**; anchors and
  external URLs were not checked. Whitespace validation passed.
- The requested Codex CLI worker ran with explicit `gpt-6.1-sol` and `xhigh`
  overrides, confirmed in execution metadata, and completed normally with exit 0
  and a final-message artifact. The coordinator reviewed the implementation.
  No live runtime inference, paid effect measurement, new credentials, target
  mutation or merge occurred. Publication is limited to this feature branch and
  its review PR. This is a cost-recording boundary,
  not completion of Gate 5 or the existing-agent integration.

### Merged PR #38 selected-issue offline probe (historical checks)

`feat/oss-selected-issue-capture` started from owner-merged
[PR #37](https://github.com/moruku36/agent-sleep-lab/pull/37) at
`63ca34df000ad95cd279d7652f4c7669d19f0c34`; GitHub verified MERGED and
[main CI success](https://github.com/moruku36/agent-sleep-lab/actions/runs/42921165592)
at that exact commit.

- Added an explicit [selected-issue probe contract](oss-selected-issue-probe.md):
  v2 capture input/output/summary with a versioned selection, strict built-in
  issue number/type, exact issue/suite hashes and prelaunch rejection. Default
  v1 remains borderline-only; saved v1 captures/plans/cohorts need no migration.
- The worker retains the pinned source/default rules, actual scoring/band and
  real judge/prompt path. Every selected route is labelled a forced-judge probe,
  including #3. The target prompt's original borderline wording is unchanged;
  nonborderline probes are not normal automatic triage or target task execution.
- Adapter receipts, frozen journal bindings and cohort `/2` documents/reports
  retain strict selection/provenance. Comparable selected-probe cohorts normalize
  the identical validated notes block while retaining complete per-task hashes.
  Existing no-retry, current-policy, invalid-output and full-denominator rules remain.
- Added [regression sources](../tests/test_oss_selected_probe.py) for actual
  pinned five-issue captures and injected-reply journal/cohort flow. The eleven
  public source blobs are copied unchanged from local pinned Git objects into a
  license-bearing fixture, checked against production hashes by the test helper.
  Git acquisition is injected in these cases; capture/scoring/judge/prompt are not.
- Coordinator reviewed the preserved draft. **All 363 unique regression cases /
  one invocation passed** on Python 3.13.18 (26.045 s), including 11 new
  selected-probe cases. This record covers local verification.
- Separate offline acceptance read all eleven source blobs from actual local
  pinned Git objects (no source-acquisition mock), launched five fresh guarded
  workers, and captured all five selected issues. Actual scores/bands were
  #1/#4/#5: 0.65/accept, #2: 0.0/skip, #3: 0.5/borderline. All used the real
  pinned judge/prompt code and inert capture transport. Journal restart,
  five-member aggregation, invalid-output accounting, zero-call replay and
  score withholding after policy revocation passed with ten injected replies.
  The fixture difference was zero, not a measured model result.
- Worker provenance: after explicit owner approval, the unchanged Codex command
  was submitted with native one-time approval. Local metadata confirms provider
  `openai`, model `gpt-6.1-sol`, effort `xhigh`. The outer tool timed out at
  600 s; no final-message file or normal-completion receipt, no matching process
  on reconciliation. No retry, substitute worker/model or API development call.
  Development usage/cost are unknown.
- The checks used offline fixtures and injected replies. Live inference, paid
  runtime measurement, independent holdout, semantic memory-use evidence and
  adoption were outside their scope. #1/#4/#5 repeat issue text.
  Parser/evaluator and target implementation bytes are unchanged.
  Real acceptance remains outstanding.

### Merged PR #37 cohort baseline evidence (historical checks)

`feat/oss-fixture-cohort`, based on owner-merged
[PR #36](https://github.com/moruku36/agent-sleep-lab/pull/36) at
`6e4018c8393103c6f3da362fa409814a61571a3a`. GitHub verified MERGED and
[main CI success](https://github.com/moruku36/agent-sleep-lab/actions/runs/42916818253)
at that exact commit.

- Added a separate [frozen synthetic fixture cohort registry](oss-fixture-cohort.md).
  Two to five unique task identities, exact plan/manifest pins and comparable
  settings are committed before any member intent. A short journal reservation
  excludes competing intent writers; membership cannot be rebound.
- Read-only reports keep every registered task in the denominator. Unknown,
  missing, withheld, corrupt or unsupported outcomes prevent overall means and
  paired difference. Invalid completed verdicts score zero without retry.
  Reports contain no reply bodies, rationale or answer labels.
- All **352 unique regression cases / one invocation passed** locally on
  Python 3.13.18 (24.123 s), including 13 new cohort cases. Feature CI is pending.
  These used injected replies and stand-in captures; default v1 selects only
  issue #3. They do not verify the new opt-in multi-task selected-probe path.
- Development worker: after automatic review refusal and explicit owner approval,
  the unchanged Codex CLI request was submitted through native one-time approval.
  Local execution metadata confirms provider `openai`, model `gpt-6.1-sol` and
  effort `xhigh`. The outer tool timed out at 600 s; no final-message file or
  normal-completion receipt was obtained and no matching worker process remained.
  Draft changes were preserved, independently reviewed and tested by the
  coordinator. No retry, substitute model or API worker call; development usage
  and cost are unknown.
- Unmerged work: no live inference, paid runtime measurement, independent
  evaluation dataset, confidence interval, rationale-quality scoring, cost
  schema, adoption, target changes or merge. This is descriptive synthetic
  development-fixture accounting, not performance evidence.
  Real acceptance remains outstanding.

## Merged PR #36 strict fixture evaluation

Historical branch `feat/oss-verdict-evaluation`, based on owner-merged
[PR #35](https://github.com/moruku36/agent-sleep-lab/pull/35) at
`7dc833f14034087b1559eb6ffcef71cf2675e582` (source
`c9d7d5e18723ee7858972a9bb3d99013bcb31e27`). GitHub confirmed MERGED and
successful Python 3.11 / 3.13 PR checks.

- Added a [strict verdict parser and frozen fixture evaluator](../src/agent_sleep_lab/oss_verdict_evaluation.py).
  This is an explicitly stricter subset of the pinned OSS parser, not a claim of
  identical permissive semantics. Only whole JSON with boolean accept and
  nonempty bounded text rationale is accepted; duplicate keys, coercion, prose,
  nonfinite/surrogate data and extra fields fail with sanitized codes.
- Optional manifest freezes the caller-declared synthetic label, task hash and
  issue number, evaluator/parser/strict-JSON implementation hashes, target-source
  hash and fixed criterion in the execution plan before any intent. Labels never
  reach the provider prompt. Posthoc changes/attachment to an unscored plan conflict.
  Existing unscored plans need no schema migration and remain unscored.
- Report-time evaluation distinguishes parsed decisions, invalid verdict failures
  and incomplete/unknown arms. Invalid completed outputs score zero without retry;
  missing/unknown arms never create a paired difference. Current-context revocation
  withholds parsed rationales and scores. Code/criterion mismatch prevents silent
  rescoring. A single-fixture difference is not scientific effect evidence.
- [Eight new regression cases](../tests/test_oss_verdict_evaluation.py).
  Full local regression: **339 unique cases / one invocation passed** (Python 3.13,
  18.845 s). Following strict-JSON and issue-binding improvements, related checks
  passed: 8 cases (1.168 s) then 16 cases (2.725 s).
  Total: 363 regression case executions / three invocations, 339 unique cases.
- Separate offline acceptance used actual pinned source/captured prompts and only
  injected replies. Three target-parser samples: one compatible strict verdict
  and two intentionally stricter refusals. Actual capture → first saved reply →
  reopen → second reply → stable replay → policy withholding passed with two
  mock calls per acceptance. Two acceptance invocations (before/after issue binding);
  six differential sample executions / two end-to-end fixture runs in total.
  Manufactured fixture differences, not model verdicts/performance.
- Worker provenance: one Muse Wonder review request was attempted with explicit
  `meta/muse-wonder-1.0`, but the tool timed out at 270 s. No response, normal
  completion, resolved-model or cost receipt was obtained; no matching process
  remained on read-only inspection, which does not establish remote outcome.
  No retry/substitution. Coordinator continued authorized implementation/review
  and verification; this is not a successful Muse development receipt.
- [Contract and limitations](oss-verdict-evaluation.md): no live/runtime inference,
  paid effect measurement, adoption, target mutation, default/auth/schedule or merge.
  Labels are unauthenticated synthetic fixtures; rationale quality is not verified.
  Remaining: justified independent dataset, broader aggregation, live verification
  under spending controls, usage/cost schema and actual paired effect measurement.
  Real acceptance remains outstanding.

## Merged PR #35 durable execution journal

Historical branch `feat/oss-durable-prompt-execution`, based on owner-merged
[PR #34](https://github.com/moruku36/agent-sleep-lab/pull/34) at
`4492cb05a5aa057b1905753834bd0bcbb0d84f81` (source
`c7071b43e30f95f0b3a7b59b9720f50048b0fbec`). GitHub confirmed MERGED and
successful Python 3.11 / 3.13 PR checks.

- Added a separate [durable execution journal](../src/agent_sleep_lab/oss_execution_journal.py)
  connecting validated captures to the exact-prompt adapter. Full capture,
  source/task/reference/arm hashes, bridge, adapter/agent/model/transport and
  limits are frozen. Existing IDs cannot be rebound to changed execution settings.
  Synthetic task provenance is distinct from injected/CLI execution provenance.
- Intent commits before each call; response and sanitized hash-bound receipt
  commit before the next arm. Close/reopen continues only unstarted arms and
  replays complete pairs without dispatch. Unclosed intents, unknown outcomes,
  invalid outputs or receipt mismatches halt the plan; fresh adapters cannot retry.
- Current context is checked before/after calls and on report. Revoked replies
  store only hash/length/status. Already saved bodies and receipt details are
  withheld from reports after context changes/unavailability (not physically erased).
- Own application ID/version/exact schema, explicit initialization, read-only
  foreign-DB inspection, full-sync writes and short immediate transactions.
  No DB lock spans transport. One driver per plan remains the contract;
  overlapping drivers conservatively stop instead of duplicating a call.
  There is no cross-store atomicity or authenticated store/worker origin.
- [Eight new mock-only cases](../tests/test_oss_execution_journal.py). All
  **331 unique local cases passed in one invocation** (Python 3.13, 18.842 s).
  After explicitly closing the read-only probe, its one affected case passed
  (0.108 s): 332 local case executions / two invocations, not 332 unique cases.
  Tests use test-authored captures/adoptions and injected CLI envelopes only.
- Worker receipt: `ok=true`, provider `meta`, model `muse-wonder-1.0`,
  no fallback attempts; one development design review. Coordinator implemented
  and verified the reviewed design. Worker suggestions are not authorization:
  live selection flags do not supply owner approval or change external controls.
- [API and limitations](oss-durable-execution.md): old fake journal/type restriction
  unchanged; no live inference, actual target acceptance, paid effect measurement,
  new CLI entry point, credentials, defaults, schedules or merge. Usage/cost remain
  unavailable; byte bounds are not token/financial caps.
  Remaining: live verification under separate spending approval, target verdict
  parsing, frozen independent evaluator, paired usage/cost and effect comparison.
  Real acceptance remains outstanding.

## Merged PR #34 exact-prompt adapter

Historical branch `feat/oss-registered-mimo-adapter`, based on owner-merged
[PR #33](https://github.com/moruku36/agent-sleep-lab/pull/33) at
`19c7e39440f4b938ba95250e212a5fce01d0f8c3` (source
`76e5b026762c5cd646fe2c92630405e09e6d4a1a`). GitHub confirmed MERGED and
successful Python 3.11 / 3.13 PR checks.

- Added a separate [exact-prompt adapter](../src/agent_sleep_lab/oss_mimo_adapter.py)
  for explicit registered MiMo calls. It validates the entire captured artifact,
  pins/source/task/reference/request/prompt hashes and A/B relation before reserving
  a call. The exact selected user text is forwarded with no instruction wrapper.
  This is not HTTP wire replay; original URL/headers/model/settings are not forwarded.
- Literal paid/uncapped-generation opt-ins, 1–2 calls, timeout at most 120 seconds,
  captured request/envelope/post-generation byte bounds, strict CLI model/provider/
  no-fallback/text-output checks and sanitized hash-bound receipts.
  Usage/cost remain unavailable; no supported usage/cost schema or financial cap.
- [Six mock-only cases](../tests/test_oss_mimo_adapter.py) cover exact Unicode
  forwarding, opt-ins/budgets, capture rejection, invalid/fallback/oversized replies,
  timeout/interruption stops and sanitized missing usage/cost. Full local regression:
  **323 unique cases / one executed invocation passed**, Python 3.13, 17.043 s.
  An earlier system-Python 3.9 launch stopped at imports (missing dependencies);
  no test cases executed in that launch.
- Worker receipt: normal completion confirms provider `meta`, model
  `muse-wonder-1.0`, `ok=true`, no fallback attempts. Coordinator reviewed the
  untrusted proposal and corrected its fictional envelope, opt-in/budget validation,
  capture binding and failure handling. No further worker invocation.
- [Contract and limitations](oss-exact-prompt-adapter.md): stop/budget are
  **in-memory per instance**, not a durable live journal. No current-policy executor,
  live paired-journal integration, actual OSS acceptance or live evaluation has
  been run for this change. All runtime adapter calls were injected mocks.
  The prior paired journal remains fake-only with unchanged schema/type restrictions.
  Next: durable context-aware live execution, target verdict parsing, frozen
  evaluator and paired usage/cost/effect measurement. Real acceptance remains outstanding.

## Merged PR #33 offline paired-outcome journal

Historical branch `feat/oss-paired-outcome-journal`, based on owner-merged
[PR #32](https://github.com/moruku36/agent-sleep-lab/pull/32) at
`46a1e585e580275aef003c72bc74f08c9be09b52` (source
`96ba94bb25d71089a5f6abdd8cd14926e42ddb97`). GitHub confirmed MERGED and
successful Python 3.11 / 3.13 PR CI checks.

- Added a separate [paired-outcome journal](../src/agent_sleep_lab/oss_paired_outcome.py)
  consuming actual captured OSS request artifacts, not replacement task prompts.
  Registration validates the capture, source/task/reference hashes, current-policy
  context and caller-supplied worker labels, then freezes both exact requests,
  original reference bytes, retrieval/bridge identity and equal per-arm byte bounds.
  Artifacts and caller-controlled store/summary labels are not authenticated authority.
- Each arm commits intent before one fake dispatch and commits its reply before
  the next arm. Close/reopen can continue an unstarted second arm; saved replies
  replay without redispatch. Unknown outcomes permanently stop the plan.
  A changed/unavailable context prevents remaining dispatches; context is rechecked
  after replies and on report, withholding stale reply bodies.
- Private SQLite journal has a separate application ID/schema, explicit full-sync
  settings, foreign-database refusal and saved-reply integrity checks.
  This assumes one driver per plan and is not a cross-store atomic transaction.
- **Fake-only execution:** only an explicitly supplied local fixture provider is
  supported. Replies are synthetic bytes, not parsed target verdicts or real model
  receipts. Usage/cost stay unavailable; byte caps are not generation-token or
  monetary caps. No live provider, CLI or evaluator was added.
- [Eight new regression cases](../tests/test_oss_paired_outcome.py) cover byte-exact
  Unicode request binding/provenance, durable continuation/replay, unknown outcomes,
  policy revocation before/after replies, malformed bindings/size bounds,
  unavailable context, database identity/durability and reply corruption.
  All **317 unique local cases passed in one invocation** (17.497 s, Python 3.13).
- Separate acceptance captured a nonempty Japanese reference through the actual
  pinned OSS judge/prompt, then passed those exact request bytes to the fake journal.
  One arm completed, the journal closed/reopened, the other completed; a third run
  replayed both, with two total fake calls. Current exclusion withheld both saved
  reply bodies. Preparation/fake execution wrote nothing to the adoption store.
  External provider calls, model verdicts and live usage/cost measurements: zero.
  Store adoption/verifier/evaluator data were explicitly test-authored fixtures.
- Worker provenance: explicitly requested `claude-fable-5-2`, but the invocation
  timed out at 300 s after saving the module and six cases. No normal-completion
  or resolved-model receipt was returned; no worker retry/substitution. Coordinator
  reviewed and hardened saved code, added two regression cases and verified it.
- Remaining: bounded live-provider wiring with current-context checks, real model
  identity/usage receipts, target verdict parsing, a frozen independent evaluator,
  paired cost accounting and effect measurement. This is offline execution plumbing,
  not semantic-memory-use or performance evidence. Known guard gaps remain open.

## Merged PR #32 adopted-reference preparation

Historical branch `feat/oss-adopted-reference-preparation`, based on merged PR #31.
**Locally verified:** all 309 unique regression cases passed in one invocation
(Python 3.13, 15.290 s). PR CI is reported separately. No paid/live evaluation inference.

- Reference canonical validation now requires retrieval's own byte form
  (sorted keys, compact, unescaped UTF-8) through one stdlib helper,
  `canonical_reference()`, in the
  [prompt-capture worker](../src/agent_sleep_lab/oss_prompt_capture_worker.py)
  and the shared [parent payload builder](../src/agent_sleep_lab/oss_offline_parent.py).
  ASCII-only bundles are byte-identical to before. Escaped, re-spaced, BOM,
  duplicate-key, invalid UTF-8, lone-surrogate and oversized bytes are refused.
  The prompt framing boundary additionally refuses data frame markers. Strict JSON, the 32,768-byte / 256-record caps and the
  exact reference SHA-256 are unchanged; worker protocol OUTPUT stays canonical ASCII.
- [Three new integration cases](../tests/test_oss_adopted_reference.py) use a
  temporary adoption store whose verifier/evaluator receipts and adoptions are
  **test-authored fixtures**, plus a labelled stand-in worker. They cover a
  nonempty eligible Unicode reference framed byte-exact in the reference arm
  only, A/B comparability, current-policy exclusion, mismatched scope, no store
  mutation during preparation and fail-closed malformed/non-canonical bytes.
- Not claimed: store-origin authentication, semantic memory use, a model
  verdict or any performance result. `OfflinePipeline` still requires the
  ASCII-canonical subset. Known filesystem guard gaps remain open.
- Actual pinned-source acceptance passed with one Japanese synthetic memory from
  a temporary adoption store (test-authored adoption and verifier/evaluator fixtures).
  The exact claim appears only in the reference prompt: 3,079 UTF-8 bytes vs 962
  baseline bytes. A second fresh worker after policy exclusion retrieved zero records
  and omitted the claim. Each worker called the real pinned judge/prompt twice;
  preparation performed zero store writes, provider calls, responses or verdicts.
- Worker provenance: normal completion receipt confirms `claude-fable-5-2`
  (`terminal_reason=completed`, `is_error=false`); no fallback. Coordinator reviewed
  the saved changes, corrected one test boundary assumption and ran verification.
- Remaining: bounded explicit live-provider executor and real provider/model receipts;
  durable paired outcome/cost accounting and frozen evaluator.

## Merged PR #31 prompt contract

Historical development branch `feat/oss-reference-prompt-contract`, based on
PR #30 and merged in PR #31 (merge `c8b6ccc`, source `c61cbb1`).
GitHub confirmed MERGED and both Python 3.11 / 3.13 PR CI checks succeeded.
Owner priority is implementing memory-use and comparable execution before
measurement. **No paid or live measurement has been run.**

- Added a separate [prompt-capture parent](../src/agent_sleep_lab/oss_prompt_capture.py)
  and [stdlib worker](../src/agent_sleep_lab/oss_prompt_capture_worker.py); old
  worker/pipeline protocols stay unchanged. Existing preflight freezes the same
  eleven reviewed blobs, then a fresh guarded process drives the real pinned
  `OpenAITriager.judge → triage_prompt` path for the built-in borderline issue.
- Both arms share the issue, actual default score/reasons, mock model and request
  settings. Baseline has no project notes; reference arm inserts one explicit
  untrusted-data frame containing the exact bounded reference bundle.
  Parent recomputes request/prompt hashes and verifies that the two prompts differ
  by only that contiguous insertion, with equal non-prompt request fields.
- An injected local transport captures the requests and raises the pinned
  `LLMTriageError`. It never sends a request, returns a response or fabricates
  a verdict. Endpoint/model/credential are explicit inert fixture labels;
  environment credentials are not consulted and header values are not exported.
- `prepare_from_bridge()` obtains an existing explicit bridge's scoped reference
  under current policy, with worker byte/record caps and pinned repository/commit.
  Store origin stays caller-controlled/unauthenticated. Artifact preparation is not
  dispatch authorization; a later executor must revalidate current context.
- **Actual pinned-source acceptance passed once**: issue #3, actual score 0.5,
  two calls each to the pinned judge/prompt function, two captured requests,
  zero provider calls/responses/verdicts, zero adoptions/verifier/evaluator receipts.
  Reference came from an empty temporary synthetic store (zero records).
  Baseline prompt was 962 UTF-8 bytes and reference prompt 1,960 bytes.
  This verifies reference-data placement in an actual request path, not semantic
  use of an adopted memory. The full collection pipeline remains unchanged.
- [Five new contract cases](../tests/test_oss_prompt_capture.py) use stand-ins
  and cover exact framing, binding/label rejection, A/B equivalence, the no-response
  transport and preflight/stand-in labels. They are not real-model evaluations.
- Worker provenance: explicitly requested `claude-fable-5-2`, but the invocation
  timed out at 300 seconds after saving two modules. No successful completion or
  resolved-model receipt was returned; do not claim a successful Fable run.
  Read-only process reconciliation found only an unrelated Claude process over a
  day old. No worker retry/substitution was started. Coordinator reviewed the
  saved modules, wrote/verified tests and actual acceptance, and updated status.
- Remaining: nonempty independently eligible memory integration; bounded explicit
  live-provider executor and real provider/model receipts; durable paired outcome/
  cost accounting and frozen evaluator. At PR #31 the capture path accepted only
  the ASCII-canonical bundle subset (addressed and locally verified on the current branch).
  Prompt framing is not proof of prompt-injection immunity or authenticated origin.

## Merged guard-verification baseline (historical checks)

The six guard cases cover selected socket/process/environment/cwd/write-open/
SQLite/resource checks in fresh children. They do **not** establish a hostile-code
sandbox. The separate side-effect-free event probe found `os.remove`, `os.rename`,
`os.mkdir`, `os.link`, `os.symlink`, `os.chmod`, `os.truncate` unhandled.
No corresponding external mutation was executed. That baseline did not harden
these events. The current local, unmerged strengthening is described above;
these six historical cases do not verify its additional boundaries.

## Merged PR #29 pipeline

Historical development branch `feat/oss-offline-journal-pipeline`, merged in PR #29.

- Added [OfflinePipeline](../src/agent_sleep_lab/oss_offline_pipeline.py):
  bridge retrieval → durable reference journal → parent checker → saved decisions
  → capture. Bridge repository/commit must match the built-in pinned task.
  Reference budget is at most the worker's 32,768 bytes and 256 records.
- A canonical contract binds retrieval, target path, launch configuration and
  capture timestamps/session/authorization into the journal consumer version
  before dispatch. Changed configuration under the same use ID conflicts.
  The bounded consumer output persists the contract, checker summary and
  hash-bound returned decisions before any capture.
- Capture resumes only from saved output. Deterministic event IDs and the existing
  store's byte-identical replay allow recovery after partial capture without
  executing the worker again. Unknown, invalid receipt and invalidated outcomes
  are never re-dispatched or captured as success. Current context is rechecked
  before/between/after capture, and the capture boundary checks authorization
  even on replay. Already captured observations are not rolled back when policy
  changes; remaining capture stops and reports partial observations.
- Added read-only `ReferenceUseJournal.context_unchanged()`; no journal schema
  change, migration, new database or automatic retry mechanism.
- **Separate actual pinned-worker pipeline acceptance passed**: an empty reference
  from a temporary synthetic store, one real worker invocation, interruption
  before capture #3, journal reopen, then two replayed and three newly captured
  observations. A further call replayed all five with total worker invocations
  still one. Outcomes were candidate, low-score skip, pending LLM, duplicate skip
  and infrastructure error. No adopted memory or verifier/evaluator receipt exists.
- [Nine integrated regression cases](../tests/test_oss_offline_pipeline.py) use
  real temporary synthetic stores/journals and a mocked checker, not target code.
  They cover replay, partial recovery, contract conflicts, unknown result,
  changed context, current capture authorization, caps, mid-capture policy change
  and oversized output. Mocked results stay explicitly labelled stand-ins.
- Development provenance: Claude Code's terminal metadata identifies
  `claude-fable-5-2` / `firstParty`, but the run **did not complete normally**:
  `is_error=true`, `terminal_reason=api_error`, HTTP 429
  `usage_limit_reached`. It saved pipeline code and the journal accessor only.
  The coordinator reviewed the partial code, added the nine acceptance tests and
  per-capture context checks, and completed verification/status updates.
  No alternative coding worker/model was started.
- This is synthetic offline orchestration, not production integration or
  authenticated delivery/use. The receipt remains unreviewed self-report and
  `delivery_and_use_verified` stays false. Empty reference bytes reach
  `Target.notes`; triage with `llm=None` does not use them semantically.
- Remaining: nonempty eligible-memory use, broader guard-boundary coverage/hardening,
  bundle-key drift/store-origin binding, real-data authorization and real comparison
  evaluation. Capture/journal/store are not one cross-database transaction.
  The explicitly supplied store remains caller-controlled, not authenticated;
  capture recovery requires the same surviving evidence store. Local origin URL
  is mutable and guard code is not a sandbox for hostile Python.
  Actual acceptance script/artifact remain local coordinator evidence, not a
  portable checked-in real-target regression.

Already merged in PR #25:

- The [reference dispatch journal](reference-use.md) freezes bounded task/reference
  bytes and identities, records durable intent before dispatch, uses CAS, refuses
  retry of unknown outcomes and rechecks context before/after dispatch.
- Returned output is hash-bound, but consumer receipts remain unreviewed;
  `delivery_and_use_verified` is always false. Accounting is not semantic-use proof.

Already merged in PR #24:

- Added an opt-in [OSS Contributor collect-only bridge](oss-bridge.md) for the
  existing agent's `TriageDecision` dictionary contract.
- Capture preserves decisions and any model rationale as untrusted observations,
  not verified issue facts. It creates no memory, verifier/evaluator receipt or
  adoption. Pending and failure states stay observations.
- Read-only context uses current-policy adopted-memory retrieval with fixed scope,
  byte limits and exclusions. No target ledger, scoring, configuration, scheduler,
  patch/PR path or production host is changed.
- This is **synthetic offline wiring**, not real-data ingestion or proof of
  delivery/use by the existing agent. Real operational capture needs a separate
  non-synthetic retention/authorization contract; do not relabel real logs.

## PR #31 verification and PR #32 handoff (historical checks)

- `feat/oss-adopted-reference-preparation`: **nothing executed yet.** The three
  new cases, full regression, documentation check and pinned-source acceptance
  are pending with the coordinator. Figures below are PR #31 history.
- **306 unique regression cases / one full invocation passed in 15.327 s** on the
  existing Python 3.13.18 environment. Includes five new prompt-capture cases.
  Earlier focused five-case run: four passed / one fixture error; corrected the
  stand-in source paths to match required trace names, then the affected one case
  passed. **312 case executions / three invocations** total in this trial.
- Separate actual acceptance: one fresh prompt-capture worker, two captured
  requests through pinned judge/prompt code, no external calls or model verdicts,
  and empty eligible-reference data. Not counted as regression cases.
  Worker-output SHA-256:
  `2d26697d97af0cf4277582b77155fefcf72febdb4d2e0a651d800bee734acc02`.
- Documentation: **370 relative file links / 76 Markdown files passed**;
  anchors and remote URLs excluded. Whitespace diff check passed.
  Feature CI not run.
- Historical PR #30 verification: 301 cases / one invocation in 15.011 s and
  earlier six focused cases (307 executions/two invocations), 366 relative
  links / 76 Markdown files. Its seven-event diagnostic was not a regression case.
  Historical PR #29 verification: 295 cases plus eight earlier focused cases,
  and one real empty-reference pipeline recovery acceptance. None was rerun here.
- Nonempty adopted-memory semantic use, live comparison/evaluation and the
  known filesystem mutation guard gaps remain unverified/unfixed.

## Genuine remaining work

1. Resolve the MiMo execution approval/binding failure and obtain a real
   provider/model receipt. The owner approved the saved review command, but the
   unchanged native `ask=always` submission was again denied before execution:
   approval could not safely bind. No alternate route or model was attempted.
   An earlier design request timed out without receipt; its usage/cost is unknown.
2. Run the prepared five-task real-response comparison with applicable caller
   budget, independently accepted experience memories and a frozen evaluator.
   [Fictional development tasks](../examples/paper-pilot/README.md) are preparation,
   not an independent holdout. Exact-match fixture scoring is not scientific
   paper-quality proof.
3. Connect ONE existing agent and verify actual capture/retrieval use. Offline
   bridge contracts and manual handoff drafts are preparation only. Real-data
   boundaries and actual delivery/use verification remain open. The new local
   dispatch journal supplies accounting only, not authenticated use evidence.
4. Opt-in lexical raw ranking and read-only cost reporting are owner-merged in
   PR #41 and PR #42; the offline demo is owner-merged in PR #43 with green CI.
   The read-only preparation gate above does not complete real acceptance.
   Semantic relevance/fairness, physical purge and broader production fault
   acceptance remain open; none is established by passing offline tests.

Runtime contracts and commands: [English](runtime-guide.md) / [日本語](runtime-guide.ja.md).
The MiMo CLI lacks per-call max-token control: post-generation byte rejection
is NOT a hard token or monetary limit; unknown outcomes may have incurred cost.
