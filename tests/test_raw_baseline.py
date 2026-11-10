"""Five offline Gate 4D cases: independent raw baseline and per-arm request audit.

Fake provider, synthetic scores, fictional fixture. Not a performance experiment.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import support  # noqa: F401
from evidence_support import StoreCase, make_item
from runtime_support import make_control, policy_body
import test_adoption_store as writer_fixtures
import test_retrieval as retrieval_fixtures
import paper_fixture
from agent_sleep_lab.ab_comparison import (
    ArmBudget, ComparisonStore, FakeTaskProvider, SyntheticEvaluator,
)
from agent_sleep_lab.provenance import ContractViolation, StorageError, sha256_hex
from agent_sleep_lab.raw_baseline import RawBaselineComparison

SCOPE = {"project": "p", "task_family": "t"}
OTHER = {"project": "q", "task_family": "u"}
BIG = ArmBudget(calls=4, request_bytes=65536, reply_bytes=64)
# Fictional, cited by no memory: proves raw selection does not follow consolidation.
UNCITED = ("FICTIONAL NOTE. Invented preprint 'Salt Clocks of the Paper Harbour' (no such "
           "paper). Curator log: the invented venue line was left blank.")
LATE = "FICTIONAL NOTE. Invented preprint 'A Ladder Made of Rain' (no such paper)."


def fake_reply(request):
    return (b"fixture-reply-with-records" if b"consolidated_record" in request
            else b"fixture-reply-raw-only")


EVALUATOR = SyntheticEvaluator(
    "raw-baseline-fixture-score", "1", "9" * 64,
    lambda task_id, reply: int(reply == paper_fixture.EVALUATOR_KEY[task_id]))


def ids(items, key="event_id"):
    return [item[key] for item in items]


class RawBaselineTests(StoreCase):
    open_adoption = writer_fixtures.AdoptionTests.open_adoption
    setup_store = writer_fixtures.AdoptionTests.setup_store
    adopt = retrieval_fixtures.RetrievalTests.adopt

    def evidence_store(self):
        """e-1/e-2 (later cited), e-3 (never cited), e-4 (generated recall of e-1)."""
        store = self.open_adoption()
        for event_id, text in paper_fixture.EXPERIENCE_SOURCES.items():
            self.put(store, make_item(event_id, text=text))
        self.put(store, make_item("e-3", text=UNCITED))
        self.put(store, make_item("e-4", derived_from=["e-1"], origin="recall", root="e-1"))
        store.set_policy(make_control(), policy_body(), expected_revision=0)
        return store

    def adopt_fixture(self, store):
        parent = None
        for memory_id, (event_id, claim) in paper_fixture.CONSOLIDATED_CLAIMS.items():
            parent = self.adopt(store, memory_id, event_id, claim=claim, parent=parent)

    def paper_store(self):
        store = self.evidence_store()
        self.adopt_fixture(store)
        return store

    def comparisons(self):
        comparisons = ComparisonStore(Path(self.dir) / "comparison.sqlite")
        self.addCleanup(comparisons.close)
        return comparisons

    def adapter(self, store, comparisons=None, **override):
        params = dict(scope=SCOPE, max_bytes=1_000_000)
        params.update(override)
        return RawBaselineComparison(store, comparisons or self.comparisons(), **params)

    def plan(self, adapter, plan_id="raw-1", **override):
        params = dict(plan_id=plan_id, tasks=paper_fixture.TASKS, config={"fixture": "raw"},
                      model="fake-model-1", evaluator_identity=EVALUATOR.identity(), budget=BIG)
        params.update(override)
        return adapter.plan(**params)

    def arm(self, audit, index, arm):
        return next(a for a in audit["arms"] if (a["task_index"], a["arm"]) == (index, arm))

    def test_uncited_raw_is_selected_independently_and_without_adopted_memory(self):
        store = self.evidence_store()
        adapter = self.adapter(store)
        self.plan(adapter)
        frozen = adapter.frozen("raw-1")
        self.assertEqual(ids(frozen["events"]), ["e-1", "e-2", "e-3"])
        self.assertEqual((frozen["snapshot_sha256"], frozen["memories"]), (None, []))
        counts = frozen["counts"]
        self.assertEqual((counts["scanned"], counts["eligible"], counts["selected"],
                          counts["non_evidence_origin"], counts["dropped_by_cap"]),
                         (4, 3, 3, 1, 0))
        self.assertEqual(frozen["raw_coverage"], "all_eligible_within_bounded_scan")
        provider = FakeTaskProvider(default=fake_reply)
        self.assertEqual(adapter.run("raw-1", provider, EVALUATOR)["status"], "complete")
        self.assertEqual(len(provider.requests), 4)
        for request in provider.requests:
            for answer in paper_fixture.EVALUATOR_KEY.values():
                self.assertNotIn(answer, request)
        for entry in adapter.audit("raw-1")["arms"]:  # A works with a null snapshot
            self.assertEqual((ids(entry["raw_present"]), entry["memories_present"]),
                             (["e-1", "e-2", "e-3"], []))
        report = adapter.report("raw-1")
        self.assertEqual(report["comparison"]["paired"]["neither"], 2)
        for name in ("performance_claim", "adoption_receipt", "scientific_fairness_claim"):
            self.assertIsNone(report[name])
        self.adopt_fixture(store)  # memories cite only e-1 and e-2
        head = store.current_snapshot(SCOPE)
        self.plan(adapter, plan_id="raw-2")
        after = adapter.frozen("raw-2")
        self.assertEqual(ids(after["events"]), ["e-1", "e-2", "e-3"])  # e-3 stays, uncited
        self.assertEqual(ids(after["memories"], "memory_id"), ["m-1", "m-2"])
        self.assertEqual(after["snapshot_sha256"], sha256_hex(head))
        self.assertEqual(store.current_snapshot(SCOPE), head)  # read-only
        capped = self.adapter(store, adapter.comparisons, max_raw=2)
        self.plan(capped, plan_id="raw-3")
        truncated = capped.frozen("raw-3")
        self.assertEqual((ids(truncated["events"]), truncated["counts"]["dropped_by_cap"],
                          truncated["raw_coverage"]),
                         (["e-1", "e-2"], 1, "truncated_by_max_raw"))

    def test_exact_scope_partition_policy_and_integrity_fail_closed(self):
        store = self.setup_store()
        store.set_policy(make_control(), policy_body(partitions=("experience", "development")),
                         expected_revision=1)
        self.put(store, make_item("e-2", evaluation="development"))
        self.put(store, make_item("e-9", scope=("q", "u")))
        comparisons = self.comparisons()

        def frozen_ids(plan_id, **override):
            adapter = self.adapter(store, comparisons, **override)
            self.plan(adapter, plan_id=plan_id)
            return ids(adapter.frozen(plan_id)["events"])

        self.assertEqual(frozen_ids("exp"), ["e-1"])
        self.assertEqual(frozen_ids("dev", partition="development"), ["e-2"])
        self.assertEqual(frozen_ids("other", scope=OTHER), ["e-9"])
        self.assertRaisesCode(ContractViolation, "retrieval.partition_not_served",
                              lambda: frozen_ids("holdout", partition="evaluation"))
        self.assertRaisesCode(StorageError, "comparison.raw_scan_exceeds_cap",
                              lambda: frozen_ids("capped", scan_limit=1))
        real_get = store.get

        def corrupt(event_id):
            stored = real_get(event_id)
            if event_id == "e-2":
                stored = dataclasses.replace(stored, source_bytes=b"altered fictional note")
            return stored

        def missing(event_id):
            if event_id == "e-2":
                raise StorageError("storage.source_missing", "original source bytes are missing")
            return real_get(event_id)

        store.get = corrupt
        self.assertRaisesCode(StorageError, "comparison.evidence_mismatch",
                              lambda: frozen_ids("dev-2", partition="development"))
        store.get = missing
        self.assertRaisesCode(StorageError, "storage.source_missing",
                              lambda: frozen_ids("dev-2", partition="development"))
        store.get = real_get
        store.set_policy(make_control(), policy_body(
            partitions=("experience", "development"), event_ids=("e-1",)), expected_revision=2)
        with self.assertRaisesRegex(ValueError, "no eligible raw evidence"):
            frozen_ids("exp-2")  # current exclusion, not historical capture, decides
        for plan_id in ("holdout", "capped", "dev-2", "exp-2"):
            with self.assertRaises(ValueError):
                comparisons.inspect(plan_id)  # nothing planned or frozen
        state = self.adapter(store, comparisons).run(
            "exp", FakeTaskProvider(default=fake_reply), EVALUATOR)
        self.assertEqual(state["status"], "invalidated")  # frozen e-1 was revoked

    def test_frozen_reopen_binding_and_eligible_set_invalidation(self):
        store = self.paper_store()
        comparisons = self.comparisons()
        adapter = self.adapter(store, comparisons)
        digest = self.plan(adapter)
        saved = adapter.frozen("raw-1")
        for name in ("policy_sha256", "eligible_set_sha256", "snapshot_sha256"):
            self.assertRegex(saved[name], "^[0-9a-f]{64}$")
        self.assertEqual(saved["rules"]["order"], "event_id_ascending")
        for event in saved["events"]:
            stored = store.get(event["event_id"])
            self.assertEqual((event["event_sha256"], event["source_sha256"],
                              event["provenance_sha256"]),
                             (stored.event_sha256, stored.source_sha256,
                              stored.provenance_sha256))
        path = comparisons.db.execute("PRAGMA database_list").fetchone()[2]
        reopened = self.adapter(store, ComparisonStore(path))
        self.addCleanup(reopened.comparisons.close)
        self.assertEqual(self.plan(reopened), digest)
        self.assertEqual(reopened.frozen("raw-1"), saved)
        with self.assertRaisesRegex(ValueError, "plan binding conflict"):
            self.plan(self.adapter(store, reopened.comparisons, max_raw=2))
        with self.assertRaisesRegex(ValueError, "plan binding conflict"):
            self.plan(reopened, model="fake-model-2")
        provider = FakeTaskProvider(default=fake_reply)
        self.assertEqual(reopened.run("raw-1", provider, EVALUATOR, limit=1)["status"], "running")
        policy, head = store.current_policy().sha256, store.current_snapshot(SCOPE)
        self.put(store, make_item("e-6", text=LATE))  # eligible set grows; policy/head do not
        self.assertEqual((store.current_policy().sha256, store.current_snapshot(SCOPE)),
                         (policy, head))
        self.assertEqual(reopened.run("raw-1", provider, EVALUATOR)["status"], "invalidated")
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(self.plan(reopened), digest)  # reopen cannot refresh a frozen context
        self.assertEqual(reopened.frozen("raw-1"), saved)
        self.assertEqual(reopened.run("raw-1", provider, EVALUATOR)["status"], "invalidated")
        self.assertEqual(len(provider.requests), 1)
        self.assertIsNone(reopened.report("raw-1")["comparison"])

    def test_equal_whole_record_budgets_have_exact_audit_membership(self):
        store = self.paper_store()
        adapter = self.adapter(store)
        self.plan(adapter)
        frozen = adapter.frozen("raw-1")
        audit = adapter.audit("raw-1")
        self.assertIsNone(audit["delivery_claim"])
        for index in (0, 1):
            a, b = self.arm(audit, index, "A"), self.arm(audit, index, "B")
            self.assertEqual(a["raw_present"], frozen["events"])
            self.assertEqual(b["raw_present"], frozen["events"])  # same whole raw prefix
            self.assertEqual((a["memories_present"], b["memories_present"]),
                             ([], frozen["memories"]))
            self.assertEqual(a["raw_dropped"] + a["memories_dropped"]
                             + b["raw_dropped"] + b["memories_dropped"], [])
            self.assertEqual((a["status"], a["delivery_confirmed"]),
                             ("planned_not_dispatched", None))
        size_a = self.arm(audit, 0, "A")["request_bytes"]
        for plan_id, cap, kept in (("tight", size_a + 20, 3), ("one", size_a - 1, 2)):
            self.plan(adapter, plan_id=plan_id,
                      budget=ArmBudget(calls=4, request_bytes=cap, reply_bytes=64))
            small = adapter.audit(plan_id)
            a, b = self.arm(small, 0, "A"), self.arm(small, 0, "B")
            self.assertEqual(a["raw_present"], frozen["events"][:kept])  # whole records only
            self.assertEqual(b["raw_present"], a["raw_present"])
            self.assertEqual(a["raw_dropped"], frozen["events"][kept:])
            self.assertEqual(b["raw_dropped"], a["raw_dropped"])
            self.assertEqual((b["memories_present"], b["memories_dropped"]),
                             ([], frozen["memories"]))
            self.assertEqual(a["request_sha256"], b["request_sha256"])  # same bytes, two arms
            self.assertNotEqual((a["task_index"], a["arm"]), (b["task_index"], b["arm"]))
            self.assertLessEqual(b["request_bytes"], cap)
        provider = FakeTaskProvider(default=fake_reply)
        self.assertEqual(adapter.run("raw-1", provider, EVALUATOR)["status"], "complete")
        done = adapter.audit("raw-1")
        self.assertEqual({entry["status"] for entry in done["arms"]}, {"completed"})
        self.assertEqual([entry["delivery_confirmed"] for entry in done["arms"]], [None] * 4)
        self.assertEqual({entry["request_sha256"] for entry in done["arms"]},
                         {sha256_hex(request) for request in provider.requests})
        original = self.arm(done, 0, "A")["request_sha256"]
        adapter.comparisons.db.execute(
            "UPDATE comparison_arms SET request_sha256=? "
            "WHERE plan_id=? AND task_index=0 AND arm='A'", ("0" * 64, "raw-1"))
        self.assertRaisesCode(StorageError, "comparison.audit_request_mismatch",
                              lambda: adapter.audit("raw-1"))
        adapter.comparisons.db.execute(
            "UPDATE comparison_arms SET request_sha256=? "
            "WHERE plan_id=? AND task_index=0 AND arm='A'", (original, "raw-1"))
        self.assertEqual(adapter.audit("raw-1")["arms"], done["arms"])

    def test_partial_and_unknown_outcomes_are_audited_without_replay(self):
        store = self.paper_store()
        adapter = self.adapter(store)
        self.plan(adapter)
        with self.assertRaises(RuntimeError):
            adapter.run("raw-1", FakeTaskProvider(default=fake_reply,
                                                  script={1: RuntimeError("lost")}), EVALUATOR)
        audit = adapter.audit("raw-1")
        statuses = {(a["task_index"], a["arm"]): (a["status"], a["outcome_known"],
                                                  a["delivery_confirmed"]) for a in audit["arms"]}
        self.assertEqual(statuses, {
            (0, "A"): ("completed", True, None),
            (0, "B"): ("dispatch_intent_outcome_unknown", False, None),
            (1, "A"): ("planned_not_dispatched", False, None),
            (1, "B"): ("planned_not_dispatched", False, None)})
        unknown = self.arm(audit, 0, "B")  # membership comes from the plan, not from delivery
        self.assertEqual(ids(unknown["memories_present"], "memory_id"), ["m-1", "m-2"])
        path = adapter.comparisons.db.execute("PRAGMA database_list").fetchone()[2]
        reopened = self.adapter(store, ComparisonStore(path))
        self.addCleanup(reopened.comparisons.close)
        self.assertEqual(self.plan(reopened), audit["plan_sha256"])
        self.assertEqual(reopened.audit("raw-1")["arms"], audit["arms"])
        retry = FakeTaskProvider(default=fake_reply)
        self.assertEqual(reopened.run("raw-1", retry, EVALUATOR)["status"], "incomplete")
        self.assertEqual(retry.requests, [])
        self.assertEqual(adapter.audit("raw-1")["arms"], audit["arms"])  # audit never resends
        self.assertIsNone(adapter.report("raw-1")["comparison"])
        self.plan(adapter, plan_id="raw-2")
        partial = FakeTaskProvider(default=fake_reply, script={0: TimeoutError(), 1: None})
        self.assertEqual(adapter.run("raw-2", partial, EVALUATOR, limit=3)["status"], "running")
        second = adapter.audit("raw-2")
        self.assertEqual([(a["task_index"], a["arm"], a["status"]) for a in second["arms"]],
                         [(0, "A", "timeout"), (0, "B", "missing"),
                          (1, "A", "planned_not_dispatched"), (1, "B", "completed")])
        self.assertEqual(len(partial.requests), 3)
