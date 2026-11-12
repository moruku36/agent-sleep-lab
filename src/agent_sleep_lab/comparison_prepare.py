"""Offline predispatch inspection of the existing independent-raw comparison.

The ordinary compare manifest and ComparisonStore are reused unchanged. Only
the separate comparison journal/contact is written. No evaluator key, provider
construction, execution, report-driven status update or adoption write occurs.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import asdict
from pathlib import Path

from agent_sleep_lab.ab_comparison import (
    ArmBudget, ComparisonStore, _encode, _evaluator_identity, _id,
)
from agent_sleep_lab.oss_read_config import MAX_PATH_CHARS, _boundaries, _file, _read
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.raw_baseline import ORDER, RANKED_ORDER, RawBaselineComparison
from agent_sleep_lab.retrieval import MAX_QUERY_CHARS, MAX_RECORDS_LIMIT, SERVED_PARTITIONS, _check_scope
from agent_sleep_lab.runtime_cli import open_store
from agent_sleep_lab.strictjson import loads_strict_bytes

MAX_INPUT_BYTES = 1_048_576  # Same file bound as runtime compare.
MODELS = ("xiaomi/mimo-v2.6-pro", "fake-model-1")


def _manifest(doc):
    required = {"plan_id", "tasks", "retrieval", "evaluator_identity"}
    if (type(doc) is not dict or not required <= set(doc)
            or set(doc) - required - {"budget", "config"}):
        raise ValueError("invalid comparison manifest fields")
    tasks = doc["tasks"]
    if (not _id(doc["plan_id"]) or type(tasks) is not list or not 1 <= len(tasks) <= 5
            or any(type(t) is not dict or set(t) != {"task_id", "prompt"}
                   or not _id(t["task_id"]) or type(t["prompt"]) is not str
                   or not t["prompt"] for t in tasks)
            or len({t["task_id"] for t in tasks}) != len(tasks)):
        raise ValueError("bounded unique paired tasks required")
    _evaluator_identity(doc["evaluator_identity"])  # Identity only; no evaluator/key.
    budget = doc.get("budget", {})
    if type(budget) is not dict or set(budget) - {"calls", "request_bytes", "reply_bytes"}:
        raise ValueError("invalid budget fields")
    budget = ArmBudget(**budget)
    if len(tasks) > budget.calls or type(doc.get("config", {})) is not dict:
        raise ValueError("invalid call budget or caller configuration")
    retrieval = doc["retrieval"]
    if (type(retrieval) is not dict or not {"scope", "max_bytes"} <= set(retrieval)
            or set(retrieval) - {"scope", "max_bytes", "partition", "query", "max_records",
                                 "scan_limit", "max_raw", "raw_order"}):
        raise ValueError("invalid retrieval fields")
    _check_scope(retrieval["scope"])
    for name, default, ceiling in (("max_bytes", None, MAX_INPUT_BYTES),
                                    ("max_records", 16, MAX_RECORDS_LIMIT),
                                    ("scan_limit", 256, 1024), ("max_raw", 16, 64)):
        value = retrieval.get(name, default)
        if type(value) is not int or not 1 <= value <= ceiling:
            raise ValueError("invalid retrieval cap")
    query = retrieval.get("query")
    if (query is not None and (type(query) is not str or len(query) > MAX_QUERY_CHARS)
            or retrieval.get("partition", "experience") not in SERVED_PARTITIONS
            or retrieval.get("raw_order", ORDER) not in (ORDER, RANKED_ORDER)):
        raise ValueError("invalid retrieval selection")
    return budget


def _journal(value, source):
    if (type(value) is not str or not 1 <= len(value) <= MAX_PATH_CHARS
            or "\x00" in value or value.startswith("file:") or value == ":memory:"):
        raise ValueError("explicit separate local journal required")
    path = Path(value).resolve()
    if (not path.parent.is_dir() or (path.exists() and not path.is_file())
            or path == source or (path.exists() and path.samefile(source))):
        raise ValueError("journal must be separate from evidence/adoption store")
    return path


def execute(manifest_path, *, store_config_path, journal_path, model):
    """Freeze/reopen, audit and recheck; return bounded metadata, never requests.

    Configuration is caller-controlled, not authentication. current() uses a new
    read after the freeze/audit; this is an observation, not a future dispatch
    permit or an atomic transaction across the two databases.
    """
    if type(model) is not str or model not in MODELS:
        raise ValueError("explicit finite model choice required")
    doc = loads_strict_bytes(_read(_file(manifest_path), MAX_INPUT_BYTES))
    budget = _manifest(doc)
    config = loads_strict_bytes(_read(_file(store_config_path), MAX_INPUT_BYTES))
    _boundaries(config)  # Existing strict store-config gates; no new authority.
    source = _file(config["path"])
    journal = _journal(journal_path, source)
    with closing(open_store(config, read_only=True)) as store:
        with closing(ComparisonStore(journal)) as comparisons:
            baseline = RawBaselineComparison(store, comparisons, **doc["retrieval"])
            plan_id = doc["plan_id"]
            baseline.plan(plan_id=plan_id, tasks=doc["tasks"], config=doc.get("config", {}),
                          model=model, evaluator_identity=doc["evaluator_identity"], budget=budget)
            audit = baseline.audit(plan_id)
            plan, digest, status, _, role = comparisons._plan(plan_id)
            if (status not in ("planned", "running", "complete", "incomplete", "invalidated")
                    or role not in ("development", "final")):
                raise ValueError("invalid saved plan status")
            # Audit is the existing hash/membership projection. Do not return its
            # optional ranking rules (contain query text), or private reason text.
            arms = audit["arms"]
            for a, b in zip(arms[::2], arms[1::2]):
                if (not a["raw_present"] or a["raw_present"] != b["raw_present"]
                        or a["memories_present"] or not b["memories_present"]
                        or a["request_sha256"] == b["request_sha256"]):
                    raise ValueError("each B must add eligible memory to the same A raw prefix")
            # Do not call report/run: those may persist invalidation or convert
            # unknown intent to incomplete. Preparation never changes statuses.
            current = baseline.current(plan_id)
            if current != comparisons._bound(plan):
                raise ValueError("frozen context is no longer current")
            return dict(
                operation="compare-prepare", offline=True, dispatch_authorization=False,
                plan_id=plan_id, plan_sha256=digest, config_sha256=plan["config_sha256"],
                taskset_sha256=plan["taskset_sha256"], context_sha256=audit["context_sha256"],
                policy_sha256=plan["policy_sha256"], snapshot_sha256=plan["snapshot_sha256"],
                evaluator_identity=plan["evaluator_identity"],
                evaluator_identity_sha256=sha256_hex(_encode(plan["evaluator_identity"])),
                evaluator_protocol_sha256=plan["evaluator_identity"]["protocol_sha256"],
                raw_references_sha256=plan["raw_references_sha256"],
                consolidated_records_sha256=plan["consolidated_records_sha256"],
                representation=audit["representation"], model=model, status=status,
                contact_role=role, planned_denominator=dict(
                    task_pairs=len(plan["tasks"]), per_arm=len(plan["tasks"]),
                    total_arms=2 * len(plan["tasks"])),
                task_order=[dict(task_index=i, task_id=t["task_id"], order=t["order"])
                            for i, t in enumerate(plan["tasks"])],
                per_arm_caps={arm: asdict(budget) for arm in "AB"},
                request_byte_check="before_dispatch", reply_byte_check="post_generation",
                byte_caps_are_token_caps=False, byte_caps_are_monetary_caps=False,
                generation_token_cap=None, monetary_cap=None,
                cost={"label": "unavailable", "value": None}, usage=None,
                arms=arms, current_validity=dict(valid=True, **current),
                performance_claim=None, acceptance_complete=False)
