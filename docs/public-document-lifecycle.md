# One-document public-data lifecycle

**English** | [日本語](public-document-lifecycle.ja.md) | [Status](implementation-status.md)

This is a **separate versioned library/store**, not a relaxation of synthetic
provenance, RuntimeStore, retrieval or CollectOnlyBridge. It admits exactly one
already-reviewed public document, with source-attributed excerpts only. There is
no fetching, provider client, CLI auto-dispatch, timer or paid-model integration.
Tests use fictional public bytes and injected offline consumers.

## Trusted host configuration

[public_document_runtime.py](../src/agent_sleep_lab/public_document_runtime.py)
uses contract `agent-sleep-public-document/1` and a dedicated private SQLite file.
Explicit `PublicDocumentStore.create(...)` exclusively creates a new file;
`PublicDocumentStore(path)` only opens an existing file. It neither migrates nor
opens a synthetic store as a fallback.

Configure four distinct `Authority(identity, version)` roles outside source/model
content: control, excerpt verifier, mechanical evaluator and semantic reviewer.
Separately configure `Consumer(identity, version, runtime_permission,
max_input_bytes, max_output_bytes)`. The consumer cannot share a role identity.
These are **local trusted-host capabilities, not identity authentication, OS
isolation or protection against code that can modify the database/Python process**.
Keep control/review handles and filesystem access away from untrusted providers.
Identity/version/permission configuration is persisted and compared on reopen.

The host calls `store.control(control_identity).approve(...)`, supplying a
separately reviewed [PublicDocumentApproval](public-source-intake.md), the exact
staging artifact SHA-256, origin task ID and expected control generation. Current
approval revision, source URL/hash, scope, approval/expiry time, artifact hash and
origin task binding are persisted. Increasing revisions require a matching current
generation and unchanged approval reference; changing a revision after admission
invalidates old derivatives. Withdrawal increments the generation. Deleted or
purge-pending stores cannot be approved again.

Every content API resolves that persisted **current** control itself. Passing an
obsolete approval object to staging cannot authorize a runtime read. Admission
calls `recheck_public_document` and requires exactly the artifact approved by the
control boundary. Each later content access checks current exclusion, finite
expiry (strict `now < expires_at`), admitted generation, staged source integrity
and every managed derivative hash. A trusted timezone-aware clock is injectable
for tests; operational callers must supply an accurate clock.

Stage/admission approval grants **no model, agent, paid execution, publication or
policy permission**. The explicit consumer permission is a separate host choice.
Native execution/approval controls of the embedding runtime remain mandatory.

## Small explicit path

These are API steps, not automatic actions. Keep runtime artifacts outside the
public checkout; public fixtures must remain fictional.

1. Acquire/review bytes outside this library. Prepare the existing canonical
   staging artifact using `prepare_public_document`.
2. Create the private store with independent host role/consumer configuration.
   Resolve the control handle and approve the exact artifact with
   `origin_task="capture-task", expected_generation=0`; then `store.admit(artifact)`.
3. Submit `store.propose_excerpt(proposal_id="excerpt", quotation=exact_quote)`.
   It stores immutable **unverified** data, not preferences, policy or abstractions.
   `read_proposal` and `candidate_snapshot(proposal_id=..., expected_parent=EMPTY_HEAD)`
   are read-only review APIs. They do not create receipts.
4. Independently invoke `store.verifier(verifier_identity).issue(proposal_id=...,
   expires_at=...)`. This deterministic verifier only checks exact source
   quotation fidelity and binds the candidate hash; it does **not** establish
   truth, abstraction quality, performance or semantic usefulness.
5. Invoke `store.evaluator(evaluator_identity).issue(proposal_id=...,
   expected_parent=..., verification_receipt=..., expires_at=...)`.
   The fixed mechanical protocol binds the exact candidate snapshot/parent and
   verification receipt. It is not a task-performance acceptance test.
6. Explicitly `store.adopt(operation_id=..., proposal_id=..., expected_parent=...,
   expected_generation=..., verification_receipt=..., evaluation_receipt=...)`.
   Registered receipts, authority/version, protocol, exact hashes, current control,
   receipt expiry and parent CAS are rechecked. The add-only snapshot, memory,
   adoption receipt, operation and head commit in **one SQLite transaction**.
   A failed write rolls all of them back. Operation-ID conflicts reject.
7. For a **different target task ID in the same approved project/task family**,
   use `retrieve(target_task=..., scope=..., max_bytes=...)` or
   `prepare_request(request_id=..., target_task=..., scope=..., task_input=...,
   reference_max_bytes=..., consumer=...)`. Retrieval returns canonical complete
   attributed records only; if none fits it refuses. Request bytes bind generation,
   snapshot, target task, task-input hash, reference hash and consumer identity,
   version, runtime permission and byte caps.
8. A separate explicit `dispatch(request_id=..., consumer=..., invoke=...)`
   commits durable `dispatch_outcome_unknown` **before** entering the consumer.
   It rechecks control immediately predispatch and postreturn. The callback
   `invoke(exact_request_bytes, observe_input)` must call
   `observe_input(exact_request_bytes)` at its actual input boundary before using
   the data. Wrong/unobserved input cannot produce a returned receipt. The observer
   and invocation close share one lock, including the entire observation transaction.
   Close waits for an admitted in-flight observer to finish; queued/late callbacks
   reject after close. Observation writes and the returned-result transition require
   the persisted status to remain unknown, so an old observation cannot overwrite
   a returned receipt. This applies to both normal return and exceptional exit.
9. Inspect `execution_receipt` and `read_result`. Only a separately configured
   `semantic_reviewer(...).record(...)` can record an independent semantic-use
   judgment bound to the exact request and result hashes. Reviewers can inspect
   those exact bytes through `read_request` / `read_result` first.

The executable fictional walkthrough is the [behavior suite](../tests/test_public_document_runtime.py).
There is deliberately no implicit authority issue, provider output-to-receipt
conversion or default public-data dispatch.

## Offline body-bound Light / Deep saved-output handoff

This separate path uses pure
[public_document_sleep.py](../src/agent_sleep_lab/public_document_sleep.py)
contract `agent-sleep-public-document-sleep/1`, **not** the synthetic
`SleepCoordinator`. It constructs canonical requests and validates caller-saved
replies; it has no transport, callback, model selector, live option, retry or
receipt issuer. An accepted reply does not prove that a model was invoked or
received the request, and does not grant permission to invoke one.

After admission, trusted host code explicitly supplies all limits:

```python
from agent_sleep_lab.public_document_sleep import SleepLimits
from agent_sleep_lab.provenance import sha256_hex

limits = SleepLimits(
    max_request_bytes=16384, max_reply_bytes=8192, max_source_units=128,
    max_candidates=8, max_quotation_bytes=1024,
)
light_bytes = store.prepare_sleep(
    sleep_id="document-night-1", scope=approved_scope,
    expected_generation=current_generation, expected_parent=current_head,
    limits=limits,
)
# light_saved_reply and deep_saved_reply are separately obtained offline bytes.
# None of these APIs invokes a provider or executes the document.
deep_bytes = store.submit_light_result(
    sleep_id="document-night-1", expected_request_sha256=sha256_hex(light_bytes),
    result_bytes=light_saved_reply,
)
if deep_bytes is not None:
    pending = store.submit_deep_result(
        sleep_id="document-night-1", expected_request_sha256=sha256_hex(deep_bytes),
        result_bytes=deep_saved_reply,
    )
```

`prepare_sleep` returns exact canonical Light bytes. Deterministic complete source
lines (including original separators) are the units: each carries a unit ID,
UTF-8 byte offsets, exact text and unit SHA-256. There is no normalization,
truncation or generated source evidence. The request binds sleep ID, exact admitted
artifact/source hashes, current generation, approved scope, origin task, current
parent and all limits. Excess source-unit count or whole canonical request bytes
refuses preparation. Limits are positive integers: request/reply bytes at most
512 KiB each, source units at most 256, candidates at most 32 and an individual
quotation at most 65,536 UTF-8 bytes. These are not token or money limits.

The strict Light reply has **only** these fields:

```json
{"schema_version":"agent-sleep-public-document-sleep/1","stage":"light","request_sha256":"<exact Light hash>","selected":[{"unit_id":"line-1","source_unit_sha256":"<exact unit hash>"}]}
```

Selections must be unique existing IDs with matching hashes and fit the candidate
cap. Source order is canonicalized, not model order. Deep receives **only the
selected original units**, plus provenance/limits, exact Light request/reply hashes
and `source_selection_sha256 = SHA256(canonical_json(selected_original_units))`.
An empty Light list returns `None`, durably records `no_change` and cannot accept
a Deep reply or later introduce evidence under that same sleep ID.

The strict Deep reply has **only** these fields:

```json
{"schema_version":"agent-sleep-public-document-sleep/1","stage":"deep","request_sha256":"<exact Deep hash>","source_selection_sha256":"<selection hash>","proposals":[{"unit_id":"line-1","source_unit_sha256":"<exact unit hash>","quotation":"<nonempty exact substring of that selected unit>","untrusted":true,"authority":false}]}
```

Both parsers reject duplicate keys, extra fields, invalid UTF-8/JSON, wrong
request/selection/unit hashes, unknown or unselected units and count/byte overflow.
Deep additionally rejects non-source or duplicate quotations and authority-bearing
metadata. Quoted prose may itself contain instructions: it remains untrusted
source data, never host authority. A quotation cannot span units. Empty Deep is
also `no_change`. No abstractions, generated answers or verification claims are
accepted as source evidence.

Every API re-resolves current approval, admitted artifact, exclusion/expiry,
generation and managed-content integrity under the existing SQLite writer lock.
Submission reconstructs the original request from the current source/control/head;
a changed scope, generation, parent or source rejects even an exact old reply.
All Deep excerpts are validated **before any writes**; one transaction saves the
raw reply, host-ID-generated **UNVERIFIED** proposals and a non-authoritative
result summary, or rolls everything back. Head, memories, snapshots, reviews,
operations and consumer dispatch remain untouched. Return state
`unverified_proposals` is not adoption. Existing separately invoked verifier,
mechanical evaluator and atomic adoption are still required; adopting one proposal
changes the parent and requires fresh independent review for subsequent additions.

Immutable managed content kinds are `sleep_light_request`, `sleep_light_reply`,
`sleep_deep_request`, `sleep_deep_reply` and `sleep_result`. Generated proposals
also retain Deep-request, selected-source and source-unit hashes. All live in the
existing `content` inventory and are covered by the same purge; no schema/table
migration or external file is created. Invalid submissions leave no proposal or
reply artifact. Accepted exact byte replay is idempotent across reopen **only while
the original bindings remain current**; a different binding or raw reply, including
different whitespace, conflicts. Deletion does not resurrect artifacts or permit
replay. Caller buffers/exported saved files remain outside managed deletion.

[Five fictional offline scenarios](../tests/test_public_document_sleep.py) are
authored for this increment; execution and independent review are separate gates
recorded in [status](implementation-status.md).

## Unknown outcomes and honest observations

`prepared`, actual input observed and `returned` are distinct. Consumer
self-claims, citations and lexical overlap never create a semantic-use review.
A recorded independent judgment is a host assertion, not authenticated human
identity, a scientific performance comparison or generalized learning evidence.

A crash/exception, missing actual-input acknowledgment or invalid output leaves
the dispatch unknown, with no usable result. No automatic retry, refund or
restart replay exists. Exact request bytes/hash retain request ID, generation and
snapshot provenance. **Effective no-retry identity is separate**: within this
dedicated store/control generation it binds schema, target task, scope, task-input
hash, actual packed-reference hash (including source attribution) and the complete
configured consumer identity/version/permission/byte caps. Request ID and snapshot
lineage do not grant another attempt. Re-adopting identical excerpts or adding
records omitted by reference packing cannot refund an unknown execution when the
effective input remains identical. Dispatch compares persisted attempted requests
under the writer lock, including pre-fix intents, without migrating their exact
provenance column or changing request bytes. Missing attempted-request content
fails closed. This check applies to every prior attempt, not only unknown ones.
A genuinely new explicitly authorized effective task/input/reference binding is
separate work, not recovery or resolution of the old unknown outcome.
A returned receipt records bounded output bytes; output caps are checked after
return and cannot limit a remote provider's generated tokens or billed cost.

Exact adoption-operation replay returns **content-free history**, marks
eligibility unasserted and sweeps current control. It never sets the head or
restores eligibility. A different payload under the same operation ID rejects.
There is no rollback/resurrection API for a withdrawn public document.

## Managed deletion and limits

The dedicated bundle inventories source/evidence, proposal, adopted memory,
snapshot, request/result and all saved Light/Deep stage bytes. On expiry, withdrawal or integrity/current
generation failure it first durably records exclusion as `purge_pending`.
`purge()` removes managed text, approval URL/body, origin task and review/dispatch
derivatives with SQLite `secure_delete=ON`, DELETE journaling and `VACUUM`, then
marks `deleted` only after compaction succeeds. Any failed/interrupted cleanup
remains `purge_pending`, never logically-forgotten-but-claimed-physically-deleted.
Reopen and explicit `purge()`/on-access cleanup can finish that pending work.
Only minimal content-free control hashes/generation, configured identities and
hashed operation/adoption history remain to suppress re-admission and answer
exact historical replay. Other bundles/files are never recursively traversed or
deleted.

Run `sweep()` explicitly for expiry/integrity cleanup; content reads also trigger
it. **A stopped program cannot enforce a deadline**: expiry blocks access at the
next check, not deletion while the process is absent. There is no schedule.
Cleanup is managed SQLite content removal, not forensic secure erasure of SSD
cells, filesystem snapshots, backups, journals copied by others or arbitrary
exports. Prior caller staging files, Python buffers, consumer-held copies and
remote requests/results are outside this managed inventory; the host remains
responsible for their deletion and any remote retention contract. Revocation
during execution cannot recall already delivered bytes, but it blocks/purges
local access and makes the returned result unusable.

No actual public document, existing private staging/live bundle, original unknown
preparation, provider, paid model or real agent is exercised by this slice.
Live acceptance, actual public-data model generation, cost accounting and
independent performance review remain separate from this offline saved-output path. Current verification is recorded
only in [implementation status](implementation-status.md).
