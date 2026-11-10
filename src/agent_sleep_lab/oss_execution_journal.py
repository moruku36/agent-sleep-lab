"""Durable exact-prompt execution, separate from the fake-only paired journal.

Single driver per plan. SQLite intent commits precede transport, never span
network calls, and interrupted intents permanently halt the plan. The evidence
store and this journal are NOT one atomic transaction. Explicit live selection
does not supply owner authorization or change external spending/host controls.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3

from agent_sleep_lab import oss_paired_outcome as paired
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_prompt_capture as capture
from agent_sleep_lab import oss_prompt_capture_worker as child
from agent_sleep_lab import oss_verdict_evaluation as evaluation
from agent_sleep_lab.oss_mimo_adapter import OSSMimoAdapter, TRANSPORT_CLI, MODEL

PROTOCOL = "agent-sleep-oss-execution/1"
APPLICATION_ID = 0x41534C45
SCHEMA_VERSION = 1
ARMS = paired.ARMS
JournalError = paired.JournalError
PlanConflict = paired.PlanConflict
DDL = (
    "CREATE TABLE plans (plan_id TEXT PRIMARY KEY, binding BLOB NOT NULL, "
    "binding_sha256 TEXT NOT NULL, stopped TEXT)",
    "CREATE TABLE arms (plan_id TEXT NOT NULL REFERENCES plans(plan_id), "
    "arm TEXT NOT NULL CHECK(arm IN ('baseline','reference')), "
    "state TEXT NOT NULL CHECK(state IN ('intent','completed','unknown','invalidated')), "
    "reply BLOB, reply_sha256 TEXT, reply_bytes INTEGER, receipt BLOB, receipt_sha256 TEXT, "
    "PRIMARY KEY(plan_id, arm))",
)


def adapter_spec(adapter, live_transport):
    if type(adapter) is not OSSMimoAdapter:
        raise TypeError("exact OSSMimoAdapter required")
    if type(live_transport) is not bool:
        raise TypeError("live_transport must be boolean")
    if adapter.transport_kind == TRANSPORT_CLI and not live_transport:
        raise JournalError("live CLI transport requires explicit caller selection")
    return dict(adapter="OSSMimoAdapter/1", agent=adapter.agent, model=MODEL,
                transport=adapter.transport_kind, live_transport_selected=live_transport,
                max_calls=adapter.max_calls, timeout_seconds=adapter.timeout,
                max_request_bytes=adapter.max_request_bytes)


def receipt_for(binding, arm, reply):
    """Allowlisted expected receipt values; no raw process/transport metadata."""
    selected = binding["arms"][arm]
    receipt = dict(status="returned", arm=arm, provider="xiaomi", model="mimo-v2.6-pro",
                model_requested=MODEL, transport=binding["adapter"]["transport"],
                capture_document_sha256=binding["capture"]["document_sha256"],
                request_sha256=selected["request_sha256"],
                prompt_sha256=selected["prompt_sha256"],
                source_sha256=binding["source"]["source_sha256"],
                agent_commit=binding["source"]["agent_commit"],
                task_sha256=binding["source"]["task_sha256"],
                reference_sha256=binding["reference"]["sha256"],
                output_sha256=worker.digest(reply), output_bytes=len(reply),
                usage="unavailable", cost="unavailable")
    if binding["capture"]["protocol"] == child.PROBE_OUTPUT_PROTOCOL:
        receipt.update({key: binding["capture"][key] for key in (
            "selected_issue_probe", "probe_provenance", "score", "band")})
    return receipt


def validate_capture_version(binding):
    """New probe bindings cannot replay as ordinary v1 execution. No migration."""
    meta, doc = binding["capture"], binding["capture_doc"]
    fields = {"selected_issue_probe", "probe_provenance", "score", "band"}
    if meta["protocol"] == child.OUTPUT_PROTOCOL:
        if (fields.intersection(meta) or doc.get("protocol") != child.OUTPUT_PROTOCOL
                or set(doc) != child.OUTPUT_KEYS
                or binding["execution_kind"] != "exact_prompt_cli_not_original_http"):
            raise JournalError("v1 execution must not carry probe metadata")
        return  # Preserve saved v1 artifacts and their existing validation path.
    if meta["protocol"] != child.PROBE_OUTPUT_PROTOCOL:
        raise JournalError("unsupported capture version")
    try:
        validated = capture.validate_output(worker.encoded(doc), task=parent.builtin_task(),
            reference=bytes.fromhex(binding["reference"]["hex"]),
            selected_issue_probe=meta["selected_issue_probe"])
        probe = child.probe_metadata(validated)
        expected_meta = {key: validated[key] for key in (
            "protocol", "artifact_kind", "dispatch_authorization", "model_receipt", "verdict",
            "semantic_memory_use", "performance_improvement", "comparability", "model", "model_identity")}
        expected_meta.update(probe, document_sha256=worker.digest(worker.encoded(doc)))
        if (worker.encoded(meta) != worker.encoded(expected_meta)
                or binding["source"]["issue_number"] != probe["selected_issue_probe"]["issue_number"]
                or binding["source"]["task_sha256"] != probe["selected_issue_probe"]["task_sha256"]
                or binding["execution_kind"] !=
                    "selected_issue_probe_exact_prompt_not_automatic_triage_or_original_http"):
            raise ValueError("probe binding mismatch")
        for arm in ARMS:
            captured = validated["arms"][arm]
            request = worker.encoded({key: captured[key] for key in ("url", "header_names", "payload")})
            expected_arm = dict(request_hex=request.hex(), request_sha256=captured["request_sha256"],
                request_bytes=len(request), prompt_sha256=captured["prompt_sha256"],
                prompt_bytes=captured["prompt_bytes"])
            if worker.encoded(binding["arms"][arm]) != worker.encoded(expected_arm):
                raise ValueError("probe frozen request mismatch")
    except (ValueError, KeyError, TypeError):
        raise JournalError("invalid selected-probe execution binding") from None


class ExecutionJournal:
    def __init__(self, path, *, initialize=False):
        if not isinstance(path, (str, Path)) or not Path(path).is_absolute():
            raise JournalError("explicit absolute private journal path required")
        path = Path(path)
        # Existing databases are inspected read-only BEFORE any write or pragma.
        if path.exists() and path.stat().st_size:
            probe = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            try:
                self._check_schema(probe)
            finally:
                probe.close()
        elif not initialize:
            raise JournalError("explicit initialize=True required for a new or empty journal")
        elif not path.exists():
            os.close(os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600))
        self._db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        try:
            if path.stat().st_size == 0:
                with self._tx():
                    for sql in DDL:
                        self._db.execute(sql)
                    self._db.execute("PRAGMA application_id=%d" % APPLICATION_ID)
                    self._db.execute("PRAGMA user_version=%d" % SCHEMA_VERSION)
            self._check_schema(self._db)  # recheck after opening writable
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA fullfsync=ON")
            self._db.execute("PRAGMA foreign_keys=ON")
        except BaseException:
            self._db.close()
            raise

    @staticmethod
    def _check_schema(db):
        sql = [r[0] for r in db.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY name")]
        if (db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
                or db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION
                or sql != sorted(DDL, key=lambda s: s.split()[2])):
            raise JournalError("foreign or changed execution journal; no migration")

    def close(self):
        self._db.close()

    @contextmanager
    def _tx(self):
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        else:
            self._db.execute("COMMIT")

    def _binding(self, plan_id, bridge):
        row = self._db.execute("SELECT * FROM plans WHERE plan_id=?", (plan_id,)).fetchone()
        if row is None:
            raise JournalError("unknown execution plan")
        raw = bytes(row["binding"])
        if worker.digest(raw) != row["binding_sha256"]:
            raise JournalError("binding integrity mismatch")
        binding = worker.strict_json(raw)
        if (binding["protocol"] != PROTOCOL
                or binding["bridge"] != paired._bridge_identity(bridge)):
            raise PlanConflict("plan protocol or bridge mismatch")
        validate_capture_version(binding)
        return binding, row["binding_sha256"], row["stopped"]

    def _rows(self, binding):
        rows = {r["arm"]: dict(r) for r in self._db.execute(
            "SELECT * FROM arms WHERE plan_id=?", (binding["plan_id"],))}
        if "reference" in rows and ("baseline" not in rows
                                    or rows["baseline"]["state"] != "completed"):
            raise JournalError("arm sequence integrity mismatch")
        for arm, row in rows.items():
            if row["state"] == "completed":
                reply, raw = row["reply"], row["receipt"]
                if (type(reply) is not bytes or not 1 <= len(reply) <=
                        binding["bounds"]["max_reply_bytes_per_arm"]
                        or worker.digest(reply) != row["reply_sha256"]
                        or len(reply) != row["reply_bytes"] or type(raw) is not bytes
                        or worker.digest(raw) != row["receipt_sha256"]
                        or worker.strict_json(raw) != receipt_for(binding, arm, reply)):
                    raise JournalError("saved reply or receipt integrity mismatch")
            elif row["reply"] is not None or row["receipt"] is not None:
                raise JournalError("non-completed arm contains a body")
        return rows

    @staticmethod
    def _current(binding, bridge):
        try:
            return (paired._current_context(bridge, binding["retrieval"])
                    == binding["reference"]["context_sha256"])
        except Exception:
            return False

    def register(self, plan_id, *, adapter, live_transport=False,
                 evaluation_manifest=None, **options):
        binding = paired.build_binding(plan_id, **options)
        binding["protocol"] = PROTOCOL
        # The task/reference remains synthetic; execution provenance is distinct.
        binding.pop("provider")
        binding["synthetic_task_only"] = binding.pop("synthetic_only")
        binding["capture_doc"] = worker.strict_json(worker.encoded(options["capture_doc"]))
        binding["adapter"] = adapter_spec(adapter, live_transport)
        binding["execution_kind"] = (
            "selected_issue_probe_exact_prompt_not_automatic_triage_or_original_http"
            if binding["capture"]["protocol"] == child.PROBE_OUTPUT_PROTOCOL
            else "exact_prompt_cli_not_original_http")
        if evaluation_manifest is not None:
            binding["evaluation_manifest"] = evaluation.validate_manifest(
                evaluation_manifest, binding["source"]["task_sha256"],
                binding["source"]["issue_number"])
        if binding["bounds"]["max_request_bytes_per_arm"] > adapter.max_request_bytes:
            raise JournalError("plan request bound exceeds adapter bound")
        raw = worker.encoded(binding)
        bridge = options["bridge"]
        with self._tx():
            row = self._db.execute("SELECT binding FROM plans WHERE plan_id=?", (plan_id,)).fetchone()
            if row is not None:
                if bytes(row[0]) != raw:
                    raise PlanConflict("plan ID already has different execution bindings")
            else:
                if not self._current(binding, bridge):
                    raise JournalError("current context differs from capture")
                self._db.execute("INSERT INTO plans VALUES (?,?,?,NULL)",
                                 (plan_id, raw, worker.digest(raw)))
        return self.report(plan_id, bridge)

    def _stop(self, plan_id, reason):
        with self._tx():
            self._db.execute("UPDATE plans SET stopped=? WHERE plan_id=? AND stopped IS NULL",
                             (reason, plan_id))

    def _finish(self, plan_id, arm, state, *, reply=None, receipt=None, stop=None):
        raw = None if receipt is None else worker.encoded(receipt)
        with self._tx():
            count = self._db.execute(
                "UPDATE arms SET state=?, reply=?, reply_sha256=?, reply_bytes=?, "
                "receipt=?, receipt_sha256=? WHERE plan_id=? AND arm=? AND state='intent'",
                (state, reply if state == "completed" else None,
                 None if reply is None else worker.digest(reply),
                 None if reply is None else len(reply), raw,
                 None if raw is None else worker.digest(raw), plan_id, arm)).rowcount
            if count != 1:
                raise JournalError("intent no longer open")
            if stop:
                self._db.execute("UPDATE plans SET stopped=? WHERE plan_id=? AND stopped IS NULL",
                                 (stop, plan_id))

    def run(self, plan_id, bridge, adapter, *, live_transport=False, limit=2):
        if type(limit) is not int or not 1 <= limit <= 2:
            raise JournalError("limit must be 1 or 2")
        binding, _, stopped = self._binding(plan_id, bridge)
        if adapter_spec(adapter, live_transport) != binding["adapter"]:
            raise PlanConflict("adapter differs from frozen plan")
        rows = self._rows(binding)
        # Recover BEFORE checking fresh adapter budgets; intent is never resent.
        for arm, row in rows.items():
            if row["state"] == "intent":
                self._finish(plan_id, arm, "unknown", stop="interrupted_" + arm)
                stopped = "interrupted_" + arm
            elif row["state"] != "completed":
                self._stop(plan_id, "terminal_" + arm)
                stopped = stopped or "terminal_" + arm
        if stopped is not None:
            return self.report(plan_id, bridge)
        pending = [a for a in ARMS if a not in rows][:limit]
        if pending and (adapter.stopped or adapter.max_calls - adapter.calls < len(pending)):
            raise JournalError("adapter stopped or remaining budget insufficient")
        for arm in pending:
            if not self._current(binding, bridge):
                self._stop(plan_id, "context_changed_before_" + arm)
                break
            # Full frozen capture is revalidated by the adapter before its call.
            capture_doc = binding["capture_doc"]
            with self._tx():
                if self._db.execute("SELECT stopped FROM plans WHERE plan_id=?",
                                    (plan_id,)).fetchone()[0] is not None:
                    raise JournalError("plan already stopped")
                self._db.execute("INSERT INTO arms (plan_id,arm,state) VALUES (?,?,'intent')",
                                 (plan_id, arm))
            try:
                reply, receipt = adapter.complete(
                    capture_doc, reference=bytes.fromhex(binding["reference"]["hex"]),
                    arm=arm, max_output_bytes=binding["bounds"]["max_reply_bytes_per_arm"])
                if (type(reply) is not bytes or not 1 <= len(reply) <=
                        binding["bounds"]["max_reply_bytes_per_arm"]):
                    raise JournalError("invalid reply")
                safe = receipt_for(binding, arm, reply)
                if type(receipt) is not dict or any(receipt.get(k) != v for k, v in safe.items()):
                    raise JournalError("receipt binding mismatch")
            except BaseException as error:
                self._finish(plan_id, arm, "unknown", stop="unknown_outcome_" + arm)
                if not isinstance(error, Exception):
                    raise
                break
            if not self._current(binding, bridge):
                self._finish(plan_id, arm, "invalidated", reply=reply,
                             stop="context_changed_after_" + arm)
                break
            self._finish(plan_id, arm, "completed", reply=reply, receipt=safe)
        return self.report(plan_id, bridge)

    def report(self, plan_id, bridge):
        binding, digest, stopped = self._binding(plan_id, bridge)
        rows = self._rows(binding)
        current = self._current(binding, bridge)
        arms = {}
        for arm in ARMS:
            row = rows.get(arm)
            state = "not_started" if row is None else row["state"]
            if state == "intent":
                state = "unknown"
                stopped = stopped or "interrupted_" + arm
            show = current and state == "completed"
            arms[arm] = dict(status=state, dispatch_intents=int(row is not None),
                             reply_sha256=None if row is None else row["reply_sha256"],
                             reply_bytes=None if row is None else row["reply_bytes"],
                             reply_body=row["reply"].decode("utf-8") if show else None,
                             receipt=worker.strict_json(row["receipt"]) if show else None)
        states = [arms[a]["status"] for a in ARMS]
        status = ("stopped" if stopped else "invalidated" if not current else
                  "complete" if states == ["completed", "completed"] else "open")
        manifest = binding.get("evaluation_manifest")
        verdict_evaluation = evaluation.evaluate_pair(
            manifest, task_sha256=binding["source"]["task_sha256"],
            issue_number=binding["source"]["issue_number"], arms=arms,
            context_current=current, plan_status=status)
        report = dict(protocol=PROTOCOL, plan_id=plan_id, binding_sha256=digest,
                    plan_status=status, stop_reason=stopped, context_current=current,
                    arms=arms, adapter=binding["adapter"], source=binding["source"],
                    worker=binding["worker"], usage="unavailable", cost="unavailable",
                    verdict=None, evaluator="not_run" if manifest is None else "frozen_fixture_report",
                    verdict_evaluation=verdict_evaluation, semantic_memory_use="not_evaluated",
                    performance_improvement="not_evaluated", adoption="none")
        if binding["capture"]["protocol"] == child.PROBE_OUTPUT_PROTOCOL:
            report.update(execution_kind=binding["execution_kind"],
                          **{key: binding["capture"][key] for key in (
                              "selected_issue_probe", "probe_provenance", "score", "band")})
        return report
