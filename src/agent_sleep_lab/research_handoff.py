"""Gate 4E: MANUAL research-notes request/result handoff journal. Draft exchange only.

Preparation for one existing-agent integration, not live delivery and not a
model-performance experiment. One frozen ``RawBaselineComparison`` plan arm becomes
a bounded JSON request envelope for one fixed target repository commit; an
untrusted bilingual draft may later be imported as ``received_unreviewed``.

This module writes only its private SQLite journal, never draft files. It never
calls an agent, a network or a model, edits the target repository, or creates comparison replies, scores, adoption receipts
or captured evidence, and never parses or follows instructions inside a draft.
Returning packet bytes from ``claim`` is NOT delivery, reading or use. A missing
result stays unknown: no retries, timers or resends. The caller keeps every
publication and execution control. Template headings below are data used for a
mechanical check only, not permission and not a quality assessment.

Limits (documented, not solved): local construction is not authentication; the
journal and the comparison store are separate SQLite files with no shared
transaction; a live recheck can be overtaken before the caller uses the bytes;
a comparison run started after preparation is only noticed at the next recheck.
"""
from __future__ import annotations

import re
import sqlite3

from agent_sleep_lab.ab_comparison import _encode
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.raw_baseline import RawBaselineComparison
from agent_sleep_lab.strictjson import loads_strict_bytes

PROTOCOL = "agent-sleep-research-handoff/1"
MAX_ENVELOPE_BYTES = 262144
MAX_RESPONSE_BYTES = 131072
MAX_OUTPUT_BYTES = 49152
STATUSES = ("prepared", "export_intent_outcome_unknown", "received_unreviewed", "invalidated")
TEMPLATE = {
    "en": {"headings": ["## Overview", "## Record fields",
                        "## Practical reading (required for future notes)"],
           "labels": ["What it is", "What it says", "Caveat"]},
    "ja": {"headings": ["## 概要", "## 記録項目", "## 実務向けの読み解き（今後の必須項目）"],
           "labels": ["何についてのものか", "何を述べているか", "留意点"]},
}
STRUCTURE_LIMITS = ("mechanical heading/label/line-count check only; not a semantic, "
                    "quality, alignment or real-paper assessment")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", re.ASCII)
_SEGMENT = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*", re.ASCII)
_RESPONSE_KEYS = {"protocol", "kind", "handoff_id", "request_sha256", "plan_id",
                  "task_index", "arm", "outputs"}


class HandoffInvalidated(ValueError):
    """The frozen context is no longer current; the handoff was stopped, not refreshed."""


def _segment(value, name):
    if (type(value) is not str or len(value) > 64 or not _SEGMENT.fullmatch(value)
            or value == "template"):
        raise ValueError("unsafe or non-canonical path segment: " + name)
    return value


def output_paths(topic, slug):
    """The only two draft paths a result may name. ASCII lower-case segments only."""
    base = "surveys/%s/%s" % (_segment(topic, "topic"), _segment(slug, "slug"))
    return {"en": base + ".md", "ja": base + ".ja.md"}


def template_structure(outputs, paths):
    """Mechanical bilingual-template check of an untrusted draft. See STRUCTURE_LIMITS."""
    report = {"limits": STRUCTURE_LIMITS}
    for language, other in (("en", "ja"), ("ja", "en")):
        text, rules = outputs[paths[language]], TEMPLATE[language]
        positions = [text.find(heading) for heading in rules["headings"]]
        practical = text.split(rules["headings"][2], 1)[-1].split("\n## ", 1)[0]
        lines = [line for line in practical.splitlines() if line.startswith("- ")]
        report[language] = {
            "headings_in_order": -1 not in positions and positions == sorted(positions),
            "overview_labels": all(label in text for label in rules["labels"]),
            "language_link": "(%s)" % paths[other].rsplit("/", 1)[-1] in text,
            "practical_lines": len(lines) if -1 not in positions else None,
            "practical_lines_in_range": -1 not in positions and 6 <= len(lines) <= 7,
        }
    return report


class ResearchHandoffJournal:
    def __init__(self, path, baseline, *, target):
        if not isinstance(baseline, RawBaselineComparison):
            raise TypeError("RawBaselineComparison required")
        target = dict(target)
        if (set(target) != {"repository", "commit"}
                or type(target["repository"]) is not str
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", target["repository"])
                or type(target["commit"]) is not str
                or not re.fullmatch(r"[0-9a-f]{40}", target["commit"])):
            raise ValueError("target requires repository and immutable 40-character commit")
        self.target = target
        self.baseline = baseline
        self.db = sqlite3.connect(path, isolation_level=None, timeout=5)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS research_handoffs (
            handoff_id TEXT PRIMARY KEY, slot TEXT NOT NULL UNIQUE,
            binding BLOB NOT NULL, request BLOB NOT NULL,
            request_sha256 TEXT NOT NULL, status TEXT NOT NULL, reason TEXT,
            result BLOB, result_sha256 TEXT)""")

    def close(self):
        self.db.close()

    # ---- frozen arm -------------------------------------------------------------
    def _arm(self, plan_id, task_index, arm):
        """Audit entry and exact packed request of one frozen arm (membership from the plan)."""
        audit = self.baseline.audit(plan_id)  # verifies plan digest, context and request hashes
        if (type(task_index) is not int or type(arm) is not str or arm not in ("A", "B")
                or not 0 <= task_index < len(audit["arms"]) // 2):
            raise ValueError("invalid task index or arm")
        entry = next(a for a in audit["arms"] if (a["task_index"], a["arm"]) == (task_index, arm))
        plan = self.baseline.comparisons._plan(plan_id)[0]
        return audit, entry, plan, plan["tasks"][task_index][arm]["request"]

    def _problem(self, binding):
        """Reason the frozen binding may no longer be used, or None. Reads only."""
        try:
            audit, entry, _, _ = self._arm(binding["plan_id"], binding["task_index"], binding["arm"])
            if (audit["plan_sha256"], audit["context_sha256"], entry["request_sha256"]) != (
                    binding["plan_sha256"], binding["context_sha256"],
                    binding["packed_request_sha256"]):
                return "frozen_binding_changed"
            if audit["status"] == "invalidated":
                return "comparison_plan_invalidated"
            if entry["status"] != "planned_not_dispatched":
                return "comparison_arm_executed"  # keep manual drafts out of the fake A/B run
            observed = self.baseline.current(binding["plan_id"])
        except Exception as exc:  # fail closed
            return "recheck_failed:" + str(getattr(exc, "code", type(exc).__name__))
        if observed != {"policy_sha256": binding["policy_sha256"],
                        "snapshot_sha256": binding["snapshot_binding"]}:
            return "frozen_context_no_longer_current"
        return None

    def _row(self, handoff_id):
        row = self.db.execute(
            "SELECT binding, request, request_sha256, status, reason, result, result_sha256 "
            "FROM research_handoffs WHERE handoff_id=?", (handoff_id,)).fetchone()
        if row is None:
            raise ValueError("unknown handoff")
        request = bytes(row[1])
        if sha256_hex(request) != row[2] or row[3] not in STATUSES:
            raise ValueError("corrupt handoff journal row")
        binding = loads_strict_bytes(bytes(row[0]))
        envelope = loads_strict_bytes(request)
        if (type(binding) is not dict or type(envelope) is not dict
                or any(key not in envelope or envelope[key] != value
                       for key, value in binding.items())
                or sha256_hex(envelope["packed_request"].encode("ascii"))
                   != binding["packed_request_sha256"]):
            raise ValueError("corrupt handoff binding")
        result, result_sha256 = row[5], row[6]
        if (result is None) != (result_sha256 is None):
            raise ValueError("corrupt handoff result")
        if result is not None:
            data = bytes(result)
            if sha256_hex(data) != result_sha256:
                raise ValueError("corrupt handoff result")
            self._parse(binding, row[2], data)
        elif row[3] == "received_unreviewed":
            raise ValueError("corrupt handoff result")
        return (binding, request) + tuple(row[2:])

    def _invalidate(self, handoff_id, reason):
        self.db.execute(
            "UPDATE research_handoffs SET status='invalidated', reason=? WHERE handoff_id=? "
            "AND status IN ('prepared','export_intent_outcome_unknown','received_unreviewed')",
            (reason, handoff_id))
        raise HandoffInvalidated(reason)

    # ---- prepare ----------------------------------------------------------------
    def prepare(self, *, handoff_id, plan_id, task_index, arm, topic, slug):
        """Idempotently bind one frozen arm to one handoff ID. Never refreshes a context."""
        if type(handoff_id) is not str or not _ID.fullmatch(handoff_id):
            raise ValueError("invalid handoff ID")
        if type(plan_id) is not str or not _ID.fullmatch(plan_id):
            raise ValueError("invalid plan ID")
        paths = output_paths(topic, slug)
        audit, entry, plan, packed = self._arm(plan_id, task_index, arm)
        context = self.baseline.frozen(plan_id)
        binding = dict(
            protocol=PROTOCOL, handoff_id=handoff_id, plan_id=plan_id, task_index=task_index,
            arm=arm, task_id=entry["task_id"], plan_sha256=audit["plan_sha256"],
            context_sha256=audit["context_sha256"], scope=context["scope"],
            policy_sha256=context["policy_sha256"], snapshot_sha256=context["snapshot_sha256"],
            snapshot_binding=context["snapshot_binding"], target=self.target, output_paths=paths,
            packed_request_sha256=entry["request_sha256"],
            packed_request_bytes=entry["request_bytes"])
        encoded = _encode(binding)
        existing = self.db.execute("SELECT binding FROM research_handoffs WHERE handoff_id=?",
                                   (handoff_id,)).fetchone()
        if existing is not None:
            if bytes(existing[0]) != encoded:
                raise ValueError("handoff binding conflict")
            status = self.status(handoff_id)
            if status["status"] != "invalidated":
                problem = self._problem(binding)
                if problem is not None:
                    self._invalidate(handoff_id, problem)
            return status
        problem = self._problem(binding)
        if problem is not None:
            raise HandoffInvalidated(problem)  # nothing is journaled
        request = _encode(dict(
            binding, kind="request", packed_request=packed, synthetic_only=True,
            reference_data_only=True, references_untrusted=True, draft_only=True,
            publication="caller_controlled", grants_permissions=False,
            template=TEMPLATE, template_is_data_not_instruction=True,
            limits={"max_response_bytes": MAX_RESPONSE_BYTES,
                    "max_output_bytes": MAX_OUTPUT_BYTES},
            response_keys=sorted(_RESPONSE_KEYS)))
        if len(request) > MAX_ENVELOPE_BYTES:
            raise ValueError("request envelope exceeds its byte bound")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            raced = self.db.execute("SELECT binding FROM research_handoffs WHERE handoff_id=?",
                                    (handoff_id,)).fetchone()
            if raced is None:
                slot = _encode([plan_id, task_index, arm]).decode("ascii")
                if self.db.execute("SELECT 1 FROM research_handoffs WHERE slot=?",
                                   (slot,)).fetchone():
                    raise ValueError("comparison arm already bound to a handoff")
                self.db.execute(
                    "INSERT INTO research_handoffs "
                    "(handoff_id,slot,binding,request,request_sha256,status) VALUES (?,?,?,?,?,?)",
                    (handoff_id, slot, encoded, request, sha256_hex(request), "prepared"))
            elif bytes(raced[0]) != encoded:
                raise ValueError("handoff binding conflict")
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return self.status(handoff_id)

    # ---- one-time claim -----------------------------------------------------------
    def claim(self, handoff_id):
        """Return the packet bytes exactly once. The durable state becomes
        ``export_intent_outcome_unknown`` BEFORE the bytes are returned; a repeat
        or reopened claim raises and never yields the packet again."""
        binding, request, _, status, _, _, _ = self._row(handoff_id)
        if status != "prepared":
            raise ValueError("packet is not claimable: " + status)
        problem = self._problem(binding)
        if problem is not None:
            self._invalidate(handoff_id, problem)
        cursor = self.db.execute(
            "UPDATE research_handoffs SET status='export_intent_outcome_unknown' "
            "WHERE handoff_id=? AND status='prepared'", (handoff_id,))
        if cursor.rowcount != 1:
            raise ValueError("packet is not claimable: claimed concurrently")
        return request

    # ---- untrusted result ---------------------------------------------------------
    @staticmethod
    def _parse(binding, request_sha256, data):
        if type(data) is not bytes or not 1 <= len(data) <= MAX_RESPONSE_BYTES:
            raise ValueError("response must be bounded non-empty bytes")
        document = loads_strict_bytes(data)  # strict UTF-8, duplicate keys rejected
        if type(document) is not dict or set(document) != _RESPONSE_KEYS:
            raise ValueError("response keys differ from the protocol")
        expected = dict(protocol=binding["protocol"], kind="result", handoff_id=binding["handoff_id"],
                        request_sha256=request_sha256, plan_id=binding["plan_id"],
                        task_index=binding["task_index"], arm=binding["arm"])
        for key, value in expected.items():
            if type(document[key]) is not type(value) or document[key] != value:
                raise ValueError("response is not bound to this request: " + key)
        outputs, paths = document["outputs"], binding["output_paths"]
        if type(outputs) is not dict or set(outputs) != set(paths.values()):
            raise ValueError("response must hold exactly the two allowed draft paths")
        for text in outputs.values():
            if type(text) is not str or not text.strip() or "\x00" in text:
                raise ValueError("draft output must be non-empty text")
            try:
                size = len(text.encode("utf-8"))
            except UnicodeEncodeError:
                raise ValueError("draft output is not valid UTF-8") from None
            if size > MAX_OUTPUT_BYTES:
                raise ValueError("draft output exceeds its byte bound")
        return outputs

    def import_result(self, handoff_id, data):
        """Store an untrusted draft as ``received_unreviewed``. Nothing is adopted,
        verified, scored, captured or executed; the text is never interpreted."""
        binding, _, request_sha256, status, _, _, result_sha256 = self._row(handoff_id)
        self._parse(binding, request_sha256, data)  # malformed results never mutate the journal
        digest = sha256_hex(data)
        if status == "received_unreviewed":
            if digest != result_sha256:
                raise ValueError("handoff result conflict")
            problem = self._problem(binding)
            if problem is not None:
                self._invalidate(handoff_id, problem)
            return self.status(handoff_id)
        if status != "export_intent_outcome_unknown":
            raise ValueError("no claimed request awaits a result: " + status)
        problem = self._problem(binding)
        if problem is not None:
            self._invalidate(handoff_id, problem)
        cursor = self.db.execute(
            "UPDATE research_handoffs SET status='received_unreviewed', result=?, result_sha256=? "
            "WHERE handoff_id=? AND status='export_intent_outcome_unknown'",
            (data, digest, handoff_id))
        if cursor.rowcount != 1:
            raise ValueError("handoff changed concurrently")
        return self.status(handoff_id)

    def unreviewed_result(self, handoff_id):
        """Release stored untrusted draft bytes for review after a live eligibility recheck."""
        row = self._row(handoff_id)
        if row[3] != "received_unreviewed" or sha256_hex(bytes(row[5])) != row[6]:
            raise ValueError("no intact unreviewed result")
        problem = self._problem(row[0])
        if problem is not None:
            self._invalidate(handoff_id, problem)
        return bytes(row[5])

    # ---- status (never returns the packet) ------------------------------------------
    def status(self, handoff_id):
        binding, _, request_sha256, status, reason, result, result_sha256 = self._row(handoff_id)
        document = {
            "handoff_id": handoff_id, "protocol": binding["protocol"], "status": status,
            "reason": reason, "plan_id": binding["plan_id"], "task_index": binding["task_index"],
            "arm": binding["arm"], "plan_sha256": binding["plan_sha256"],
            "context_sha256": binding["context_sha256"],
            "packed_request_sha256": binding["packed_request_sha256"],
            "request_sha256": request_sha256, "target": binding["target"],
            "output_paths": binding["output_paths"], "packet_claimable": status == "prepared",
            "delivery_confirmed": None, "requires_human_review": True,
            "adopted": False, "verified": False, "agent_execution_confirmed": None,
            "result_sha256": result_sha256, "result_bytes": None, "structure": None,
        }
        if status == "received_unreviewed":
            data = bytes(result)
            document["result_bytes"] = len(data)
            document["structure"] = template_structure(
                loads_strict_bytes(data)["outputs"], binding["output_paths"])
        return document
