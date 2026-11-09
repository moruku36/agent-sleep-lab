# Memory Promotion and Implementation Contract

[日本語](contracts-and-acceptance.ja.md) | [Home](../README.md)

Status: design only, 2026-11-09. This document specifies the first durable memory boundary for another implementing AI. No capture engine, model call, active memory or schedule is created.

## 1. Preserve v0.1; add an explicit adoption boundary

The existing event/memory schemas remain `0.1` design records. They are useful for candidate exchange but insufficient for runtime adoption. The new [promotion request schema](../schemas/promotion-request.schema.json), version `sleep-promotion/1`, supplements them. No old candidate is automatically migrated to verified or active.

An importer may preserve a v0.1 object for inspection, but promotion additionally requires source attestations, verification receipts, an exact snapshot evaluation, current exclusions and an expected parent. Migration records old/new hashes and unresolved evidence; missing provenance remains missing. Current configuration does not become executable by changing a schema version.

## 2. Evidence is not self-authenticating

The capture adapter, not the source text or candidate model, creates a provenance sidecar with these fields:

| Field group | Required meaning |
|---|---|
| Identity | Event ID/hash, project/task family, adapter identity and pinned revision |
| Origin | Authenticated user correction, tool observation, external document, model-derived summary, recall, REM or diary |
| Source | Original object ID/hash, locator and observation/capture timestamps |
| Lineage | Original root IDs and derived-from IDs; repeats share roots |
| Eligibility | Current authorization reference/revision, permitted purpose, retention/expiry, synthetic flag and evaluation partition |

A hash establishes identity, not truth or consent. An external document may support a factual claim after verification; it cannot establish a user preference or permission. Recall, REM, diary and generated answers can propose a candidate but are never independent root evidence. Do not infer origin from a `trusted=true` field in text.

Verification receipts bind the exact memory content hash, source hashes, scope, method/version, verifier identity, time, result and limitations. The writer resolves the receipt from an accepted verifier boundary; a model-written verifier name is insufficient. A hypothesis stays a candidate until its factual/procedural claim is checked and reclassified. The number of mentions or retrievals does not establish confidence.

## 3. Operations, not replacement snapshots from the model

Deep proposes one operation per target ID: `add`, `supersede`, `mark_stale`, `reject` or `defer`. Each includes target ID, replacement record reference where needed, reason and evidence IDs. `supersede` creates a new memory ID and retains the old record as superseded. `mark_stale` removes an item from normal retrieval without claiming it false. `defer` records a pending proposal without changing active memory.

The writer constructs the candidate snapshot from the expected parent and validated operations. Reject unknown targets, duplicate target operations, ID collisions, scope changes, cycles and unmentioned removal/modification. No model-supplied full file replacement is accepted. If size limits would be exceeded, defer; do not silently evict unrelated memories.

Evidence verification and snapshot acceptance remain separate. An item may be verified but absent from active. A passed snapshot evaluation does not verify the truth of every member by itself.

## 4. Atomic promotion protocol

The request binds operation ID, run ID, scope, expected parent, candidate snapshot hash, operation-manifest hash, source-manifest hash, verification receipt, evaluation receipt, authorization revision and exclusion revision. Opaque references are locally resolved, not automatically fetched from arbitrary URLs. The [synthetic request](../examples/promotion-request.synthetic.json) is inactive and contains symbolic references only.

1. Read current authoritative permissions/exclusions and expected parent. A stale revision fails closed.
2. Resolve and verify all input hashes; check source existence/access/expiry, exact memory verification and snapshot evaluation binding.
3. Build immutable candidate files in staging, flush them and verify their content before publishing references.
4. In one writer transaction, compare parent and current policy/exclusion revisions again, then commit operation ID, adoption receipt and active pointer together. A separate read followed by filesystem replace is not a compare-and-swap transaction.
5. Acknowledge only after durable commit. On uncertain acknowledgement, look up the operation ID and digest; do not repeat promotion. Same ID with different content is a conflict.

An initial project expects parent `null`; null must not match an already initialized project. Concurrent writers are serialized by a cross-process lock plus revision check or an equivalent transactional store. Document the chosen crash/durability behavior on the accepted OS. Staged orphan blobs may be garbage-collected only after checking all committed references.

The verifier's identity and current policy must be independent of candidate input. If evidence changes outside the writer's transaction domain, use immutable captured evidence plus a trusted revocation version, or a source lease/attestation with recheck. Do not claim a cross-system atomic guarantee from a local file rename.

## 5. Revocation and rollback

Exclusions are an independently versioned authority, never stored solely inside an old memory snapshot. Every retrieve, promote, replay and rollback reads the current exclusion revision. Follow derived-from links to block affected descendants immediately, then complete required deletion from caches, indexes, snapshots and diaries. Keep only the minimal permitted suppression record; a hash can itself be sensitive.

Rollback is a new audited active-pointer operation to a retained snapshot, subject to current permissions, expiry and exclusions. It is not restoration of historical permission. Recheck the target's integrity and eligible members; if removed evidence prevents safe restoration, reject rollback and retain the last safe configuration/raw retrieval path.

If exclusions cannot be loaded, memory retrieval fails closed while the foreground task may continue without memory. Do not block user responses waiting for optional sleep. A permission or contradiction change may remove a previously active item immediately; a later performance study is not required to stop using revoked or false evidence.

## 6. Retrieval as bounded reference data

A bundle carries project/task family, active snapshot hash, current exclusion revision, as-of time, selected memory IDs/hashes, source references, measured tokenizer/version and tokens used. Filter scope, synthetic/production, status, expiry and exclusions before ranking. Normal retrieval requires active membership and verified evidence; investigate candidates/stale material only in a distinct diagnostic mode.

Never truncate a claim away from its scope or evidence. Drop whole low-ranked records when exceeding the budget. If no accepted tokenizer is available, return an explicit unavailable status or use a separately declared byte limit; do not report estimated characters as exact tokens. An empty eligible result is valid.

Pin the snapshot for an evaluation task, but current revocation still applies. If revocation changes the bundle during a frozen study, stop/mark that paired trial invalid under the protocol rather than serving prohibited data or silently comparing different treatments. Log which memories were supplied and used without treating repeated retrieval as new experience.

## 7. Development gates are not perpetual holdouts

Use development/regression tasks to inspect and improve candidate snapshots. Freeze the candidate, retrieval policy and protocol before a separate final comparison. A set repeatedly consulted to adopt daily memories becomes development data; do not call every promotion an independent held-out result. Reserve fresh assessment batches or clearly label continued monitoring exploratory.

Preserve the existing raw-retrieval A versus consolidated B comparison, same task/model/tool budget and full cost. Record unsupported claims, contradictory/stale memory use and abstentions, not only retrieval hit rate. A verified user correction can be retained as a candidate without repeatedly querying a final benchmark. Operational adoption, item verification and a scientific performance claim are distinct decisions.

## 8. Optional sibling integration

Follow the [reference-only three-harness contract](https://github.com/moruku36/ai-agent-scientist/blob/main/docs/11-harness-boundaries.md) only after standalone acceptance. Scientist owns current research state; CTF owns investigation evidence; Sleep owns reusable eligible knowledge. Current authorization remains outside all memory. No shared writable store or mandatory service dependency.

Only reviewed development lessons enter from siblings; preserve their source/evaluation partition and export permission. No raw flags, private datasets, final answers or protected evaluator details. Record shared cost reservations without double counting. Pin accepted external schemas locally by commit/hash; no mutable schema download during offline operation.

## 9. Implementation acceptance matrix

All cases are **planned, not executed**. Schema checks in this design update do not satisfy runtime acceptance.

| ID | Fixture | Required result |
|---|---|---|
| SLP-01 | Event redelivery or recalled/REM/diary text | Same roots deduplicated; generated content not independent evidence |
| SLP-02 | `verified` candidate with pending or forged receipt | No promotion; active unchanged |
| SLP-03 | Source changes/disappears between proposal and adoption | Hash/access recheck fails; no activation |
| SLP-04 | Another writer promotes first | Expected-parent conflict; unrelated records preserved |
| SLP-05 | Two simultaneous requests expecting null parent | Exactly one initialization commit; other conflicts |
| SLP-06 | Crash before/after active-pointer commit and lost ACK | Last committed active remains valid; operation lookup prevents double write |
| SLP-07 | Evaluation refers to another snapshot or protocol | Receipt rejected, even when reported score is high |
| SLP-08 | Revocation after candidate creation, then replay/rollback | Current exclusion wins; no resurrection |
| SLP-09 | Cross-project or synthetic memory in production | Filter before ranking; no recall leakage |
| SLP-10 | Oversized bundle, missing tokenizer, no eligible memory | Whole-record omission or explicit unavailable/empty; no fake token count |
| SLP-11 | Delete unrelated memory or supersession cycle | Operation rejected; immutable history retained |
| SLP-12 | Repeated final-set-guided promotion | Exposure recorded; set is development, not fresh confirmation |

First implement local contracts, provenance and the writer with fake model/verifier outputs; then retrieval; then candidate generation. Return fixture IDs/outcomes, schema/source versions, crash recovery evidence, resource usage, migration and known limitations. Model calls, live adapters and performance experiments are later milestones.
