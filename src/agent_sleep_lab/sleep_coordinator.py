"""Manual, offline synthetic Light/Deep checkpoints. Not an authentication boundary.

Only a locally supplied fake provider is supported. No network, schedules, REM or
diary. A trusted preparer constructs artifacts/receipts using existing boundaries;
provider proposals cannot supply verification, policy or adoption identities.
Use a separate private SQLite path, never the evidence-store path.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass

from agent_sleep_lab.adoption_candidates import parse_canonical
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.strictjson import loads_strict_bytes


def _encode(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")
    loads_strict_bytes(data)
    return data


def _id(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", value)


@dataclass(frozen=True)
class Limits:
    calls: int = 2
    input_bytes: int = 65536
    output_bytes: int = 32768
    stage_output_bytes: int = 16384
    candidates: int = 16

    def __post_init__(self):
        for name, ceiling in (("calls", 2), ("input_bytes", 1048576),
                              ("output_bytes", 1048576), ("stage_output_bytes", 65536),
                              ("candidates", 64)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError("invalid limit: " + name)


class FakeProvider:
    """Deterministic, bytes-only test seam; no live-provider implementation."""
    def __init__(self, light: bytes, deep: bytes):
        self.responses = {"light": light, "deep": deep}
        self.calls = []

    def propose(self, stage, request, max_output_bytes):
        self.calls.append(stage)
        return self.responses[stage]


class SleepCoordinator:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=5)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS sleep_runs (
            run_id TEXT PRIMARY KEY, binding BLOB NOT NULL, state BLOB NOT NULL)""")

    def close(self):
        self.db.close()

    def _read(self, run_id):
        row = self.db.execute("SELECT binding, state FROM sleep_runs WHERE run_id=?",
                              (run_id,)).fetchone()
        if row is None:
            raise ValueError("unknown run")
        return row[0], loads_strict_bytes(row[1])

    def inspect(self, run_id):
        return self._read(run_id)[1]

    def _cas(self, run_id, before, after):
        cursor = self.db.execute(
            "UPDATE sleep_runs SET state=? WHERE run_id=? AND state=?",
            (_encode(after), run_id, _encode(before)))
        if cursor.rowcount != 1:
            raise ValueError("run changed concurrently")

    def bind(self, *, run_id, scope, events, config, parent_sha256=None, limits=Limits()):
        if not _id(run_id):
            raise ValueError("invalid run ID")
        if (type(scope) is not dict or set(scope) != {"project", "task_family"}
                or not all(type(v) is str and v for v in scope.values())):
            raise ValueError("invalid scope")
        if parent_sha256 is not None and (
                type(parent_sha256) is not str or not re.fullmatch("[0-9a-f]{64}", parent_sha256)):
            raise ValueError("invalid parent hash")
        if type(events) is not list or len(events) > 64:
            raise ValueError("bounded event list required")
        if (any(type(e) is not dict or set(e) != {"event_id", "event_sha256"}
                or not _id(e["event_id"]) or type(e["event_sha256"]) is not str
                or not re.fullmatch("[0-9a-f]{64}", e["event_sha256"]) for e in events)
                or len({e["event_id"] for e in events}) != len(events)):
            raise ValueError("invalid input references")
        binding = _encode(dict(version=1, synthetic_only=True, scope=scope, events=events,
                               config=config, parent_sha256=parent_sha256, limits=asdict(limits)))
        if len(binding) > limits.input_bytes:
            raise ValueError("binding exceeds input cap")
        state = dict(status="light", reason=None, calls=0, input_bytes=0,
                     output_reserved=0, output_actual=0, light=None, deep=None, handoff=None)
        self.db.execute("INSERT OR IGNORE INTO sleep_runs VALUES (?,?,?)",
                        (run_id, binding, _encode(state)))
        if self._read(run_id)[0] != binding:
            raise ValueError("run binding conflict")
        return sha256_hex(binding)

    @staticmethod
    def _proposal(stage, raw, binding):
        doc = loads_strict_bytes(raw)
        key = "event_ids" if stage == "light" else "operations"
        if type(doc) is not dict or set(doc) != {key} or type(doc[key]) is not list:
            raise ValueError("unexpected provider fields")
        if len(doc[key]) > binding["limits"]["candidates"]:
            raise ValueError("too many proposals")
        allowed = {e["event_id"] for e in binding["events"]}
        if stage == "light":
            ids = doc[key]
            if (any(type(i) is not str or i not in allowed for i in ids)
                    or len(set(ids)) != len(ids)):
                raise ValueError("invalid Light references")
        else:
            touched = set()
            for op in doc[key]:
                # First slice supports explicit adds only; no implicit whole-snapshot rewrite.
                if (type(op) is not dict or set(op) != {"op", "memory_id", "event_ids"}
                        or op["op"] != "add" or not _id(op["memory_id"])
                        or op["memory_id"] in touched or type(op["event_ids"]) is not list
                        or not op["event_ids"] or len(op["event_ids"]) > len(allowed)
                        or any(type(i) is not str or i not in allowed for i in op["event_ids"])
                        or len(set(op["event_ids"])) != len(op["event_ids"])):
                    raise ValueError("invalid Deep operation")
                touched.add(op["memory_id"])
        return doc

    def advance(self, run_id, provider):
        if not isinstance(provider, FakeProvider):
            raise TypeError("only offline FakeProvider is supported")
        raw_binding, before = self._read(run_id)
        binding = loads_strict_bytes(raw_binding)
        stage = before["status"]
        if stage not in ("light", "deep"):
            return before  # in-flight work is never replayed, nor silently recovered
        request = _encode(dict(binding=binding, stage=stage, light=before["light"]))
        limits = binding["limits"]
        after = dict(before)
        if (before["calls"] + 1 > limits["calls"]
                or before["input_bytes"] + len(request) > limits["input_bytes"]
                or before["output_reserved"] + limits["stage_output_bytes"] > limits["output_bytes"]):
            after.update(status="incomplete", reason="provider_budget_exhausted")
            self._cas(run_id, before, after)
            return after
        after.update(status=stage + "_inflight", calls=before["calls"] + 1,
                     input_bytes=before["input_bytes"] + len(request),
                     output_reserved=before["output_reserved"] + limits["stage_output_bytes"])
        self._cas(run_id, before, after)  # committed BEFORE dispatch; reservation never refunded
        try:
            raw = provider.propose(stage, request, limits["stage_output_bytes"])
        except Exception:
            result = dict(after, status="incomplete", reason="provider_outcome_unknown")
        else:
            result = dict(after)
            if type(raw) is not bytes:
                result.update(status="failed", reason="provider_not_bytes")
            else:
                result["output_actual"] += len(raw)
                try:
                    if len(raw) > limits["stage_output_bytes"]:
                        raise ValueError("output cap")
                    proposal = self._proposal(stage, raw, binding)
                    if stage == "deep":
                        selected = set(before["light"]["event_ids"])
                        if any(not set(o["event_ids"]) <= selected for o in proposal["operations"]):
                            raise ValueError("Deep used an unselected source")
                    result[stage] = proposal
                    result["status"] = ("deep" if proposal["event_ids"] else "no_change") if stage == "light" else (
                        "ready" if proposal["operations"] else "no_change")
                except ValueError:
                    result.update(status="failed", reason="invalid_provider_output")
        self._cas(run_id, after, result)
        return result

    def recover_stopped_provider(self, run_id):
        """Explicitly call ONLY after the old worker has been confirmed stopped.

        No timeout-based leases or automatic retries. A concurrent late return
        loses its checkpoint CAS rather than overwriting this unknown outcome.
        """
        _, before = self._read(run_id)
        if before["status"] not in ("light_inflight", "deep_inflight"):
            return before
        after = dict(before, status="incomplete", reason="provider_outcome_unknown")
        self._cas(run_id, before, after)
        return after

    def prepare(self, run_id, trusted_preparer):
        """Trusted LOCAL callback constructs exact artifacts and independent receipts.

        Signature: (operation_id, run_id, binding, proposal) -> writer kwargs.
        Not supplied by provider bytes; no receipt-registration shortcut here.
        """
        raw_binding, before = self._read(run_id)
        if before["status"] != "ready":
            return before
        binding = loads_strict_bytes(raw_binding)
        operation_id = "sleep-" + sha256_hex(_encode(
            dict(run_id=run_id, binding=sha256_hex(raw_binding), proposal=before["deep"])))
        # Persist intent before any trusted preparation side effect.
        preparing = dict(before, status="preparing", operation_id=operation_id)
        self._cas(run_id, before, preparing)
        try:
            payload = trusted_preparer(operation_id, run_id, binding, before["deep"])
            req = parse_canonical("adoption_request", payload["request_bytes"])
            if (req["run_id"] != run_id or req["operation_id"] != operation_id
                    or req["scope"] != binding["scope"]
                    or req["expected_parent_snapshot_sha256"] != binding["parent_sha256"]):
                raise ValueError("handoff binding mismatch")
            ops = parse_canonical("operation_manifest", payload["manifest_bytes"])["operations"]
            proposed = before["deep"]["operations"]
            if (len(ops) != len(proposed)
                    or {(o["op"], o["memory_id"]) for o in ops}
                    != {(o["op"], o["memory_id"]) for o in proposed}):
                raise ValueError("handoff differs from proposal")
            source = parse_canonical("source_manifest", payload["source_manifest_bytes"])
            expected = {o["memory_id"]: set(o["event_ids"]) for o in proposed}
            event_hashes = {e["event_id"]: e["event_sha256"] for e in binding["events"]}
            if ({e["memory_id"]: {r["event_id"] for r in e["evidence"]} for e in source["entries"]}
                    != expected or any(r["event_sha256"] != event_hashes[r["event_id"]]
                                       for e in source["entries"] for r in e["evidence"])):
                raise ValueError("handoff source mismatch")
            handoff = {key: payload[key].hex() for key in
                       ("request_bytes", "manifest_bytes", "source_manifest_bytes")}
            handoff["memory_bytes"] = {mid: blob.hex() for mid, blob in payload["memory_bytes"].items()}
            if len(_encode(handoff)) > 1048576:
                raise ValueError("handoff exceeds cap")
            after = dict(preparing, status="handoff", handoff=handoff)
        except Exception:
            after = dict(preparing, status="failed", reason="trusted_preparation_failed")
            self._cas(run_id, preparing, after)
            raise
        self._cas(run_id, preparing, after)
        return after

    def adopt(self, run_id, store):
        """Resolve a stored operation before writing. Unknown ACK stays reconcilable."""
        from agent_sleep_lab.adoption_store import AdoptionStore
        if not isinstance(store, AdoptionStore):
            raise TypeError("existing AdoptionStore required")
        _, before = self._read(run_id)
        if before["status"] != "handoff":
            return before
        handoff = before["handoff"]
        payload = {key: bytes.fromhex(handoff[key]) for key in
                   ("request_bytes", "manifest_bytes", "source_manifest_bytes")}
        payload["memory_bytes"] = {mid: bytes.fromhex(blob)
                                   for mid, blob in handoff["memory_bytes"].items()}
        # commit_adoption rechecks exact replay bytes, parent, current policy and receipts.
        # Even when resolve succeeds, use its exact-replay validation, not just an ID match.
        store.resolve_operation(before["operation_id"])
        result = store.commit_adoption(**payload)
        after = dict(before, status="adopted", receipt_sha256=result.receipt_sha256)
        self._cas(run_id, before, after)
        return after
