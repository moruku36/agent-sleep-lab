"""Gate 4B: offline synthetic paired A/B comparison. Not a performance experiment.

Arm A receives raw references; arm B receives consolidated records plus the same
raw references, under the same per-arm request-byte / reply-byte / call budget.
Only a locally supplied fake provider is supported: no network, live model,
schedule, REM, diary, fallback or spending. Scores come from a separate trusted
local evaluator callable and are synthetic; this module never produces adoption
receipts, performance claims or measured savings. Plan registration is local,
NOT authentication. Use a separate private SQLite path.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass

from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.strictjson import loads_strict_bytes

REPORT_SCHEMA = "agent-sleep-ab-report/1"
COST_PHASES = ("capture", "consolidation", "verification", "retrieval",
               "task_execution", "task_input", "task_output", "maintenance", "evaluation")
COST_LABELS = ("synthetic_zero", "unavailable")
TERMINAL = ("completed", "timeout", "missing", "invalid")
ROLES = ("development", "final")


def _encode(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")
    loads_strict_bytes(data)
    return data


def _id(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", value)


def _sha(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value)


def _texts(value, name):
    if (type(value) is not list or len(value) > 64
            or not all(type(v) is str and v for v in value)):
        raise ValueError("bounded list of non-empty strings required: " + name)
    return list(value)


@dataclass(frozen=True)
class ArmBudget:
    """Identical for both arms: one call per task, same request/reply byte caps."""
    calls: int = 64
    request_bytes: int = 8192
    reply_bytes: int = 2048

    def __post_init__(self):
        for name, ceiling in (("calls", 64), ("request_bytes", 1048576),
                              ("reply_bytes", 65536)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError("invalid budget: " + name)


@dataclass(frozen=True)
class SyntheticEvaluator:
    """Trusted local evaluator; its scoring protocol is bound before execution."""
    name: str
    version: str
    protocol_sha256: str
    evaluate: object

    def identity(self):
        identity = dict(name=self.name, version=self.version,
                        protocol_sha256=self.protocol_sha256)
        _evaluator_identity(identity)
        if not callable(self.evaluate):
            raise ValueError("local evaluator callable required")
        return identity

    def __call__(self, task_id, reply):
        return self.evaluate(task_id, reply)


def _evaluator_identity(identity):
    if (type(identity) is not dict
            or set(identity) != {"name", "version", "protocol_sha256"}
            or not _id(identity["name"]) or not _id(identity["version"])
            or not _sha(identity["protocol_sha256"])):
        raise ValueError("explicit evaluator identity/protocol required")
    return dict(identity)


class FakeTaskProvider:
    """Deterministic bytes-only seam. `script` maps a call index to bytes, None
    (missing reply) or an exception instance to raise. It sees only the request."""
    def __init__(self, default=b"synthetic-reply", script=None):
        self.default = default
        self.script = dict(script or {})
        self.requests = []

    def reply(self, request, max_output_bytes):
        index = len(self.requests)
        self.requests.append(request)
        outcome = self.script.get(index, self.default)
        if isinstance(outcome, BaseException):
            raise outcome
        if callable(outcome):
            return outcome(request)
        return outcome


def _request(task, items, cap):
    """Greedy whole-item packing in fixed order; returns (bytes, included)."""
    def build(context):
        return _encode({"reference_data_only": True, "task_id": task["task_id"],
                        "prompt": task["prompt"], "context": context})
    chosen, data = [], build([])
    if len(data) > cap:
        raise ValueError("request budget cannot hold the task prompt")
    for item in items:
        trial = build(chosen + [item])
        if len(trial) > cap:
            break
        chosen.append(item)
        data = trial
    return data, len(chosen)


class ComparisonStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=5)
        if (self.db.execute("PRAGMA application_id").fetchone()[0] != 0
                or self.db.execute("PRAGMA user_version").fetchone()[0] != 0
                or any(row[0] not in {"comparison_plans", "evaluation_contacts", "comparison_arms",
                                     "frozen_contexts", "comparison_provider_receipts"}
                       for row in self.db.execute("SELECT name FROM sqlite_master WHERE type=\'table\'"))):
            self.db.close()
            raise ValueError("separate comparison journal required; foreign database refused")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS comparison_provider_receipts (
            plan_id TEXT NOT NULL, task_index INTEGER NOT NULL, arm TEXT NOT NULL,
            receipt BLOB NOT NULL, PRIMARY KEY(plan_id, task_index, arm))""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS comparison_plans (
            plan_id TEXT PRIMARY KEY, plan BLOB NOT NULL, plan_sha256 TEXT NOT NULL,
            status TEXT NOT NULL, reason TEXT, contact_role TEXT NOT NULL)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS evaluation_contacts (
            taskset_sha256 TEXT NOT NULL, plan_sha256 TEXT NOT NULL, plan_id TEXT NOT NULL,
            contact_role TEXT NOT NULL, PRIMARY KEY (taskset_sha256, plan_sha256))""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS comparison_arms (
            plan_id TEXT NOT NULL, task_index INTEGER NOT NULL, arm TEXT NOT NULL,
            position INTEGER NOT NULL, status TEXT NOT NULL, request_sha256 TEXT NOT NULL,
            reply BLOB, score INTEGER, PRIMARY KEY (plan_id, task_index, arm))""")

    def close(self):
        self.db.close()

    # ---- plan -------------------------------------------------------------
    def plan(self, *, plan_id, tasks, raw_references, consolidated_records, config, model,
             scope, snapshot_sha256, policy_sha256, evaluator_identity, declared_role="development",
             budget=ArmBudget(), consolidation_cost="unavailable", diagnostic_only=False):
        """Bind an immutable canonical plan and record evaluation contact.

        Tasks carry only task_id and prompt; evaluator answers must stay inside
        the trusted evaluator and are rejected here by the exact key set.
        """
        if not _id(plan_id):
            raise ValueError("invalid plan ID")
        if (type(tasks) is not list or not 1 <= len(tasks) <= budget.calls
                or any(type(t) is not dict or set(t) != {"task_id", "prompt"}
                       or not _id(t["task_id"]) or type(t["prompt"]) is not str
                       or not t["prompt"] for t in tasks)
                or len({t["task_id"] for t in tasks}) != len(tasks)):
            raise ValueError("tasks must be unique {task_id, prompt} within the call budget")
        if (type(scope) is not dict or set(scope) != {"project", "task_family"}
                or not all(type(v) is str and v for v in scope.values())):
            raise ValueError("invalid scope")
        if not _sha(snapshot_sha256) or not _sha(policy_sha256):
            raise ValueError("snapshot and policy hashes required")
        if type(model) is not str or not model:
            raise ValueError("model label required")
        if declared_role not in ROLES or consolidation_cost not in COST_LABELS:
            raise ValueError("invalid role or cost label")
        if type(diagnostic_only) is not bool:
            raise ValueError("diagnostic_only must be boolean")
        raw = _texts(raw_references, "raw_references")
        memo = _texts(consolidated_records, "consolidated_records")
        # Exact prompt-content multiset: task renames and reordering do not erase contact.
        # Semantic equivalents/translations still require external grouping review.
        taskset_sha256 = sha256_hex(_encode(sorted(t["prompt"] for t in tasks)))
        evaluator_identity = _evaluator_identity(evaluator_identity)
        planned = []
        for index, task in enumerate(tasks):
            entry = {"task_id": task["task_id"], "order": "AB" if index % 2 == 0 else "BA"}
            for arm, items in (("A", raw), ("B", raw + memo)):
                data, included = _request(task, items, budget.request_bytes)
                entry[arm] = {"request": data.decode("ascii"), "request_sha256": sha256_hex(data),
                              "request_bytes": len(data), "included": included,
                              "dropped": len(items) - included}
            if entry["A"]["request_sha256"] == entry["B"]["request_sha256"] and not diagnostic_only:
                raise ValueError("identical A/B inputs: increase request budget or reduce raw context")
            planned.append(entry)

        def zero():
            return {"label": "synthetic_zero", "value": 0}
        cost = {arm: {phase: zero() for phase in COST_PHASES} for arm in "AB"}
        from agent_sleep_lab.mimo_provider import MODEL
        if model == MODEL:
            cost = {arm: {phase: {"label": "unavailable", "value": None}
                          for phase in COST_PHASES} for arm in "AB"}
        if consolidation_cost == "unavailable":
            cost["B"]["consolidation"] = {"label": "unavailable", "value": None}
        document = _encode(dict(
            version=1, synthetic_only=True, plan_id=plan_id, taskset_sha256=taskset_sha256,
            config_sha256=sha256_hex(_encode(config)), model=model, scope=scope,
            evaluator_identity=evaluator_identity, diagnostic_only=diagnostic_only,
            raw_references_sha256=sha256_hex(_encode(raw)),
            consolidated_records_sha256=sha256_hex(_encode(memo)),
            snapshot_sha256=snapshot_sha256, policy_sha256=policy_sha256,
            declared_role=declared_role, budget=asdict(budget), cost=cost, tasks=planned))
        digest = sha256_hex(document)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT plan FROM comparison_plans WHERE plan_id=?",
                                  (plan_id,)).fetchone()
            if row is None:
                prior = self.db.execute(
                    "SELECT COUNT(*) FROM evaluation_contacts WHERE taskset_sha256=?",
                    (taskset_sha256,)).fetchone()[0]
                role = "final" if declared_role == "final" and prior == 0 else "development"
                self.db.execute("INSERT INTO comparison_plans VALUES (?,?,?,?,?,?)",
                                (plan_id, document, digest, "planned", None, role))
                self.db.execute("INSERT INTO evaluation_contacts VALUES (?,?,?,?)",
                                (taskset_sha256, digest, plan_id, role))
            elif bytes(row[0]) != document:
                raise ValueError("plan binding conflict")
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return digest

    def _plan(self, plan_id):
        row = self.db.execute(
            "SELECT plan, plan_sha256, status, reason, contact_role FROM comparison_plans "
            "WHERE plan_id=?", (plan_id,)).fetchone()
        if row is None:
            raise ValueError("unknown plan")
        if sha256_hex(bytes(row[0])) != row[1]:
            raise ValueError("corrupt plan digest")
        return (loads_strict_bytes(bytes(row[0])),) + tuple(row[1:])

    def _status(self, plan_id, status, reason):
        # invalidated and incomplete are sticky; nothing may overwrite them.
        self.db.execute(
            "UPDATE comparison_plans SET status=?, reason=? WHERE plan_id=? "
            "AND status NOT IN ('invalidated','incomplete')", (status, reason, plan_id))

    def _arm(self, plan_id, index, arm, status, reply=None, score=None):
        self.db.execute(
            "UPDATE comparison_arms SET status=?, reply=?, score=? "
            "WHERE plan_id=? AND task_index=? AND arm=?",
            (status, reply, score, plan_id, index, arm))

    def inspect(self, plan_id):
        _, digest, status, reason, role = self._plan(plan_id)
        arms = self.db.execute(
            "SELECT task_index, arm, position, status, score FROM comparison_arms "
            "WHERE plan_id=? ORDER BY task_index, position", (plan_id,)).fetchall()
        return {"plan_sha256": digest, "status": status, "reason": reason,
                "contact_role": role, "arms": [list(a) for a in arms]}

    @staticmethod
    def _bound(plan):
        return {"policy_sha256": plan["policy_sha256"],
                "snapshot_sha256": plan["snapshot_sha256"]}

    # ---- run --------------------------------------------------------------
    def run(self, plan_id, provider, evaluator, current, limit=None):
        """Dispatch remaining arms in the fixed order. `current()` is a trusted
        local callable returning the present policy/snapshot hashes; `evaluator`
        is a trusted local callable (task_id, reply_bytes) -> 0 or 1, separate
        from the provider. `limit` bounds new dispatches in this call."""
        plan, _, status, _, _ = self._plan(plan_id)
        from agent_sleep_lab.mimo_provider import MODEL, OpenClawMimoProvider
        fake = isinstance(provider, FakeTaskProvider)
        if not (fake or isinstance(provider, OpenClawMimoProvider)) or not isinstance(evaluator, SyntheticEvaluator):
            raise TypeError("explicit supported provider and protocol-bound evaluator required")
        if (not fake and plan["model"] != MODEL) or (fake and plan["model"] == MODEL):
            raise ValueError("provider/model binding conflict")
        if not plan.get("diagnostic_only", False) and any(
                t["A"]["request_sha256"] == t["B"]["request_sha256"] for t in plan["tasks"]):
            raise ValueError("identical A/B inputs are not comparable")
        if evaluator.identity() != plan["evaluator_identity"]:
            raise ValueError("evaluator binding conflict")
        if limit is not None and (type(limit) is not int or limit < 1):
            raise ValueError("limit must be a positive dispatch count")
        if status in ("invalidated", "incomplete", "complete"):
            return self.inspect(plan_id)
        if self.db.execute("SELECT 1 FROM comparison_arms WHERE plan_id=? AND status='intent'",
                           (plan_id,)).fetchone():
            # Intent persisted but outcome never recorded: unknown, never auto-replayed.
            self._status(plan_id, "incomplete", "unknown_outcome")
            return self.inspect(plan_id)
        cap, dispatched = plan["budget"]["reply_bytes"], 0
        for index, task in enumerate(plan["tasks"]):
            for position, arm in enumerate(task["order"]):
                row = self.db.execute(
                    "SELECT status, reply FROM comparison_arms WHERE plan_id=? "
                    "AND task_index=? AND arm=?", (plan_id, index, arm)).fetchone()
                if row is not None and row[0] in TERMINAL:
                    continue
                if current() != self._bound(plan):
                    self._status(plan_id, "invalidated", "policy_or_snapshot_changed")
                    return self.inspect(plan_id)
                if row is None:
                    if limit is not None and dispatched >= limit:
                        self._status(plan_id, "running", None)
                        return self.inspect(plan_id)
                    self.db.execute(
                        "INSERT INTO comparison_arms VALUES (?,?,?,?,?,?,NULL,NULL)",
                        (plan_id, index, arm, position, "intent", task[arm]["request_sha256"]))
                    dispatched += 1
                    prior_receipt_count = len(getattr(provider, "receipts", []))
                    try:  # fresh context: the provider receives only this frozen request
                        try:
                            reply = provider.reply(task[arm]["request"].encode("ascii"), cap)
                        finally:
                            if not fake and len(provider.receipts) > prior_receipt_count:
                                self.db.execute(
                                    "INSERT OR REPLACE INTO comparison_provider_receipts VALUES (?,?,?,?)",
                                    (plan_id, index, arm, _encode(provider.receipts[-1])))
                    except TimeoutError:
                        self._arm(plan_id, index, arm, "timeout")
                        continue
                    except BaseException:
                        self._status(plan_id, "incomplete", "unknown_outcome")
                        raise
                    if reply is None:
                        self._arm(plan_id, index, arm, "missing")
                        continue
                    if type(reply) is not bytes or len(reply) > cap:
                        self._arm(plan_id, index, arm, "invalid")
                        continue
                    self._arm(plan_id, index, arm, "replied", reply)
                else:  # 'replied': reply is durable, only local evaluation remains
                    reply = bytes(row[1])
                if current() != self._bound(plan):
                    self._status(plan_id, "invalidated", "policy_or_snapshot_changed")
                    return self.inspect(plan_id)
                score = evaluator(task["task_id"], reply)
                if type(score) is not int or score not in (0, 1):
                    raise ValueError("evaluator must return 0 or 1")
                self._arm(plan_id, index, arm, "completed", reply, score)
        self._status(plan_id, "complete", None)
        return self.inspect(plan_id)

    # ---- report -----------------------------------------------------------
    def report(self, plan_id, current):
        plan, digest, status, reason, role = self._plan(plan_id)
        if status != "invalidated" and current() != self._bound(plan):
            self._status(plan_id, "invalidated", "policy_or_snapshot_changed")
            plan, digest, status, reason, role = self._plan(plan_id)
        cost = {}
        for arm in "AB":
            phases = plan["cost"][arm]
            missing = any(p["label"] == "unavailable" for p in phases.values())
            cost[arm] = {"phases": phases, "total": (
                {"label": "unavailable", "value": None} if missing
                else {"label": "synthetic_zero", "value": 0})}
        from agent_sleep_lab.mimo_provider import MODEL
        document = {
            "schema_version": REPORT_SCHEMA, "synthetic_only": True, "fake_provider": plan["model"] != MODEL,
            "scores_are_synthetic": True, "plan_id": plan_id, "plan_sha256": digest,
            "taskset_sha256": plan["taskset_sha256"], "status": status, "reason": reason,
            "declared_role": plan["declared_role"], "contact_role": role,
            "independent_holdout": False, "first_final_contact": role == "final",
            "adoption_receipt": None, "performance_claim": None,
            "cost": cost, "measured_savings": None,
            "savings_basis": "none: synthetic-zero or unavailable costs are not measurements",
            "comparison": None,
            "cost_unit": None if plan["model"] == MODEL else "synthetic_currency_units", "currency": None,
            "evaluator_identity": plan["evaluator_identity"],
        }
        outcomes = {arm: dict(denominator=len(plan["tasks"]), completed=0, timeout=0,
                             missing=0, invalid=0, unknown=0, replied=0, not_started=0)
                    for arm in "AB"}
        observed = {(r[0], r[1]): r[2] for r in self.db.execute(
            "SELECT task_index, arm, status FROM comparison_arms WHERE plan_id=?", (plan_id,))}
        for index in range(len(plan["tasks"])):
            for arm in "AB":
                value = observed.get((index, arm), "not_started")
                outcomes[arm]["unknown" if value == "intent" else value] += 1
        document["provider_receipts"] = [dict(task_index=i, arm=a, receipt=loads_strict_bytes(bytes(r)))
            for i, a, r in self.db.execute(
                "SELECT task_index, arm, receipt FROM comparison_provider_receipts WHERE plan_id=? "
                "ORDER BY task_index, arm", (plan_id,))]
        document["outcomes"] = outcomes
        document["all_outcomes_scored"] = all(
            outcomes[arm]["completed"] == len(plan["tasks"]) for arm in "AB")
        document["comparable"] = not plan.get("diagnostic_only", False) and all(
            t["A"]["request_sha256"] != t["B"]["request_sha256"] for t in plan["tasks"])
        if status != "complete" or not document["comparable"]:
            return document
        rows = {(r[0], r[1]): (r[2], r[3]) for r in self.db.execute(
            "SELECT task_index, arm, status, score FROM comparison_arms WHERE plan_id=?",
            (plan_id,))}
        total = len(plan["tasks"])
        arms = {arm: dict({name: 0 for name in TERMINAL}, denominator=total, evaluator_pass=0)
                for arm in "AB"}
        paired = {"denominator": total, "both": 0, "a_only": 0, "b_only": 0, "neither": 0}
        order = {"AB": 0, "BA": 0}
        for index, task in enumerate(plan["tasks"]):
            order[task["order"]] += 1
            passed = {}
            for arm in "AB":
                state, score = rows[(index, arm)]
                arms[arm][state] += 1
                passed[arm] = score == 1  # timeout/missing/invalid stay in the denominator
                arms[arm]["evaluator_pass"] += int(passed[arm])
            key = ("both" if passed["A"] and passed["B"] else "a_only" if passed["A"]
                   else "b_only" if passed["B"] else "neither")
            paired[key] += 1
        document["comparison"] = {"arms": arms, "paired": paired, "order": order}
        return document
