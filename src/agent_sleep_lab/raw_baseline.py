"""Gate 4D: independent raw-evidence baseline and read-only per-arm request audit.

Raw evidence is selected from the accepted evidence store by a bounded scan of
one exact scope and partition, INDEPENDENTLY of which memories cite it (Gate 4C
``source_matched_fixture`` is unchanged in ``retrieval_comparison``). Both arms
get the same frozen whole raw prefix under the same ``ArmBudget``; arm B may add
currently eligible consolidated records returned by the existing retrieval.

Eligibility reuses trusted existing checks: ``RuntimeStore._evidence_failures``
(integrity, expiry, authorization, purpose, partition acceptance, exclusions,
synthetic flag, over every ancestor and root), ``retrieval._closure`` (ancestor
partitions) and ``INDEPENDENT_ORIGINS`` (generated/reflection origins rejected).
Caller text is never read as verification or permission. Read-only towards the
accepted store. Offline fake provider / synthetic evaluator only.

Not claimed: retrieval quality, fairness, performance, authentication, delivery.
The scan is one read transaction, but the memory retrieval that follows and every
later live recheck are separate reads, and a change between a recheck and the fake
dispatch that follows it is not excluded.
"""
from __future__ import annotations

from agent_sleep_lab.ab_comparison import ArmBudget, _encode
from agent_sleep_lab.adoption_store import _check_v3
from agent_sleep_lab.provenance import INDEPENDENT_ORIGINS, ContractViolation, sha256_hex
from agent_sleep_lab.retrieval import SERVED_PARTITIONS, _check_scope, _closure
from agent_sleep_lab.retrieval_comparison import RetrievalComparison, _fail
from agent_sleep_lab.strictjson import loads_strict_bytes

REPRESENTATION = "independent_raw_baseline"
ORDER = "event_id_ascending"
# ComparisonStore binds a 64-hex snapshot value; a scope with no adopted head binds this label.
NO_SNAPSHOT = sha256_hex(b"agent-sleep-lab:no-adopted-snapshot")
_INELIGIBLE = frozenset({"evidence.authorization.expired", "evidence.not_synthetic"})
AUDIT_STATUS = {None: "planned_not_dispatched", "intent": "dispatch_intent_outcome_unknown"}


class RawBaselineComparison(RetrievalComparison):
    def __init__(self, store, comparisons, *, scope, max_bytes, partition="experience",
                 query=None, max_records=16, scan_limit=256, max_raw=16):
        super().__init__(store, comparisons, scope=_check_scope(scope), max_bytes=max_bytes,
                         partition=partition, query=query, max_records=max_records)
        for name, value, ceiling in (("scan_limit", scan_limit, 4096), ("max_raw", max_raw, 64)):
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError("invalid cap: " + name)
        self.rules = dict(order=ORDER, scan_limit=scan_limit, max_raw=max_raw,
                          origins=sorted(INDEPENDENT_ORIGINS), partition=partition,
                          memory_retrieval=self.params)

    # ---- live read-only observation -----------------------------------------
    def _scan(self):
        """One read transaction: policy, head and every evidence row of the exact scope."""
        store, scope, partition = self.store, self.scope, self.params["partition"]
        if partition not in SERVED_PARTITIONS:
            raise ContractViolation("retrieval.partition_not_served", "partition is not served")
        counts = dict(scanned=0, eligible=0, selected=0, dropped_by_cap=0, other_partition=0,
                      non_evidence_origin=0, policy_excluded=0, ineligible=0)
        eligible = []
        with store._read_transaction():
            _check_v3(store._db())
            now, policy = store._now(), store.current_policy()  # missing/corrupt raises
            if partition not in policy.document["accepted_partitions"]:
                raise ContractViolation("retrieval.partition_not_accepted",
                                        "policy does not accept partition")
            head = store._head(scope)  # None when nothing was ever adopted
            limit = self.rules["scan_limit"]
            rows = store._rows(
                "SELECT event_id FROM evidence WHERE project = ? AND task_family = ? "
                "ORDER BY event_id LIMIT ?", (scope["project"], scope["task_family"], limit + 1))
            if len(rows) > limit:  # never silently omit a tail
                _fail("raw_scan_exceeds_cap", "scope holds more evidence than scan_limit")
            for (event_id,) in rows:
                counts["scanned"] += 1
                stored = store.get(event_id)  # missing source / unreadable provenance raises
                hashes = {"event_id": event_id, "event_sha256": stored.event_sha256,
                          "source_sha256": stored.source_sha256,
                          "provenance_sha256": stored.provenance_sha256}
                failures = set()
                store._evidence_failures(hashes, policy.document, now, failures)
                if (sha256_hex(stored.event_bytes) != stored.event_sha256
                        or sha256_hex(stored.source_bytes) != stored.source_sha256
                        or any(not code.startswith("policy.") and code not in _INELIGIBLE
                               for code in failures)):
                    _fail("evidence_mismatch", "stored evidence fails its integrity recheck")
                if (stored.project, stored.task_family) != (scope["project"],
                                                            scope["task_family"]):
                    _fail("scope_mismatch", "evidence belongs to another scope")
                if stored.provenance["partition"]["evaluation"] != partition:
                    counts["other_partition"] += 1
                    continue
                if stored.provenance["origin"] not in INDEPENDENT_ORIGINS:
                    counts["non_evidence_origin"] += 1  # summaries, recall, REM, diary, answers
                    continue
                if failures:
                    key = ("policy_excluded" if any(c.startswith("policy.") for c in failures)
                           else "ineligible")  # e.g. expired, lineage, not synthetic
                    counts[key] += 1
                    continue
                origins, partitions = _closure(store, [event_id])
                if partitions != {partition} or not origins <= INDEPENDENT_ORIGINS:
                    counts["ineligible"] += 1
                    continue
                try:
                    event = stored.event_bytes.decode("utf-8")
                    source = stored.source_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    _fail("evidence_not_text", "only UTF-8 synthetic evidence can be frozen")
                eligible.append((hashes, _encode(dict(
                    hashes, kind="raw_source", event=event, source=source)).decode("ascii")))
        counts["eligible"] = len(eligible)
        selected = eligible[:self.rules["max_raw"]]
        counts["selected"] = len(selected)
        counts["dropped_by_cap"] = len(eligible) - len(selected)
        return policy, head, eligible, selected, counts

    def _observe(self):
        policy, head, eligible, selected, counts = self._scan()
        if not selected:
            raise ValueError("no eligible raw evidence to freeze")
        document = self._bundle().document  # separate read transaction (existing retrieval)
        if document["snapshot_sha256"] != head or document["policy"]["sha256"] != policy.sha256:
            _fail("changed_during_read", "store changed between the raw scan and retrieval")
        memories, consolidated = [], []
        for record in document["records"]:
            if record["eligibility"] != "verified":  # set by retrieval, never by the caller
                _fail("not_eligible", "record lacks the retrieval eligibility recheck")
            memories.append({"memory_id": record["memory_id"],
                             "memory_sha256": record["memory_sha256"]})
            consolidated.append(_encode({
                "kind": "consolidated_record", "memory_id": record["memory_id"],
                "memory_sha256": record["memory_sha256"], "rank": record["rank"],
                "evidence": record["evidence"], "memory": record["memory"]}).decode("ascii"))
        all_events = [hashes for hashes, _ in eligible]
        return dict(
            policy_sha256=policy.sha256, policy_revision=policy.revision, snapshot_sha256=head,
            snapshot_binding=head or NO_SNAPSHOT,
            eligible_set_sha256=sha256_hex(_encode({"raw": all_events, "memories": memories})),
            events=[hashes for hashes, _ in selected], memories=memories,
            raw=[text for _, text in selected], consolidated=consolidated, counts=counts,
            raw_coverage=("truncated_by_max_raw" if counts["dropped_by_cap"]
                          else "all_eligible_within_bounded_scan"),
            memory_counts=document["counts"],
            memory_coverage=("truncated_by_retrieval_caps" if document["counts"]["dropped"]
                             else "all_eligible_returned"))

    # ---- frozen plan ----------------------------------------------------------
    def frozen(self, plan_id):
        context = super().frozen(plan_id)
        if context.get("representation") != REPRESENTATION:
            raise ValueError("plan binding conflict")
        return context

    def plan(self, *, plan_id, tasks, config, model, evaluator_identity,
             budget=ArmBudget(), declared_role="development"):
        """Freeze once; an identical reopen reuses the saved bytes without a new scan."""
        data, created = self._saved(plan_id), False
        if data is None:
            data = _encode(dict(
                self._observe(), version=1, representation=REPRESENTATION, synthetic_only=True,
                scope=self.scope, rules=self.rules, caller_config=config, fairness_claim=None))
            self.comparisons.db.execute(
                "INSERT INTO frozen_contexts VALUES (?,?,?)", (plan_id, data, sha256_hex(data)))
            created = True
        context = loads_strict_bytes(data)
        try:
            if context.get("representation") != REPRESENTATION:
                raise ValueError("plan binding conflict")  # e.g. a Gate 4C context
            return self.comparisons.plan(
                plan_id=plan_id, tasks=tasks, raw_references=context["raw"],
                consolidated_records=context["consolidated"],
                config={"caller": config, "representation": REPRESENTATION,
                        "rules": self.rules, "context_sha256": sha256_hex(data)},
                model=model, scope=self.scope, snapshot_sha256=context["snapshot_binding"],
                policy_sha256=context["policy_sha256"], evaluator_identity=evaluator_identity,
                declared_role=declared_role, budget=budget)
        except BaseException:
            if created:
                self.comparisons.db.execute(
                    "DELETE FROM frozen_contexts WHERE plan_id=?", (plan_id,))
            raise

    def current(self, plan_id):
        """Live recheck; any failure or difference yields a non-matching observation."""
        context = self.frozen(plan_id)
        try:
            if context["scope"] != self.scope or context["rules"] != self.rules:
                raise ValueError("plan binding conflict")
            live = self._observe()
        except Exception as exc:  # fail closed: revoked, corrupt, expired, missing
            return {"policy_sha256": None, "snapshot_sha256": None,
                    "failure": getattr(exc, "code", type(exc).__name__)}
        observed = {"policy_sha256": live["policy_sha256"],
                    "snapshot_sha256": live["snapshot_binding"]}
        if any(live[key] != context[key] for key in
               ("eligible_set_sha256", "raw", "consolidated", "events", "memories")):
            observed["context"] = "changed"
        return observed

    def report(self, plan_id):
        context = self.frozen(plan_id)
        document = self.comparisons.report(plan_id, lambda: self.current(plan_id))
        document.update(
            representation=REPRESENTATION, scientific_fairness_claim=None,
            context_sha256=sha256_hex(self._saved(plan_id)), rules=context["rules"],
            raw_counts=context["counts"], raw_coverage=context["raw_coverage"],
            memory_coverage=context["memory_coverage"],
            complete_raw_baseline=False,  # bounded synthetic scan; no completeness claim
            eligible_set_sha256=context["eligible_set_sha256"])
        return document

    # ---- read-only audit ------------------------------------------------------
    def audit(self, plan_id):
        """What each arm's immutable packed request contains, plus its durable status.

        Never writes, dispatches or resends. A persisted intent is reported as an
        unknown outcome; nothing here confirms delivery, reading or use.
        """
        context = self.frozen(plan_id)
        plan, digest, status, reason, _ = self.comparisons._plan(plan_id)  # verifies plan hash
        bound_config = {"caller": context["caller_config"], "representation": REPRESENTATION,
                        "rules": context["rules"],
                        "context_sha256": sha256_hex(self._saved(plan_id))}
        if (plan["config_sha256"] != sha256_hex(_encode(bound_config))
                or plan["scope"] != context["scope"]
                or plan["raw_references_sha256"] != sha256_hex(_encode(context["raw"]))
                or plan["consolidated_records_sha256"] != sha256_hex(_encode(context["consolidated"]))
                or plan["policy_sha256"] != context["policy_sha256"]
                or plan["snapshot_sha256"] != context["snapshot_binding"]):
            _fail("audit_binding_mismatch", "plan is not bound to this frozen context")
        if (len(context["raw"]) != len(context["events"])
                or len(context["consolidated"]) != len(context["memories"])):
            _fail("audit_binding_mismatch", "frozen membership lengths differ")
        raw = dict(zip(context["raw"], context["events"]))
        memo = dict(zip(context["consolidated"], context["memories"]))
        rows = {(r[0], r[1]): (r[2], r[3], r[4]) for r in self.comparisons.db.execute(
            "SELECT task_index, arm, status, request_sha256, position FROM comparison_arms "
            "WHERE plan_id=?", (plan_id,))}
        if not set(rows) <= {(i, a) for i in range(len(plan["tasks"])) for a in "AB"}:
            _fail("audit_request_mismatch", "unexpected durable arm identity")
        arms = []
        for index, task in enumerate(plan["tasks"]):
            for arm in "AB":
                entry = task[arm]
                request = entry["request"].encode("ascii")
                position = task["order"].index(arm)
                state, recorded, saved_position = rows.get(
                    (index, arm), (None, entry["request_sha256"], position))
                if (state not in (None, "intent", "replied", "completed", "timeout", "missing", "invalid")
                        or saved_position != position):
                    _fail("audit_request_mismatch", "invalid durable arm status or position")
                if sha256_hex(request) != entry["request_sha256"] or recorded != entry["request_sha256"]:
                    _fail("audit_request_mismatch", "request hash differs from the plan")
                items = loads_strict_bytes(request)["context"]
                offered = list(raw) + (list(memo) if arm == "B" else [])
                if (type(entry["included"]) is not int or not 0 <= entry["included"] <= len(offered)
                        or items != offered[:entry["included"]]
                        or entry["dropped"] != len(offered) - len(items)
                        or entry["request_bytes"] != len(request)
                        or len(request) > plan["budget"]["request_bytes"]):
                    _fail("audit_request_mismatch", "request differs from its frozen whole prefix")
                arms.append({
                    "plan_id": plan_id, "task_index": index, "arm": arm,
                    "task_id": task["task_id"], "position": task["order"].index(arm),
                    "request_sha256": entry["request_sha256"],
                    "request_bytes": entry["request_bytes"],
                    "status": AUDIT_STATUS.get(state, state),
                    "outcome_known": state not in (None, "intent"),
                    "delivery_confirmed": None,  # not observable from this harness
                    "raw_present": [raw[i] for i in items if i in raw],
                    "memories_present": [memo[i] for i in items if i in memo],
                    "raw_dropped": [raw[i] for i in offered if i in raw and i not in items],
                    "memories_dropped": [memo[i] for i in offered if i in memo and i not in items],
                })
        return {"plan_id": plan_id, "plan_sha256": digest, "status": status, "reason": reason,
                "representation": REPRESENTATION,
                "context_sha256": sha256_hex(self._saved(plan_id)),
                "delivery_claim": None, "arms": arms}
