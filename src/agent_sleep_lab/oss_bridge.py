"""Opt-in collect-only boundary for OSS Contributor TriageDecision dictionaries.

Synthetic offline inputs only. Observing a decision does not verify its rationale
or issue facts. This module never imports/executes the target agent, changes its
ledger/configuration, dispatches a model, or submits a patch/PR.
"""
from __future__ import annotations

import math
import re

from agent_sleep_lab.provenance import canonical_json, sha256_hex
from agent_sleep_lab.retrieval import retrieve_reference_bundle

_OUTCOMES = frozenset({
    "candidate", "pending_llm", "skipped_low_score", "skipped_llm_reject",
    "skipped_duplicate", "infra_error",
})
_FIELDS = frozenset({
    "repo", "number", "title", "url", "score", "outcome", "reasons",
    "llm_rationale", "is_new",
})


class CollectOnlyBridge:
    """Explicit caller wiring, not an installed production-agent integration."""

    def __init__(self, store, *, scope, repository, agent_commit):
        if (type(scope) is not dict or set(scope) != {"project", "task_family"}
                or any(type(v) is not str or not re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", v) for v in scope.values())):
            raise ValueError("explicit project/task_family scope required")
        if type(repository) is not str or not re.fullmatch(
                r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("explicit target repository required")
        if type(agent_commit) is not str or not re.fullmatch(r"[0-9a-f]{40}", agent_commit):
            raise ValueError("immutable agent commit required")
        self.store = store
        self.scope = dict(scope)
        self.repository = repository
        self.agent_commit = agent_commit

    def capture_decision(self, decision, *, event_id, session_id, observed_at,
                         captured_at, authorization, synthetic):
        # Never relabel real operational logs as synthetic. Production ingestion
        # needs a separately reviewed non-synthetic store/retention contract.
        if synthetic is not True:
            raise ValueError("bridge accepts explicitly synthetic offline decisions only")
        if type(decision) is not dict or set(decision) != _FIELDS:
            raise ValueError("exact TriageDecision fields required")
        if decision["repo"] != self.repository:
            raise ValueError("decision repository differs from configured target")
        if (type(decision["number"]) is not int or decision["number"] < 1
                or type(decision["is_new"]) is not bool
                or type(decision["outcome"]) is not str
                or decision["outcome"] not in _OUTCOMES):
            raise ValueError("invalid decision identity/outcome")
        score = decision["score"]
        if score is not None and (type(score) not in (int, float)
                                  or not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError("invalid triage score")
        for key in ("title", "url", "llm_rationale"):
            value = decision[key]
            if type(value) is not str or "\x00" in value or len(value.encode("utf-8")) > 8192:
                raise ValueError("bounded decision text required")
        reasons = decision["reasons"]
        if (type(reasons) is not list or len(reasons) > 32
                or any(type(v) is not str or "\x00" in v
                       or len(v.encode("utf-8")) > 2048 for v in reasons)):
            raise ValueError("bounded decision reasons required")
        source = canonical_json({
            "schema_version": "agent-sleep-oss-observation/1",
            "agent_repository": "moruku36/oss-contributor-agent",
            "agent_commit": self.agent_commit,
            "mode": "collect-only",
            "synthetic": True,
            "decision_is_not_fact_verification": True,
            "decision": decision,
        })
        event = canonical_json({
            "schema_version": "0.1", "event_id": event_id, "session_id": session_id,
            "occurred_at": observed_at, "scope": self.scope, "kind": "observation",
            "summary": ("Observed collect-only triage outcome " + decision["outcome"]
                        + "; rationale and issue facts remain unverified."),
            "source_uri": "oss-decision:sha256:" + sha256_hex(source), "synthetic": True,
        })
        # The existing capture boundary validates IDs, timestamps, authorization,
        # lineage, bytes and scope and stamps its configured adapter identity.
        # No verifier/evaluator receipts are created here.
        claim = {
            "schema_version": "agent-sleep-provenance/1",
            "event": {"event_id": event_id, "sha256": sha256_hex(event), "scope": self.scope},
            "origin": "tool_observation",
            "source": {"source_id": event_id, "sha256": sha256_hex(source),
                       "locator": "decision"},
            "observed_at": observed_at, "captured_at": captured_at,
            "lineage": {"original_root_id": event_id, "derived_from": []},
            "authorization": dict(authorization),
            "partition": {"synthetic": True, "evaluation": "experience"},
        }
        return self.store.capture(event_bytes=event, source_bytes=source, claim=claim)

    def reference_context(self, *, query, max_bytes, max_records=16):
        """Read-only reference data. Returning a bundle is not delivery/use proof."""
        return retrieve_reference_bundle(
            self.store, scope=dict(self.scope), partition="experience",
            query=query, max_bytes=max_bytes, max_records=max_records)
