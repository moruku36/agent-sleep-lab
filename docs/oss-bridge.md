# OSS Contributor collect-only bridge

**English** | [日本語](oss-bridge.ja.md) | [Integration design](integration.ja.md)

## Boundary

`CollectOnlyBridge` accepts the dictionary returned by
`dataclasses.asdict(TriageDecision)` from
`moruku36/oss-contributor-agent/src/collector/digest.py`. The caller pins the
actual agent commit, target repository and Sleep Lab project/task-family.
The commit is caller-asserted provenance, not remotely authenticated identity.

This is opt-in **synthetic offline wiring**, not a deployed connection.
The existing store remains synthetic-only: do not pass production decisions with
`synthetic=True`. Non-synthetic storage, retention and authorization require a
separate contract before real operational logs can be ingested.
No timer, remote host, target configuration or production ledger is changed.

## Capture

```python
from dataclasses import asdict
from agent_sleep_lab.oss_bridge import CollectOnlyBridge

bridge = CollectOnlyBridge(
    store, scope={"project": "oss-pilot", "task_family": "triage"},
    repository="fixture/project", agent_commit=verified_agent_commit,
)
captured = bridge.capture_decision(
    asdict(synthetic_decision), event_id="triage-1", session_id="offline-pass-1",
    observed_at="2026-11-10T00:00:00Z", captured_at="2026-11-10T00:01:00Z",
    authorization=caller_authorization, synthetic=True,
)
```

`store` is an explicitly configured existing `AdoptionStore`;
`caller_authorization` follows the existing capture contract. No implicit store
initialization or authorization expansion occurs. All six current outcome labels,
including pending and infrastructure failure, are observations, not success.

The stored source preserves the bounded decision, including any model rationale,
as untrusted data. A `tool_observation` root establishes only that this decision
was observed; it does not establish that issue facts or generated reasoning are
correct. The adapter creates no verification/evaluation receipt, memory,
adoption, patch or PR. Repeating exact capture bytes replays; changing content
under the same event ID conflicts through the existing writer.

## Reference context

```python
bundle = bridge.reference_context(query="duplicate checks", max_bytes=16384)
# Pass bundle.bundle_bytes only to the caller's explicit reference-data slot.
# Do not replace current instructions, target policy or execution permissions.
```

The read-only retriever rechecks current policy, evidence, registered receipts
and exclusions; only the configured scope's adopted memories are eligible.
An empty bundle is normal. Budget units are UTF-8 bytes, not tokens.
No target scorer, threshold, pending state, ledger or collect-only gate changes.
The bridge does not execute the consumer: returning reference bytes is not proof
that an agent received or used them. Delivery/use verification remains required.

Use the optional [reference dispatch journal](reference-use.md) to freeze the
exact bundle and record one explicit local consumer call. Its receipt remains
unreviewed and is not verified delivery/use.

## Offline verification and next boundary

Contract regressions cover exact capture/replay without adoption, untrusted
rationale, real-data rejection, foreign repository rejection, malformed decisions,
authorization mismatch, adopted-context retrieval, scope isolation, present
exclusions and missing policy. These checks use synthetic fixtures, not a live
model or production run. See [current status](implementation-status.md).

Before claiming one connected existing agent, independently verify an actual
target invocation consuming a fixed eligible memory bundle and producing an
auditable outcome, with compatible non-synthetic capture/use authorization.
No automatic production enablement follows from these offline tests.
