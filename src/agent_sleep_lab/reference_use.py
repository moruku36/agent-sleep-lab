"""Durable local reference dispatch accounting, not authenticated delivery/use proof.

Only explicitly supplied trusted local consumers run. No dynamic plugin loading,
network, scheduler, model, automatic retry, adoption or evaluator is provided.
A consumer's receipt is unreviewed self-report, never semantic-use verification.
"""
from __future__ import annotations

import re
import sqlite3

from agent_sleep_lab.oss_bridge import CollectOnlyBridge
from agent_sleep_lab.provenance import canonical_json, sha256_hex
from agent_sleep_lab.strictjson import loads_strict_bytes

_APPLICATION_ID = 0x41534C55
_MAX_TASK = 65536
_MAX_REFERENCE = 262144
_MAX_OUTPUT = 65536
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")
_STATES = frozenset({"prepared", "dispatch_outcome_unknown", "received_unreviewed",
                     "invalid_receipt_unreviewed", "invalidated"})


def _identifier(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise ValueError("bounded canonical identity required")
    return value


def _context_hash(bundle):
    # as_of is a read timestamp, not a policy/evidence/record change.
    value = dict(bundle.document)
    value.pop("as_of")
    return sha256_hex(canonical_json(value))


class ReferenceUseJournal:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=5)
        try:
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("PRAGMA fullfsync=ON")
            self.db.execute("BEGIN IMMEDIATE")
            app = self.db.execute("PRAGMA application_id").fetchone()[0]
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            objects = self.db.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0]
            if (app, version, objects) == (0, 0, 0):
                self.db.execute("""CREATE TABLE reference_uses (
                    use_id TEXT PRIMARY KEY, binding BLOB NOT NULL,
                    binding_sha256 TEXT NOT NULL, state BLOB NOT NULL)""")
                self.db.execute("PRAGMA application_id=" + str(_APPLICATION_ID))
                self.db.execute("PRAGMA user_version=1")
            elif app != _APPLICATION_ID or version != 1:
                raise ValueError("separate reference-use journal required; foreign database refused")
            self.db.execute("COMMIT")
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            self.db.close()
            raise

    def close(self):
        self.db.close()

    def _row(self, use_id):
        row = self.db.execute(
            "SELECT binding,binding_sha256,state FROM reference_uses WHERE use_id=?",
            (_identifier(use_id),)).fetchone()
        if row is None:
            raise ValueError("unknown reference use")
        if sha256_hex(row[0]) != row[1]:
            raise ValueError("corrupt reference-use binding")
        binding, state = loads_strict_bytes(row[0]), loads_strict_bytes(row[2])
        if (canonical_json(binding) != row[0] or canonical_json(state) != row[2]
                or state["status"] not in _STATES
                or sha256_hex(bytes.fromhex(binding["task_hex"])) != binding["task_sha256"]
                or sha256_hex(bytes.fromhex(binding["reference_hex"])) != binding["reference_sha256"]):
            raise ValueError("corrupt reference-use row")
        if state.get("output_hex") is not None and (
                sha256_hex(bytes.fromhex(state["output_hex"])) != state["output_sha256"]):
            raise ValueError("corrupt consumer output")
        return binding, state

    def status(self, use_id):
        binding, state = self._row(use_id)
        return dict(state, use_id=use_id, task_sha256=binding["task_sha256"],
                    reference_sha256=binding["reference_sha256"],
                    consumer=dict(binding["config"]["consumer"]),
                    delivery_and_use_verified=False)

    def context_unchanged(self, use_id, bridge):
        """Read-only recheck of the frozen reference context under current policy.

        Writes nothing and changes no state. A different bridge identity raises;
        an unavailable or changed context returns False (fail closed).
        """
        binding, _ = self._row(use_id)
        config = binding["config"]
        if self._bridge_identity(bridge) != {k: config[k] for k in
                                             ("scope", "repository", "agent_commit")}:
            raise ValueError("bridge identity differs from frozen binding")
        try:
            bundle = bridge.reference_context(
                query=config["query"], max_bytes=config["max_bytes"],
                max_records=config["max_records"])
            return _context_hash(bundle) == binding["context_sha256"]
        except Exception:
            return False

    def _cas(self, use_id, before, after):
        changed = self.db.execute(
            "UPDATE reference_uses SET state=? WHERE use_id=? AND state=?",
            (canonical_json(after), use_id, canonical_json(before)))
        if changed.rowcount != 1:
            raise ValueError("reference use changed concurrently")

    @staticmethod
    def _bridge_identity(bridge):
        if not isinstance(bridge, CollectOnlyBridge):
            raise TypeError("explicit CollectOnlyBridge required")
        return dict(scope=dict(bridge.scope), repository=bridge.repository,
                    agent_commit=bridge.agent_commit)

    def prepare(self, use_id, bridge, *, task_bytes, query, max_bytes,
                consumer_id, consumer_version, max_records=16):
        _identifier(use_id)
        if type(task_bytes) is not bytes or not 1 <= len(task_bytes) <= _MAX_TASK:
            raise ValueError("bounded nonempty task bytes required")
        if type(max_bytes) is not int or not 1 <= max_bytes <= _MAX_REFERENCE:
            raise ValueError("reference byte cap out of range")
        if type(query) is not str or not query.strip() or len(query) > 1024:
            raise ValueError("explicit bounded retrieval query required")
        if type(max_records) is not int or not 1 <= max_records <= 256:
            raise ValueError("record cap out of range")
        config = dict(self._bridge_identity(bridge), query=query,
                      max_bytes=max_bytes, max_records=max_records,
                      consumer=dict(id=_identifier(consumer_id),
                                    version=_identifier(consumer_version)))
        existing = self.db.execute("SELECT 1 FROM reference_uses WHERE use_id=?", (use_id,)).fetchone()
        if existing:
            binding, _ = self._row(use_id)
            if binding["config"] != config or binding["task_hex"] != task_bytes.hex():
                raise ValueError("reference-use binding conflict")
            return self.status(use_id)  # never refresh/replay a prepared or unknown dispatch
        bundle = bridge.reference_context(query=query, max_bytes=max_bytes, max_records=max_records)
        binding = dict(protocol="agent-sleep-reference-use/1", synthetic_only=True,
                       config=config, task_hex=task_bytes.hex(), task_sha256=sha256_hex(task_bytes),
                       reference_hex=bundle.bundle_bytes.hex(), reference_sha256=bundle.bundle_sha256,
                       context_sha256=_context_hash(bundle))
        encoded = canonical_json(binding)
        # A concurrent prepare is rejected by the unique key before any dispatch.
        self.db.execute("INSERT INTO reference_uses VALUES (?,?,?,?)",
                        (use_id, encoded, sha256_hex(encoded),
                         canonical_json(dict(status="prepared", reason=None, dispatches=0))))
        return self.status(use_id)

    def dispatch(self, use_id, bridge, consumer, *, consumer_id, consumer_version):
        """One local call at most; caller remains responsible for consumer authority.

        Consumer signature: keyword use_id, task_bytes, reference_bytes.
        Receipt: exactly use_id, task_sha256, reference_sha256, output_bytes.
        No receipt assertion establishes factual correctness or actual memory use.
        """
        binding, before = self._row(use_id)
        if before["status"] != "prepared":
            return self.status(use_id)
        config = binding["config"]
        if (self._bridge_identity(bridge) != {k: config[k] for k in
                                             ("scope", "repository", "agent_commit")}
                or config["consumer"] != dict(id=consumer_id, version=consumer_version)):
            raise ValueError("dispatch identity differs from frozen binding")
        if not callable(consumer):
            raise TypeError("explicit trusted local consumer required")
        try:
            bundle = bridge.reference_context(
                query=config["query"], max_bytes=config["max_bytes"],
                max_records=config["max_records"])
            current = _context_hash(bundle)
        except Exception:
            current = None
        if current != binding["context_sha256"]:
            self._cas(use_id, before, dict(before, status="invalidated",
                                          reason="reference_context_changed_or_unavailable"))
            return self.status(use_id)
        inflight = dict(before, status="dispatch_outcome_unknown", reason="consumer_outcome_unknown",
                        dispatches=1)
        self._cas(use_id, before, inflight)  # durable BEFORE caller code, never refunded
        try:
            receipt = consumer(use_id=use_id, task_bytes=bytes.fromhex(binding["task_hex"]),
                               reference_bytes=bytes.fromhex(binding["reference_hex"]))
        except Exception:
            return self.status(use_id)  # uncertain side effects: never invoke again
        valid = (type(receipt) is dict and set(receipt) ==
                 {"use_id", "task_sha256", "reference_sha256", "output_bytes"}
                 and receipt["use_id"] == use_id
                 and receipt["task_sha256"] == binding["task_sha256"]
                 and receipt["reference_sha256"] == binding["reference_sha256"]
                 and type(receipt["output_bytes"]) is bytes
                 and len(receipt["output_bytes"]) <= _MAX_OUTPUT)
        if not valid:
            after = dict(inflight, status="invalid_receipt_unreviewed", reason="receipt_contract_mismatch")
        else:
            after = dict(inflight, status="received_unreviewed", reason=None,
                         output_hex=receipt["output_bytes"].hex(),
                         output_sha256=sha256_hex(receipt["output_bytes"]))
        # Recheck AFTER return as well. A result is retained but never served as
        # current-context success if permission/evidence changed during the call.
        try:
            post = bridge.reference_context(
                query=config["query"], max_bytes=config["max_bytes"],
                max_records=config["max_records"])
            unchanged = _context_hash(post) == binding["context_sha256"]
        except Exception:
            unchanged = False
        if not unchanged:
            after.update(status="invalidated", reason="reference_context_changed_during_dispatch")
        self._cas(use_id, inflight, after)
        return self.status(use_id)
