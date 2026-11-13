"""Pure presentation of the existing synthetic demo result; no execution or I/O."""


def format_demo_text(result):
    capture = result["capture"]
    report = result["comparison"]["report"]
    candidates = result["candidates"]
    checks = result["fixture_registration"]["checks"]
    calls = result["calls"]
    lines = [
        "Offline synthetic demo: " + result["status"],
        "Built-in fixtures and scripted providers; no live-model calls.",
        f"Capture: {capture['count']} events; created="
        f"{sum(r['status'] == 'created' for r in capture['results'])}",
        f"Light: {result['sleep']['light']['status']}; Deep: {result['sleep']['deep']['status']}",
        f"Candidates: {len(candidates)}; pending verification="
        f"{sum(c['verification']['result'] == 'pending' for c in candidates)} "
        "(before separate local fixture receipts)",
        f"Local synthetic fixture checks: {sum(checks.values())}/{len(checks)} passed",
        "Atomic adoption: " + result["adoption"]["status"],
        f"Retrieval: {len(result['retrieval']['bundle']['records'])} adopted records",
        "Comparison: " + report["status"] + "; A=raw, B=same raw + memory",
    ]
    for arm in "AB":
        outcome = report["outcomes"][arm]
        scores = (report.get("comparison") or {}).get("arms", {}).get(arm)
        score = (f"{scores['evaluator_pass']}/{scores['denominator']}" if scores
                 else "unavailable")
        counts = ", ".join(f"{key}={outcome[key]}" for key in
                           ("timeout", "missing", "invalid", "unknown", "replied", "not_started"))
        lines.append(f"  {arm}: completed={outcome['completed']}/{outcome['denominator']}; "
                     f"{counts}; scripted exact-match pass={score}")
        cost = report["cost"][arm]
        phases = ", ".join(f"{name}={value['label']}"
                           for name, value in sorted(cost["phases"].items()))
        lines.append(f"  {arm} cost: total={cost['total']['label']}; {phases}")
    lines.extend([
        f"Calls: scripted Light/Deep={calls['scripted_sleep']}; "
        f"scripted task={calls['scripted_task']}; paired evaluator={calls['paired_evaluator']}",
        "Costs: synthetic_zero is fixture zero; unavailable is unknown, not zero. "
        "Neither is measured savings.",
        "Scores check scripted wiring, not performance improvement or an independent holdout.",
        "Local fixture verification/evaluation is not scientific review.",
        "No live-provider or existing-agent integration verification.",
        "Temporary state removed: " + str(result["temporary_state_removed"]).lower(),
        "Use --format json for full bindings, receipts and per-arm evidence.",
    ])
    return "\n".join(lines)
