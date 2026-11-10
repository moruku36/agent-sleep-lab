"""Five offline Gate 4C cases: accepted-store retrieval -> frozen source-matched comparison.

Fake provider, synthetic scores, fictional fixture. Not a performance experiment.
"""
from __future__ import annotations

import dataclasses
import json
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
from agent_sleep_lab.retrieval_comparison import RetrievalComparison

SCOPE = {"project": "p", "task_family": "t"}
OTHER = {"project": "q", "task_family": "u"}
BIG = ArmBudget(calls=4, request_bytes=65536, reply_bytes=64)


def fake_reply(request):
    # Fake behavior only: reacts to the presence of a consolidated record.
    return (b"fixture-reply-with-records" if b"consolidated_record" in request
            else b"fixture-reply-raw-only")


EVALUATOR = SyntheticEvaluator(
    "paper-fixture-score", "1", "f" * 64,
    lambda task_id, reply: int(reply == paper_fixture.EVALUATOR_KEY[task_id]))


def kinds(request):
    return [json.loads(item)["kind"] for item in json.loads(request)["context"]]


class RetrievalComparisonTests(StoreCase):
    open_adoption = writer_fixtures.AdoptionTests.open_adoption
    setup_store = writer_fixtures.AdoptionTests.setup_store
    adopt = retrieval_fixtures.RetrievalTests.adopt

    def paper_store(self):
        """Synthetic capture -> independent receipts -> adoption, via existing helpers."""
        store = self.open_adoption()
        for event_id, text in paper_fixture.EXPERIENCE_SOURCES.items():
            self.put(store, make_item(event_id, text=text))
        store.set_policy(make_control(), policy_body(), expected_revision=0)
        parent = None
        for memory_id, (event_id, claim) in paper_fixture.CONSOLIDATED_CLAIMS.items():
            parent = self.adopt(store, memory_id, event_id, claim=claim, parent=parent)
        return store

    def comparisons(self):
        comparisons = ComparisonStore(Path(self.dir) / "comparison.sqlite")
        self.addCleanup(comparisons.close)
        return comparisons

    def adapter(self, store, comparisons=None, **override):
        params = dict(scope=SCOPE, max_bytes=1_000_000)
        params.update(override)
        return RetrievalComparison(store, comparisons or self.comparisons(), **params)

    def plan(self, adapter, plan_id="paper-1", **override):
        params = dict(plan_id=plan_id, tasks=paper_fixture.TASKS, config={"fixture": "paper"},
                      model="fake-model-1", evaluator_identity=EVALUATOR.identity(), budget=BIG)
        params.update(override)
        return adapter.plan(**params)

    def test_adopted_store_retrieval_freezes_source_matched_paper_comparison(self):
        store = self.paper_store()
        head = store.current_snapshot(SCOPE)
        adapter = self.adapter(store)
        self.plan(adapter)
        provider = FakeTaskProvider(default=fake_reply)
        self.assertEqual(adapter.run("paper-1", provider, EVALUATOR)["status"], "complete")
        self.assertEqual(len(provider.requests), 4)
        for request in provider.requests:
            for key in paper_fixture.EVALUATOR_KEY.values():
                self.assertNotIn(key, request)
            items = [json.loads(item) for item in json.loads(request)["context"]]
            raw = [item for item in items if item["kind"] == "raw_source"]
            self.assertEqual([item["event_id"] for item in raw], ["e-1", "e-2"])
            for item in raw:  # exact stored bytes and hashes, not caller text
                stored = store.get(item["event_id"])
                self.assertEqual(item["source"].encode("utf-8"), stored.source_bytes)
                self.assertEqual(item["event"].encode("utf-8"), stored.event_bytes)
                self.assertEqual(item["source_sha256"], sha256_hex(stored.source_bytes))
                self.assertEqual(item["event_sha256"], stored.event_sha256)
            memo = [item for item in items if item["kind"] == "consolidated_record"]
            self.assertIn([item["memory_id"] for item in memo], ([], ["m-1", "m-2"]))
            self.assertEqual(items[:2], raw)  # B's raw prefix is A's whole context
        self.assertEqual(sorted(len(kinds(r)) for r in provider.requests), [2, 2, 4, 4])
        report = adapter.report("paper-1")
        frozen = adapter.frozen("paper-1")
        self.assertEqual(frozen["snapshot_sha256"], sha256_hex(head))
        self.assertEqual((report["representation"], report["complete_raw_baseline"]),
                         ("source_matched_fixture", False))
        self.assertEqual(report["comparison"]["paired"],
                         {"denominator": 2, "both": 0, "a_only": 0, "b_only": 2, "neither": 0})
        for name in ("performance_claim", "adoption_receipt", "measured_savings",
                     "scientific_fairness_claim"):
            self.assertIsNone(report[name])
        self.assertFalse(report["independent_holdout"])
        self.assertEqual(store.current_snapshot(SCOPE), head)  # read-only: head untouched

    def test_corrupt_or_missing_evidence_fails_closed_before_and_after_freeze(self):
        store = self.paper_store()
        comparisons = self.comparisons()
        adapter = self.adapter(store, comparisons)
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
                              lambda: self.plan(adapter))
        store.get = missing
        self.assertRaisesCode(StorageError, "storage.source_missing", lambda: self.plan(adapter))
        with self.assertRaises(ValueError):
            comparisons.inspect("paper-1")  # nothing was planned or frozen
        with self.assertRaises(ValueError):
            adapter.frozen("paper-1")
        store.get = real_get
        self.plan(adapter)
        store.get = corrupt  # evidence changes after the freeze
        provider = FakeTaskProvider(default=fake_reply)
        state = adapter.run("paper-1", provider, EVALUATOR)
        self.assertEqual((state["status"], provider.requests), ("invalidated", []))
        store.get = real_get  # restoring the bytes does not revive the plan
        self.assertEqual(adapter.run("paper-1", provider, EVALUATOR)["status"], "invalidated")
        self.assertEqual(provider.requests, [])
        self.assertIsNone(adapter.report("paper-1")["comparison"])

    def test_only_exact_scope_and_partition_records_are_frozen(self):
        store = self.setup_store()
        store.set_policy(make_control(), policy_body(partitions=("experience", "development")),
                         expected_revision=1)
        self.put(store, make_item("e-2", evaluation="development"))
        self.put(store, make_item("e-9", scope=("q", "u")))
        snap = self.adopt(store, "m-1", "e-1", revision=2)
        self.adopt(store, "m-2", "e-2", parent=snap, revision=2)
        self.adopt(store, "m-9", "e-9", scope=OTHER, revision=2)
        comparisons = self.comparisons()

        def frozen_ids(plan_id, **override):
            adapter = self.adapter(store, comparisons, **override)
            self.plan(adapter, plan_id=plan_id)
            context = adapter.frozen(plan_id)
            return ([e["event_id"] for e in context["events"]],
                    [json.loads(c)["memory_id"] for c in context["consolidated"]])

        self.assertEqual(frozen_ids("exp"), (["e-1"], ["m-1"]))
        self.assertEqual(frozen_ids("dev", partition="development"), (["e-2"], ["m-2"]))
        self.assertEqual(frozen_ids("other", scope=OTHER), (["e-9"], ["m-9"]))
        self.assertRaisesCode(ContractViolation, "retrieval.partition_not_served",
                              lambda: frozen_ids("holdout", partition="evaluation"))
        with self.assertRaisesRegex(ValueError, "no eligible"):
            frozen_ids("empty", scope={"project": "z", "task_family": "z"})
        with self.assertRaisesRegex(ValueError, "plan binding conflict"):
            frozen_ids("exp", partition="development")  # saved context is not re-scoped
        self.assertEqual(self.adapter(store, comparisons).frozen("exp")["retrieval"]["partition"],
                         "experience")

    def test_live_revocation_after_plan_blocks_next_dispatch_and_report(self):
        store = self.paper_store()
        comparisons = self.comparisons()
        adapter = self.adapter(store, comparisons)
        digest = self.plan(adapter)
        saved = adapter.frozen("paper-1")
        provider = FakeTaskProvider(default=fake_reply)
        self.assertEqual(adapter.run("paper-1", provider, EVALUATOR, limit=1)["status"], "running")
        store.set_policy(make_control(), policy_body(event_ids=("e-1",)), expected_revision=1)
        state = adapter.run("paper-1", provider, EVALUATOR)
        self.assertEqual((state["status"], state["reason"]),
                         ("invalidated", "policy_or_snapshot_changed"))
        self.assertEqual(len(provider.requests), 1)
        report = adapter.report("paper-1")
        self.assertEqual((report["status"], report["comparison"]), ("invalidated", None))
        self.assertIsNone(report["performance_claim"])
        reopened = self.adapter(store, ComparisonStore(comparisons.db.execute(
            "PRAGMA database_list").fetchone()[2]))
        self.addCleanup(reopened.comparisons.close)
        self.assertEqual(self.plan(reopened), digest)  # saved bytes, not a fresh freeze
        self.assertEqual(reopened.frozen("paper-1"), saved)
        self.assertEqual(reopened.run("paper-1", provider, EVALUATOR)["status"], "invalidated")
        self.assertEqual(len(provider.requests), 1)
        self.plan(reopened, plan_id="paper-2")  # a new plan sees only what is still eligible
        self.assertEqual([e["event_id"] for e in reopened.frozen("paper-2")["events"]], ["e-2"])

    def test_whole_record_budget_and_frozen_reopen_without_replay(self):
        store = self.paper_store()
        comparisons = self.comparisons()
        adapter = self.adapter(store, comparisons)
        digest = self.plan(adapter)
        first = comparisons._plan("paper-1")[0]["tasks"][0]
        self.assertEqual((first["A"]["included"], first["B"]["included"]), (2, 4))
        size_a = first["A"]["request_bytes"]
        for plan_id, cap, expected in (("tight", size_a + 20, ((2, 0), (2, 2))),
                                       ("one", size_a - 1, ((1, 1), (1, 3)))):
            with self.assertRaisesRegex(ValueError, "identical A/B"):
                self.plan(adapter, plan_id=plan_id,
                          budget=ArmBudget(calls=4, request_bytes=cap, reply_bytes=64))
            self.plan(adapter, plan_id=plan_id, diagnostic_only=True,
                      budget=ArmBudget(calls=4, request_bytes=cap, reply_bytes=64))
            task = comparisons._plan(plan_id)[0]["tasks"][0]
            self.assertEqual(((task["A"]["included"], task["A"]["dropped"]),
                              (task["B"]["included"], task["B"]["dropped"])), expected)
            a_context = json.loads(task["A"]["request"])["context"]
            self.assertEqual(json.loads(task["B"]["request"])["context"], a_context)
            self.assertEqual(a_context, adapter.frozen(plan_id)["raw"][:len(a_context)])  # whole
            self.assertLessEqual(task["B"]["request_bytes"], cap)
        before = FakeTaskProvider(default=fake_reply)
        self.assertEqual(adapter.run("paper-1", before, EVALUATOR, limit=3)["status"], "running")
        saved = adapter.frozen("paper-1")
        path = comparisons.db.execute("PRAGMA database_list").fetchone()[2]
        comparisons.close()
        reopened = self.adapter(store, ComparisonStore(path))
        self.addCleanup(reopened.comparisons.close)
        self.assertEqual(self.plan(reopened), digest)
        self.assertEqual(reopened.frozen("paper-1"), saved)
        after = FakeTaskProvider(default=fake_reply)
        self.assertEqual(reopened.run("paper-1", after, EVALUATOR)["status"], "complete")
        reopened.run("paper-1", after, EVALUATOR)
        self.assertEqual((len(before.requests), len(after.requests)), (3, 1))
        planned = {task[arm]["request"].encode("ascii")
                   for task in reopened.comparisons._plan("paper-1")[0]["tasks"] for arm in "AB"}
        self.assertEqual(set(before.requests + after.requests), planned)
