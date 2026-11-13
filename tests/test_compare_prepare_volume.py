"""Planned request-volume contracts; synthetic stores, no model execution."""
import copy
import json
from pathlib import Path
import sqlite3
from unittest import TestCase, mock

import test_compare_prepare_cli as fixtures
from agent_sleep_lab import comparison_prepare as prepare
from agent_sleep_lab import runtime_cli
from agent_sleep_lab.ab_comparison import ComparisonStore
from agent_sleep_lab.raw_baseline import RawBaselineComparison


class ComparePreparationVolumeTests(TestCase):
    def setUp(self):
        self.f = fixtures.ComparePreparationTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    def test_five_pairs_match_frozen_bytes_and_preserve_offline_boundaries(self):
        before = tuple(self.f.store._db().iterdump())
        before_bytes = Path(self.f.f.path).read_bytes()
        with mock.patch.object(runtime_cli, "OpenClawMimoProvider",
                               side_effect=AssertionError("provider")), \
             mock.patch.object(runtime_cli, "FakeTaskProvider",
                               side_effect=AssertionError("provider")), \
             mock.patch.object(runtime_cli, "SyntheticEvaluator",
                               side_effect=AssertionError("evaluator")), \
             mock.patch.object(runtime_cli, "read_json",
                               side_effect=AssertionError("answer-key read")), \
             mock.patch.object(ComparisonStore, "run", side_effect=AssertionError("dispatch")), \
             mock.patch.object(ComparisonStore, "report", side_effect=AssertionError("status write")):
            result = self.f.success()
            frozen = self.f.journal_dump()
            self.assertEqual(result, self.f.success())
            self.assertEqual(self.f.journal_dump(), frozen)
        with sqlite3.connect(self.f.journal) as db:
            blob, digest = db.execute("SELECT plan, plan_sha256 FROM comparison_plans").fetchone()
        plan = json.loads(blob)
        self.assertEqual(result["plan_sha256"], digest)
        self.assertEqual([t["order"] for t in result["task_order"]],
                         ["AB", "BA", "AB", "BA", "AB"])
        volume = result["input_volume"]
        self.assertEqual(volume["basis"], "planned_serialized_utf8_json_request_bytes")
        self.assertEqual((volume["task_pairs"], volume["total_arms"]), (5, 10))
        sizes = {arm: [len(t[arm]["request"].encode("utf-8")) for t in plan["tasks"]]
                 for arm in "AB"}
        for i, pair in enumerate(volume["pairs"]):
            self.assertEqual(pair["task_index"], i)
            self.assertEqual(pair["a_request_bytes"], sizes["A"][i])
            self.assertEqual(pair["b_request_bytes"], sizes["B"][i])
            self.assertEqual(pair["delta_bytes"], sizes["B"][i] - sizes["A"][i])
            self.assertGreater(pair["delta_percent"], 0)
        total = volume["totals"]
        self.assertEqual(total["a_request_bytes"], sum(sizes["A"]))
        self.assertEqual(total["b_request_bytes"], sum(sizes["B"]))
        self.assertEqual(total["combined_request_bytes"], sum(sizes["A"] + sizes["B"]))
        self.assertEqual(total["delta_bytes"], sum(sizes["B"]) - sum(sizes["A"]))
        self.assertFalse(result["dispatch_authorization"])
        self.assertEqual(result["cost"], {"label": "unavailable", "value": None})
        for secret in ("PRIVATE-TASK", "PRIVATE-SYNTHETIC", "EVALUATOR-ONLY-ANSWER", "duplicate"):
            self.assertNotIn(secret, json.dumps(result))
        self.assertEqual(tuple(self.f.store._db().iterdump()), before)
        self.assertEqual(Path(self.f.f.path).read_bytes(), before_bytes)

    def test_unicode_uses_actual_escaped_serialization_not_text_length(self):
        prompt = "日本語の課題 🦞"
        self.f.manifest["tasks"][0]["prompt"] = prompt
        self.f.write("comparison.json", self.f.manifest)
        result = self.f.success()
        with sqlite3.connect(self.f.journal) as db:
            plan = json.loads(db.execute("SELECT plan FROM comparison_plans").fetchone()[0])
        pair = result["input_volume"]["pairs"][0]
        for arm, field in (("A", "a_request_bytes"), ("B", "b_request_bytes")):
            request = plan["tasks"][0][arm]["request"]
            self.assertEqual(json.loads(request)["prompt"], prompt)
            self.assertTrue(request.isascii())
            self.assertIn("\\u65e5", request)
            self.assertEqual(pair[field], len(request.encode("utf-8")))
            unescaped = json.dumps(json.loads(request), ensure_ascii=False,
                                   sort_keys=True, separators=(",", ":"))
            self.assertGreater(pair[field], len(unescaped.encode("utf-8")))

    def test_identity_validation_and_weighted_half_up_percentage(self):
        tasks = [{"task_id": "one"}, {"task_id": "two"}]
        arms = [dict(plan_id="volume", task_index=i, task_id=t["task_id"],
                     arm=arm, request_bytes=size)
                for i, t, sizes in ((0, tasks[0], (32, 33)), (1, tasks[1], (96, 192)))
                for arm, size in zip("AB", sizes)]
        result = prepare._input_volume("volume", tasks, list(reversed(arms)))
        self.assertEqual([p["delta_percent"] for p in result["pairs"]], [3.13, 100.0])
        self.assertEqual(result["totals"],
                         dict(a_request_bytes=128, b_request_bytes=225,
                              delta_bytes=97, delta_percent=75.78, combined_request_bytes=353))
        self.assertEqual(result["percentage_rounding"], "half_up_2_decimal_places")
        variants = [arms[:-1], arms + [arms[0]], [arms[0], arms[0], *arms[2:]]]
        for key, values in {
                "task_index": (True, -1, 2, "0", None, []),
                "request_bytes": (True, 0, -1, 1.5, "32", None, 1_048_577),
                "arm": ("C", "AB", None, []),
                "task_id": ("wrong", None),
                "plan_id": ("other", None)}.items():
            for value in values:
                changed = copy.deepcopy(arms)
                changed[0][key] = value
                variants.append(changed)
        variants.extend((None, {}, [None, *arms[1:]]))
        for invalid in variants:
            with self.subTest(arms=invalid), self.assertRaisesRegex(
                    ValueError, "^invalid planned request-volume"):
                prepare._input_volume("volume", tasks, invalid)
        for invalid_tasks in ([], tasks * 3, [tasks[0], tasks[0]], [None], [{"task_id": []}]):
            with self.subTest(tasks=invalid_tasks), self.assertRaises(ValueError):
                prepare._input_volume("volume", invalid_tasks, arms)

    def test_unknown_and_mixed_statuses_keep_all_slots_and_journal_unchanged(self):
        first = self.f.success()
        before_store = tuple(self.f.store._db().iterdump())
        with sqlite3.connect(self.f.journal) as db:
            for arm, state in zip(first["arms"],
                                  ("intent", "completed", "replied", "timeout", "missing", "invalid")):
                db.execute("INSERT INTO comparison_arms VALUES (?,?,?,?,?,?,?,?)",
                           (self.f.manifest["plan_id"], arm["task_index"], arm["arm"],
                            arm["position"], state, arm["request_sha256"], b"PRIVATE-REPLY", None))
            db.execute("UPDATE comparison_plans SET status='running'")
        frozen = self.f.journal_dump()
        # Audit order is not dispatch order; pairing must also survive reordering.
        audit = RawBaselineComparison.audit

        def reversed_audit(baseline, plan_id):
            result = audit(baseline, plan_id)
            result["arms"].reverse()
            return result

        with mock.patch.object(RawBaselineComparison, "audit", reversed_audit):
            reopened = self.f.success()
        self.assertEqual(reopened["input_volume"], first["input_volume"])
        self.assertEqual(reopened["planned_denominator"], first["planned_denominator"])
        self.assertIn("dispatch_intent_outcome_unknown", {a["status"] for a in reopened["arms"]})
        self.assertEqual(reopened["input_volume"]["total_arms"], 10)
        self.assertEqual(self.f.journal_dump(), frozen)
        self.assertEqual(tuple(self.f.store._db().iterdump()), before_store)
        self.assertNotIn("PRIVATE-REPLY", json.dumps(reopened))
