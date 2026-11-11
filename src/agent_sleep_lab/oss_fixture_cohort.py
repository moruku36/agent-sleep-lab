"""Frozen local synthetic-development cohorts; read-only ExecutionJournal reports.

No dispatcher, retry, answer store, adoption receipt or scientific inference.
The registry commits while a short journal reservation excludes new intents.
Journal outcomes and current evidence-store policy are not one transaction.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import re
import sqlite3

from agent_sleep_lab import oss_execution_journal as execution
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_prompt_capture_worker as child
from agent_sleep_lab import oss_verdict_evaluation as evaluation
from agent_sleep_lab.strictjson import loads_strict_bytes

PROTOCOL = "agent-sleep-oss-fixture-cohort/1"
PROBE_PROTOCOL = "agent-sleep-oss-fixture-cohort/2"
PARTITION = "synthetic_development_fixture"
APPLICATION_ID = 0x41534C43
SCHEMA_VERSION = 1
MAX_TASKS = 5
MAX_DOCUMENT_BYTES = 8192
MAX_BINDING_BYTES = 2097152
ARMS = evaluation.ARMS
DDL = (
    "CREATE TABLE cohorts (cohort_id TEXT PRIMARY KEY, document BLOB NOT NULL, "
    "document_sha256 TEXT NOT NULL)",
)
MEMBER_KEYS = {"plan_id", "binding_sha256", "manifest_sha256", "task_sha256", "issue_number"}
DOCUMENT_KEYS = {"protocol", "cohort_id", "partition", "registered_tasks", "members",
                 "comparison_sha256"}
PROBE_DOCUMENT_KEYS = DOCUMENT_KEYS | {"selection_contract", "probe_provenance"}
BINDING_KEYS = {"protocol", "plan_id", "synthetic_task_only", "capture", "source", "worker",
                "reference", "retrieval", "bridge", "arms", "bounds", "capture_doc", "adapter",
                "execution_kind", "evaluation_manifest"}


class CohortError(ValueError):
    """Sanitized contract/integrity refusal, never a provider or database excerpt."""


def _id(value):
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value):
        raise CohortError("bounded cohort/plan ID required")


def _hash(value):
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise CohortError("exact lowercase SHA-256 required")


def _members(members):
    if type(members) is not list or not 2 <= len(members) <= MAX_TASKS:
        raise CohortError("two to five explicit synthetic task members required")
    plans, tasks = set(), set()
    for item in members:
        if type(item) is not dict or set(item) != MEMBER_KEYS:
            raise CohortError("exact member identity keys required")
        _id(item["plan_id"])
        for key in ("binding_sha256", "manifest_sha256", "task_sha256"):
            _hash(item[key])
        number = item["issue_number"]
        if type(number) is not int or number not in range(1, 6):
            raise CohortError("built-in synthetic issue number required")
        task = (item["task_sha256"], number)
        if item["plan_id"] in plans or task in tasks:
            raise CohortError("duplicate plan or task identity")
        plans.add(item["plan_id"])
        tasks.add(task)
    # Detach caller-owned mutable containers and define one stable member order.
    return sorted((dict(item) for item in members), key=lambda item: item["issue_number"])


def _document(value):
    if type(value) is not dict:
        raise CohortError("exact cohort document keys required")
    probe = value.get("protocol") == PROBE_PROTOCOL
    if set(value) != (PROBE_DOCUMENT_KEYS if probe else DOCUMENT_KEYS):
        raise CohortError("exact cohort document keys required")
    _id(value["cohort_id"])
    _hash(value["comparison_sha256"])
    members = _members(value["members"])
    if (value["protocol"] not in {PROTOCOL, PROBE_PROTOCOL} or value["partition"] != PARTITION
            or type(value["registered_tasks"]) is not int
            or value["registered_tasks"] != len(members) or members != value["members"]
            or len({item["task_sha256"] for item in members}) != 1):
        raise CohortError("unsupported cohort contract or denominator")
    if probe and (value["selection_contract"] != child.PROBE_PROTOCOL
                  or worker.encoded(value["probe_provenance"]) != worker.encoded(child.PROBE_PROVENANCE)):
        raise CohortError("exact selected-probe cohort provenance required")
    return value


@contextmanager
def _journal_view(journal, *, reserve=False):
    if type(journal) is not execution.ExecutionJournal:
        raise CohortError("exact ExecutionJournal required")
    db = journal._db
    if db.in_transaction:
        raise CohortError("journal transaction already open")
    execution.ExecutionJournal._check_schema(db)
    # No journal data is written. IMMEDIATE excludes competing intent writers
    # until the separate registry commit is durable. Reports use a read snapshot.
    db.execute("BEGIN IMMEDIATE" if reserve else "BEGIN")
    try:
        yield
    finally:
        db.execute("ROLLBACK")


def _plan(journal, plan_id, bridge):
    row = journal._db.execute(
        "SELECT length(binding),typeof(binding) FROM plans WHERE plan_id=?", (plan_id,)).fetchone()
    if row is None:
        return None
    if row[1] != "blob" or not 1 <= row[0] <= MAX_BINDING_BYTES:
        raise CohortError("bounded execution binding required")
    try:
        binding, digest, stopped = journal._binding(plan_id, bridge)
        _hash(digest)
        if (type(binding) is not dict or set(binding) != BINDING_KEYS
                or binding["plan_id"] != plan_id or binding["synthetic_task_only"] is not True
                or worker.digest(worker.encoded(binding)) != digest):
            raise CohortError("exact canonical synthetic execution binding required")
        manifest = binding["evaluation_manifest"]
        if type(manifest) is not dict:
            raise CohortError("pre-frozen fixture manifest required")
        source = binding["source"]
        identity = dict(plan_id=plan_id, binding_sha256=digest,
                        manifest_sha256=worker.digest(worker.encoded(manifest)),
                        task_sha256=source["task_sha256"], issue_number=source["issue_number"])
    except (ValueError, KeyError, TypeError, RecursionError):
        raise CohortError("invalid execution binding or missing frozen manifest") from None
    return binding, identity, stopped


def member_identity(journal, plan_id, bridge):
    """Read exact pins for a caller to review; registration rechecks them all."""
    _id(plan_id)
    with _journal_view(journal):
        plan = _plan(journal, plan_id, bridge)
        if plan is None:
            raise CohortError("unknown member plan")
        return plan[1]


def _comparison(binding):
    """Conservative equality: only task identity, prompt and fixture label vary.

    Hash the settings without persisting labels, prompts or reference text in
    the registry. Full binding hashes additionally pin every omitted byte.
    """
    manifest = {key: value for key, value in binding["evaluation_manifest"].items()
                if key not in {"expected_accept", "task_sha256", "issue_number"}}
    requests = {}
    for arm in ARMS:
        request = loads_strict_bytes(bytes.fromhex(binding["arms"][arm]["request_hex"]))
        request["payload"]["messages"][0]["content"] = None
        requests[arm] = request
    source = {key: value for key, value in binding["source"].items() if key != "issue_number"}
    reference = {key: value for key, value in binding["reference"].items() if key != "hex"}
    settings = {key: binding[key] for key in (
        "protocol", "execution_kind", "adapter", "bounds", "worker", "bridge", "retrieval")}
    settings.update(source=source, reference=reference, evaluation=manifest, requests=requests,
                    capture={key: binding["capture"][key] for key in (
                        "protocol", "artifact_kind", "model", "model_identity", "comparability")})
    if binding["capture"]["protocol"] == child.PROBE_OUTPUT_PROTOCOL:
        # Validate the complete new contract first. The old equality/hash rule
        # remains byte-identical for saved v1 cohort documents.
        execution.validate_capture_version(binding)
        selection = binding["capture"]["selected_issue_probe"]
        settings["capture"].update(
            selection_contract=selection["protocol"],
            probe_provenance=binding["capture"]["probe_provenance"])
        # The pinned insertion is identical data across tasks, but the generic
        # longest-prefix/suffix representation can rotate adjacent newlines.
        # v2 validation requires exactly this block and no other prompt change.
        notes = child.reference_notes(bytes.fromhex(binding["reference"]["hex"]))
        block = ("\nProject notes:\n" + notes + "\n").encode("utf-8")
        settings["capture"]["comparability"] = dict(
            relation=child.RELATION, non_prompt_request_fields_equal=True,
            pinned_notes_block_sha256=worker.digest(block), pinned_notes_block_bytes=len(block))
    return worker.digest(worker.encoded(settings))


def _bridges(bridges, members, *, complete):
    plans = {item["plan_id"] for item in members}
    if (type(bridges) is not dict or len(bridges) > len(plans) or not set(bridges) <= plans
            or (complete and set(bridges) != plans)):
        raise CohortError("explicit per-plan bridge mapping required")


class CohortRegistry:
    """Separate private SQLite registry. No execution or adoption methods.

    New registration requires ALL existing plans to be current, unstopped and
    without ANY arm row. Exact replay of an already frozen cohort is allowed.
    Membership cannot be added, removed, relabelled or rebound by this API.
    """

    def __init__(self, path, *, initialize=False):
        if not isinstance(path, (str, Path)) or not Path(path).is_absolute():
            raise CohortError("explicit absolute private registry path required")
        path = Path(path)
        if path.exists() and path.stat().st_size:
            probe = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            try:
                self._check_schema(probe)
            finally:
                probe.close()
        elif not initialize:
            raise CohortError("explicit initialize=True required for a new registry")
        elif not path.exists():
            os.close(os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600))
        self._db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, isolation_level=None)
        try:
            if path.stat().st_size == 0:
                self._db.execute("BEGIN IMMEDIATE")
                for sql in DDL:
                    self._db.execute(sql)
                self._db.execute("PRAGMA application_id=%d" % APPLICATION_ID)
                self._db.execute("PRAGMA user_version=%d" % SCHEMA_VERSION)
                self._db.execute("COMMIT")
            self._check_schema(self._db)
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA fullfsync=ON")
        except BaseException:
            self._db.close()
            raise

    @staticmethod
    def _check_schema(db):
        try:
            sql = [row[0] for row in db.execute(
                "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY name")]
            if (db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
                    or db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION
                    or sql != list(DDL)):
                raise CohortError("foreign or changed cohort registry; no migration")
        except sqlite3.DatabaseError:
            raise CohortError("unreadable cohort registry schema") from None

    def close(self):
        self._db.close()

    def _load(self, cohort_id):
        self._check_schema(self._db)
        row = self._db.execute(
            "SELECT CASE WHEN length(document)<=? THEN document END,document_sha256 "
            "FROM cohorts WHERE cohort_id=?", (MAX_DOCUMENT_BYTES, cohort_id)).fetchone()
        if row is None:
            return None
        raw, digest = row
        if (type(raw) is not bytes or not 1 <= len(raw) <= MAX_DOCUMENT_BYTES
                or worker.digest(raw) != digest):
            raise CohortError("cohort document integrity mismatch")
        try:
            value = _document(loads_strict_bytes(raw))
            if value["cohort_id"] != cohort_id or worker.encoded(value) != raw:
                raise CohortError("noncanonical or mismatched cohort document")
        except (ValueError, TypeError, RecursionError):
            raise CohortError("invalid saved cohort document") from None
        return value

    def register(self, cohort_id, *, journal, members, bridges):
        _id(cohort_id)
        members = _members(members)
        _bridges(bridges, members, complete=True)
        with _journal_view(journal, reserve=True):
            plans, comparisons = [], set()
            for member in members:
                plan = _plan(journal, member["plan_id"], bridges[member["plan_id"]])
                if plan is None or plan[1] != member:
                    raise CohortError("member plan identity mismatch or missing plan")
                binding = plan[0]
                comparisons.add(_comparison(binding))
                plans.append(plan)
            if len(comparisons) != 1:
                raise CohortError("incompatible comparison settings")
            document = dict(
                protocol=PROTOCOL, cohort_id=cohort_id, partition=PARTITION,
                registered_tasks=len(members), members=members,
                comparison_sha256=comparisons.pop())
            if plans[0][0]["capture"]["protocol"] == child.PROBE_OUTPUT_PROTOCOL:
                document.update(protocol=PROBE_PROTOCOL, selection_contract=child.PROBE_PROTOCOL,
                                probe_provenance=dict(child.PROBE_PROVENANCE))
            document = _document(document)
            raw = worker.encoded(document)
            if len(raw) > MAX_DOCUMENT_BYTES:
                raise CohortError("cohort document byte bound")
            self._db.execute("BEGIN IMMEDIATE")
            try:
                existing = self._load(cohort_id)
                if existing is not None:
                    if existing != document:
                        raise CohortError("cohort ID already frozen differently")
                else:
                    for binding, identity, stopped in plans:
                        started = journal._db.execute(
                            "SELECT 1 FROM arms WHERE plan_id=? LIMIT 1", (identity["plan_id"],)).fetchone()
                        if stopped is not None or started is not None:
                            raise CohortError("cohort registration must precede every member intent")
                        try:
                            evaluation.validate_manifest(binding["evaluation_manifest"],
                                                         identity["task_sha256"], identity["issue_number"])
                        except ValueError:
                            raise CohortError("current frozen evaluation manifest required") from None
                        if (identity["task_sha256"] != worker.digest(worker.encoded(worker.synthetic_task()))
                                or not journal._current(binding, bridges[identity["plan_id"]])):
                            raise CohortError("member task version or current context mismatch")
                    self._db.execute("INSERT INTO cohorts VALUES (?,?,?)",
                                     (cohort_id, raw, worker.digest(raw)))
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
        return document

    @staticmethod
    def _task(member, document, journal, bridges, execution_reports):
        result = dict(member, status="incomplete", arms={
            arm: dict(status="unresolved", execution_status="unavailable", score=None) for arm in ARMS})
        plan_id = member["plan_id"]
        if plan_id not in bridges:
            result["status"] = "unavailable_context"
            return result
        try:
            plan = _plan(journal, plan_id, bridges[plan_id])
            if plan is None:
                result["status"] = "missing_plan"
                return result
            if plan[1] != member or _comparison(plan[0]) != document["comparison_sha256"]:
                result["status"] = "identity_or_settings_mismatch"
                return result
            report = journal.report(plan_id, bridges[plan_id])
        except execution.PlanConflict:
            result["status"] = "identity_or_settings_mismatch"
            return result
        except (execution.JournalError, CohortError, ValueError, KeyError, TypeError, UnicodeError):
            result["status"] = "unavailable_journal_integrity"
            return result
        if execution_reports is not None:
            execution_reports[plan_id] = report
        scored = report["verdict_evaluation"]
        result["status"] = scored["status"]
        # Allowlist numeric/status fields only. Never copy verdicts, bodies,
        # rationale, answer labels or transport receipts into aggregate reports.
        for arm, item in scored["arms"].items():
            result["arms"][arm] = {key: item[key] for key in ("status", "execution_status", "score")}
        return result

    def report(self, cohort_id, *, journal, bridges):
        return self._report(cohort_id, journal=journal, bridges=bridges)

    def _report(self, cohort_id, *, journal, bridges, execution_reports=None):
        # Accounting can pin exact member reports from the same journal read
        # snapshot. The public cohort report keeps its existing allowlist.
        _id(cohort_id)
        document = self._load(cohort_id)
        if document is None:
            raise CohortError("unknown cohort")
        _bridges(bridges, document["members"], complete=False)
        with _journal_view(journal):
            tasks = [self._task(member, document, journal, bridges, execution_reports)
                     for member in document["members"]]
        count = document["registered_tasks"]
        complete = sum(task["status"] in {"complete", "complete_with_invalid_verdict"} for task in tasks)
        arms = {}
        for arm in ARMS:
            scores = [task["arms"][arm]["score"] for task in tasks]
            arms[arm] = dict(registered_tasks=count, scored_tasks=sum(s is not None for s in scores),
                             observed_successes=sum(s for s in scores if s is not None),
                             invalid_verdicts=sum(task["arms"][arm]["status"] == "invalid_verdict"
                                                  for task in tasks),
                             mean_score=sum(scores) / count if complete == count else None)
        difference = None
        if complete == count:
            difference = sum(task["arms"]["reference"]["score"] - task["arms"]["baseline"]["score"]
                             for task in tasks) / count
        report = dict(protocol=document["protocol"], cohort_id=cohort_id,
                    cohort_sha256=worker.digest(worker.encoded(document)), partition=PARTITION,
                    comparison_sha256=document["comparison_sha256"],
                    status="complete" if complete == count else "incomplete",
                    registered_tasks=count, complete_tasks=complete, incomplete_tasks=count - complete,
                    tasks=tasks, arms=arms, reference_minus_baseline=difference,
                    usage="unavailable", cost="unavailable", adoption="none",
                    scope="descriptive_synthetic_development_fixtures_not_independent_effect_evidence",
                    performance_improvement="not_evaluated", semantic_memory_use="not_evaluated")
        if document["protocol"] == PROBE_PROTOCOL:
            report.update(selection_contract=document["selection_contract"],
                          probe_provenance=document["probe_provenance"])
        return report
