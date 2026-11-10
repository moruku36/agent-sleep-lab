"""Materialize model-generated prose as UNVERIFIED candidates, never receipts."""
from agent_sleep_lab.sleep_coordinator import _encode
from agent_sleep_lab.strictjson import loads_strict_bytes


def candidate_memories(binding, deep, *, observed_at):
    if binding["version"] != 2:
        raise ValueError("body-bound version 2 proposal required")
    events = {e["event_id"]: loads_strict_bytes(e["event"].encode("utf-8"))
              for e in binding["events"]}
    memories = {}
    for op in deep["operations"]:
        memory = {"schema_version": "0.1", "memory_id": op["memory_id"],
                  "scope": binding["scope"], "kind": "procedure", "claim": op["claim"],
                  "status": "candidate", "observed_at": observed_at, "valid_until": None,
                  "supersedes": [], "tags": [],
                  "evidence": [{"event_id": eid, "source_uri": events[eid]["source_uri"],
                                "locator": "source"} for eid in op["event_ids"]],
                  "verification": {"method": "pending independent check",
                                   "verifier": None, "result": "pending"}}
        # Materialization has no registration/adoption authority.
        from agent_sleep_lab.validation import validate_bytes
        blob = _encode(memory)
        if not validate_bytes("memory", blob).valid:
            raise ValueError("generated candidate violates memory contract")
        memories[op["memory_id"]] = blob
    return memories
