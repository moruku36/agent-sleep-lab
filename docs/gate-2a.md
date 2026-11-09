# Gate 2A: provenance contract and local evidence store

[日本語](gate-2a.ja.md) | [Home](../README.md)

Status: **locally accepted on macOS arm64 / Python 3.13.18: 110 tests passed, including 23 Gate 2A tests.** The built wheel passed synthetic evidence-store and Gate 1 CLI checks from outside the checkout. GitHub CI and publication status are separate; see the [acceptance report](../reports/gate-2a-progress.md). Gate 1 (read-only validation CLI) is unchanged. This slice adds a Python library only: no writable CLI, active pointer, memory promotion, retrieval, verifier/evaluation integration, schedule, model call, or migration.

Design basis: [ADR 0004](decisions/0004-local-evidence-store.md) and [contracts §2](contracts-and-acceptance.ja.md).

## What it does

`agent_sleep_lab.provenance` defines the strict sidecar schema `agent-sleep-provenance/1` (packaged as `schemas/provenance.schema.json`, same bytes under the repository `schemas/`). `agent_sleep_lab.evidence_store` stores event bytes, original source bytes, and the stamped provenance in SQLite.

API sketch below: `ev`, `src`, and `claim` are prepared synthetic inputs, and the database parent directory must already exist. For a complete runnable fixture, use [the installed-wheel acceptance helper](../tools/check_evidence_installed.py).

```python
from agent_sleep_lab.provenance import CaptureBoundary
from agent_sleep_lab.evidence_store import EvidenceStore, ReadOnlyEvidenceStore

boundary = CaptureBoundary(                       # configured separately from the data
    adapter_id="synthetic-adapter", adapter_version="1.0.0",
    allowed_origins=frozenset({"tool_observation", "recall"}),
    authorizations={"auth-1": 1},                 # reference -> current revision
)
path = "/tmp/asl-demo/evidence.sqlite3"  # existing parent directory
with EvidenceStore(path, boundary) as store:
    result = store.capture(event_bytes=ev, source_bytes=src, claim=claim)  # created | replayed
    report = store.verify(result.event_id)        # IntegrityReport(ok, failures)
with ReadOnlyEvidenceStore(path) as reader:
    stored = reader.get("e-1")                    # no capture API; get is not verification
```

- `capture` is atomic. It returns `created`, or `replayed` for byte-identical content (including the boundary's adapter identity) whose stored record still passes `verify`. A corrupt existing record raises `storage.corrupt_existing`; different content under the same id raises `conflict.event_id`.
- `get`, `list_event_ids`, `independent_root_count(project, task_family)`, `verify`, `verify_all`, `close`.
- The `claim` is the provenance JSON **without** `adapter`; the boundary adds it, and a claim carrying one is rejected. Event text is never read for origin, adapter, authorization, or lineage; only `event_id`, scope and `synthetic` are compared with the claim.
- Errors are `EvidenceError` subclasses with a stable `.code`: `ContractViolation`, `BoundaryViolation`, `LineageViolation`, `ConflictError`, `NotFoundError`, `StorageError`.

## Rules enforced

- Synthetic only: a non-synthetic claim or event fails closed (`synthetic.required`).
- Unknown schema version, extra or missing fields, invalid RFC 3339 times, `observed_at` after `captured_at`, malformed identifiers: rejected.
- Scope in the claim must equal the event's scope and the parent's scope; origin, scope and authorization (reference, **current** revision, expiry) must be permitted by the boundary.
- Independent origins (`user_correction`, `tool_observation`, `external_document`) are their own root. Generated origins (`model_derived_summary`, `recall`, `rem`, `diary`, `generated_answer`) must derive from stored records and never count as roots; a second root with the same source bytes in a scope is `conflict.duplicate_root_source`.
- Before a descendant is added, every transitive ancestor including the root is re-verified in the same transaction: hashes match, source bytes present, unexpired, current authorization revision, same evaluation partition. Otherwise nothing is written.
- One original root per record; mixed-root lineage is unsupported.

## Limits

The boundary is a local simulation, not authentication. Hashes identify bytes; they do not prove truth or consent, and a writer of the database file can forge rows and hashes. There is no exclusion/revocation ledger, no adoption, no crash- or power-loss acceptance, and no network-filesystem support. `canonical_json` is an internal encoding, not RFC 8785 JCS. The origin `user_correction` is a label asserted by the boundary, not an authenticated user.

## Executed acceptance

```sh
.venv/bin/python tests/run_tests.py          # includes tests/test_evidence_store.py
.venv/bin/python tools/check_docs.py
```

`tests/test_evidence_store.py` uses only temporary synthetic directories; the combined suite passed 110 tests. A restart test closes and reopens connections, not an OS reboot or a process-crash test. The read-only `get` is raw lookup, while `verify` checks stored integrity and expiry; it does not consult the current capture boundary or revocation state and is not an eligibility/permission decision.

The built wheel was installed in `.venv-wheel-gate2a`. With that environment's Python, [check_evidence_installed.py](../tools/check_evidence_installed.py) passed from outside the checkout: packaged schema bytes, capture/replay, derived lineage/root deduplication, restart and read-only verification. It uses a fixed synthetic fixture clock, not current authorization. No real capture or API call was performed.
