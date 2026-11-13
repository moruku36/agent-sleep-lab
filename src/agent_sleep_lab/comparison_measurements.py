"""Content-free projection of saved transport receipts, never runtime recovery.

Local hashes bind observations to frozen requests, not to an authenticated
origin. Missing, invalid and mismatched receipts remain in every denominator.
No text, usage, cost or arbitrary receipt field is returned.
"""
from __future__ import annotations

from agent_sleep_lab.provider_usage import MAX_SAFE_INTEGER
from agent_sleep_lab.strictjson import loads_strict_bytes

MAX_RECEIPT_BYTES = 65_536
TIMING_BASIS = "monotonic_cli_process_including_startup_not_provider_latency"
SOURCES = ("registered_openclaw_cli", "injected_transport_not_live_verified")
METRICS = ("request_bytes", "cli_prompt_bytes", "output_bytes", "transport_elapsed_ns")
RECEIPT_STATES = ("missing", "invalid", "binding_mismatch", "recorded")


def _number(value):
    return type(value) is int and 0 <= value <= MAX_SAFE_INTEGER


def _slot(entry, model, raw):
    result = dict(task_index=entry["task_index"], arm=entry["arm"],
                  receipt_state="missing", transport_source=None, receipt_status=None,
                  metrics={name: dict(state="absent", value=None) for name in METRICS})
    if raw is None:
        return result
    result["receipt_state"] = "invalid"
    if type(raw) is not bytes or len(raw) > MAX_RECEIPT_BYTES:
        return result
    try:
        receipt = loads_strict_bytes(raw)
    except (ValueError, UnicodeError, RecursionError):
        return result
    if type(receipt) is not dict:
        return result
    if (receipt.get("model_requested") != model
            or receipt.get("request_sha256") != entry["request_sha256"]
            or entry["status"] == "planned_not_dispatched"):
        result["receipt_state"] = "binding_mismatch"
        return result
    if (receipt.get("transport_source") not in SOURCES
            or receipt.get("status") not in ("returned", "outcome_unknown")):
        return result
    result.update(receipt_state="recorded", transport_source=receipt["transport_source"],
                  receipt_status=receipt["status"])
    for name in METRICS:
        value = receipt.get(name)
        if value is None:
            continue
        valid = _number(value)
        if name == "request_bytes":
            valid = valid and value == entry["request_bytes"]
        elif name == "cli_prompt_bytes":
            valid = valid and value >= entry["request_bytes"]
        elif name == "transport_elapsed_ns":
            valid = valid and receipt.get("timing_basis") == TIMING_BASIS
        result["metrics"][name] = dict(state="observed" if valid else "invalid",
                                        value=value if valid else None)
    return result


def project(db, plan_id, model, arms):
    """Read bounded receipt blobs inside the inspector's existing read snapshot."""
    identities = {(e["task_index"], e["arm"]) for e in arms}
    # Older valid journals can predate receipt retention. Do not migrate them.
    has_table = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='comparison_provider_receipts'").fetchone()
    rows = (db.execute(
        "SELECT task_index, arm, substr(receipt,1,?) "
        "FROM comparison_provider_receipts WHERE plan_id=? LIMIT ?",
        (MAX_RECEIPT_BYTES + 1, plan_id, len(arms) + 1)).fetchall() if has_table else [])
    receipts = {}
    for index, arm, raw in rows:
        if (index, arm) not in identities or (index, arm) in receipts:
            raise ValueError("unexpected saved measurement identity")
        receipts[index, arm] = raw
    slots = [_slot(e, model, receipts.get((e["task_index"], e["arm"]))) for e in arms]
    summaries = {}
    for arm in "AB":
        selected = [slot for slot in slots if slot["arm"] == arm]
        metrics = {}
        for name in METRICS:
            observed = [s["metrics"][name]["value"] for s in selected
                        if s["metrics"][name]["state"] == "observed"]
            metrics[name] = dict(
                observed_slots=len(observed),
                absent_slots=sum(s["metrics"][name]["state"] == "absent" for s in selected),
                invalid_slots=sum(s["metrics"][name]["state"] == "invalid" for s in selected),
                observed_sum=sum(observed) if observed else None,
                all_slots_observed=len(observed) == len(selected))
        summaries[arm] = dict(
            denominator=len(selected),
            receipts={state: sum(s["receipt_state"] == state for s in selected)
                      for state in RECEIPT_STATES},
            transport_sources={source: sum(s["transport_source"] == source for s in selected)
                               for source in SOURCES}, metrics=metrics)
    return dict(basis="saved_transport_receipt_observations", timing_basis=TIMING_BASIS,
                origin_authenticated=False, live_verified=False,
                tokens_or_billed_cost=False, provider_latency=False,
                slots=slots, per_arm=summaries)
