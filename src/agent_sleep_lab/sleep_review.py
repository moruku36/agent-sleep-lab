"""Bounded private review and exact same-run artifact handoff; no receipt issuer."""
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.sleep_candidates import candidate_memories
from agent_sleep_lab.sleep_coordinator import Limits, _encode, _id, preparation_operation_id
from agent_sleep_lab.sleep_evidence import observe
from agent_sleep_lab.strictjson import loads_strict_bytes

MAX_BYTES = 1048576
ARTIFACT_KEYS = {"request_bytes", "manifest_bytes", "source_manifest_bytes", "memory_bytes"}


def load_run(coordinator, run_id, *, statuses=("ready",)):
    """Read bounded persisted bytes without creating or recovering a run."""
    if not _id(run_id):
        raise ValueError("bounded existing run ID required")
    row = coordinator.db.execute(
        "SELECT binding, state FROM sleep_runs WHERE run_id=? "
        "AND typeof(binding)='blob' AND length(binding) BETWEEN 1 AND ? "
        "AND typeof(state)='blob' AND length(state) BETWEEN 1 AND ?",
        (run_id, MAX_BYTES, 2 * MAX_BYTES)).fetchone()
    if row is None:
        raise ValueError("existing bounded run required")
    raw_binding, raw_state = row
    binding, state = loads_strict_bytes(raw_binding), loads_strict_bytes(raw_state)
    if (_encode(binding) != raw_binding or _encode(state) != raw_state
            or type(binding) is not dict or type(state) is not dict
            or state.get("status") not in statuses
            or binding.get("version") != 2 or binding.get("synthetic_only") is not True):
        raise ValueError("current-store-bound version 2 completed proposals required")
    limits = Limits(**binding["limits"])
    events, scope, bound = binding["events"], binding["scope"], binding["store_binding"]
    if (len(raw_binding) > limits.input_bytes or type(events) is not list
            or not 1 <= len(events) <= 64
            or type(scope) is not dict or set(scope) != {"project", "task_family"}
            or not all(type(v) is str and v for v in scope.values())
            or type(bound) is not dict
            or set(bound) != {"policy_sha256", "snapshot_sha256", "evidence_sha256"}
            or bound["snapshot_sha256"] != binding["parent_sha256"]
            or bound["evidence_sha256"] != sha256_hex(_encode(events))
            or state.get("calls") != 2 or limits.calls != 2
            or state.get("reason") is not None):
        raise ValueError("invalid persisted binding or incomplete stages")
    ids = [e["event_id"] for e in events]
    if any(not _id(eid) for eid in ids) or len(set(ids)) != len(ids):
        raise ValueError("invalid persisted evidence IDs")
    for stage in ("light", "deep"):
        raw = _encode(state[stage])
        if len(raw) > limits.stage_output_bytes:
            raise ValueError("persisted proposal exceeds stage cap")
        coordinator._proposal(stage, raw, binding)
    selected = state["light"]["event_ids"]
    operations = state["deep"]["operations"]
    if (not selected or not operations
            or any(not set(op["event_ids"]) <= set(selected) for op in operations)):
        raise ValueError("nonempty selected generated candidates required")
    # Materialization validates scope, timestamp, source references and pending prose.
    candidate_memories(binding, state["deep"], observed_at=binding["config"]["observed_at"])
    operation_id = preparation_operation_id(run_id, raw_binding, state["deep"])
    if state["status"] != "ready" and state.get("operation_id") != operation_id:
        raise ValueError("persisted operation identity mismatch")
    return raw_binding, binding, state, operation_id


def check_current(store, binding):
    events, current = observe(store, scope=binding["scope"],
                              event_ids=[e["event_id"] for e in binding["events"]])
    if current != binding["store_binding"] or events != binding["events"]:
        raise ValueError("evidence, policy or head changed")


def review_packet(coordinator, run_id, store):
    raw_binding, binding, state, operation_id = load_run(coordinator, run_id)
    memories = candidate_memories(binding, state["deep"],
                                  observed_at=binding["config"]["observed_at"])
    packet = dict(protocol="agent-sleep-review/1", private_output=True,
                  publication_authorized=False, independent_verification_required=True,
                  independent_evaluation_required=True, synthetic_only=True,
                  run_id=run_id, operation_id=operation_id,
                  binding_sha256=sha256_hex(raw_binding), binding=binding,
                  proposal_sha256=sha256_hex(_encode(state["deep"])), proposal=state["deep"],
                  candidate_memories={mid: loads_strict_bytes(blob) for mid, blob in memories.items()},
                  candidate_sha256={mid: sha256_hex(blob) for mid, blob in memories.items()})
    if len(_encode(packet)) + 1 > MAX_BYTES:
        raise ValueError("private review packet exceeds 1 MiB")
    if coordinator.db.execute(
            "SELECT 1 FROM sleep_runs WHERE run_id=? AND binding=? AND state=?",
            (run_id, raw_binding, _encode(state))).fetchone() is None:
        raise ValueError("run changed during review")
    check_current(store, binding)  # last check before exposing private evidence/prose
    return packet


def decode_artifact(document):
    if type(document) is not dict or set(document) != ARTIFACT_KEYS:
        raise ValueError("exact independently prepared artifact fields required")
    if (type(document["memory_bytes"]) is not dict
            or not 1 <= len(document["memory_bytes"]) <= 64):
        raise ValueError("bounded nonempty prepared memory map required")
    payload = {key: bytes.fromhex(document[key]) for key in ARTIFACT_KEYS - {"memory_bytes"}}
    payload["memory_bytes"] = {mid: bytes.fromhex(blob)
                               for mid, blob in document["memory_bytes"].items()}
    return payload


def adopt_prepared(coordinator, run_id, store, payload):
    _, binding, state, operation_id = load_run(
        coordinator, run_id, statuses=("ready", "handoff", "adopted"))
    if state["status"] == "ready":
        check_current(store, binding)
        # Inert local return only: no callback import, verification or registration.
        state = coordinator.prepare(run_id, lambda *_: payload)
    # prepare can observe a concurrent transition and return an existing handoff.
    # Compare in BOTH branches before adopting any persisted artifact.
    if decode_artifact(state["handoff"]) != payload:
        raise ValueError("artifact differs from persisted exact handoff")
    prior = store.resolve_operation(operation_id)
    if prior is None:
        if state["status"] == "adopted":
            raise ValueError("adopted operation missing from store")
        check_current(store, binding)
    # A committed same operation may have moved the head or since been revoked.
    # Only the writer's exact replay is allowed; it does not reapply old permission.
    if state["status"] == "adopted":
        replay = store.commit_adoption(**payload)
        if replay.receipt_sha256 != state["receipt_sha256"]:
            raise ValueError("persisted adoption receipt mismatch")
    state = coordinator.adopt(run_id, store)
    return dict(status=state["status"], run_id=run_id, operation_id=operation_id,
                receipt_sha256=state["receipt_sha256"])
