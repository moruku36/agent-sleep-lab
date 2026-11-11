# Read-only OSS request preparation

[日本語](oss-prepare.ja.md) | [Runtime guide](runtime-guide.md)

`oss-prepare` connects an existing adopted **synthetic experience** memory to
the pinned OSS Contributor request-construction path. It prepares baseline and
reference requests offline; it never sends them. This is not live-agent delivery,
real-data ingestion, semantic memory use or evidence of improvement.

## Usage

```sh
agent-sleep-lab oss-prepare --manifest /private/run/prepare.json --store-config /private/run/store.json
```

The store configuration uses the unchanged fields and boundary gates from
[the runtime example](../configs/runtime-store.example.json). Its SQLite path must
already exist with the supported adoption-store schema, policy and adopted memory.
This command cannot create a store or adopt a memory. Boundary labels configure
local simulation; they do not authenticate the caller or store.

The manifest is a strict JSON object, rejecting duplicate keys and unknown fields:

```json
{
  "protocol": "agent-sleep-oss-prepare-input/1",
  "target_repo": "/absolute/local/oss-contributor-agent",
  "bridge": {
    "scope": {"project": "p", "task_family": "t"},
    "repository": "moruku36/oss-contributor-agent",
    "agent_commit": "e40b39c6258ac5a4446c38246bdfd7f5dc5dbf7b"
  },
  "retrieval": {"query": "duplicate", "max_bytes": 32768, "max_records": 16}
}
```

Manifest and configuration each have a 32,768-byte input cap. Query must be
nonempty printable text, at most 1,024 characters. Byte and record limits are
explicit integers, excluding booleans, in 1–32,768 and 1–256 respectively.
The byte cap covers the whole canonical reference bundle, not tokens or dollars.
The target repository must be an existing absolute directory. The existing parent
reads only pinned Git objects and verifies reviewed source hashes; it does not
import the target worktree. The local origin URL remains an unauthenticated claim.

## Read / prepare / recheck

1. Open the existing adoption store read-only/query-only, without initialization
   or migration; retrieve eligible adopted experience records in the explicit scope.
2. Refuse an empty returned bundle before any target preparation.
3. Freeze the exact bundle bytes and run the existing built-in prompt-capture
   worker once for both arms. The reference arm adds the bounded untrusted-data
   frame; baseline does not contain it. Existing source, framing, byte and
   comparability gates remain enforced.
4. Retrieve again in a fresh read transaction. Refuse changed snapshot, policy,
   returned records or other context, including newly expired/ineligible memory.
   Only the retrieval `as_of` timestamp may advance.
5. Emit one JSON object with protocol `agent-sleep-oss-prepare-output/1`,
   `synthetic_only`, context hash, validated summary and capture document.

No artifact is emitted on failure; exit code is 2 with a generic diagnostic that
does not echo input paths, raw worker output or exception details. Success is 0.
There is no retry. Provider, adapter, injected worker argv, transport, plugin,
journal and output-file options are not accepted. No inference, capture, receipt
registration, adoption or target configuration/ledger modification occurs.
Read-only SQLite can still use locks or sidecars; this is not filesystem isolation.

The output intentionally includes complete **synthetic reference text and request
payloads**. Keep runtime outputs private; stdout is not an automatic publication
allowlist. Output does not grant later inference permission. Policy can change
after emission; any eventual consumer must revalidate its own current context.
The command is not a durable dispatch journal or a hostile-code sandbox.

## Verification boundary

[Implementation status](implementation-status.md) records current evidence.
Unit contracts use real temporary adopted stores and labelled stand-in workers.
Separate local acceptance can use the actual pinned source; neither kind calls a
model, authenticates store origin, measures semantic use or proves improvement.
