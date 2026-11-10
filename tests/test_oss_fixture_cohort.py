"""Frozen cohorts over real local journal logic and injected synthetic replies.

All captures, decisions, adoptions and process envelopes are authored fixtures.
No target worker, provider, credential, network or performance measurement.
Only helper methods are borrowed; imported TestCase aliases are not collected.
"""
import copy
from pathlib import Path
import sqlite3
from unittest import mock

import support  # noqa: F401
import test_oss_verdict_evaluation as verdict_fixtures
import test_oss_paired_outcome as capture_fixtures
from evidence_support import StoreCase
from agent_sleep_lab import oss_fixture_cohort as cohort
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_prompt_capture as capture
from agent_sleep_lab import oss_prompt_capture_worker as child
from agent_sleep_lab import oss_verdict_evaluation as evaluation
from test_oss_mimo_adapter import Transport, envelope


class FixtureCohortTests(StoreCase):
    setup_store = verdict_fixtures.FrozenVerdictJournalTests.setup_store
    open_adoption = verdict_fixtures.FrozenVerdictJournalTests.open_adoption
    adopt = verdict_fixtures.FrozenVerdictJournalTests.adopt
    make_bridge = verdict_fixtures.FrozenVerdictJournalTests.make_bridge
    exclude_memory = verdict_fixtures.FrozenVerdictJournalTests.exclude_memory
    make_adapter = verdict_fixtures.FrozenVerdictJournalTests.make_adapter
    open_journal = verdict_fixtures.FrozenVerdictJournalTests.open_journal
    register = verdict_fixtures.FrozenVerdictJournalTests.register

    def setUp(self):
        super().setUp()
        self.issue_number = 1
        self.store = self.setup_store()
        self.adopt(self.store, "m-1", "e-1", claim=capture_fixtures.CLAIM)
        self.sources = {name: ("# stand-in: " + name).encode() for name in worker.SOURCE_HASHES}
        pins = {name: worker.digest(body) for name, body in self.sources.items()}
        self.delivered = []
        for patch in (
            mock.patch.object(worker, "SOURCE_HASHES", pins),
            mock.patch.object(capture_fixtures.parent, "freeze_sources", return_value=self.sources),
            mock.patch.object(capture_fixtures.parent, "launch", side_effect=self.stand_in),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        self.bridge = self.make_bridge()
        self.path = str(Path(self.dir) / "cohort-execution.sqlite")
        self.journal = self.open_journal(initialize=True)
        self.registry_path = Path(self.dir) / "cohorts.sqlite"
        self.registry = self.open_registry(initialize=True)
        self.members, self.instances, self.transports = [], {}, {}

    def open_registry(self, initialize=False):
        registry = cohort.CohortRegistry(self.registry_path, initialize=initialize)
        self.addCleanup(registry.close)
        return registry

    def stand_in(self, argv, payload, timeout=None):
        # Structural capture validation supports all five built-in issues. The
        # actual pinned worker still selects only issue #3; this is a stand-in,
        # including its deliberately authored borderline score/reasons.
        doc = worker.strict_json(capture_fixtures.PairedOutcomeJournalTests.stand_in(
            self, argv, payload, timeout))
        reference = self.delivered[-1]
        item = worker.synthetic_task()["issues"][self.issue_number - 1]
        doc["issue"] = dict(item, repo=worker.REPOSITORY,
                            url="fixture://issue/%d" % self.issue_number)
        prefix = "\n".join([worker.REPOSITORY, item["title"], item["body"], "synthetic reason"]) + "\n"
        notes = child.reference_notes(reference)
        for arm in cohort.ARMS:
            payload = copy.deepcopy(doc["arms"][arm]["payload"])
            payload["messages"][0]["content"] = prefix + (
                "\nProject notes:\n" + notes + "\n" if arm == "reference" else "") + "Respond with JSON"
            doc["arms"][arm] = child.arm_artifact(
                arm, child.MOCK_URL, doc["arms"][arm]["header_names"], payload,
                notes if arm == "reference" else "")
        doc["comparability"] = child.comparability(
            doc["arms"]["baseline"]["payload"], doc["arms"]["reference"]["payload"], notes)
        return worker.encoded(doc)

    def add_plan(self, number, *, plan_id=None, expected=True, adapter_changes=None, **changes):
        self.issue_number = number
        self.summary, self.doc = capture.prepare_from_bridge(
            self.bridge, self.dir, query=capture_fixtures.QUERY,
            max_bytes=worker.MAX_REFERENCE_BYTES, worker_argv=["/synthetic/stand-in"])
        self.reference = self.delivered[-1]
        plan_id = plan_id or "plan-%d" % number
        transport = Transport(envelope(text=verdict_fixtures.reply(True)))
        instance = self.make_adapter(transport, **(adapter_changes or {}))
        manifest = evaluation.freeze_manifest(
            dataset_id="synthetic-cohort-v1", expected_accept=expected,
            task_sha256=self.doc["task_sha256"], issue_number=number)
        options = dict(evaluation_manifest=manifest)
        options.update(changes)
        self.register(instance, plan_id=plan_id, **options)
        member = cohort.member_identity(self.journal, plan_id, self.bridge)
        self.members.append(member)
        self.instances[plan_id], self.transports[plan_id] = instance, transport
        return member

    def freeze(self, cohort_id="cohort-1", *, members=None, **changes):
        selected = self.members if members is None else members
        options = dict(journal=self.journal, members=selected,
                       bridges={member["plan_id"]: self.bridge for member in selected})
        options.update(changes)
        return self.registry.register(cohort_id, **options)

    def report(self, **changes):
        options = dict(journal=self.journal,
                       bridges={member["plan_id"]: self.bridge for member in self.members})
        options.update(changes)
        return self.registry.report("cohort-1", **options)

    def finish(self, number, baseline=True, reference=True):
        plan_id = "plan-%d" % number
        transport, instance = self.transports[plan_id], self.instances[plan_id]
        transport.result = envelope(text=verdict_fixtures.reply(baseline))
        self.journal.run(plan_id, self.bridge, instance, limit=1)
        transport.result = envelope(text=verdict_fixtures.reply(reference))
        self.journal.run(plan_id, self.bridge, instance)

    def test_multitask_pairing_fixed_denominator_and_private_report_allowlist(self):
        for number, expected in ((1, True), (2, False), (3, True)):
            self.add_plan(number, expected=expected)
        changes = self.journal._db.total_changes
        frozen = self.freeze()
        self.assertEqual(frozen["registered_tasks"], 3)
        self.assertEqual(self.journal._db.total_changes, changes)
        self.finish(1, False, True)  # scores 0, 1
        self.finish(2, False, False)  # scores 1, 1
        self.finish(3, False, False)  # scores 0, 0
        changes = self.journal._db.total_changes
        report = self.report()
        self.assertEqual(report["status"], "complete")
        self.assertEqual((report["registered_tasks"], report["complete_tasks"], report["incomplete_tasks"]),
                         (3, 3, 0))
        self.assertAlmostEqual(report["reference_minus_baseline"], 1 / 3)
        self.assertEqual([report["arms"][arm]["observed_successes"] for arm in cohort.ARMS], [1, 2])
        self.assertEqual([report["arms"][arm]["scored_tasks"] for arm in cohort.ARMS], [3, 3])
        for forbidden in ("reply_body", "rationale", "expected_accept", "合成の理由", "verdict"):
            # 'invalid_verdicts' is a count, so inspect keys rather than a
            # substring search for the legitimate status/count vocabulary.
            if forbidden == "verdict":
                self.assertNotIn(forbidden, report)
            else:
                self.assertNotIn(forbidden, repr(report))
                self.assertNotIn(forbidden, repr(frozen))
        self.assertEqual((report["usage"], report["cost"], report["adoption"],
                          report["performance_improvement"]),
                         ("unavailable", "unavailable", "none", "not_evaluated"))
        self.assertEqual(self.journal._db.total_changes, changes)
        self.assertEqual(sum(len(t.calls) for t in self.transports.values()), 6)
        self.assertEqual(self.report(), report)
        self.assertEqual(sum(len(t.calls) for t in self.transports.values()), 6)

    def test_any_member_intent_prevents_new_registration_including_unclosed_and_completed(self):
        for number in (1, 2):
            self.add_plan(number)
        self.journal._db.execute(
            "INSERT INTO arms (plan_id,arm,state) VALUES ('plan-2','baseline','intent')")
        with self.assertRaisesRegex(cohort.CohortError, "precede"):
            self.freeze()
        self.assertEqual(self.registry._db.execute("SELECT COUNT(*) FROM cohorts").fetchone()[0], 0)
        self.assertEqual(sum(len(t.calls) for t in self.transports.values()), 0)
        healthy = Transport()
        self.journal.run("plan-2", self.bridge, self.make_adapter(healthy))
        self.assertEqual(healthy.calls, [])  # intent recovery retains no-retry
        self.finish(1)
        with self.assertRaisesRegex(cohort.CohortError, "precede"):
            self.freeze("after-completion")

    def test_registration_reserves_all_journal_intents_until_registry_commit(self):
        for number in (1, 2):
            self.add_plan(number)
        other = self.open_journal()
        other._db.execute("PRAGMA busy_timeout=0")
        load = self.registry._load
        attempts = []

        def competing(cohort_id):
            with self.assertRaises(sqlite3.OperationalError):
                other._db.execute("BEGIN IMMEDIATE")
            attempts.append(cohort_id)
            return load(cohort_id)

        with mock.patch.object(self.registry, "_load", side_effect=competing):
            self.freeze()
        self.assertEqual(attempts, ["cohort-1"])
        self.assertFalse(self.journal._db.in_transaction)
        other._db.execute("BEGIN IMMEDIATE")  # released after durable freeze
        other._db.execute("ROLLBACK")
        self.assertEqual(sum(len(t.calls) for t in self.transports.values()), 0)

    def test_exact_member_identities_and_comparison_settings_are_required(self):
        for number in (1, 2):
            self.add_plan(number)
        for key, value in (("plan_id", "missing"), ("binding_sha256", "0" * 64),
                           ("manifest_sha256", "0" * 64), ("task_sha256", "0" * 64),
                           ("issue_number", 3)):
            members = copy.deepcopy(self.members)
            members[0][key] = value
            with self.subTest(key=key), self.assertRaises(cohort.CohortError):
                self.freeze(members=members)
        self.add_plan(3, adapter_changes=dict(timeout=119))
        with self.assertRaisesRegex(cohort.CohortError, "settings"):
            self.freeze(members=[self.members[0], self.members[2]])
        self.add_plan(4, max_reply_bytes=4095)
        with self.assertRaisesRegex(cohort.CohortError, "settings"):
            self.freeze(members=[self.members[0], self.members[3]])
        self.add_plan(5, evaluation_manifest=evaluation.freeze_manifest(
            dataset_id="other-development-dataset", expected_accept=True,
            task_sha256=self.doc["task_sha256"], issue_number=5))
        with self.assertRaisesRegex(cohort.CohortError, "settings"):
            self.freeze(members=[self.members[0], self.members[4]])
        self.assertEqual(sum(len(t.calls) for t in self.transports.values()), 0)

    def test_duplicate_plans_tasks_exact_schema_bounds_and_independent_relabelling_refused(self):
        self.add_plan(1)
        self.add_plan(1, plan_id="duplicate-task")
        with self.assertRaisesRegex(cohort.CohortError, "duplicate"):
            self.freeze()
        with self.assertRaisesRegex(cohort.CohortError, "duplicate"):
            self.freeze(members=[self.members[0], self.members[0]])
        self.add_plan(2)
        good = [self.members[0], self.members[2]]
        for members in (good[:1], good * 3, tuple(good)):
            with self.subTest(shape=type(members)), self.assertRaises(cohort.CohortError):
                self.freeze(members=members)
        for key, value in (("issue_number", True), ("manifest_sha256", "A" * 64),
                           ("plan_id", "p" * 129), ("partition", "independent_evaluation"),
                           ("expected_accept", True)):
            members = copy.deepcopy(good)
            members[0][key] = value
            with self.subTest(key=key), self.assertRaises(cohort.CohortError):
                self.freeze(members=members)
        frozen = self.freeze(members=list(reversed(good)))
        self.assertEqual(frozen["members"], good)
        with self.assertRaises(cohort.CohortError):
            self.freeze(members=good, bridges={good[0]["plan_id"]: self.bridge})
        self.add_plan(3)
        with self.assertRaisesRegex(cohort.CohortError, "already frozen"):
            self.freeze(members=[*good, self.members[-1]])

    def test_all_frozen_manifests_and_correct_bridges_required_before_registration(self):
        for number in (1, 2):
            self.add_plan(number)
        with self.assertRaisesRegex(cohort.CohortError, "manifest"):
            self.add_plan(3, evaluation_manifest=None)
        unscored = dict(self.members[0], plan_id="plan-3", issue_number=3)
        with self.assertRaisesRegex(cohort.CohortError, "manifest"):
            self.freeze(members=[self.members[0], unscored])
        with mock.patch.object(evaluation, "IMPLEMENTATION_SHA256", "0" * 64):
            with self.assertRaisesRegex(cohort.CohortError, "manifest"):
                self.freeze()
        wrong = self.make_bridge(scope=capture_fixtures.OTHER)
        with self.assertRaises(capture_fixtures.paired.PlanConflict):
            self.freeze(bridges={"plan-1": self.bridge, "plan-2": wrong})
        self.assertEqual(self.registry._db.execute("SELECT COUNT(*) FROM cohorts").fetchone()[0], 0)
        self.freeze()
        report = self.report(bridges={"plan-1": self.bridge, "plan-2": wrong})
        self.assertEqual(report["tasks"][1]["status"], "identity_or_settings_mismatch")
        self.assertIsNone(report["reference_minus_baseline"])
        self.assertEqual(sum(len(t.calls) for t in self.transports.values()), 0)

    def test_missing_and_unknown_arms_stay_incomplete_without_zero_imputation_or_retry(self):
        for number in (1, 2, 3):
            self.add_plan(number)
        self.freeze()
        self.finish(1)
        self.journal.run("plan-2", self.bridge, self.instances["plan-2"], limit=1)
        failed = Transport(error=TimeoutError("private provider details"))
        self.journal.run("plan-2", self.bridge, self.make_adapter(failed))
        report = self.report()
        self.assertEqual((report["registered_tasks"], report["complete_tasks"], report["incomplete_tasks"]),
                         (3, 1, 2))
        self.assertEqual([task["status"] for task in report["tasks"]], ["complete", "incomplete", "incomplete"])
        self.assertEqual(report["tasks"][1]["arms"]["reference"]["execution_status"], "unknown")
        self.assertIsNone(report["tasks"][1]["arms"]["reference"]["score"])
        self.assertIsNone(report["reference_minus_baseline"])
        self.assertEqual([report["arms"][arm]["scored_tasks"] for arm in cohort.ARMS], [2, 1])
        self.assertTrue(all(report["arms"][arm]["mean_score"] is None for arm in cohort.ARMS))
        self.assertNotIn("private", repr(report))
        healthy = Transport()
        self.journal.run("plan-2", self.bridge, self.make_adapter(healthy))
        self.assertEqual((len(failed.calls), healthy.calls), (1, []))
        self.assertEqual(self.report(), report)

    def test_completed_invalid_verdicts_are_failures_in_complete_cohort(self):
        for number in (1, 2):
            self.add_plan(number)
        self.freeze()
        self.finish(1)
        transport = self.transports["plan-2"]
        transport.result = envelope(text="invalid private rationale and answer label")
        self.journal.run("plan-2", self.bridge, self.instances["plan-2"])
        report = self.report()
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["tasks"][1]["status"], "complete_with_invalid_verdict")
        for arm in cohort.ARMS:
            self.assertEqual(report["arms"][arm], dict(
                registered_tasks=2, scored_tasks=2, observed_successes=1, invalid_verdicts=1, mean_score=0.5))
        self.assertEqual(report["reference_minus_baseline"], 0)
        self.assertNotIn("private", repr(report))
        self.assertEqual(len(transport.calls), 2)

    def test_context_unavailability_and_revocation_withhold_only_affected_plan_scores(self):
        for number in (1, 2):
            self.add_plan(number)
        other_bridge = self.make_bridge()
        bridges = {"plan-1": self.bridge, "plan-2": other_bridge}
        self.freeze(bridges=bridges)
        self.finish(1)
        self.finish(2)
        with mock.patch.object(other_bridge, "reference_context", side_effect=ValueError("private")):
            report = self.report(bridges=bridges)
        self.assertEqual([task["status"] for task in report["tasks"]], ["complete", "withheld_context"])
        self.assertIsNone(report["reference_minus_baseline"])
        self.assertTrue(all(item["score"] is None for item in report["tasks"][1]["arms"].values()))
        for number in (3, 4):
            self.add_plan(number)  # still-current, genuinely unstarted plans
        self.exclude_memory()
        report = self.report(bridges=bridges)
        self.assertEqual([task["status"] for task in report["tasks"]], ["withheld_context"] * 2)
        self.assertEqual((report["registered_tasks"], report["complete_tasks"]), (2, 0))
        self.assertTrue(all(report["arms"][arm]["scored_tasks"] == 0 for arm in cohort.ARMS))
        self.assertEqual(sum(len(t.calls) for t in self.transports.values()), 4)
        with self.assertRaisesRegex(cohort.CohortError, "context"):
            self.freeze("revoked-before-registration", members=self.members[2:])

    def test_missing_plan_bridge_or_changed_evaluator_never_shrinks_denominator(self):
        for number in (1, 2):
            self.add_plan(number)
        self.freeze()
        self.finish(1)
        self.finish(2)
        with mock.patch.object(evaluation, "IMPLEMENTATION_SHA256", "0" * 64):
            report = self.report()
        self.assertEqual([task["status"] for task in report["tasks"]],
                         ["unavailable_evaluator_version_or_manifest"] * 2)
        self.assertIsNone(report["reference_minus_baseline"])
        self.assertEqual(self.report(bridges={})["incomplete_tasks"], 2)
        self.journal._db.execute("DELETE FROM arms WHERE plan_id='plan-2'")
        self.journal._db.execute("DELETE FROM plans WHERE plan_id='plan-2'")
        report = self.report()
        self.assertEqual(report["tasks"][1]["status"], "missing_plan")
        self.assertEqual((report["registered_tasks"], report["incomplete_tasks"]), (2, 1))
        self.assertIsNone(report["reference_minus_baseline"])

    def test_reopen_exact_registration_replay_and_execution_replay_preserve_calls(self):
        for number in (1, 2):
            self.add_plan(number)
        frozen = self.freeze()
        frozen["members"][0]["binding_sha256"] = "0" * 64  # returned copy has no authority
        self.finish(1)
        self.journal.run("plan-2", self.bridge, self.instances["plan-2"], limit=1)
        self.registry.close()
        self.journal.close()
        self.registry, self.journal = self.open_registry(), self.open_journal()
        self.assertEqual(self.report()["registered_tasks"], 2)
        # This is replay of an existing registration, never post-hoc registration.
        self.assertEqual(self.freeze()["members"], self.members)
        second = self.make_adapter(self.transports["plan-2"])
        self.journal.run("plan-2", self.bridge, second)
        report = self.report()
        healthy = Transport()
        for number in (1, 2):
            self.journal.run("plan-%d" % number, self.bridge, self.make_adapter(healthy))
        self.assertEqual(healthy.calls, [])
        self.assertEqual(self.report(), report)
        self.assertEqual(sum(len(t.calls) for t in self.transports.values()), 4)
        with self.assertRaisesRegex(cohort.CohortError, "precede"):
            self.freeze("post-hoc-new-cohort")

    def test_saved_registry_schema_hash_and_exact_document_integrity_fail_closed(self):
        for number in (1, 2):
            self.add_plan(number)
        self.freeze()
        original = self.registry._db.execute("SELECT document FROM cohorts").fetchone()[0]
        variants = []
        for key, value in (("partition", "independent_evaluation"), ("registered_tasks", True),
                           ("registered_tasks", 3), ("extra", "private")):
            doc = worker.strict_json(original)
            doc[key] = value
            variants.append(worker.encoded(doc))
        doc = worker.strict_json(original)
        doc["members"][1] = doc["members"][0]
        variants.extend([worker.encoded(doc), original + b" ",
                         b'{"protocol":"a","protocol":"b"}', b"x" * (cohort.MAX_DOCUMENT_BYTES + 1)])
        for raw in variants:
            self.registry._db.execute("UPDATE cohorts SET document=?,document_sha256=?",
                                      (raw, worker.digest(raw)))
            with self.subTest(size=len(raw)), self.assertRaises(cohort.CohortError):
                self.report()
        self.registry._db.execute("UPDATE cohorts SET document=?,document_sha256=?", (original, "0" * 64))
        with self.assertRaisesRegex(cohort.CohortError, "integrity"):
            self.report()
        self.registry._db.execute("CREATE TABLE foreign_table (value TEXT)")
        with self.assertRaisesRegex(cohort.CohortError, "changed"):
            self.open_registry()

    def test_foreign_database_refusal_and_plan_corruption_remain_read_only(self):
        foreign = Path(self.dir) / "foreign.sqlite"
        with sqlite3.connect(foreign) as db:
            db.execute("CREATE TABLE foreign_table (value TEXT)")
        before = foreign.read_bytes()
        with self.assertRaises(cohort.CohortError):
            cohort.CohortRegistry(foreign, initialize=True)
        self.assertEqual(foreign.read_bytes(), before)
        with self.assertRaises(cohort.CohortError):
            cohort.CohortRegistry(Path(self.dir) / "missing.sqlite")
        for number in (1, 2):
            self.add_plan(number)
        self.freeze()
        raw = self.journal._db.execute("SELECT binding FROM plans WHERE plan_id='plan-2'").fetchone()[0]
        binding = worker.strict_json(raw)
        binding["adapter"]["timeout_seconds"] = 119
        changed = worker.encoded(binding)
        self.journal._db.execute("UPDATE plans SET binding=?,binding_sha256=? WHERE plan_id='plan-2'",
                                 (changed, worker.digest(changed)))
        report = self.report()
        self.assertEqual(report["tasks"][1]["status"], "identity_or_settings_mismatch")
        self.assertIsNone(report["reference_minus_baseline"])
        self.journal._db.execute("UPDATE plans SET binding_sha256=? WHERE plan_id='plan-2'", ("0" * 64,))
        changes = self.journal._db.total_changes
        self.assertEqual(self.report()["tasks"][1]["status"], "unavailable_journal_integrity")
        self.assertEqual(self.journal._db.total_changes, changes)
        self.assertEqual(sum(len(t.calls) for t in self.transports.values()), 0)
