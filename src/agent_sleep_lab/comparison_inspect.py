"""Read-only saved independent-raw comparison inspection; never run or recover."""
from __future__ import annotations

from contextlib import closing

from agent_sleep_lab.ab_comparison import ComparisonStore, _id
from agent_sleep_lab.comparison_prepare import MAX_INPUT_BYTES, MODELS, _input_volume
from agent_sleep_lab.oss_read_config import _boundaries, _file, _read
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.raw_baseline import RawBaselineComparison
from agent_sleep_lab.runtime_cli import open_store
from agent_sleep_lab.strictjson import loads_strict_bytes

STATES = ("planned_not_dispatched", "dispatch_intent_outcome_unknown", "replied",
          "completed", "timeout", "missing", "invalid")


def execute(*, store_config_path, journal_path, plan_id):
    """Inspect one existing plan from a journal read snapshot, without a rubric.

    Current eligibility is observed separately in the evidence store. Neither
    this observation nor a complete journal authorizes dispatch or adoption.
    SQLite's normal read locks/WAL sidecars may still be needed.
    """
    if not _id(plan_id):
        raise ValueError("bounded comparison plan ID required")
    config = loads_strict_bytes(_read(_file(store_config_path), MAX_INPUT_BYTES))
    _boundaries(config)
    source, journal = _file(config["path"]), _file(journal_path)
    if source == journal or source.samefile(journal):
        raise ValueError("distinct evidence and comparison databases required")
    with closing(open_store(config, read_only=True)) as store:
        with closing(ComparisonStore(journal, read_only=True)) as comparisons:
            comparisons.db.execute("BEGIN")  # Consistent journal view; no writes.
            plan, digest, status, _, role = comparisons._plan(plan_id)
            if (plan.get("version") != 1 or plan.get("synthetic_only") is not True
                    or plan.get("plan_id") != plan_id or plan.get("model") not in MODELS
                    or status not in ("planned", "running", "complete", "incomplete", "invalidated")
                    or role not in ("development", "final")):
                raise ValueError("unsupported saved comparison")
            row = comparisons.db.execute(
                "SELECT context, context_sha256 FROM frozen_contexts WHERE plan_id=?",
                (plan_id,)).fetchone()
            if row is None or sha256_hex(bytes(row[0])) != row[1]:
                raise ValueError("missing or corrupt frozen context")
            context = loads_strict_bytes(bytes(row[0]))
            rules = context["rules"]
            baseline = RawBaselineComparison(
                store, comparisons, scope=context["scope"], **rules["memory_retrieval"],
                scan_limit=rules["scan_limit"], max_raw=rules["max_raw"], raw_order=rules["order"])
            if baseline.scope != context["scope"] or baseline.rules != rules:
                raise ValueError("frozen retrieval binding mismatch")
            audit = baseline.audit(plan_id)  # Existing request/hash/membership checks.
            volume = _input_volume(plan_id, plan["tasks"], audit["arms"])
            scores = {}
            for index, arm, state, score in comparisons.db.execute(
                    "SELECT task_index, arm, status, score FROM comparison_arms WHERE plan_id=?",
                    (plan_id,)):
                if ((state == "completed" and (type(score) is not int or score not in (0, 1)))
                        or (state != "completed" and score is not None)):
                    raise ValueError("invalid saved evaluator score")
                scores[index, arm] = score
            outcomes = {a: dict(denominator=volume["task_pairs"], evaluator_pass=0,
                                **{state: 0 for state in STATES}) for a in "AB"}
            arms = []
            for entry in audit["arms"]:
                arm, state = entry["arm"], entry["status"]
                score = scores.get((entry["task_index"], arm))
                outcomes[arm][state] += 1
                outcomes[arm]["evaluator_pass"] += int(score == 1)
                # No prompt, query, source, reply, free-text reason or receipt metadata.
                arms.append({key: entry[key] for key in (
                    "task_index", "arm", "position", "request_sha256", "request_bytes",
                    "status", "outcome_known")} | {"score": score})
            current = baseline.current(plan_id)
            valid = current == comparisons._bound(plan)
            return dict(
                operation="compare-inspect", offline=True, read_only=True,
                dispatch_authorization=False, adoption_receipt=None,
                plan_id=plan_id, plan_sha256=digest, context_sha256=audit["context_sha256"],
                taskset_sha256=plan["taskset_sha256"], model=plan["model"],
                status=status, contact_role=role, representation=audit["representation"],
                synthetic_only=True, scores_are_synthetic=True, independent_holdout=False,
                planned_denominator=dict(task_pairs=volume["task_pairs"],
                                         per_arm=volume["task_pairs"], total_arms=volume["total_arms"]),
                arms=arms, outcomes=outcomes, input_volume=volume,
                all_outcomes_scored=all(outcomes[a]["completed"] == volume["task_pairs"] for a in "AB"),
                current_validity={"valid": valid},
                cost={"label": "unavailable", "value": None}, usage=None,
                comparison=None, performance_claim=None, acceptance_complete=False)
