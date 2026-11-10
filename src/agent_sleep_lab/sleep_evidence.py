"""Body-bound synthetic evidence, rechecked from the existing adoption store."""
from agent_sleep_lab.sleep_coordinator import _encode
from agent_sleep_lab.strictjson import loads_strict_bytes
from agent_sleep_lab.raw_baseline import select_raw_evidence
from agent_sleep_lab.provenance import sha256_hex


def observe(store, *, scope, event_ids):
    # Reuse bounded independent raw selection, policy/lineage/hash checks in ONE read transaction.
    policy, head, _, selected, _ = select_raw_evidence(
        store, scope=scope, partition="experience", scan_limit=256, max_raw=256)
    by_id = {refs["event_id"]: loads_strict_bytes(text.encode("ascii")) for refs, text in selected}
    if len(set(event_ids)) != len(event_ids) or not set(event_ids) <= set(by_id):
        raise ValueError("requested evidence missing or not currently eligible")
    events = []
    for event_id in event_ids:
        raw = by_id[event_id]
        events.append({key: raw[key] for key in ("event_id", "event_sha256", "event", "source",
                                                "source_sha256", "provenance_sha256")})
    return events, {"policy_sha256": policy.sha256, "snapshot_sha256": head,
                    "evidence_sha256": sha256_hex(_encode(events))}


def bind_from_store(coordinator, store, *, run_id, scope, event_ids, config, **kwargs):
    events, state = observe(store, scope=scope, event_ids=event_ids)
    return coordinator.bind(run_id=run_id, scope=scope, events=events, config=config,
                            parent_sha256=state["snapshot_sha256"], store_binding=state, **kwargs)


def current_store(store, *, scope, event_ids):
    def current():
        try:
            return observe(store, scope=scope, event_ids=event_ids)[1]
        except Exception:
            return None
    return current
