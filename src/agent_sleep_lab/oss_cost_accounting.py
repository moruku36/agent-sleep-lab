"""Offline accounting against current, integrity-checked OSS report snapshots."""
from __future__ import annotations

import re

from agent_sleep_lab import oss_fixture_cohort as cohort
from agent_sleep_lab.oss_execution_journal import ARMS
from agent_sleep_lab.oss_offline_worker import digest, encoded
from agent_sleep_lab.strictjson import loads_strict_bytes

ARTIFACT_PROTOCOL = "agent-sleep-oss-cost-observations/1"
REPORT_PROTOCOL = "agent-sleep-oss-cost-accounting/1"
TRUST = "caller_supplied_unverified"
STAGES = ("capture", "consolidation", "verification", "retrieval", "task_execution",
          "maintenance", "evaluation")
METRICS = ("cost", "input_tokens", "output_tokens")
MAX_OBSERVATIONS = cohort.MAX_TASKS * len(ARMS) * len(STAGES)
MAX_ARTIFACT_BYTES = 32_768
TARGET_KEYS = {"kind", "id", "frozen_sha256", "report_sha256"}
OBSERVATION_KEYS = {"plan_id", "arm", "stage", "evidence_sha256", *METRICS}
ARTIFACT_KEYS = {"protocol", "observation_trust", "target", "currency", "observations"}
DECIMAL_PLACES = 12
SCALE = 10 ** DECIMAL_PLACES


class AccountingError(ValueError):
    """A malformed observation or a mismatch with the current source report."""


def _matches(value, pattern):
    return type(value) is str and re.fullmatch(pattern, value) is not None


def _is_id(value):
    return _matches(value, r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


def _is_sha256(value):
    return _matches(value, r"[0-9a-f]{64}")


def _slot(row):
    return row["plan_id"], row["arm"], row["stage"]


def freeze_observations(target, *, currency, observations):
    """Encode explicit caller observations for an exact previously read target."""
    if (type(target) is not dict or set(target) != TARGET_KEYS
            or type(target["kind"]) is not str or target["kind"] not in ("pair", "cohort")
            or not _is_id(target["id"])
            or not all(_is_sha256(target[key]) for key in ("frozen_sha256", "report_sha256"))):
        raise AccountingError("exact accounting target required")
    if currency is not None and not _matches(currency, r"[A-Z]{3}"):
        raise AccountingError("one uppercase three-letter currency code required for money")
    if type(observations) is not list or len(observations) > MAX_OBSERVATIONS:
        raise AccountingError("bounded observation list required")
    rows = {}
    for row in observations:
        if (type(row) is not dict or set(row) != OBSERVATION_KEYS
                or not _is_id(row["plan_id"]) or not _is_sha256(row["evidence_sha256"])
                or type(row["arm"]) is not str or row["arm"] not in ARMS
                or type(row["stage"]) is not str or row["stage"] not in STAGES):
            raise AccountingError("exact task, arm, stage and evidence hash required")
        cost = row["cost"]
        if cost is not None and (currency is None or not _matches(
                cost, r"(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,12})?")):
            raise AccountingError("money requires a bounded nonnegative decimal string and currency")
        for key in ("input_tokens", "output_tokens"):
            count = row[key]
            if count is not None and (type(count) is not int or not 0 <= count < 2**63):
                raise AccountingError("token counts must be nonnegative bounded integers or null")
        if all(row[key] is None for key in METRICS):
            raise AccountingError("an observation must supply at least one metric")
        slot = _slot(row)
        if slot in rows:
            raise AccountingError("duplicate task, arm and stage observation")
        rows[slot] = row
    raw = encoded(dict(protocol=ARTIFACT_PROTOCOL, observation_trust=TRUST, target=target,
                       currency=currency, observations=[rows[slot] for slot in sorted(rows)]))
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise AccountingError("accounting artifact byte bound exceeded")
    return raw


def _load(raw, target, eligible_plans):
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_ARTIFACT_BYTES:
        raise AccountingError("bounded canonical artifact bytes required")
    try:
        doc = loads_strict_bytes(raw)
    except ValueError:
        raise AccountingError("invalid accounting JSON") from None
    if (type(doc) is not dict or set(doc) != ARTIFACT_KEYS or doc["protocol"] != ARTIFACT_PROTOCOL
            or doc["observation_trust"] != TRUST):
        raise AccountingError("unsupported accounting artifact contract")
    if raw != freeze_observations(doc["target"], currency=doc["currency"],
                                 observations=doc["observations"]):
        raise AccountingError("noncanonical accounting artifact")
    if doc["target"] != target:
        raise AccountingError("accounting target differs from current frozen identity or report")
    if any(row["plan_id"] not in eligible_plans for row in doc["observations"]):
        raise AccountingError("observation requires a member with a current execution report")
    return doc["currency"], {_slot(row): row for row in doc["observations"]}


def _units(amount):
    whole, _, fraction = amount.partition(".")
    return int(whole) * SCALE + int(fraction.ljust(DECIMAL_PLACES, "0"))


def _amount(units):
    whole, fraction = divmod(abs(units), SCALE)
    return ("-" if units < 0 else "") + f"{whole}.{fraction:012d}".rstrip("0").rstrip(".")


def _totals(stages):
    result = dict(stage_slots=len(stages))
    for key in METRICS:
        observed = [stage[key] for stage in stages if stage[key] is not None]
        result["observed_" + key + "_slots"] = len(observed)
        result[key] = None
        if len(observed) == len(stages):
            result[key] = (_amount(sum(_units(value) for value in observed)) if key == "cost"
                           else sum(observed))
    return result


def _task(identity, status, execution_report):
    if execution_report is None:
        return dict(identity, status=status, context_current=None, plan_status=None, transport=None,
                    execution_report_sha256=None,
                    arms={arm: dict(execution_status="unavailable", verdict_status="unresolved")
                          for arm in ARMS})
    verdicts = execution_report["verdict_evaluation"]["arms"]
    return dict(identity, status=status, context_current=execution_report["context_current"],
                plan_status=execution_report["plan_status"],
                transport=execution_report["adapter"]["transport"],
                execution_report_sha256=digest(encoded(execution_report)),
                arms={arm: dict(execution_status=execution_report["arms"][arm]["status"],
                                verdict_status=verdicts.get(arm, {}).get("status", "unresolved"))
                      for arm in ARMS})


def _report(target, tasks, source_status, artifact):
    eligible_plans = {task["plan_id"] for task in tasks if task["context_current"] is True}
    currency, observations = (None, {}) if artifact is None else _load(
        artifact, target, eligible_plans)
    by_arm = {arm: [] for arm in ARMS}
    for task in tasks:
        for arm, item in task["arms"].items():
            stages = {}
            for stage in STAGES:
                row = observations.get((task["plan_id"], arm, stage), {})
                stages[stage] = {key: row.get(key) for key in (*METRICS, "evidence_sha256")}
            item.update(stages=stages, totals=_totals(list(stages.values())))
            by_arm[arm].extend(stages.values())
    arms = {arm: _totals(stages) for arm, stages in by_arm.items()}
    baseline, reference = (arms[arm]["cost"] for arm in ARMS)
    difference = None
    if source_status == "complete" and baseline is not None and reference is not None:
        difference = _amount(_units(reference) - _units(baseline))
    return dict(protocol=REPORT_PROTOCOL, target=target, source_status=source_status,
                observation_trust=TRUST, artifact_sha256=None if artifact is None else digest(artifact),
                provider_usage="unavailable", provider_cost="unavailable", currency=currency,
                registered_tasks=len(tasks), tasks=tasks, arms=arms,
                totals=_totals(by_arm["baseline"] + by_arm["reference"]),
                reference_minus_baseline_cost=difference)


def pair_report(journal, plan_id, bridge, *, artifact=None):
    """Read an existing ExecutionJournal pair and optionally apply exact observations."""
    if not _is_id(plan_id):
        raise AccountingError("bounded plan ID required")
    with cohort._journal_view(journal):
        source = journal.report(plan_id, bridge)
    verdict = source["verdict_evaluation"]
    identity = dict(plan_id=plan_id, binding_sha256=source["binding_sha256"],
                    manifest_sha256=verdict["manifest_sha256"],
                    task_sha256=source["source"]["task_sha256"],
                    issue_number=source["source"]["issue_number"])
    task = _task(identity, verdict["status"], source)
    target = dict(kind="pair", id=plan_id, frozen_sha256=source["binding_sha256"],
                  report_sha256=task["execution_report_sha256"])
    return _report(target, [task], source["plan_status"], artifact)


def cohort_report(registry, cohort_id, *, journal, bridges, artifact=None):
    """Read a frozen cohort and pin every available exact member report in one view."""
    if type(registry) is not cohort.CohortRegistry:
        raise AccountingError("exact CohortRegistry required")
    execution_reports = {}
    source = registry._report(cohort_id, journal=journal, bridges=bridges,
                              execution_reports=execution_reports)
    tasks = [_task({key: member[key] for key in cohort.MEMBER_KEYS}, member["status"],
                   execution_reports.get(member["plan_id"])) for member in source["tasks"]]
    members = {task["plan_id"]: task["execution_report_sha256"] for task in tasks}
    target = dict(kind="cohort", id=cohort_id, frozen_sha256=source["cohort_sha256"],
                  report_sha256=digest(encoded(dict(cohort_report=source, execution_reports=members))))
    return _report(target, tasks, source["status"], artifact)
