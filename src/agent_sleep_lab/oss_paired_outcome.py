"""Durable OFFLINE paired-outcome journal over actual OSS prompt-capture artifacts.

Consumes the capture document produced by ``oss_prompt_capture.prepare*`` (the
two request bodies the pinned ``OpenAITriager.judge`` path built) and journals
one FAKE dispatch per arm in a private SQLite database of its own. No existing
schema is touched or migrated and ``ComparisonStore`` formats are unchanged.

FAKE ONLY. The single provider seam is ``FakeReplyProvider``, which returns
test-authored synthetic bytes. There is no live provider, CLI, credential or
network support here. Every reply is labelled synthetic; usage and cost are
reported as *unavailable*, never as zero. Nothing in this module is a model
receipt, a verdict, an evaluation, an adoption, a saving or performance
evidence.

Not claimed: store-origin authentication (the bridge's store is
caller-controlled), authentication of the caller-supplied prepare summary or
its worker-launch label, a cross-database transaction with the evidence store,
or multi-process safety beyond SQLite ``BEGIN IMMEDIATE``. Byte caps are checked
AFTER a reply is returned; they are not token or monetary limits.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import re
import sqlite3

from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_prompt_capture as capture
from agent_sleep_lab import oss_prompt_capture_worker as child
from agent_sleep_lab.oss_bridge import CollectOnlyBridge
from agent_sleep_lab.provenance import canonical_json, sha256_hex

PROTOCOL = "agent-sleep-oss-paired-outcome/1"
ARMS = ("baseline", "reference")
MAX_REQUEST_BYTES = 131072
MAX_REPLY_BYTES = 65536
CALLS_PER_ARM = 1
PROVIDER_CLASS = "fake_test_authored_provider_no_network_no_credentials"
REPLY_KIND = "synthetic_test_authored_reply_not_a_model_receipt_or_verdict"
UNAVAILABLE = "unavailable_fake_provider_nothing_measured"
BOUND_KIND = "post_output_utf8_byte_caps_not_token_or_monetary_limits"
SUMMARY_ORIGIN = "caller_supplied_prepare_summary_unauthenticated"
STORE_ORIGIN = "caller_controlled_store_unauthenticated"
CheckError = capture.CheckError
_TABLES = {"plans", "arms"}
_SCHEMA = 1
_APPLICATION_ID = 0x41534C50


class JournalError(Exception):
    """The journal refused an operation; nothing was dispatched by the refusal."""


class PlanConflict(JournalError):
    """A plan ID was reused with a different binding or bridge identity."""


class FakeReplyProvider:
    """The ONLY provider seam: returns test-authored synthetic reply bytes.

    ``reply`` is a test-authored callable ``(arm, request_bytes) -> bytes``.
    The journal accepts exactly this class (subclasses are refused), so no
    provider adapter is accidentally substituted. The callable is trusted local
    fixture code; this type check is not a sandbox. Replies are fixture data:
    never a model receipt, verdict, usage record or cost.
    """

    label = PROVIDER_CLASS

    def __init__(self, reply):
        if not callable(reply):
            raise TypeError("test-authored reply callable required")
        self._reply = reply
        self.calls = 0

    def complete(self, arm, request):
        self.calls += 1
        return self._reply(arm, request)


def _context_hash(document):
    # as_of is a read timestamp, not a policy/evidence/record change.
    value = dict(document)
    value.pop("as_of", None)
    return sha256_hex(canonical_json(value))


def _bridge_identity(bridge):
    if not isinstance(bridge, CollectOnlyBridge):
        raise TypeError("explicit CollectOnlyBridge required")
    return dict(scope=dict(bridge.scope), repository=bridge.repository,
                agent_commit=bridge.agent_commit, store_origin=STORE_ORIGIN)


def _current_context(bridge, retrieval):
    """Explicit current-policy retrieval; the artifact is never the authority."""
    bundle = bridge.reference_context(query=retrieval["query"],
                                      max_bytes=retrieval["max_bytes"],
                                      max_records=retrieval["max_records"])
    return _context_hash(worker.strict_json(bundle.bundle_bytes))


def _cap(value, limit, name):
    if type(value) is not int or not 1 <= value <= limit:
        raise JournalError("%s must be an integer in 1..%d" % (name, limit))
    return value


def build_binding(plan_id, *, summary, capture_doc, reference, bridge, query,
                  max_bytes, max_records, max_request_bytes, max_reply_bytes):
    """Validate the capture artifact and freeze everything a dispatch depends on.

    Pure: no store write, no provider call. The capture document is checked by
    ``oss_prompt_capture.validate_output`` against the exact reference bytes.
    """
    if type(plan_id) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", plan_id):
        raise JournalError("bounded plan ID required")
    identity = _bridge_identity(bridge)
    if (bridge.repository != worker.REPOSITORY or bridge.agent_commit != worker.AGENT_COMMIT):
        raise CheckError("bridge repository/agent commit differ from the pinned task")
    if type(query) is not str or not query.strip() or len(query) > 1024:
        raise CheckError("explicit bounded retrieval query required")
    _cap(max_bytes, worker.MAX_REFERENCE_BYTES, "max_bytes")
    _cap(max_records, worker.MAX_REFERENCE_RECORDS, "max_records")
    _cap(max_request_bytes, MAX_REQUEST_BYTES, "max_request_bytes")
    _cap(max_reply_bytes, MAX_REPLY_BYTES, "max_reply_bytes")
    if type(reference) is not bytes or not 1 <= len(reference) <= max_bytes:
        raise CheckError("original reference bytes within the declared cap required")
    try:
        raw = worker.encoded(capture_doc)
    except (TypeError, ValueError, RecursionError):
        raise CheckError("capture document must be plain JSON data") from None
    doc = capture.validate_output(raw, task=parent.builtin_task(), reference=reference,
        selected_issue_probe=(capture_doc.get("selected_issue_probe")
                              if type(capture_doc) is dict else None))
    probe = child.probe_metadata(doc)
    capture_sha256 = worker.digest(raw)
    if type(summary) is not dict:
        raise CheckError("prepare summary dictionary required")
    launch = summary.get("worker_launch")
    if launch == capture.BUILTIN_WORKER:
        integration = ("forced_selected_issue_probe_not_normal_target_execution_unauthenticated_label"
                       if probe else "builtin_pinned_worker_label_from_unauthenticated_summary")
        hashes = summary.get("worker_sha256")
        if (type(hashes) is not dict or set(hashes) != {"capture", "base"}
                or any(type(v) is not str or not re.fullmatch(r"[0-9a-f]{64}", v)
                       for v in hashes.values())):
            raise CheckError("builtin worker label requires both worker hashes")
    elif launch == capture.STAND_IN_WORKER:
        integration, hashes = "stand_in_worker_not_target_integration", None
        if summary.get("worker_sha256") is not None:
            raise CheckError("stand-in worker must not carry builtin worker hashes")
    else:
        raise CheckError("unknown worker launch label")
    if (summary.get("protocol") != (capture.PROBE_CHECK_PROTOCOL if probe else capture.CHECK_PROTOCOL)
            or summary.get("worker_output_sha256") != capture_sha256
            or summary.get("agent_commit") != doc["agent_commit"]
            or summary.get("source_sha256") != doc["executed_source_sha256"]
            or summary.get("task_sha256") != doc["task_sha256"]
            or summary.get("reference_sha256") != doc["reference_sha256"]
            or summary.get("reference_records") != doc["reference_records"]):
        raise CheckError("prepare summary does not match the capture document")
    if probe:
        if any(worker.encoded(summary.get(key)) != worker.encoded(value)
               for key, value in probe.items()):
            raise CheckError("prepare summary selected-probe binding mismatch")
    elif any(key in summary for key in ("selected_issue_probe", "probe_provenance")):
        raise CheckError("v1 summary must not carry selected-probe fields")
    if summary.get("reference_origin") != capture.ORIGIN_BRIDGE:
        raise CheckError("capture must come from explicit bridge retrieval")
    if (summary.get("dispatch_authorization") is not False
            or summary.get("model_receipt") is not None or summary.get("verdict") is not None
            or summary.get("semantic_memory_use") != "not_evaluated"
            or summary.get("performance_improvement") != "not_evaluated"
            or summary.get("delivery_and_use_verified") is not False):
        raise CheckError("prepare summary must keep its no-verdict labels")
    arms = {}
    for name in ARMS:
        arm = doc["arms"][name]
        request = worker.encoded(dict(url=arm["url"], header_names=arm["header_names"],
                                      payload=arm["payload"]))
        if worker.digest(request) != arm["request_sha256"]:
            raise CheckError("captured request hash mismatch: " + name)
        if len(request) > max_request_bytes:
            raise JournalError("captured %s request exceeds the per-arm byte bound" % name)
        arms[name] = dict(request_hex=request.hex(), request_sha256=arm["request_sha256"],
                          request_bytes=len(request), prompt_sha256=arm["prompt_sha256"],
                          prompt_bytes=arm["prompt_bytes"])
    binding = dict(
        protocol=PROTOCOL, plan_id=plan_id, synthetic_only=True,
        capture=dict(document_sha256=capture_sha256, artifact_kind=doc["artifact_kind"],
                     protocol=doc["protocol"], dispatch_authorization=False,
                     model_receipt=None, verdict=None, semantic_memory_use="not_evaluated",
                     performance_improvement="not_evaluated",
                     comparability=doc["comparability"], model=doc["model"],
                     model_identity=doc["model_identity"]),
        source=dict(agent_repository=parent.AGENT_REPOSITORY, agent_commit=doc["agent_commit"],
                    source_sha256=doc["executed_source_sha256"],
                    task_sha256=doc["task_sha256"], issue_number=doc["issue"]["number"]),
        worker=dict(launch=launch, sha256=hashes, target_integration=integration,
                    label_origin=SUMMARY_ORIGIN),
        reference=dict(hex=reference.hex(), sha256=doc["reference_sha256"],
                       records=doc["reference_records"], bytes=len(reference),
                       context_sha256=_context_hash(worker.strict_json(reference)),
                       origin=capture.ORIGIN_BRIDGE,
                       role="untrusted_reference_data_not_operating_authority"),
        retrieval=dict(query=query, max_bytes=max_bytes, max_records=max_records,
                       declared_by="caller", context_rule="equal_ignoring_only_as_of"),
        bridge=identity, arms=arms,
        bounds=dict(max_request_bytes_per_arm=max_request_bytes,
                    max_reply_bytes_per_arm=max_reply_bytes,
                    max_calls_per_arm=CALLS_PER_ARM, kind=BOUND_KIND),
        provider=dict(provider_class=PROVIDER_CLASS, reply_kind=REPLY_KIND,
                      live_provider_support=False))
    binding["capture"].update(probe)
    return binding


class PairedOutcomeJournal:
    """Private SQLite journal: intent before dispatch, reply before the next arm.

    One process is assumed to drive a plan at a time. An arm whose intent was
    committed without a recorded outcome is ``unknown`` and is never dispatched
    again; it stops the remaining arms of that plan permanently.
    """

    def __init__(self, path):
        if not isinstance(path, (str, Path)) or not os.path.isabs(str(path)):
            raise JournalError("explicit absolute journal path required")
        os.close(os.open(str(path), os.O_RDWR | os.O_CREAT, 0o600))
        self._db = sqlite3.connect(str(path), isolation_level=None)
        try:
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA fullfsync=ON")
            application_id = self._db.execute("PRAGMA application_id").fetchone()[0]
            version = self._db.execute("PRAGMA user_version").fetchone()[0]
            tables = {row[0] for row in self._db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            objects = self._db.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0]
            if (application_id, version, objects) == (0, 0, 0):
                with self._tx():
                    self._db.execute(
                        "CREATE TABLE plans (plan_id TEXT PRIMARY KEY, binding BLOB NOT NULL,"
                        " binding_sha256 TEXT NOT NULL, stopped TEXT)")
                    self._db.execute(
                        "CREATE TABLE arms (plan_id TEXT NOT NULL, arm TEXT NOT NULL,"
                        " state TEXT NOT NULL, request_sha256 TEXT NOT NULL, reply BLOB,"
                        " reply_sha256 TEXT, reply_bytes INTEGER, detail TEXT,"
                        " PRIMARY KEY (plan_id, arm))")
                    self._db.execute("PRAGMA user_version=%d" % _SCHEMA)
                    self._db.execute("PRAGMA application_id=%d" % _APPLICATION_ID)
            elif (application_id != _APPLICATION_ID or version != _SCHEMA
                  or tables != _TABLES):
                raise JournalError("not a paired-outcome journal database; no migration exists")
        except BaseException:
            self._db.close()
            raise

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

    # -- reads -----------------------------------------------------------------

    def _binding(self, plan_id, bridge):
        identity = _bridge_identity(bridge)
        row = self._db.execute("SELECT binding, binding_sha256 FROM plans WHERE plan_id=?",
                               (plan_id,)).fetchone()
        if row is None:
            raise JournalError("unknown plan ID")
        raw = bytes(row[0])
        if worker.digest(raw) != row[1]:
            raise JournalError("stored binding hash mismatch")
        binding = worker.strict_json(raw)
        if binding["bridge"] != identity:
            raise PlanConflict("bridge identity differs from the frozen plan binding")
        return binding, row[1]

    def _state(self, plan_id):
        stopped = self._db.execute("SELECT stopped FROM plans WHERE plan_id=?",
                                   (plan_id,)).fetchone()[0]
        rows = {row[0]: dict(state=row[1], request_sha256=row[2],
                             reply=None if row[3] is None else bytes(row[3]),
                             reply_sha256=row[4], reply_bytes=row[5], detail=row[6])
                for row in self._db.execute(
                    "SELECT arm, state, request_sha256, reply, reply_sha256, reply_bytes,"
                    " detail FROM arms WHERE plan_id=?", (plan_id,))}
        for arm, row in rows.items():
            if row["state"] == "completed":
                reply = row["reply"]
                if (type(reply) is not bytes or worker.digest(reply) != row["reply_sha256"]
                        or len(reply) != row["reply_bytes"]):
                    raise JournalError("stored reply integrity mismatch: " + arm)
        return stopped, rows

    # -- writes ----------------------------------------------------------------

    def _stop(self, plan_id, reason):
        with self._tx():
            self._db.execute("UPDATE plans SET stopped=? WHERE plan_id=? AND stopped IS NULL",
                             (reason, plan_id))

    def _finish(self, plan_id, arm, state, *, reply=None, sha256=None, size=None,
                detail=None, stop=None):
        with self._tx():
            done = self._db.execute(
                "UPDATE arms SET state=?, reply=?, reply_sha256=?, reply_bytes=?, detail=?"
                " WHERE plan_id=? AND arm=? AND state='intent'",
                (state, reply, sha256, size, detail, plan_id, arm)).rowcount
            if done != 1:
                raise JournalError("arm outcome already recorded")
            if stop is not None:
                self._db.execute(
                    "UPDATE plans SET stopped=? WHERE plan_id=? AND stopped IS NULL",
                    (stop, plan_id))

    def _recover(self, plan_id):
        """An intent without an outcome is an interruption: unknown, stop forever."""
        _, rows = self._state(plan_id)
        for arm in ARMS:
            if arm in rows and rows[arm]["state"] == "intent":
                self._finish(plan_id, arm, "unknown",
                             detail="intent_committed_outcome_never_recorded",
                             stop="interrupted_" + arm)

    def register(self, plan_id, *, summary, capture_doc, reference, bridge, query,
                 max_bytes, max_request_bytes, max_reply_bytes, max_records=16):
        """Freeze a plan. Same ID + identical binding replays; any change conflicts."""
        binding = build_binding(
            plan_id, summary=summary, capture_doc=capture_doc, reference=reference,
            bridge=bridge, query=query, max_bytes=max_bytes, max_records=max_records,
            max_request_bytes=max_request_bytes, max_reply_bytes=max_reply_bytes)
        raw = worker.encoded(binding)
        row = self._db.execute("SELECT binding FROM plans WHERE plan_id=?",
                               (plan_id,)).fetchone()
        if row is not None:
            if bytes(row[0]) != raw:
                raise PlanConflict("plan ID already bound to a different frozen binding")
            return self.report(plan_id, bridge)
        # Current policy, not the artifact, decides whether this context may be used.
        if _current_context(bridge, binding["retrieval"]) != binding["reference"]["context_sha256"]:
            raise JournalError("current retrieval differs from the captured reference context")
        try:
            with self._tx():
                self._db.execute(
                    "INSERT INTO plans (plan_id, binding, binding_sha256, stopped)"
                    " VALUES (?, ?, ?, NULL)", (plan_id, raw, worker.digest(raw)))
        except sqlite3.IntegrityError:
            raise PlanConflict("plan ID was registered concurrently") from None
        return self.report(plan_id, bridge)

    def run(self, plan_id, bridge, provider, *, limit=None):
        """Dispatch at most ``limit`` not-yet-started arms through the fake seam.

        Saved replies are replayed, never re-dispatched. No automatic retry:
        an exception or interruption leaves the arm ``unknown`` and stops the
        plan permanently. Non-``Exception`` interruptions are re-raised after
        the stop is recorded.
        """
        if type(provider) is not FakeReplyProvider:
            raise TypeError("only FakeReplyProvider is supported; no live provider seam exists")
        if limit is not None and (type(limit) is not int or limit < 1):
            raise JournalError("limit must be a positive integer or None")
        binding, _ = self._binding(plan_id, bridge)
        frozen = binding["reference"]["context_sha256"]
        cap = binding["bounds"]["max_reply_bytes_per_arm"]
        self._recover(plan_id)
        dispatched = 0
        for arm in ARMS:
            stopped, rows = self._state(plan_id)
            if stopped is not None:
                break
            if arm in rows:
                continue  # completed and saved; every other state stops the plan
            if limit is not None and dispatched >= limit:
                break
            try:
                unchanged = _current_context(bridge, binding["retrieval"]) == frozen
            except Exception:
                unchanged = False
            if not unchanged:
                self._stop(plan_id, "context_changed_before_" + arm)
                break
            request = bytes.fromhex(binding["arms"][arm]["request_hex"])
            if (worker.digest(request) != binding["arms"][arm]["request_sha256"]
                    or len(request) > binding["bounds"]["max_request_bytes_per_arm"]):
                self._stop(plan_id, "frozen_request_mismatch_" + arm)
                break
            with self._tx():  # durable intent BEFORE the one fake dispatch
                state = self._db.execute("SELECT stopped FROM plans WHERE plan_id=?",
                                         (plan_id,)).fetchone()[0]
                if state is not None:
                    raise JournalError("plan stopped concurrently")
                self._db.execute(
                    "INSERT INTO arms (plan_id, arm, state, request_sha256)"
                    " VALUES (?, ?, 'intent', ?)",
                    (plan_id, arm, binding["arms"][arm]["request_sha256"]))
            dispatched += 1
            try:
                reply = provider.complete(arm, request)
            except BaseException as error:
                self._finish(plan_id, arm, "unknown",
                             detail="fake_provider_raised_" + type(error).__name__,
                             stop="unknown_outcome_" + arm)
                if not isinstance(error, Exception):
                    raise
                break
            if type(reply) is not bytes:
                self._finish(plan_id, arm, "invalid", detail="reply_not_bytes",
                             stop="invalid_reply_" + arm)
                break
            sha256, size, detail = worker.digest(reply), len(reply), None
            if not 1 <= size <= cap:
                detail = "reply_outside_post_output_byte_cap"
            else:
                try:
                    reply.decode("utf-8")
                except UnicodeDecodeError:
                    detail = "reply_not_utf8"
            if detail is not None:  # status and hash only; the body is not stored
                self._finish(plan_id, arm, "invalid", sha256=sha256, size=size,
                             detail=detail, stop="invalid_reply_" + arm)
                break
            try:
                unchanged = _current_context(bridge, binding["retrieval"]) == frozen
                detail = None if unchanged else "context_changed_after_reply"
            except Exception:
                unchanged, detail = False, "context_recheck_failed_after_reply"
            if not unchanged:  # revoked context: never persist the stale body
                self._finish(plan_id, arm, "invalidated", sha256=sha256, size=size,
                             detail=detail, stop="context_changed_after_" + arm)
                break
            self._finish(plan_id, arm, "completed", reply=reply, sha256=sha256, size=size)
        return self.report(plan_id, bridge)

    def report(self, plan_id, bridge):
        """Read-only summary. Reply bodies are withheld unless the context still holds."""
        binding, binding_sha256 = self._binding(plan_id, bridge)
        try:
            current = (_current_context(bridge, binding["retrieval"])
                       == binding["reference"]["context_sha256"])
        except Exception:
            current = False
        stopped, rows = self._state(plan_id)
        for arm in ARMS:  # not yet durably recovered; reported, not written, here
            if stopped is None and arm in rows and rows[arm]["state"] == "intent":
                stopped = "interrupted_" + arm
        arms = {}
        for arm in ARMS:
            row = rows.get(arm)
            if row is None:
                status = "not_started" if stopped is None else "missing"
            else:
                status = "unknown" if row["state"] == "intent" else row["state"]
            body, export = None, "no_reply_body_recorded"
            if status == "completed":
                if current:
                    body, export = row["reply"].decode("utf-8"), "exported_context_rechecked"
                else:
                    export = "withheld_context_changed_hash_and_status_only"
            arms[arm] = dict(
                status=status, fake_dispatches=0 if row is None else 1,
                detail=None if row is None else row["detail"],
                request_sha256=binding["arms"][arm]["request_sha256"],
                request_bytes=binding["arms"][arm]["request_bytes"],
                reply_sha256=None if row is None else row["reply_sha256"],
                reply_bytes=None if row is None else row["reply_bytes"],
                reply_body=body, reply_export=export, reply_kind=REPLY_KIND,
                usage=UNAVAILABLE, cost=UNAVAILABLE, model_receipt=None, verdict=None)
        states = [arms[arm]["status"] for arm in ARMS]
        if not current and stopped is None:
            plan_status, pair = "invalidated", "context_changed_or_unverifiable"
        elif states == ["completed", "completed"]:
            plan_status, pair = "complete", "both_arms_completed_synthetic_replies"
        elif stopped is not None:
            plan_status, pair = "stopped", "incomplete_stopped_no_retry"
        else:
            plan_status, pair = "open", "incomplete_open"
        report = dict(
            protocol=PROTOCOL, plan_id=plan_id, synthetic_only=True,
            plan_status=plan_status, stop_reason=stopped, pair_outcome=pair,
            arm_statuses=dict(zip(ARMS, states)),
            context="unchanged_ignoring_as_of" if current else "changed_or_unverifiable",
            binding_sha256=binding_sha256,
            capture_document_sha256=binding["capture"]["document_sha256"],
            source=binding["source"], worker=binding["worker"],
            reference=dict(sha256=binding["reference"]["sha256"],
                           records=binding["reference"]["records"],
                           origin=binding["reference"]["origin"], store_origin=STORE_ORIGIN),
            retrieval=binding["retrieval"], bridge=binding["bridge"],
            bounds=binding["bounds"], arms=arms,
            provider_class=PROVIDER_CLASS, live_provider_support=False,
            usage=UNAVAILABLE, cost=UNAVAILABLE, savings="not_measured",
            model_receipt=None, verdict=None, evaluator="not_run", adoption="none",
            semantic_memory_use="not_evaluated", performance_improvement="not_evaluated",
            delivery_and_use_verified=False)
        if binding["capture"]["protocol"] == child.PROBE_OUTPUT_PROTOCOL:
            report.update(child.probe_metadata(binding["capture"]))
        return report

    def frozen(self, plan_id, bridge):
        """Exact frozen bytes: both request payloads and the original reference."""
        binding, _ = self._binding(plan_id, bridge)
        return dict(reference=bytes.fromhex(binding["reference"]["hex"]),
                    requests={arm: bytes.fromhex(binding["arms"][arm]["request_hex"])
                              for arm in ARMS})
