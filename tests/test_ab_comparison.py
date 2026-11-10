"""Five offline Gate 4B cases. Fake provider, synthetic scores; not a performance experiment."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401  (makes src importable)
from agent_sleep_lab.ab_comparison import ArmBudget, ComparisonStore, FakeTaskProvider, SyntheticEvaluator

SCOPE = {"project": "p", "task_family": "t"}
RAW = ["raw reference one", "raw reference two"]
MEMO = ["MEMO consolidated lesson"]
ANSWER = b"EVALUATOR-KEY"  # lives only in the trusted local evaluator


def tasks(count, prefix="t"):
    return [{"task_id": f"{prefix}-{i}", "prompt": f"synthetic prompt {i}"}
            for i in range(1, count + 1)]


def memo_aware(request):
    # Fake behavior only: a different reply when consolidated context is present.
    return b"used-memo" if b"MEMO" in request else b"raw-only"


def evaluator(task_id, reply):
    return int(reply == b"used-memo" and bool(ANSWER))


evaluator = SyntheticEvaluator("fixture-score", "1", "e" * 64, evaluator)


def arm_of(request):
    return "B" if MEMO[0] in json.loads(request)["context"] else "A"


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "comparison.sqlite"
        self.current = {"policy_sha256": "a" * 64, "snapshot_sha256": "b" * 64}

    def store(self):
        store = ComparisonStore(self.path)
        self.addCleanup(store.close)
        return store

    def observe(self):
        return dict(self.current)

    def params(self, **override):
        params = dict(plan_id="plan-1", tasks=tasks(4), raw_references=RAW,
                      consolidated_records=MEMO, config={"fixture": "1"},
                      model="fake-model-1", scope=SCOPE, declared_role="development",
                      evaluator_identity=evaluator.identity(),
                      snapshot_sha256=self.current["snapshot_sha256"],
                      policy_sha256=self.current["policy_sha256"],
                      budget=ArmBudget(calls=8, request_bytes=1024, reply_bytes=64))
        params.update(override)
        return params

    def test_paired_arms_are_isolated_ordered_and_reported_without_claims(self):
        store = self.store()
        store.plan(**self.params())
        provider = FakeTaskProvider(default=memo_aware)
        self.assertEqual(store.run("plan-1", provider, evaluator, self.observe)["status"],
                         "complete")
        self.assertEqual([arm_of(r) for r in provider.requests], list("ABBAABBA"))
        for position, request in enumerate(provider.requests):
            document = json.loads(request)
            self.assertEqual(set(document),
                             {"reference_data_only", "task_id", "prompt", "context"})
            self.assertEqual(document["task_id"], f"t-{position // 2 + 1}")
            self.assertEqual(document["context"],
                             RAW + MEMO if arm_of(request) == "B" else RAW)
            self.assertNotIn(ANSWER, request)
            self.assertLessEqual(len(request), 1024)
        report = store.report("plan-1", self.observe)
        comparison = report["comparison"]
        self.assertEqual(comparison["order"], {"AB": 2, "BA": 2})
        self.assertEqual(comparison["arms"]["A"]["denominator"], 4)
        self.assertEqual(comparison["arms"]["B"]["denominator"], 4)
        self.assertEqual(comparison["paired"],
                         {"denominator": 4, "both": 0, "a_only": 0, "b_only": 4, "neither": 0})
        self.assertIsNone(report["adoption_receipt"])
        self.assertIsNone(report["performance_claim"])
        self.assertIsNone(report["measured_savings"])
        self.assertTrue(report["scores_are_synthetic"])
        self.assertEqual(report["cost"]["A"]["total"], {"label": "synthetic_zero", "value": 0})
        self.assertEqual(report["cost"]["B"]["phases"]["consolidation"],
                         {"label": "unavailable", "value": None})
        self.assertEqual(report["cost"]["B"]["total"], {"label": "unavailable", "value": None})

    def test_reopen_skips_completed_arms_and_rejects_changed_binding(self):
        first = ComparisonStore(self.path)
        digest = first.plan(**self.params())
        before = FakeTaskProvider(default=memo_aware)
        self.assertEqual(first.run("plan-1", before, evaluator, self.observe, limit=3)["status"],
                         "running")
        first.close()
        store = self.store()
        self.assertEqual(store.plan(**self.params()), digest)
        for change in (dict(model="fake-model-2"), dict(config={"fixture": "2"}),
                       dict(tasks=tasks(3)), dict(snapshot_sha256="c" * 64)):
            with self.assertRaises(ValueError):
                store.plan(**self.params(**change))
        self.assertEqual(store.inspect("plan-1")["plan_sha256"], digest)
        self.assertEqual(len(store.inspect("plan-1")["arms"]), 3)
        after = FakeTaskProvider(default=memo_aware)
        with self.assertRaisesRegex(ValueError, "evaluator binding conflict"):
            store.run("plan-1", after, SyntheticEvaluator("fixture-score", "2", "e" * 64,
                                                        evaluator.evaluate), self.observe)
        self.assertEqual(after.requests, [])
        self.assertEqual(store.run("plan-1", after, evaluator, self.observe)["status"],
                         "complete")
        self.assertEqual(len(before.requests), 3)
        self.assertEqual(len(after.requests), 5)
        self.assertEqual(len(set(before.requests + after.requests)), 8)
        self.assertEqual(store.report("plan-1", self.observe)["comparison"]["paired"]["b_only"], 4)

    def test_reused_final_taskset_is_recorded_as_development_contact(self):
        store = self.store()
        store.plan(**self.params(declared_role="final"))
        self.assertEqual(store.inspect("plan-1")["contact_role"], "final")
        store.plan(**self.params(plan_id="plan-2", declared_role="final",
                                 config={"fixture": "tuned"}))
        reused = store.report("plan-2", self.observe)
        self.assertEqual(reused["declared_role"], "final")
        self.assertEqual(reused["contact_role"], "development")
        self.assertFalse(reused["independent_holdout"])
        store.plan(**self.params(declared_role="final"))  # idempotent reopen, not a new contact
        self.assertEqual(store.inspect("plan-1")["contact_role"], "final")
        store.plan(**self.params(plan_id="plan-3", declared_role="final",
                                 tasks=tasks(4, prefix="fresh")))
        self.assertEqual(store.inspect("plan-3")["contact_role"], "development")
        self.assertFalse(store.report("plan-3", self.observe)["independent_holdout"])

    def test_timeout_stays_in_denominator_and_unknown_outcome_never_replays(self):
        store = self.store()
        store.plan(**self.params(tasks=tasks(2)))
        provider = FakeTaskProvider(default=memo_aware, script={1: TimeoutError(), 2: None})
        self.assertEqual(store.run("plan-1", provider, evaluator, self.observe)["status"],
                         "complete")
        store.run("plan-1", provider, evaluator, self.observe)
        self.assertEqual(len(provider.requests), 4)
        comparison = store.report("plan-1", self.observe)["comparison"]
        self.assertEqual(comparison["arms"]["B"]["timeout"], 1)   # task 1, second position
        self.assertEqual(comparison["arms"]["B"]["missing"], 1)   # task 2, first position
        self.assertEqual(comparison["arms"]["B"]["denominator"], 2)
        self.assertEqual(comparison["paired"],
                         {"denominator": 2, "both": 0, "a_only": 0, "b_only": 0, "neither": 2})
        store.plan(**self.params(plan_id="plan-2", tasks=tasks(2, prefix="u")))
        with self.assertRaises(RuntimeError):
            store.run("plan-2", FakeTaskProvider(script={0: RuntimeError("lost")}),
                      evaluator, self.observe)
        retry = FakeTaskProvider(default=memo_aware)
        self.assertEqual(store.run("plan-2", retry, evaluator, self.observe)["status"],
                         "incomplete")
        self.assertEqual(retry.requests, [])
        unknown = store.report("plan-2", self.observe)
        self.assertIsNone(unknown["comparison"])
        self.assertEqual(unknown["outcomes"]["A"]["unknown"], 1)
        self.assertEqual(unknown["outcomes"]["A"]["denominator"], 2)

    def test_policy_change_invalidates_comparison_and_stops_dispatch(self):
        store = self.store()
        digest = store.plan(**self.params())
        provider = FakeTaskProvider(default=memo_aware)
        store.run("plan-1", provider, evaluator, self.observe, limit=2)
        self.current["policy_sha256"] = "d" * 64
        state = store.run("plan-1", provider, evaluator, self.observe)
        self.assertEqual((state["status"], state["reason"]),
                         ("invalidated", "policy_or_snapshot_changed"))
        self.assertEqual(len(provider.requests), 2)
        self.current["policy_sha256"] = "a" * 64  # reverting does not revive the run
        self.assertEqual(store.run("plan-1", provider, evaluator, self.observe)["status"],
                         "invalidated")
        self.assertEqual(len(provider.requests), 2)
        report = store.report("plan-1", self.observe)
        self.assertIsNone(report["comparison"])
        self.assertIsNone(report["performance_claim"])
        self.assertEqual(report["plan_sha256"], digest)  # frozen plan/contexts retained
