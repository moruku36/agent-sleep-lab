"""Synthetic offline orchestration: retrieve -> journal -> parent checker -> capture.

Connects ``CollectOnlyBridge`` reference retrieval, ``ReferenceUseJournal``,
the ``oss_offline_parent`` checker and capture of the decisions that checker
actually returned. Explicit caller wiring only; no scheduler, network, model,
retry, memory, adoption or verifier/evaluator receipt is created here.

Durability contract (no new database, table or schema version):
- Every setting that decides what runs and how its result is captured is
  frozen into one canonical *contract*. Its SHA-256 is the journal consumer
  version, so the existing journal binding ties the contract to the use ID
  before any dispatch. A reopen with a changed timestamp, authorization,
  identity, cap, repository path or worker launch is refused, never remapped.
- The consumer output saved by the journal carries the whole contract, the
  checker summary and the returned decisions, hash-bound, before any capture.
- Capture reads decisions and capture metadata only from that saved output.
  It never calls the checker, so recovery after an interruption replays
  capture through the store's existing byte-identical replay.

Limits callers must not overstate: the receipt is unreviewed self-report,
``delivery_and_use_verified`` is always False, an injected worker argv is a
stand-in, and nothing here shows that reference bytes influenced a decision.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab.oss_bridge import CollectOnlyBridge
from agent_sleep_lab.provenance import canonical_json, sha256_hex
from agent_sleep_lab.reference_use import ReferenceUseJournal
from agent_sleep_lab.strictjson import loads_strict_bytes

PIPELINE_ID = "oss-offline-pipeline"
CONTRACT_PROTOCOL = "agent-sleep-oss-offline-pipeline-contract/1"
OUTPUT_PROTOCOL = "agent-sleep-oss-offline-pipeline-output/1"
RECEIPT_LABEL = "unreviewed_consumer_self_report"
MAX_DECISIONS = 64
_AUTHORIZATION_KEYS = frozenset({"ref", "revision", "purpose", "retention", "expires_at"})
_OUTPUT_KEYS = frozenset({
    "protocol", "synthetic_only", "contract", "contract_sha256", "check", "decisions",
    "decisions_sha256", "receipt", "semantic_memory_use", "performance_improvement",
    "delivery_and_use_verified"})


def _text(value, limit, label):
    if (type(value) is not str or not value.strip() or len(value) > limit
            or not value.isprintable()):
        raise ValueError("bounded printable " + label + " required")
    return value


def _plain(value, label):
    try:
        return loads_strict_bytes(canonical_json(value))
    except (TypeError, ValueError, RecursionError):
        raise ValueError(label + " must be plain JSON data") from None


class OfflinePipeline:
    """One use ID, at most one checker dispatch, replayable decision capture."""

    def __init__(self, journal, bridge, *, use_id, repo, query, max_bytes,
                 session_id, observed_at, captured_at, authorization,
                 max_records=16, git=None, worker_argv=None,
                 timeout=parent.WORKER_TIMEOUT):
        if not isinstance(journal, ReferenceUseJournal):
            raise TypeError("explicit ReferenceUseJournal required")
        if not isinstance(bridge, CollectOnlyBridge):
            raise TypeError("explicit CollectOnlyBridge required")
        task = worker.synthetic_task()
        # The bridge stamps its repository/commit onto captured observations,
        # so both must be the ones the built-in pinned task actually runs.
        if (bridge.repository != task["repository"]
                or bridge.agent_commit != task["agent_commit"]):
            raise ValueError("bridge repository/agent commit differ from the pinned task")
        if type(use_id) is not str or not 1 <= len(use_id) <= 96:
            raise ValueError("bounded reference use identity required")
        if type(max_bytes) is not int or not 1 <= max_bytes <= worker.MAX_REFERENCE_BYTES:
            raise ValueError("reference byte cap exceeds the offline worker cap")
        if type(max_records) is not int or not 1 <= max_records <= worker.MAX_REFERENCE_RECORDS:
            raise ValueError("reference record cap exceeds the offline worker cap")
        if not isinstance(repo, (str, Path)) or not os.path.isabs(str(repo)):
            raise ValueError("explicit absolute local repository path required")
        if git is not None and (type(git) is not str or not os.path.isabs(git)):
            raise ValueError("absolute git executable required")
        if worker_argv is not None and (
                type(worker_argv) is not list or not worker_argv
                or any(type(item) is not str for item in worker_argv)
                or not os.path.isabs(worker_argv[0])):
            raise ValueError("explicit absolute stand-in argv required")
        if (type(timeout) not in (int, float) or not math.isfinite(timeout)
                or not 0 < timeout <= parent.WORKER_TIMEOUT):
            raise ValueError("worker timeout out of range")
        if type(authorization) is not dict or set(authorization) != _AUTHORIZATION_KEYS:
            raise ValueError("exact capture authorization fields required")
        self.journal, self.bridge = journal, bridge
        self._repo = os.path.realpath(str(repo))
        self._git, self._timeout = git, timeout
        self._argv = None if worker_argv is None else list(worker_argv)
        self.contract = dict(
            protocol=CONTRACT_PROTOCOL, synthetic_only=True, use_id=use_id,
            bridge=dict(scope=dict(bridge.scope), repository=bridge.repository,
                        agent_commit=bridge.agent_commit),
            task_sha256=sha256_hex(parent.builtin_task()),
            source_pins_sha256=sha256_hex(canonical_json(dict(worker.SOURCE_HASHES))),
            retrieval=dict(query=_text(query, 1024, "retrieval query"),
                           max_bytes=max_bytes, max_records=max_records),
            checker=dict(
                id=parent.CONSUMER_ID, version=parent.CONSUMER_VERSION,
                repository_path=self._repo, git=git, timeout=timeout,
                worker_launch=(parent.BUILTIN_WORKER if worker_argv is None
                               else parent.STAND_IN_WORKER),
                worker_argv_sha256=(None if worker_argv is None
                                    else sha256_hex(canonical_json(self._argv)))),
            capture=dict(
                session_id=_text(session_id, 128, "session identity"),
                observed_at=_text(observed_at, 64, "observed_at"),
                captured_at=_text(captured_at, 64, "captured_at"),
                authorization=_plain(authorization, "capture authorization"),
                event_ids="<use_id>.dNNN in returned decision order"),
            receipt=RECEIPT_LABEL, delivery_and_use_verified=False)
        self.contract_sha256 = sha256_hex(canonical_json(self.contract))
        # Bound into the journal's frozen config; also rejects a wrong contract
        # at prepare and dispatch through the journal's own identity checks.
        self.version = "1." + self.contract_sha256

    # ------------------------------------------------------------------ dispatch

    def _preflight_reference(self):
        """Refuse an unusable reference before any journal row or dispatch exists."""
        retrieval = self.contract["retrieval"]
        bundle = self.bridge.reference_context(**retrieval)
        doc = worker.validate_reference(bundle.bundle_bytes)
        if worker.encoded(doc) != bundle.bundle_bytes:
            raise ValueError("canonical ASCII reference bundle bytes required by the worker")

    def _consumer(self, *, use_id, task_bytes, reference_bytes):
        if use_id != self.contract["use_id"] or task_bytes != parent.builtin_task():
            raise parent.CheckError("request differs from the frozen pipeline contract")
        if type(reference_bytes) is not bytes or len(reference_bytes) > worker.MAX_REFERENCE_BYTES:
            raise parent.CheckError("reference byte cap exceeded")
        summary, doc = parent.check(self._repo, reference_bytes, git=self._git,
                                    worker_argv=self._argv, timeout=self._timeout)
        decisions = doc["decisions"] if type(doc) is dict else None
        if (type(summary) is not dict or type(decisions) is not list
                or len(decisions) > MAX_DECISIONS
                or any(type(item) is not dict for item in decisions)):
            raise parent.CheckError("bounded checker decisions required")
        if (summary.get("protocol") != parent.CHECK_PROTOCOL
                or summary.get("worker_launch") != self.contract["checker"]["worker_launch"]
                or summary.get("task_sha256") != sha256_hex(task_bytes)
                or summary.get("reference_sha256") != sha256_hex(reference_bytes)
                or summary.get("decisions") != len(decisions)
                or summary.get("delivery_and_use_verified") is not False
                or summary.get("semantic_memory_use") != "not_evaluated"
                or summary.get("performance_improvement") != "not_evaluated"):
            raise parent.CheckError("checker summary differs from the frozen request")
        try:
            output = canonical_json(dict(
                protocol=OUTPUT_PROTOCOL, synthetic_only=True, contract=self.contract,
                contract_sha256=self.contract_sha256, check=summary, decisions=decisions,
                decisions_sha256=sha256_hex(canonical_json(decisions)),
                receipt=RECEIPT_LABEL, semantic_memory_use="not_evaluated",
                performance_improvement="not_evaluated", delivery_and_use_verified=False))
        except (TypeError, ValueError, RecursionError):
            raise parent.CheckError("checker output must be plain JSON data") from None
        # Never truncated: an oversized result stays an unknown outcome.
        if len(output) > parent.MAX_RECEIPT_BYTES:
            raise parent.CheckError("consumer receipt output cap exceeded")
        return dict(use_id=use_id, task_sha256=sha256_hex(task_bytes),
                    reference_sha256=sha256_hex(reference_bytes), output_bytes=output)

    def _identity(self):
        return dict(consumer_id=PIPELINE_ID, consumer_version=self.version)

    def run(self):
        """Prepare, dispatch at most once, then capture or replay saved decisions.

        Safe to call again after any interruption: an existing use is never
        refreshed or re-dispatched, and only saved output is captured.
        """
        use_id, retrieval = self.contract["use_id"], self.contract["retrieval"]
        try:
            self.journal.status(use_id)
        except ValueError as error:
            if str(error) != "unknown reference use":
                raise
            self._preflight_reference()
        self.journal.prepare(use_id, self.bridge, task_bytes=parent.builtin_task(),
                             query=retrieval["query"], max_bytes=retrieval["max_bytes"],
                             max_records=retrieval["max_records"], **self._identity())
        self.journal.dispatch(use_id, self.bridge, self._consumer, **self._identity())
        return self.capture()

    # ------------------------------------------------------------------- capture

    def _saved_output(self, status):
        raw = bytes.fromhex(status["output_hex"])
        doc = loads_strict_bytes(raw)
        if (type(doc) is not dict or set(doc) != _OUTPUT_KEYS or canonical_json(doc) != raw
                or doc["protocol"] != OUTPUT_PROTOCOL or doc["synthetic_only"] is not True
                or doc["contract"] != self.contract
                or doc["contract_sha256"] != self.contract_sha256
                or type(doc["decisions"]) is not list or len(doc["decisions"]) > MAX_DECISIONS
                or any(type(item) is not dict for item in doc["decisions"])
                or doc["decisions_sha256"] != sha256_hex(canonical_json(doc["decisions"]))
                or type(doc["check"]) is not dict
                or doc["check"].get("decisions") != len(doc["decisions"])
                or doc["receipt"] != RECEIPT_LABEL
                or doc["delivery_and_use_verified"] is not False):
            raise ValueError("saved pipeline output does not match its frozen contract")
        return doc

    def capture(self):
        """Capture the saved decisions; never runs the checker.

        Only ``received_unreviewed`` uses whose reference context is still
        current are captured. The store's capture boundary checks the frozen
        authorization against its current configuration on every call,
        including byte-identical replays.
        """
        use_id = self.contract["use_id"]
        status = self.journal.status(use_id)
        if status["consumer"] != dict(id=PIPELINE_ID, version=self.version):
            raise ValueError("pipeline contract differs from the frozen binding")
        report = dict(
            use_id=use_id, status=status["status"], reason=status["reason"],
            dispatches=status["dispatches"], contract_sha256=self.contract_sha256,
            output_sha256=status.get("output_sha256"),
            worker_launch=self.contract["checker"]["worker_launch"],
            receipt=RECEIPT_LABEL, capture="not_captured", capture_reason=None, events=[],
            semantic_memory_use="not_evaluated", performance_improvement="not_evaluated",
            delivery_and_use_verified=False)
        if status["status"] != "received_unreviewed":
            report["capture_reason"] = "journal_status_" + status["status"]
            return report
        saved = self._saved_output(status)
        if not self.journal.context_unchanged(use_id, self.bridge):
            report["capture_reason"] = "reference_context_changed_or_unavailable"
            return report
        frozen = saved["contract"]["capture"]  # durable copy, not live arguments
        for index, decision in enumerate(saved["decisions"], 1):
            # Capture is not one cross-database transaction: stop the remaining
            # batch if policy/context changed after an earlier observation.
            if not self.journal.context_unchanged(use_id, self.bridge):
                report["capture"] = ("partial_unverified_observations"
                                     if report["events"] else "not_captured")
                report["capture_reason"] = "reference_context_changed_during_capture"
                return report
            event_id = "%s.d%03d" % (use_id, index)
            result = self.bridge.capture_decision(
                decision, event_id=event_id, session_id=frozen["session_id"],
                observed_at=frozen["observed_at"], captured_at=frozen["captured_at"],
                authorization=dict(frozen["authorization"]), synthetic=True)
            report["events"].append(dict(event_id=event_id, status=result.status))
        if not self.journal.context_unchanged(use_id, self.bridge):
            report["capture"] = "partial_unverified_observations"
            report["capture_reason"] = "reference_context_changed_during_capture"
            return report
        report["capture"] = "captured_unverified_observations"
        return report
