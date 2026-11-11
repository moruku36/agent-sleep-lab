"""Offline cost reporting over real stores and synthetic captures/replies."""
from pathlib import Path
from unittest import TestCase, mock

import test_oss_fixture_cohort as fixtures
import test_oss_selected_probe as probes
from agent_sleep_lab import oss_cost_accounting as accounting
from agent_sleep_lab import oss_execution_journal as execution
from agent_sleep_lab import oss_offline_worker as worker
from test_oss_mimo_adapter import Transport, envelope


def observation(plan_id="plan-1", arm="baseline", stage="task_execution", **changes):
    return dict(plan_id=plan_id, arm=arm, stage=stage, cost="0.01", input_tokens=None,
                output_tokens=None, evidence_sha256=worker.digest(b"synthetic accounting record")) | changes


def freeze(report, rows, currency="USD"):
    return accounting.freeze_observations(report["target"], currency=currency, observations=rows)


class CostAccountingTests(TestCase):
    def setUp(self):
        self.fixture = fixtures.FixtureCohortTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()

    def pair(self, **options):
        return accounting.pair_report(self.fixture.journal, "plan-1", self.fixture.bridge, **options)

    def group(self, **changes):
        options = dict(journal=self.fixture.journal, bridges={p["plan_id"]: self.fixture.bridge for p in self.fixture.members})
        return accounting.cohort_report(self.fixture.registry, "cohort-1", **(options | changes))

    def test_saved_unscored_pair_leaves_all_accounting_unknown(self):
        self.fixture.add_plan(1)
        # Register an older-style binding without a frozen verdict manifest.
        transport = Transport(envelope(usage={"input_tokens": 123}, cost="0.01"))
        instance = self.fixture.make_adapter(transport)
        self.fixture.register(instance, plan_id="old-unscored")
        original = self.fixture.journal.run("old-unscored", self.fixture.bridge, instance)
        self.fixture.journal = self.fixture.open_journal()
        report = accounting.pair_report(self.fixture.journal, "old-unscored", self.fixture.bridge)
        task = report["tasks"][0]
        self.assertIsNone(task["manifest_sha256"])
        self.assertEqual(task["status"], "not_configured")
        self.assertEqual(report["target"]["report_sha256"], worker.digest(worker.encoded(original)))
        self.assertEqual((report["provider_usage"], report["provider_cost"]), ("unavailable",) * 2)
        self.assertIsNone(report["currency"])
        self.assertIsNone(report["artifact_sha256"])
        self.assertEqual(report["totals"]["stage_slots"], 14)
        for arm in task["arms"].values():
            self.assertEqual(arm["execution_status"], "completed")
            self.assertEqual(tuple(arm["stages"]), accounting.STAGES)
            self.assertTrue(all(v is None for stage in arm["stages"].values() for v in stage.values()))
        for metric in accounting.METRICS:
            self.assertIsNone(report["totals"][metric])
        self.assertEqual(self.fixture.journal.report("old-unscored", self.fixture.bridge), original)
        self.assertEqual((len(transport.calls), self.fixture.journal._db.total_changes), (2, 0))

    def test_exact_money_and_explicit_zero_keep_invalid_completed_arm(self):
        self.fixture.add_plan(1)
        transport = self.fixture.transports["plan-1"]
        transport.result = envelope(text="invalid synthetic rationale")
        self.fixture.journal.run("plan-1", self.fixture.bridge, self.fixture.instances["plan-1"], limit=1)
        transport.result = envelope(text=fixtures.verdict_fixtures.reply(True))
        self.fixture.journal.run("plan-1", self.fixture.bridge, self.fixture.instances["plan-1"])
        amount = "999999999999999999.999999999999"
        rows = [observation(arm=arm, stage=stage, input_tokens=0, cost="0")
                for arm in accounting.ARMS for stage in accounting.STAGES]
        rows[0]["cost"] = rows[len(accounting.STAGES)]["cost"] = amount
        rows[1]["cost"] = "0.000000000001"
        target = self.pair()
        raw = freeze(target, rows)
        self.assertEqual(raw, freeze(target, list(reversed(rows))))
        report = self.pair(artifact=raw)
        self.assertEqual(report["observation_trust"], "caller_supplied_unverified")
        self.assertEqual(report["artifact_sha256"], worker.digest(raw))
        self.assertEqual(report["currency"], "USD")
        baseline = report["tasks"][0]["arms"]["baseline"]
        self.assertEqual(baseline["verdict_status"], "invalid_verdict")
        self.assertEqual(baseline["stages"]["capture"]["cost"], amount)
        self.assertEqual(baseline["totals"]["cost"], "1000000000000000000")
        self.assertEqual(report["totals"]["cost"], "1999999999999999999.999999999999")
        self.assertEqual(report["reference_minus_baseline_cost"], "-0.000000000001")
        self.assertEqual(report["totals"]["input_tokens"], 0)
        self.assertIsNone(report["totals"]["output_tokens"])
        self.assertNotIn("synthetic rationale", repr(report))
        self.assertNotIn("expected_accept", repr(report))
        self.assertEqual(len(transport.calls), 2)

    def test_pair_binding_and_outcome_changes_reject_stale_observations(self):
        self.fixture.add_plan(1)
        initial = self.pair()
        raw = freeze(initial, [observation(stage="capture")])
        other = execution.ExecutionJournal(Path(self.fixture.dir) / "other.sqlite", initialize=True)
        self.addCleanup(other.close)
        self.fixture.register(self.fixture.make_adapter(), journal=other, max_reply_bytes=4095)
        self.assertNotEqual(accounting.pair_report(other, "plan-1", self.fixture.bridge)["target"]["frozen_sha256"],
                            initial["target"]["frozen_sha256"])
        with self.assertRaisesRegex(accounting.AccountingError, "differs"):
            accounting.pair_report(other, "plan-1", self.fixture.bridge, artifact=raw)
        self.fixture.journal.run("plan-1", self.fixture.bridge, self.fixture.instances["plan-1"], limit=1)
        progressed = self.pair()
        self.assertEqual(progressed["target"]["frozen_sha256"], initial["target"]["frozen_sha256"])
        self.assertNotEqual(progressed["target"]["report_sha256"], initial["target"]["report_sha256"])
        with self.assertRaisesRegex(accounting.AccountingError, "differs"):
            self.pair(artifact=raw)
        all_zero = [observation(arm=arm, stage=stage, cost="0")
                    for arm in accounting.ARMS for stage in accounting.STAGES]
        partial_run = self.pair(artifact=freeze(progressed, all_zero))
        self.assertEqual(partial_run["totals"]["cost"], "0")
        self.assertIsNone(partial_run["reference_minus_baseline_cost"])
        new = freeze(progressed, [observation(stage="capture", cost=None, output_tokens=0)], None)
        current = self.pair(artifact=new)
        self.assertEqual(current["totals"]["observed_output_tokens_slots"], 1)
        self.assertIsNone(current["totals"]["output_tokens"])
        self.fixture.exclude_memory()
        self.assertFalse(self.pair()["tasks"][0]["context_current"])
        with self.assertRaisesRegex(accounting.AccountingError, "differs"):
            self.pair(artifact=new)
        revoked = freeze(self.pair(), [observation(stage="capture")])
        with self.assertRaisesRegex(accounting.AccountingError, "current execution report"):
            self.pair(artifact=revoked)

    def test_artifact_rejects_ambiguous_values_duplicate_slots_and_noncanonical_input(self):
        self.fixture.add_plan(1)
        target = self.pair()
        for changes in (dict(cost=True), dict(cost=0.1), dict(cost="1e-3"), dict(cost="01"),
                        dict(cost="-0"), dict(cost="1.0000000000001"), dict(cost="1" * 19),
                        dict(input_tokens=True), dict(output_tokens=-1), dict(input_tokens=2**63),
                        dict(cost=None), dict(stage="other"), dict(arm="both"),
                        dict(currency="JPY"), dict(evidence_sha256="F" * 64)):
            with self.subTest(changes=changes), self.assertRaises(accounting.AccountingError):
                freeze(target, [observation(**changes)])
        for currency in (None, "usd", "USD/JPY"):
            with self.subTest(currency=currency), self.assertRaises(accounting.AccountingError):
                freeze(target, [observation()], currency)
        with self.assertRaisesRegex(accounting.AccountingError, "duplicate"):
            freeze(target, [observation(), observation(cost="0")])
        with self.assertRaisesRegex(accounting.AccountingError, "current execution report"):
            self.pair(artifact=freeze(target, [observation("other-plan")]))
        good = freeze(target, [observation()])
        for raw in (good + b"\n", good.replace(b'"currency":"USD"', b'"currency":"USD","currency":"USD"'),
                    good.replace(b"caller_supplied_unverified", b"verified_billing"),
                    b"x" * (accounting.MAX_ARTIFACT_BYTES + 1)):
            with self.subTest(size=len(raw)), self.assertRaises(accounting.AccountingError):
                self.pair(artifact=raw)

    def test_cohort_keeps_incomplete_invalid_missing_and_corrupt_members(self):
        for number in range(1, 5):
            self.fixture.add_plan(number)
        self.fixture.freeze()
        self.fixture.transports["plan-1"].result = envelope(text="invalid synthetic reply")
        self.fixture.journal.run("plan-1", self.fixture.bridge, self.fixture.instances["plan-1"])
        failed = Transport(error=TimeoutError("synthetic failure"))
        self.fixture.journal.run("plan-2", self.fixture.bridge, self.fixture.make_adapter(failed))
        self.fixture.finish(4)
        self.fixture.journal._db.execute("UPDATE arms SET receipt=? WHERE plan_id='plan-4'", (b"bad receipt",))
        bridges = {plan: self.fixture.bridge for plan in ("plan-1", "plan-2", "plan-4")}
        target = self.group(bridges=bridges)
        raw = freeze(target, [observation(), observation("plan-2", cost="0.02")])
        changes = self.fixture.journal._db.total_changes, self.fixture.registry._db.total_changes
        report = self.group(bridges=bridges, artifact=raw)
        tasks = report["tasks"]
        self.assertEqual([task["status"] for task in tasks], ["complete_with_invalid_verdict", "incomplete",
                         "unavailable_context", "unavailable_journal_integrity"])
        self.assertEqual((report["registered_tasks"], report["totals"]["stage_slots"]), (4, 56))
        self.assertEqual(tasks[1]["arms"]["baseline"]["execution_status"], "unknown")
        self.assertEqual(tasks[1]["arms"]["baseline"]["stages"]["task_execution"]["cost"], "0.02")
        self.assertEqual(tasks[1]["arms"]["reference"]["execution_status"], "not_started")
        self.assertEqual(report["totals"]["observed_cost_slots"], 2)
        self.assertIsNone(report["arms"]["baseline"]["cost"])
        self.assertIsNone(report["reference_minus_baseline_cost"])
        self.assertEqual((self.fixture.journal._db.total_changes, self.fixture.registry._db.total_changes), changes)
        self.assertEqual(len(failed.calls), 1)

    def test_identical_cohort_scores_do_not_substitute_for_exact_member_reports(self):
        self.fixture.add_plan(1)
        self.fixture.add_plan(2)
        self.fixture.freeze()
        bridges = {"plan-1": self.fixture.bridge, "plan-2": self.fixture.bridge}
        other = execution.ExecutionJournal(Path(self.fixture.dir) / "copy.sqlite", initialize=True)
        self.addCleanup(other.close)
        self.fixture.journal._db.backup(other._db)
        self.fixture.finish(1)
        changed = envelope(text='{"accept":true,"rationale":"other synthetic rationale"}')
        other.run("plan-1", self.fixture.bridge, self.fixture.make_adapter(Transport(changed)))
        self.assertEqual(self.fixture.registry.report("cohort-1", journal=self.fixture.journal, bridges=bridges),
                         self.fixture.registry.report("cohort-1", journal=other, bridges=bridges))
        report = self.group()
        alternate = self.group(journal=other)
        self.assertEqual(report["target"]["frozen_sha256"], alternate["target"]["frozen_sha256"])
        self.assertNotEqual(report["target"]["report_sha256"], alternate["target"]["report_sha256"])
        with self.assertRaisesRegex(accounting.AccountingError, "differs"):
            self.group(journal=other, artifact=freeze(report, [observation()]))


class SelectedProbeAccountingTests(TestCase):
    def setUp(self):
        self.fixture = probes.SelectedIssueProbeTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()

    def test_selected_cohort_aggregates_all_costs_and_rechecks_current_policy(self):
        plans = [self.fixture.register(number) for number in (1, 2)]
        registry = self.fixture.registry()
        document, bridges = self.fixture.freeze(registry, [plan[0] for plan in plans])
        for plan_id, adapter, transport, _ in plans:
            self.fixture.journal.run(plan_id, self.fixture.bridge, adapter)
            self.assertEqual(len(transport.calls), 2)
        target = accounting.cohort_report(registry, "selected-cohort", journal=self.fixture.journal, bridges=bridges)
        rows = [observation(plan_id, arm, stage, cost="0.1" if arm == "baseline" else "0.2")
                for plan_id in bridges for arm in accounting.ARMS for stage in accounting.STAGES]
        raw = freeze(target, rows)
        report = accounting.cohort_report(registry, "selected-cohort", journal=self.fixture.journal,
                                          bridges=bridges, artifact=raw)
        self.assertEqual(report["target"]["frozen_sha256"], worker.digest(worker.encoded(document)))
        self.assertEqual(report["totals"]["cost"], "4.2")
        self.assertEqual(report["reference_minus_baseline_cost"], "1.4")
        self.assertEqual(report["totals"]["observed_cost_slots"], 28)
        with mock.patch.object(self.fixture.bridge, "reference_context", side_effect=ValueError("synthetic policy change")):
            with self.assertRaisesRegex(accounting.AccountingError, "differs"):
                accounting.cohort_report(registry, "selected-cohort", journal=self.fixture.journal,
                                         bridges=bridges, artifact=raw)
            withheld = accounting.cohort_report(registry, "selected-cohort", journal=self.fixture.journal, bridges=bridges)
        self.assertEqual([task["status"] for task in withheld["tasks"]], ["withheld_context"] * 2)
        self.assertIsNone(withheld["totals"]["cost"])
