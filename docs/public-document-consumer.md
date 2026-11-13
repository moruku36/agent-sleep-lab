# Explicit public-document later consumer

**English** | [日本語](public-document-consumer.ja.md)

This library adapter connects an already persisted later-task request to one
explicit MiMo invocation. It does not prepare requests, fetch documents, adopt
memory, run semantic review or change the synthetic runtime.
[Implementation status](implementation-status.md) is the sole current verification
authority; this usage contract is not a claim that the helper is live-verified.

## Host invocation

After admission, independent quotation/mechanical review and adoption, use
`store.prepare_request(..., consumer=configured_consumer)` as described in the
[lifecycle](public-document-lifecycle.md). Independently inspect the exact saved
request, scope, current approval and host permission before invoking:

```python
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.public_document_model import InvocationPermission, inspect_journal
from agent_sleep_lab.public_document_consumer import invoke_consumer

request = store.read_request(request_id)
permission = InvocationPermission(
    request_sha256=sha256_hex(request),
    agent=registered_agent,             # explicit host configuration
    allow_paid_call=True,              # only after independent host authorization
    accept_unknown_cost=True,
    max_prompt_bytes=32768,
    timeout_seconds=60,
)
receipt, metadata = invoke_consumer(
    store=store, request_id=request_id, consumer=configured_consumer,
    journal_path=preserved_private_sidecar_path, permission=permission,
)
result = store.read_result(request_id)   # managed content; do not export implicitly
observations = inspect_journal(preserved_private_sidecar_path)
```

The permission must be the frozen `InvocationPermission` type, not model/document
text. The consumer must exactly match the store configuration. Request/consumer
bounds must fit 65,536 bytes, output bounds 1–65,536 bytes, prompt permission
1–131,072 UTF-8 bytes, timeout 1–120 integer seconds. The fixed model is
`xiaomi/mimo-v2.6-pro`, one call maximum, no fallback or automatic retry.
Byte checks and CLI elapsed time are not token/financial caps or provider latency;
post-generation output checks cannot cap generation charges. Missing accounting
remains unknown, never zero.

## Durable lifecycle and boundaries

Before reserving, the helper checks the exact persisted request, hash permission,
configured consumer, current generation/head, byte bounds and previous exact
attempt. Provider initialization validates agent and timeout first. These are
preflight checks, not authorization leases: `store.dispatch` repeats the current
checks and remains authoritative for same/effectively identical requests, including
renamed request IDs.

A separate SQLite sidecar uses the stage adapter's metadata-only `calls` schema.
Its unique identity binds canonical store path, consumer stage and exact request
hash. A FULL-synchronous committed UNKNOWN reservation precedes dispatch and
transport. Preserve the same sidecar across processes/restarts; a concurrent
reservation cannot obtain a second call. Different sidecars do not override the
main store's effective-identity gate. Do not delete/reset reservations to retry.

At transport entry the helper checks the entire expected CLI argv, exact prompt,
timeout and subprocess options. It calls `observe_input(exact_request)` immediately
before `subprocess.run`, never during preparation or reading. This is a local input
observation, not remote authentication. Nested provider receipts intentionally say
`injected_transport_not_live_verified`; an envelope label alone does not upgrade it.

The return is a dispatch receipt plus content-free metadata. Raw replies are held
only in the managed result path. The finally block saves provider observations,
including elapsed time/unknown accounting when available, without exception strings,
source text, prompt or raw reply. Exceptions after reservation leave conservative
UNKNOWN/no-retry status, even if dispatch was blocked before transport. A crash can
leave only the initial UNKNOWN row; inspect evidence without redispatch.

Postreturn revocation/current-control checks stay in the store. A provider return
does not imply a usable managed result. `semantic_use` remains `not_reviewed`;
semantic review is a separate host operation, never consumer self-certification.
Preserve content-free no-retry metadata while applying the lifecycle's deletion
rules to managed content and any independently created derivatives. No timer,
automatic cleanup, credential change or background execution is installed.
