"""Allowlisted observations from OpenClaw model.run JSON, not a price estimator.

Missing/default zeros are not measurements. Aggregate and last-call snapshots
stay separate. Unknown metadata is never persisted, including account fields.
"""
from __future__ import annotations

import math

TOKENS = ("input", "output", "cacheRead", "cacheWrite", "cacheWrite1h",
          "cacheWrite5m", "reasoningTokens", "total")
COST_COMPONENTS = ("input", "output", "cacheRead", "cacheWrite")
MAX_SAFE_INTEGER = 2**53 - 1


def _amount(value):
    return (type(value) in (int, float) and 0 <= value <= MAX_SAFE_INTEGER
            and math.isfinite(value))


def usage_observation(raw):
    """Return (sanitized snapshot or None, availability); never infer totals.

    Only normalized CLI names are accepted, not arbitrary provider aliases.
    A malformed recognized field invalidates this snapshot, not the response.
    """
    if raw is None:
        return None, "absent"
    if type(raw) is not dict:
        return None, "invalid"
    report = raw.get("usageReport")
    if report is not None:
        if type(report) is not dict or report.get("state") not in ("available", "unavailable"):
            return None, "invalid"
        if report["state"] == "unavailable":
            return {"usageReport": {"state": "unavailable"}}, "unavailable"
    result = {}
    for key in TOKENS:
        if key in raw:
            value = raw[key]
            if type(value) is not int or not 0 <= value <= MAX_SAFE_INTEGER:
                return None, "invalid"
            result[key] = value
    cost_status = raw.get("costStatus")
    if cost_status is not None:
        if cost_status not in ("complete", "unavailable"):
            return None, "invalid"
        result["costStatus"] = cost_status
    cost = raw.get("cost")
    if cost is not None and cost_status != "unavailable":
        if type(cost) is not dict:
            return None, "invalid"
        amounts = {}
        for key in ("total",) + COST_COMPONENTS:
            if key in cost:
                if not _amount(cost[key]):
                    return None, "invalid"
                amounts[key] = cost[key]
        billed = cost.get("totalOrigin") == "provider-billed"
        # A billed zero, nonzero cost or explicit aggregate complete zero is
        # recorded; a naked adapter-default zero is not.
        if "total" in amounts and (billed or any(amounts.values()) or cost_status == "complete"):
            result["cost"] = amounts
            if billed:
                result["cost"]["totalOrigin"] = "provider-billed"
    if report is not None:
        result["usageReport"] = {"state": "available"}
    observed = (report is not None or "cost" in result or cost_status is not None
                or any(result.get(key, 0) > 0 for key in TOKENS))
    return (result, "observed") if observed else (None, "absent")


def accounting_fields(envelope):
    usage, state = usage_observation(envelope.get("usage"))
    last, last_state = usage_observation(envelope.get("lastCallUsage"))
    cost = usage.get("cost") if usage else None
    return dict(
        usage=usage, last_call_usage=last,
        usage_state=state, last_call_usage_state=last_state,
        cost=(dict(label=("provider_billed" if cost.get("totalOrigin") == "provider-billed"
                          else "recorded_unverified_billing"), value=cost["total"], currency=None)
              if cost else None))
