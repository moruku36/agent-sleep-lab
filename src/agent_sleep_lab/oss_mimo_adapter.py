"""Explicit exact-prompt adapter for validated synthetic OSS captures.

Development draft reviewed from Muse Wonder's proposal. This is NOT an HTTP
replay: only the captured user text reaches the registered CLI model. There is
no context/policy driver or durable live journal here. The old paired journal
remains fake-only. Callers must check current context before/after execution,
keep intent/outcome durably, and never replace an interrupted adapter to retry.

Budgets/stops are per instance, single-driver only. Post-generation byte caps
are not token or monetary caps. Caller opt-ins do not replace owner approval.
"""
from __future__ import annotations

import re
import subprocess

from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_prompt_capture as capture
from agent_sleep_lab import oss_prompt_capture_worker as child
from agent_sleep_lab.mimo_provider import MODEL
from agent_sleep_lab.strictjson import loads_strict_bytes

MAX_REQUEST_BYTES = 131072
MAX_ENVELOPE_BYTES = 1048576
MAX_OUTPUT_BYTES = 65536
UNAVAILABLE = "unavailable"
TRANSPORT_TEST = "injected_transport_not_live_verified"
TRANSPORT_CLI = "registered_openclaw_cli"


class AdapterError(RuntimeError):
    """Sanitized failure. A post-dispatch failure must never be retried."""


def _bound(value, maximum, name):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(name + " outside its integer bound")
    return value


class OSSMimoAdapter:
    """Exact prompt transport, not a current-policy executor or verdict parser.

    Constructing an instance does not execute inference. Both acknowledgments
    must be literally True. No fallback/retry; after any post-dispatch failure
    this instance stays stopped, even on KeyboardInterrupt. Process death and
    constructing another instance are NOT covered by this in-memory stop.
    """

    def __init__(self, *, agent, max_calls, acknowledge_paid_execution=False,
                 acknowledge_uncapped_generation=False, timeout=120,
                 max_request_bytes=MAX_REQUEST_BYTES, transport=None):
        if (type(agent) is not str
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", agent)):
            raise ValueError("explicit registered agent required")
        if (acknowledge_paid_execution is not True
                or acknowledge_uncapped_generation is not True):
            raise ValueError("explicit paid and uncapped-generation acknowledgments required")
        self.max_calls = _bound(max_calls, 2, "max_calls")
        self.timeout = _bound(timeout, 120, "timeout")
        self.max_request_bytes = _bound(max_request_bytes, MAX_REQUEST_BYTES,
                                        "max_request_bytes")
        if transport is not None and not callable(transport):
            raise TypeError("transport must be callable")
        self.agent = agent
        self.transport = subprocess.run if transport is None else transport
        self.transport_kind = TRANSPORT_CLI if transport is None else TRANSPORT_TEST
        self.calls = 0
        self.stopped = False
        self.receipts = []

    def complete(self, capture_doc, *, reference, arm, max_output_bytes):
        """Return (raw UTF-8 reply bytes, sanitized receipt), no verdict.

        Full capture validation recomputes request/prompt/task/source/reference
        hashes before reserving a call. Artifact labels are not authenticated
        worker/store origin or permission. No instruction wrapper is added.
        """
        if self.stopped:
            raise AdapterError("adapter stopped; do not retry")
        if self.calls >= self.max_calls:
            raise AdapterError("call budget exhausted")
        if type(arm) is not str or arm not in ("baseline", "reference"):
            raise ValueError("explicit baseline or reference arm required")
        _bound(max_output_bytes, MAX_OUTPUT_BYTES, "max_output_bytes")
        raw = worker.encoded(capture_doc)
        doc = capture.validate_output(raw, task=parent.builtin_task(), reference=reference,
            selected_issue_probe=(capture_doc.get("selected_issue_probe")
                                  if type(capture_doc) is dict else None))
        selected = doc["arms"][arm]
        request = worker.encoded(dict(url=selected["url"],
                                     header_names=selected["header_names"],
                                     payload=selected["payload"]))
        prompt = child.prompt_of(selected["payload"])
        if len(request) > self.max_request_bytes:
            raise ValueError("captured request exceeds input-byte bound")
        argv = ["openclaw", "infer", "model", "run", "--agent", self.agent,
                "--model", MODEL, "--thinking", "low", "--json", "--prompt", prompt]
        receipt = dict(
            status="outcome_unknown", arm=arm, model_requested=MODEL,
            capture_document_sha256=worker.digest(raw),
            request_sha256=selected["request_sha256"],
            prompt_sha256=selected["prompt_sha256"], prompt_bytes=selected["prompt_bytes"],
            source_sha256=dict(doc["executed_source_sha256"]),
            agent_commit=doc["agent_commit"], task_sha256=doc["task_sha256"],
            reference_sha256=doc["reference_sha256"],
            capture_origin="caller_supplied_artifact_unauthenticated",
            transport=self.transport_kind, usage=UNAVAILABLE, cost=UNAVAILABLE,
            generation_token_cap=None, monetary_cap=None,
            max_request_bytes=self.max_request_bytes, post_output_byte_cap=max_output_bytes,
            timeout_seconds=self.timeout, http_wire_equivalent=False,
            verdict=None, semantic_memory_use="not_evaluated",
            performance_improvement="not_evaluated")
        receipt.update(child.probe_metadata(doc))
        self.calls += 1  # reserve BEFORE dispatch, including failures
        self.receipts.append(receipt)
        self.stopped = True  # remains true on any exception/interruption after this point
        try:
            result = self.transport(argv, capture_output=True, timeout=self.timeout, check=False)
            if result.returncode != 0:
                raise ValueError("nonzero return")
            if type(result.stdout) is not bytes or not 1 <= len(result.stdout) <= MAX_ENVELOPE_BYTES:
                raise ValueError("invalid envelope bound")
            envelope = loads_strict_bytes(result.stdout)
            if (type(envelope) is not dict or envelope.get("ok") is not True
                    or envelope.get("provider") != "xiaomi"
                    or envelope.get("model") != "mimo-v2.6-pro"
                    or envelope.get("attempts") != []):
                raise ValueError("model or fallback mismatch")
            outputs = envelope.get("outputs")
            if (type(outputs) is not list or len(outputs) != 1
                    or type(outputs[0]) is not dict or type(outputs[0].get("text")) is not str
                    or any(value for key, value in outputs[0].items() if key != "text")):
                raise ValueError("single text output required")
            reply = outputs[0]["text"].encode("utf-8")
            if not 1 <= len(reply) <= max_output_bytes:
                raise ValueError("post-generation output bound")
        except Exception:
            # Never expose stdout/stderr or transport exception/account details.
            raise AdapterError("unverified inference outcome; stopped, do not retry") from None
        receipt.update(status="returned", provider="xiaomi", model="mimo-v2.6-pro",
                       output_sha256=worker.digest(reply), output_bytes=len(reply))
        # No stable CLI usage/cost contract is supported; do not infer or copy it.
        self.stopped = False
        return reply, dict(receipt, source_sha256=dict(receipt["source_sha256"]))
