"""Saved byte/time inspection over synthetic journals; never a live call."""
import io
import json
from pathlib import Path
import sqlite3
from unittest import TestCase, mock

import test_compare_prepare_cli as fixtures
from agent_sleep_lab import comparison_inspect as inspect
from agent_sleep_lab import runtime_cli
from agent_sleep_lab.ab_comparison import ComparisonStore
from agent_sleep_lab.cli import main
from agent_sleep_lab.comparison_measurements import MAX_RECEIPT_BYTES, METRICS, TIMING_BASIS


class CompareMeasurementTests(TestCase):
    def setUp(self):
        self.f = fixtures.ComparePreparationTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.prepared = self.f.success()

    def call(self, measurements=True):
        out, err = io.StringIO(), io.StringIO()
        code = main(["compare-inspect", "--store-config", self.f.config_path,
                     "--journal", str(self.f.journal), "--plan-id", self.f.manifest["plan_id"],
                     *(["--measurements"] if measurements else [])], out, err)
        return code, out.getvalue(), err.getvalue()

    def success(self, measurements=True):
        code, output, error = self.call(measurements)
        self.assertEqual((code, error), (0, ""))
        result = json.loads(output)
        for private in ("PRIVATE-", "EVALUATOR-ONLY-ANSWER", "duplicate"):
            self.assertNotIn(private, output)
        self.assertEqual(result["cost"], {"label": "unavailable", "value": None})
        self.assertIsNone(result["usage"])
        self.assertIsNone(result["performance_claim"])
        self.assertFalse(result["acceptance_complete"])
        return result

    def receipt(self, entry, **changes):
        receipt = dict(model_requested=self.prepared["model"],
                       request_sha256=entry["request_sha256"], status="returned",
                       request_bytes=entry["request_bytes"],
                       cli_prompt_bytes=entry["request_bytes"] + 100,
                       output_bytes=7, transport_elapsed_ns=1000, timing_basis=TIMING_BASIS,
                       transport_source="injected_transport_not_live_verified",
                       account="PRIVATE-ACCOUNT", outputs="PRIVATE-REPLY", cost="PRIVATE-COST",
                       usage={"input": 999, "private": "PRIVATE-USAGE"})
        receipt.update(changes)
        return json.dumps(receipt).encode()

    def save(self, entry, raw, state="intent"):
        with sqlite3.connect(self.f.journal) as db:
            db.execute("INSERT OR REPLACE INTO comparison_arms VALUES (?,?,?,?,?,?,?,?)",
                       (self.f.manifest["plan_id"], entry["task_index"], entry["arm"],
                        entry["position"], state, entry["request_sha256"], b"PRIVATE-REPLY", None))
            db.execute("INSERT OR REPLACE INTO comparison_provider_receipts VALUES (?,?,?,?)",
                       (self.f.manifest["plan_id"], entry["task_index"], entry["arm"], raw))

    def test_missing_and_legacy_receipts_keep_null_totals_readonly_no_execution(self):
        source = Path(self.f.f.path).read_bytes()
        before = self.f.journal_dump()
        journal = self.f.journal.read_bytes()
        with mock.patch.object(runtime_cli, "OpenClawMimoProvider", side_effect=AssertionError("provider")), \
             mock.patch.object(runtime_cli, "SyntheticEvaluator", side_effect=AssertionError("evaluator")), \
             mock.patch.object(ComparisonStore, "run", side_effect=AssertionError("dispatch")), \
             mock.patch.object(ComparisonStore, "report", side_effect=AssertionError("mutation")):
            result = self.success()
        self.assertEqual(result["status"], "planned")
        self.assertFalse(result["dispatch_authorization"])
        projection = result["measurements"]
        self.assertEqual(len(projection["slots"]), 10)
        for arm in "AB":
            summary = projection["per_arm"][arm]
            self.assertEqual(summary["denominator"], 5)
            self.assertEqual(summary["receipts"]["missing"], 5)
            for metric in summary["metrics"].values():
                self.assertEqual(metric, dict(observed_slots=0, absent_slots=5, invalid_slots=0,
                                              observed_sum=None, all_slots_observed=False))
        self.assertEqual(self.f.journal_dump(), before)
        self.assertEqual(self.f.journal.read_bytes(), journal)
        self.assertEqual(Path(self.f.f.path).read_bytes(), source)
        # Historical journals without the optional retention table stay untouched.
        with sqlite3.connect(self.f.journal) as db:
            db.execute("DROP TABLE comparison_provider_receipts")
        legacy_before = self.f.journal.read_bytes()
        self.assertEqual(self.success()["measurements"], projection)
        self.assertEqual(self.f.journal.read_bytes(), legacy_before)

    def test_complete_observations_are_per_arm_sums_not_live_success_or_billing(self):
        for entry in self.prepared["arms"]:
            self.save(entry, self.receipt(entry))
        before = self.f.journal_dump()
        result = self.success()
        for arm in "AB":
            summary = result["measurements"]["per_arm"][arm]
            self.assertEqual(summary["receipts"]["recorded"], 5)
            expected = dict(request_bytes=sum(e["request_bytes"] for e in self.prepared["arms"]
                                             if e["arm"] == arm),
                            output_bytes=35, transport_elapsed_ns=5000)
            expected["cli_prompt_bytes"] = expected["request_bytes"] + 500
            for name, total in expected.items():
                self.assertEqual(summary["metrics"][name],
                                 dict(observed_slots=5, absent_slots=0, invalid_slots=0,
                                      observed_sum=total, all_slots_observed=True))
            self.assertEqual(summary["transport_sources"]["injected_transport_not_live_verified"], 5)
        # A returned receipt is not a durable reply/evaluation or authenticated dispatch.
        self.assertFalse(result["all_outcomes_scored"])
        self.assertEqual(result["outcomes"]["A"]["dispatch_intent_outcome_unknown"], 5)
        for flag in ("live_verified", "origin_authenticated", "tokens_or_billed_cost", "provider_latency"):
            self.assertFalse(result["measurements"][flag])
        self.assertEqual(self.f.journal_dump(), before)

    def test_mixed_failed_unknown_mismatched_and_absent_slots_never_shrink_denominators(self):
        a0, b0, a1, b1 = self.prepared["arms"][:4]
        self.save(a0, self.receipt(a0, status="outcome_unknown", output_bytes=None,
                                  transport_source="registered_openclaw_cli"), state="timeout")
        self.save(b0, b"PRIVATE-RECEIPT malformed", state="invalid")
        self.save(a1, self.receipt(a1, request_sha256="0" * 64), state="replied")
        self.save(b1, self.receipt(b1, output_bytes=0, transport_elapsed_ns=0), state="invalid")
        before = self.f.journal_dump()
        result = self.success()
        a, b = (result["measurements"]["per_arm"][arm] for arm in "AB")
        self.assertEqual(a["receipts"], dict(missing=3, invalid=0, binding_mismatch=1, recorded=1))
        self.assertEqual(b["receipts"], dict(missing=3, invalid=1, binding_mismatch=0, recorded=1))
        self.assertEqual(a["metrics"]["output_bytes"]["observed_sum"], None)
        self.assertEqual(a["metrics"]["transport_elapsed_ns"]["observed_sum"], 1000)
        self.assertEqual(b["metrics"]["output_bytes"]["observed_sum"], 0)
        self.assertEqual(b["metrics"]["transport_elapsed_ns"]["observed_sum"], 0)
        self.assertEqual(a["transport_sources"]["registered_openclaw_cli"], 1)
        for summary in (a, b):
            self.assertEqual(summary["denominator"], 5)
            for metric in summary["metrics"].values():
                self.assertFalse(metric["all_slots_observed"])
                self.assertEqual(sum(metric[n] for n in ("observed_slots", "absent_slots", "invalid_slots")), 5)
        self.assertEqual(result["arms"][0]["status"], "timeout")
        self.assertEqual(result["arms"][2]["status"], "replied")
        self.assertEqual(self.f.journal_dump(), before)

    def test_invalid_values_wrong_timing_basis_and_bounded_json_do_not_become_measurements(self):
        entries = self.prepared["arms"]
        self.save(entries[0], self.receipt(entries[0], request_bytes=True, cli_prompt_bytes=-1,
                                          output_bytes="PRIVATE-BYTES", transport_elapsed_ns=1.5))
        self.save(entries[1], self.receipt(entries[1], timing_basis="PRIVATE-provider-latency"))
        self.save(entries[2], b" " * (MAX_RECEIPT_BYTES + 1))
        self.save(entries[3], b'{"status":"PRIVATE","status":"PRIVATE-duplicate"}')
        result = self.success()
        slots = result["measurements"]["slots"]
        for name in METRICS:
            self.assertEqual(slots[0]["metrics"][name], dict(state="invalid", value=None))
        self.assertEqual(slots[1]["metrics"]["transport_elapsed_ns"], dict(state="invalid", value=None))
        self.assertEqual(slots[2]["receipt_state"], "invalid")
        self.assertEqual(slots[3]["receipt_state"], "invalid")
        for arm in "AB":
            self.assertEqual(result["measurements"]["per_arm"][arm]["receipts"]["invalid"], 1)

    def test_default_remains_opaque_optin_refuses_orphan_identity_without_echo_or_repair(self):
        entry = self.prepared["arms"][0]
        self.save(entry, b"PRIVATE-RECEIPT malformed")
        default = self.success(measurements=False)
        self.assertNotIn("measurements", default)
        self.assertEqual(self.success()["measurements"]["slots"][0]["receipt_state"], "invalid")
        with sqlite3.connect(self.f.journal) as db:
            db.execute("INSERT INTO comparison_provider_receipts VALUES (?,?,?,?)",
                       (self.f.manifest["plan_id"], 99, "A", b"PRIVATE-ORPHAN"))
        before = self.f.journal_dump()
        code, output, error = self.call()
        self.assertEqual((code, output), (2, ""))
        self.assertEqual(error, "error[compare-inspect]: inspection refused; check strict inputs, "
                         "existing distinct databases and saved comparison integrity\n")
        self.assertNotIn("measurements", self.success(measurements=False))
        self.assertEqual(self.f.journal_dump(), before)
        with self.assertRaisesRegex(ValueError, "measurements must be boolean"):
            inspect.execute(store_config_path=self.f.config_path, journal_path=self.f.journal,
                            plan_id=self.f.manifest["plan_id"], measurements=1)
