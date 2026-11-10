# OSS exact-prompt adapter contract

[English status](implementation-status.md) | [日本語の状況](implementation-status.ja.md)

## API and boundary

[OSSMimoAdapter](../src/agent_sleep_lab/oss_mimo_adapter.py) is a separate library
adapter for the existing registered `xiaomi/mimo-v2.6-pro` account. Construct it
with an explicit registered `agent`, `max_calls` (1–2), and literal-True
`acknowledge_paid_execution` and `acknowledge_uncapped_generation`. These flags
do not supply owner authorization or override host approval/spending controls.

`complete(capture_doc, reference=original_reference_bytes, arm="baseline" or
"reference", max_output_bytes=...)` returns `(UTF-8 reply bytes, receipt)`.
It validates the whole canonical capture via the existing validator, including
both arms, pinned source/task/reference hashes and their one-insertion relation.
Then it passes the selected captured user prompt **unchanged**, with no new
instruction wrapper, to the explicit model through `openclaw infer model run`.
It never uses the captured mock URL, header values or mock model for networking.

This is **prompt-text forwarding, not replaying the original HTTP request**.
The CLI controls its own request; target request settings such as temperature
are not forwarded or claimed equivalent. The module does not parse target
verdicts, run an evaluator, adopt memory or measure semantic memory use.

## Bounds, receipts and stops

- Full captured request: at most 131,072 bytes (configurable downward).
- CLI timeout: integer 1–120 seconds; honored by the normal subprocess transport.
- Envelope: at most 1,048,576 bytes after process return.
- Reply: caller-selected 1–65,536 UTF-8 bytes, checked **after generation**.
- Calls reserved before dispatch; never automatically retried or sent to a fallback.
- Any post-dispatch error (including malformed output, mismatched model/provider,
  fallback attempts, timeout, oversize or interruption) leaves the instance stopped.
- Success requires `ok=true`, provider `xiaomi`, model `mimo-v2.6-pro`, no
  fallback attempts and exactly one text-only output.
- Receipts whitelist request/prompt/capture/source/task/reference/output hashes,
  verified envelope model labels, bounds and transport provenance. Raw process
  output, stderr, private errors, account metadata and arbitrary fields are not copied.
  Injected transport receipts explicitly say `injected_transport_not_live_verified`.
- Usage/cost remain **unavailable**, not zero. This adapter does not yet support a
  stable CLI usage/cost schema and ignores arbitrary supplied metadata.

These are not generation-token, monetary, process-memory or wire-output limits.
`subprocess.run(capture_output=True)` buffers output before validating its size.
A custom injected transport is trusted local code, not a timeout sandbox.

## Deliberately incomplete integration

The call budget and stop are **in memory, per instance, single-driver only**.
They are not a durable intent/outcome ledger, multi-process lock or permission
boundary. Constructing another instance or restarting a process does not recover
an unknown outcome and must never be used to retry one.

Artifact validity does not authenticate a worker, a store or current policy.
The separate [durable driver](oss-durable-execution.md) now checks current context
before/after each call, saves intent/outcome/receipts and withholds stale bodies;
its verification is mock-only, not live evaluation. The adapter by itself still
does not supply those guarantees. The existing paired-outcome journal is still **fake-only**;
its provider type restriction, schema and synthetic reporting are unchanged.
There is no new live CLI command, automatic schedule or paid evaluation.

[Six new regression cases](../tests/test_oss_mimo_adapter.py) use test-authored
capture stand-ins and injected process envelopes only. They verify exact Unicode
prompt forwarding, strict opt-ins/budgets, full capture rejection, permanent
instance stops, interrupts and sanitized unavailable cost reporting. They do
not verify actual OSS execution, a live model, durable continuation or performance.
