"""Gate 4C: trusted offline adapter from accepted-store retrieval to a frozen A/B plan.

SOURCE-MATCHED REPRESENTATION FIXTURE. Arm A receives the exact stored event and
source bytes behind the memories that ``retrieve_reference_bundle`` currently
returns as eligible; arm B receives the same whole raw prefix plus the complete
consolidated records, under the identical ``ArmBudget``. Raw evidence is limited
to the sources of returned memories, so this is NOT a complete raw-retrieval
baseline, not a scientifically fair comparison and not a performance experiment.

Read-only towards the accepted store: no receipts, adoption, rollback, forget or
head changes. Eligibility comes only from the existing retrieval recheck, never
from caller text. Fake provider and synthetic evaluator only (enforced by
``ComparisonStore.run``); no network, live model, CLI, schedule or spending.

Known races (documented, not solved): retrieval is one read transaction, but the
following evidence reads and the second confirming retrieval are separate reads,
and a policy/head change between a live recheck and the fake dispatch that
follows it is not excluded. Local construction is NOT authentication.
"""
from __future__ import annotations

from agent_sleep_lab.ab_comparison import ArmBudget, ComparisonStore, _encode
from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.provenance import StorageError, sha256_hex
from agent_sleep_lab.retrieval import retrieve_reference_bundle
from agent_sleep_lab.strictjson import loads_strict_bytes

REPRESENTATION = "source_matched_fixture"


def _fail(code, message):
    raise StorageError("comparison." + code, message)


class RetrievalComparison:
    def __init__(self, store, comparisons, *, scope, max_bytes, partition="experience",
                 query=None, max_records=16):
        if not isinstance(store, AdoptionStore) or not isinstance(comparisons, ComparisonStore):
            raise TypeError("AdoptionStore and ComparisonStore required")
        self.store, self.comparisons = store, comparisons
        self.scope = {"project": scope["project"], "task_family": scope["task_family"]} \
            if type(scope) is dict and set(scope) == {"project", "task_family"} else scope
        self.params = dict(partition=partition, max_bytes=max_bytes, query=query,
                           max_records=max_records)
        if comparisons.read_only:
            comparisons.db.execute("SELECT plan_id, context, context_sha256 FROM frozen_contexts LIMIT 0")
        else:
            comparisons.db.execute("""CREATE TABLE IF NOT EXISTS frozen_contexts (
                plan_id TEXT PRIMARY KEY, context BLOB NOT NULL, context_sha256 TEXT NOT NULL)""")

    # ---- live read-only observation -----------------------------------------
    def _bundle(self):
        bundle = retrieve_reference_bundle(self.store, scope=self.scope, **self.params)
        document = bundle.document
        if document["scope"] != self.scope or document["partition"] != self.params["partition"]:
            _fail("scope_mismatch", "retrieval returned another scope or partition")
        return bundle

    def _evidence(self, reference):
        """Fetch one evidence item and verify it against the retrieval reference."""
        event_id = reference.get("event_id")
        stored = self.store.get(event_id)  # missing / unreadable raises: fail closed
        for name, data in (("event_sha256", stored.event_bytes),
                           ("source_sha256", stored.source_bytes)):
            expected = reference.get(name)
            if (type(expected) is not str or type(data) is not bytes
                    or sha256_hex(data) != expected or getattr(stored, name) != expected):
                _fail("evidence_mismatch", "stored evidence bytes differ from the reference")
        if reference.get("provenance_sha256") != stored.provenance_sha256:
            _fail("evidence_mismatch", "stored provenance differs from the reference")
        if (stored.project, stored.task_family) != (self.scope["project"],
                                                    self.scope["task_family"]):
            _fail("scope_mismatch", "evidence belongs to another scope")
        if stored.provenance["partition"]["evaluation"] != self.params["partition"]:
            _fail("partition_mismatch", "evidence belongs to another partition")
        if not self.store.verify(event_id).ok:
            _fail("evidence_mismatch", "stored evidence fails its integrity recheck")
        try:
            event, source = stored.event_bytes.decode("utf-8"), stored.source_bytes.decode("utf-8")
        except UnicodeDecodeError:
            _fail("evidence_not_text", "only UTF-8 synthetic evidence can be frozen")
        return _encode({"kind": "raw_source", "event_id": event_id,
                        "event_sha256": reference["event_sha256"],
                        "source_sha256": reference["source_sha256"],
                        "event": event, "source": source}).decode("ascii")

    def _observe(self):
        """Current eligible context: (bundle, raw items, consolidated items, event refs)."""
        bundle = self._bundle()
        document = bundle.document
        if document["snapshot_sha256"] is None or not document["records"]:
            raise ValueError("no eligible adopted records to freeze")
        raw, consolidated, events, seen = [], [], [], set()
        for record in document["records"]:
            if record["eligibility"] != "verified":  # set by retrieval, never by the caller
                _fail("not_eligible", "record lacks the retrieval eligibility recheck")
            for reference in record["evidence"]:
                if reference["event_id"] in seen:
                    continue
                seen.add(reference["event_id"])
                raw.append(self._evidence(reference))
                events.append({"event_id": reference["event_id"],
                               "event_sha256": reference["event_sha256"],
                               "source_sha256": reference["source_sha256"]})
            consolidated.append(_encode({
                "kind": "consolidated_record", "memory_id": record["memory_id"],
                "memory_sha256": record["memory_sha256"], "rank": record["rank"],
                "evidence": record["evidence"], "memory": record["memory"]}).decode("ascii"))
        confirm = self._bundle().document  # separate read: detects, does not prevent, races
        if (confirm["snapshot_sha256"], confirm["policy"], confirm["records"]) != (
                document["snapshot_sha256"], document["policy"], document["records"]):
            _fail("changed_during_read", "store changed while evidence was being read")
        return bundle, raw, consolidated, events

    # ---- frozen context -------------------------------------------------------
    def _saved(self, plan_id):
        row = self.comparisons.db.execute(
            "SELECT context, context_sha256 FROM frozen_contexts WHERE plan_id=?",
            (plan_id,)).fetchone()
        if row is None:
            return None
        data = bytes(row[0])
        if sha256_hex(data) != row[1]:
            _fail("context_corrupt", "saved frozen context fails its hash")
        return data

    def frozen(self, plan_id):
        data = self._saved(plan_id)
        if data is None:
            raise ValueError("unknown frozen context")
        return loads_strict_bytes(data)

    def plan(self, *, plan_id, tasks, config, model, evaluator_identity,
             budget=ArmBudget(), declared_role="development", diagnostic_only=False):
        """Freeze the live context once; an identical reopen reuses the saved bytes."""
        data, created = self._saved(plan_id), False
        if data is None:
            bundle, raw, consolidated, events = self._observe()
            document = bundle.document
            data = _encode(dict(
                version=1, representation=REPRESENTATION, complete_raw_baseline=False,
                synthetic_only=True, scope=self.scope, retrieval=self.params,
                bundle_sha256=bundle.bundle_sha256, as_of=document["as_of"],
                snapshot_sha256=document["snapshot_sha256"],
                policy_sha256=document["policy"]["sha256"],
                policy_revision=document["policy"]["revision"],
                events=events, raw=raw, consolidated=consolidated))
            self.comparisons.db.execute(
                "INSERT INTO frozen_contexts VALUES (?,?,?)", (plan_id, data, sha256_hex(data)))
            created = True
        context = loads_strict_bytes(data)
        try:
            return self.comparisons.plan(
                plan_id=plan_id, tasks=tasks, raw_references=context["raw"],
                consolidated_records=context["consolidated"],
                config={"caller": config, "representation": REPRESENTATION,
                        "retrieval": self.params, "context_sha256": sha256_hex(data)},
                model=model, scope=self.scope, snapshot_sha256=context["snapshot_sha256"],
                policy_sha256=context["policy_sha256"], evaluator_identity=evaluator_identity,
                declared_role=declared_role, budget=budget, diagnostic_only=diagnostic_only)
        except BaseException:
            if created:
                self.comparisons.db.execute(
                    "DELETE FROM frozen_contexts WHERE plan_id=?", (plan_id,))
            raise

    def current(self, plan_id):
        """Live recheck through the read-only retrieval boundary. Any failure or any
        difference from the frozen whole records yields a non-matching observation,
        which makes ``ComparisonStore`` invalidate the plan (sticky)."""
        context = self.frozen(plan_id)
        try:
            bundle, raw, consolidated, _ = self._observe()
        except Exception as exc:  # fail closed: withdrawal, corruption, missing evidence
            return {"policy_sha256": None, "snapshot_sha256": None,
                    "failure": getattr(exc, "code", type(exc).__name__)}
        observed = {"policy_sha256": bundle.document["policy"]["sha256"],
                    "snapshot_sha256": bundle.document["snapshot_sha256"]}
        if raw != context["raw"] or consolidated != context["consolidated"]:
            observed["context"] = "changed"
        return observed

    def run(self, plan_id, provider, evaluator, limit=None):
        return self.comparisons.run(plan_id, provider, evaluator,
                                    lambda: self.current(plan_id), limit=limit)

    def report(self, plan_id):
        context = self.frozen(plan_id)
        document = self.comparisons.report(plan_id, lambda: self.current(plan_id))
        document.update(
            representation=REPRESENTATION, complete_raw_baseline=False,
            scientific_fairness_claim=None,
            context_sha256=sha256_hex(self._saved(plan_id)),
            frozen_events=context["events"], retrieval=context["retrieval"])
        return document
