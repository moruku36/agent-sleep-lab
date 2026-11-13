# Explicit public-document model connection

**English** | [日本語](public-document-model.ja.md) | [Lifecycle](public-document-lifecycle.md)

This optional library connects prepared public-document requests to the existing
registered OpenClaw route, explicitly selecting `xiaomi/mimo-v2.6-pro`. It does not
change the pure saved-output protocol or synthetic runtime. No CLI auto-dispatch,
fetch, fallback, retry, automatic adoption or agent loop is introduced.

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
call the provider again. The runner does not persist raw replies before submission;
a crash in that gap may lose them and requires stopping, not redispatch.

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
