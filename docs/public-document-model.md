# Explicit public-document model connection

**English** | [日本語](public-document-model.ja.md) | [Lifecycle](public-document-lifecycle.md)

This optional library connects prepared public-document requests to the existing
registered OpenClaw route, explicitly selecting `xiaomi/mimo-v2.6-pro`. It does not
change the pure saved-output protocol or synthetic runtime. No CLI auto-dispatch,
fetch, fallback, retry, automatic adoption or agent loop is introduced.

For current verification and release readiness, use only
[implementation status](implementation-status.md). This page defines the library
contract, not a release or performance claim. The library-only surface is
intentional: the host owns each permission, stage submission, independent review,
adoption and later consumer choice; there is no new CLI or automatic chain.
See the [component map](architecture-overview.md) and
[documentation index](index.md) for navigation.

## Host invocation contract

Import `InvocationPermission`, `invoke_stage`, `inspect_journal` from
`agent_sleep_lab.public_document_model`. A permission is an explicit independent
host choice, not an authenticated approval receipt and never parsed from source
or model output. Configure the registered agent explicitly. Request hash,
positive prompt-byte bound (at most 131072), timeout (1–120 seconds), paid-call
choice and acceptance of unknown cost must all be supplied.

Use ONE newly reviewed owner-authorized public document and a fresh isolated
public-document store, following the existing lifecycle admission contract.
Keep roles separate. Never reuse the old synthetic pilot store, reports or
unknown execution. Create one private metadata sidecar path alongside the new
store and preserve that SAME sidecar for all invocations.

```python
from agent_sleep_lab.public_document_model import InvocationPermission, invoke_stage
from agent_sleep_lab.provenance import sha256_hex

# store is an admitted PublicDocumentStore; all values below are host-selected.
preparation = dict(sleep_id=sleep_id, scope=scope,
                   expected_generation=generation, expected_parent=parent,
                   limits=limits)
light_request = store.prepare_sleep(**preparation)

def permission(request):
    return InvocationPermission(
        request_sha256=sha256_hex(request), agent=registered_agent,
        allow_paid_call=True, accept_unknown_cost=True,
        max_prompt_bytes=32768, timeout_seconds=120)

light_reply, light_observation = invoke_stage(
    store=store, preparation=preparation, stage="light",
    journal_path=sidecar, permission=permission(light_request))
deep_request = store.submit_light_result(
    sleep_id=sleep_id, expected_request_sha256=sha256_hex(light_request),
    result_bytes=light_reply)
if deep_request is not None:  # empty Light is terminal, never force a second call
    deep_reply, deep_observation = invoke_stage(
        store=store, preparation=preparation, stage="deep", journal_path=sidecar,
        permission=permission(deep_request), light_result_bytes=light_reply)
    proposals = store.submit_deep_result(
        sleep_id=sleep_id, expected_request_sha256=sha256_hex(deep_request),
        result_bytes=deep_reply)
```

This is at most two NEW model calls, one per explicit stage, only after a host
authorizes the concrete document and invocation. Source and replies stay in the
store's managed inventory when submitted; do not export raw replies to the repo.
If submission fails after a return, stop and inspect existing evidence: do not
call the provider again. By default the runner does not persist raw replies before
submission. The optional rejected-reply quarantine below covers only bounded
returned protocol failures; a crash can still lose a reply and requires stopping,
not redispatch.

## Optional Light task/rubric context

`prepare_sleep(..., selection_context=SelectionContext(task=..., rubric=...,
max_bytes=2048))` accepts an explicit `SelectionContext` from
`public_document_sleep`. The combined exact UTF-8 task/rubric text must be nonempty
and fit that positive bound, which cannot exceed **8192 bytes**. The entire canonical
request must still fit `SleepLimits.max_request_bytes`; nothing is truncated.
Use reviewed public development-task context only. Private text, credentials,
evaluation answers and held-out evaluation rubrics must not enter this field or
provider requests. Context exposed to Sleep is development input, not independent
holdout evidence.

The optional Light `selection_context` object contains exactly `task`, `rubric`,
`max_bytes`, `untrusted:true`, `authority:false`. It helps select useful original
units; it supplies no source evidence, permissions, review or adoption authority.
Deep receives only selected source units and binds the context through the exact
Light request hash. The context itself is omitted from Deep. Context text cannot
change limits, roles, paid-call choice, retry identity or execution restrictions.

Omitting context (or passing `None`) preserves the existing request and prompt
bytes. Adding/changing context changes the canonical request hash, so a permission
for an old request fails before reservation/dispatch. Reusing a sleep ID with
different context conflicts. Reopen/current-control reconstruction retains the
saved context. It is managed request content and is removed by the same purge.

To additionally pin the exact instruction plus request prompt, use
`build_stage_prompt(request=request_bytes, stage="light")` from
`public_document_model` and supply its SHA-256 as
`InvocationPermission(..., prompt_sha256=...)`. This field defaults to `None` for
existing callers. Request-hash permission and the prompt-byte cap are always
required; a supplied prompt hash must match before reservation. The actual outgoing
prompt is always hash-checked at transport entry and its hash/byte count recorded.
Prompt pinning grants no independent authority and authorizes no extra attempt.

## Opt-in managed rejected-reply quarantine

`invoke_stage(..., quarantine_max_bytes=N)` explicitly opts into retaining a
rejected raw reply. Default `None` retains no rejected bytes. `N` must be a positive
integer at most **65536** and no larger than the prepared reply limit. Only a
returned text reply from the verified transport envelope that fails the strict
Light/Deep protocol can be saved. Oversized quarantine input is skipped whole,
never truncated. Transport-envelope failures, unknown outcomes and crashes do
not produce a quarantined reply; generation/output-byte rejection before return
also cannot preserve it. These bounds are not token or monetary caps.

The adapter calls `store.quarantine_sleep_result(sleep_id=..., stage=...,
expected_request_sha256=..., result_bytes=..., max_bytes=N)`. Offline callers may
explicitly use that same API after a saved-output rejection. It rechecks current
control/source/parent/request and independently confirms strict rejection. Its cap
cannot exceed the reply limit (store maximum 512 KiB). Valid or already-accepted
replies cannot enter quarantine. A store has **one immutable raw-reply slot per
stage**, plus one small content-free rejection record per slot. Exact replay is
idempotent; a different request or raw reply conflicts without growing inventory.
Both writes commit together or roll back together.

Managed kinds `sleep_rejected_reply` and `sleep_rejection` use the existing content
inventory, integrity guard, expiry/withdrawal exclusion, `purge_pending`,
secure-delete and compaction path. No new table, migration or raw-output sidecar is
added. The explicit `read_sleep_quarantine(sleep_id=..., stage=...,
expected_request_sha256=...)` diagnostic read returns rejected bytes only while
their original bindings remain current. It does not parse them into proposals.
A saved quarantine is terminal for submission under that exact request: even a
corrected saved reply cannot replace it. Invalid Deep replies produce **zero**
proposals, reviews, adoptions or consumer results. Verifier/adoption/consumer
boundaries are unchanged.

Sleep errors expose content-free `.code` categories: `invalid_json`,
`protocol_fields`, `binding_mismatch`, `source_selection`, legacy `invalid_excerpt`,
`authority_claim`, `excerpt_source_mismatch`, `quotation_bound`,
`quotation_not_exact`, `duplicate_excerpt`,
`byte_limit`, `item_limit`, `invalid_context` and fallback `invalid_protocol`.
For structurally valid Deep items, first-failure order is authority flags, source
binding, quotation byte bound, exact substring, then duplicate quotation. Malformed
fields/text still use protocol categories. No partial proposal list is returned.
Store quarantine refusal adds `quarantine_bound` or `quarantined`; ordinary
lifecycle rejection uses `lifecycle_rejected`. Transport errors use
`transport_rejected` or `transport_outcome_unknown`. No raw output, hostile keys or
exception text is copied into exceptions, logs or receipts. Sidecar metadata adds
only `error_category` and `quarantine_status`: `disabled`, `skipped_bound`,
`saved_untrusted` or `not_saved`. `not_saved` can reflect exclusion, an immutable
slot conflict or a storage failure; it asserts no retention success.

Quarantine never refunds the durable stage reservation. Changing context, sleep
ID, request, parent or quarantine opt-in does not permit redispatch. Purge removes
the managed quarantine but leaves the separate metadata no-retry tombstone.
Caller buffers/exports, provider copies, backups and stopped-program deadlines
remain outside the managed deletion guarantee. Retained bytes are untrusted
diagnostic data, not an independent verification/adoption receipt.

## Observability and durable stops

The sidecar reserves UNKNOWN synchronously before transport entry. Its unique key
binds canonical store path, document artifact hash, generation and stage, so a new
sleep ID, parent or request cannot bypass a reserved stage. Even returned stages
cannot redispatch. Concurrent callers sharing this sidecar cannot both reserve.
Keep the sidecar; replacing/deleting it, cloning the store, changing its path or
approval generation is not a recovery mechanism or permission to retry. This is
local cooperative no-retry protection, not authenticated global exactly-once.

Metadata includes exact prepared-request and actual CLI prompt SHA-256/byte
counts; the outgoing prompt hash is checked at transport entry. The existing
provider checks model/provider identity, no-fallback envelope, output bytes and
monotonic CLI transport time. Strict public-document parsing then checks exact
reply bindings. Response hash/bytes and accounting availability live in
`transport_receipt`; absent usage/cost is unknown, never zero. A transport wrapper
is truthfully labelled injected by the underlying adapter; it only validates the
prompt then calls the supported CLI. Fake tests are not live evidence.

Byte limits are preflight request/prompt bounds and post-generation output bounds,
NOT hard token or monetary caps. CLI prompts can appear in local process metadata.
No credentials, defaults or host configuration are changed. Current store control
is rechecked immediately before reservation and again on result submission;
there is no distributed transaction with the remote provider. Withdrawal racing
with transport cannot recall already sent public bytes.

## Review, adoption, later task and deletion

A valid Deep result creates only unverified excerpts. Independently inspect source
quotation fidelity through the configured verifier, then obtain the separate
snapshot evaluator receipt against the exact parent/candidate. Invoke guarded
adoption explicitly with current generation/parent/receipts. Do not convert model
output or transport observations into review receipts. Mechanical quotation
checks do not prove useful abstraction or performance.

Only after adoption, prepare retrieval for a different target task and explicitly
invoke the separately configured consumer through the existing dispatch boundary.
Input observation, consumer return, independent semantic review and performance
evaluation remain distinct; this adapter performs none of them.

The metadata-only sidecar is OUTSIDE managed deletion: it contains hashes and
accounting/timing metadata, not prompts/replies. Host lifecycle management must
retain its no-retry tombstones, restrict access and decide metadata retention.
Do not delete it merely because source bytes expire. Store sweep/purge cannot
erase CLI/provider copies, local process observation, backups or caller exports.
No timer or cleanup automation is added.
