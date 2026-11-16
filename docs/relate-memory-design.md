# Connected Recall with Relate

**English** | [日本語: full implementation design](relate-memory-design.ja.md) | [Experiment](../experiments/relate-memory/README.md)

Design date: 2026-11-17 JST. Availability and executed evidence belong only in
[implementation status](implementation-status.md). This page specifies future work.

## Recommendation and alternatives

| Option | Benefit | Cost / limitation | Decision |
|---|---|---|---|
| Move the canonical store to Relate | One graph transaction domain | Rebuild adoption, receipt, CAS, forgetting and recovery contracts; migrate existing stores | Defer |
| SQLite authority + rebuildable Relate index | Preserve existing correctness boundaries; relationships change recall; easy removal | Projection freshness, duplicate storage, deletion and final eligibility checks | **Recommend** |
| Frozen export + standalone graph viewer | Smallest isolated demonstrator | A viewer alone need not improve recall | First milestone / reduced-scope fallback |

Keep the forgetful-agent assumption in [ADR 0002](decisions/0002-assume-agent-forgets.md).
Relate discovers candidates and explanatory paths. SQLite decides which records
are adopted and currently eligible. Neither a graph edge nor a model output grants
permission or creates verification receipts.

## Existing boundaries

The [baseline](../experiments/relate-memory/BASELINE.md) pins core commit
9853c4e993fefadab003c52b5a30729c6ddfa683. Its synthetic AdoptionStore and
[retriever](../src/agent_sleep_lab/retrieval.py) enforce exact project/task_family,
partition, current policy, hashes, receipts and evidence ancestry in a SQLite
read transaction. Its lexical ranking is deterministic; budgets are UTF-8 bytes.
The separate [public-document store](public-document-lifecycle.md) is a different
contract and is not the MVP input. Do not relabel real data as synthetic.

## Model

Use stable identifiers namespaced by store_instance_id, project, task_family and
partition. Add content hashes for immutable versions. IDs and actor names are
bindings, not authentication. Never merge scopes because IDs or source URLs match.

| Node | Key data |
|---|---|
| Scope | Explicit store identity, project, task_family, partition |
| Snapshot | Snapshot and parent hashes, policy identity |
| MemoryVersion | Memory ID/hash, kind, validity |
| EvidenceVersion | Event ID/hash, root, origin, observation time |
| SourceVersion | Source ID/hash and bounded locator reference |
| Task | Task ID, exact input hash |
| Entity | Scoped file/API/decision identity |
| UseEvent | Use ID, stage, bundle hash, outcome reference |
| Agent | Host-declared agent ID and role |

| Directed edge | Meaning |
|---|---|
| Scope → HAS_SNAPSHOT → Snapshot | Version belongs to this scope |
| Snapshot → HAS_MEMBER → MemoryVersion | Membership state and verification receipt binding |
| MemoryVersion → SUPPORTED_BY → EvidenceVersion | Grounding and locator |
| EvidenceVersion → DERIVED_FROM → EvidenceVersion | Child to parent; shared roots are not independent support |
| EvidenceVersion → FROM_SOURCE → SourceVersion | Fixed source version |
| New MemoryVersion → SUPERSEDES → Old MemoryVersion | Adopted correction, not a graph-inferred replacement |
| MemoryVersion → ABOUT → Entity | Reviewed relation with evidence |
| Task → TARGETS → Entity | Explicit task target |
| Task → DEPENDS_ON → Task | Explicit task dependency |
| Task → HAS_USE → UseEvent | Observed preparation / dispatch / result |
| UseEvent → INCLUDED_MEMORY → MemoryVersion | Inclusion does not prove semantic use |
| UseEvent → BY_AGENT → Agent | Actor metadata |
| UseEvent → REVIEWED_USE_OF → MemoryVersion | Only when an independent semantic-use receipt exists; optional in MVP |

Task/entity relations are not all existing core fields. The experiment needs a
versioned, hashed synthetic relation-assertion sidecar with endpoint IDs, evidence
references and review state. Begin with manually reviewed synthetic relations,
not automatic LLM extraction. Canonical content stays in SQLite. Graph metadata
and paths can still be sensitive and belong in deletion inventories.

## Projection and retrieval contract

There is no atomic transaction across SQLite and Relate. Use bounded full rebuilds
per scope first; do not add a dual write to the existing adoption transaction.

1. A new CoreReadBridge exports one consistent SQLite view: head, policy,
   exclusions, eligible records, evidence closure and permitted historical metadata.
   Reuse core eligibility checks. The existing bounded retrieval bundle is not a
   complete export API: truncation must fail explicitly. Isolate any pinned
   internal API dependency in this adapter. An additive shared read API, if needed,
   is a separate minimal core commit with unchanged existing behavior.
2. Bind the export hash, core format/version, store identity, scope, partition,
   snapshot, policy, relation-sidecar hash, graph schema and Relate version in a manifest.
3. Build a fresh generation, validate endpoints/scope/IDs/cycles, close and reopen
   it, and compare current SQLite state again. Publish only its small generation
   pointer atomically. Never overwrite an open graph file.
4. Retrieval uses graph seeds from lexical overlap and explicit task entities.
   Traverse TARGETS / ABOUT, optional dependency-use paths, reverse SUPERSEDES,
   and evidence/source paths. Only reviewed edges participate.
5. Revalidate selected ID/hash pairs and every explanation path against current
   canonical state before reading content. Historical nodes may supply permitted
   navigation metadata, never obsolete recall text. All-ancestor evidence checks
   remain mandatory even when relevance traversal is shallow.
6. Rank deterministically, then fit whole records and their explanations inside
   one measured byte budget. A new versioned experiment envelope binds snapshot,
   policy, graph generation, query template, sidecar and selected IDs. Do not
   silently extend the existing v1 bundle or pass it to an unaware consumer.
7. Recheck context before dispatch. This does not make subsequent agent actions
   atomic with SQLite.

Initial proposed limits: 8 seeds, 32 candidates, 200 visited nodes / 400 edges,
3 hops per relevance template, 8 supersession hops, 8 returned memories and
8,192 UTF-8 bytes. Record reached limits. Full evidence eligibility is separate.
Rank by explicit task relation, distance, distinct source-root coverage, lexical
match and stable ID; popularity is not truth.

Missing, stale, corrupt or busy graph: use the existing SQLite lexical path only
if its canonical checks pass, with an explicit fallback reason. Canonical policy
or evidence failure stops retrieval; never serve graph-only content.
Revocation first blocks canonical retrieval, then invalidates and cleans graph
generations, caches and exports. Do not promise deletion of unmanaged copies.

## Isolation and rollback

Put optional dependencies, config, code, tests, fixtures and output under
experiments/relate-memory/. Root packaging and default CLI stay unchanged.
Dependency direction is experiment → pinned core; core never imports the experiment.
Use a separate environment. No automatic database migration or writeback.

One process and owning thread use a graph connection; agents do not concurrently
open its storage file. The first interface is a bounded, explicit CLI, not a new
server or scheduler. Competing invocations wait within a bound or return busy.

Disable the experiment and return to core retrieval to roll back behavior.
Retain current canonical data. Revert experiment commits without resetting shared
main or reverting unrelated core work. A baseline code checkout is not permission
to overwrite a current database with an old copy.

## Demonstrator and schedule

One synthetic development project, two agent roles, approximately 20 memories,
one handoff scenario: find a relevant but lexically dissimilar constraint, follow
its correction and evidence, then stop recalling it after revocation.

Compare lexical, graph expansion and graph with a useful edge type removed using
the same snapshot, policy, query, seeds and total byte budget. All arms preserve
scope, correction and deletion safety. Include unrelated high-degree distractors
and cases where graph expansion does not help. Separate development fixtures from
frozen expected results. Measure retrieval coverage, valid paths, safety violations,
bytes, projection/retrieval time and storage. Synthetic results are a functional
demonstration, not general agent-performance evidence.

| Dates (JST) | Deliverable |
|---|---|
| Nov 18–20 | Pinned runtime persistence/reopen and isolated read/export bridge |
| Nov 21–25 | Rebuildable projection, manifest and inspectable store |
| Nov 26–30 | Graph retrieval, canonical recheck, explanation and fallback |
| Dec 1–4 | Correction/revocation and bounded comparative acceptance |
| Dec 5–8 | Reproducible judge workflow and 90-second demonstration |
| Dec 9–11 | Freeze artifacts, verify reopening and prepare submission |

Follow the existing [test budget](testing-budget.md). Select affected cases from:
persistence/idempotence; useful edge ablation; scope/correction/revocation;
partial rebuild/fallback; optional-dependency removal and unchanged core.
Do not run the whole historical suite or paid inference for documentation work.

If the Python binding fails the first milestone, try a pinned CLI adapter.
If graph retrieval is unfinished by Dec 1, reduce to a truthful standalone
connected-context demonstrator. Vector search, WASM UI, MCP, live migration and
wider deployment are not required.

## Dependencies and submission caveats

Relate upstream reviewed: [5f8eaf1](https://github.com/relatedb/relate/tree/5f8eaf129a6490bd4b6664cffc7b9498e2c6b93f).
Its [limitations](https://github.com/relatedb/relate/blob/5f8eaf129a6490bd4b6664cffc7b9498e2c6b93f/docs/limitations.md)
include a single-process, in-memory working set. A transaction is not a general
multi-process writer guarantee. Prefer an embedded Python .rl store, but verify
installation, platform, thread affinity and close/reopen on the selected release;
README/reference distribution descriptions differ. A full directory store is an
acceptable persistence fallback. Preserve WAL and checkpoint together when needed.

See the Japanese design for the checked [event page](https://relate.devpost.com/)
versus [official-rules](https://relate.devpost.com/rules) discrepancy concerning
existing extensions and scoring. Eligibility and final scoring require organizer
confirmation. Deadline: Dec 12, 2026, 11:00 JST. Disclose the reused core,
new extension work and AI assistance in [REUSE](../experiments/relate-memory/REUSE.md).
The core is public but UNLICENSED; this change does not grant a new license.
Ship only synthetic public data. A design document alone is not a working entry.
