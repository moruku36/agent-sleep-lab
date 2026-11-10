"""Actual pinned judge/prompt captures, temporary stores, injected replies only.

Only source acquisition is injected: all eleven original public source blobs
are checked against the production pins and run by the actual guarded worker.
Adoption/evaluator receipts and response envelopes are authored synthetic data.
No network, credentials, model calls, target mutations or performance evidence.
"""
import copy
from pathlib import Path
from unittest import mock

import support  # noqa: F401
import test_oss_execution_journal as journal_fixtures
import test_oss_paired_outcome as store_fixtures
import test_oss_verdict_evaluation as verdict_fixtures
from evidence_support import StoreCase
from oss_pinned_support import pinned_sources
from agent_sleep_lab import oss_execution_journal as execution
from agent_sleep_lab import oss_fixture_cohort as cohort
from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_prompt_capture as capture
from agent_sleep_lab import oss_prompt_capture_worker as child
from agent_sleep_lab import oss_verdict_evaluation as evaluation
from test_oss_mimo_adapter import Transport, envelope


class SelectedIssueProbeTests(StoreCase):
    setup_store = store_fixtures.PairedOutcomeJournalTests.setup_store
    open_adoption = store_fixtures.PairedOutcomeJournalTests.open_adoption
    adopt = store_fixtures.PairedOutcomeJournalTests.adopt
    make_bridge = store_fixtures.PairedOutcomeJournalTests.make_bridge
    exclude_memory = store_fixtures.PairedOutcomeJournalTests.exclude_memory
    make_adapter = journal_fixtures.ExecutionJournalTests.make_adapter

    def setUp(self):
        super().setUp()
        self.sources = pinned_sources()
        self.store = self.setup_store()
        self.adopt(self.store, "m-1", "e-1", claim=store_fixtures.CLAIM)
        self.bridge = self.make_bridge()
        self.reference = self.bridge.reference_context(
            query=store_fixtures.QUERY, max_bytes=worker.MAX_REFERENCE_BYTES).bundle_bytes
        patch = mock.patch.object(parent, "freeze_sources", return_value=self.sources)
        self.freeze_sources = patch.start()
        self.addCleanup(patch.stop)
        self.path = Path(self.dir) / "selected-execution.sqlite"
        self.journal = self.open_journal(initialize=True)

    def open_journal(self, initialize=False):
        journal = execution.ExecutionJournal(self.path, initialize=initialize)
        self.addCleanup(journal.close)
        return journal

    def prepare(self, number=None):
        options = {} if number is None else dict(selected_issue_probe=capture.selected_issue_probe(number))
        summary, doc = capture.prepare_from_bridge(self.bridge, self.dir,
            query=store_fixtures.QUERY, max_bytes=worker.MAX_REFERENCE_BYTES, **options)
        self.assertEqual(doc["reference_sha256"], worker.digest(self.reference))
        self.assertEqual(summary["worker_launch"], capture.BUILTIN_WORKER)
        self.assertEqual(doc["executed_source_sha256"], worker.SOURCE_HASHES)
        return summary, doc

    def validate(self, doc, selection=None):
        return capture.validate_output(worker.encoded(doc), task=parent.builtin_task(),
            reference=self.reference, selected_issue_probe=selection)

    def register(self, number, *, plan_id=None, capture_pair=None, expected=True):
        summary, doc = self.prepare(number) if capture_pair is None else capture_pair
        plan_id = plan_id or "selected-%d" % number
        transport = Transport(envelope(text=verdict_fixtures.reply(expected)))
        adapter = self.make_adapter(transport)
        manifest = evaluation.freeze_manifest(dataset_id="selected-probes-v1",
            expected_accept=expected, task_sha256=doc["task_sha256"],
            issue_number=doc["issue"]["number"])
        options = dict(summary=summary, capture_doc=doc, reference=self.reference,
            bridge=self.bridge, query=store_fixtures.QUERY, max_bytes=worker.MAX_REFERENCE_BYTES,
            max_records=16, max_request_bytes=131072, max_reply_bytes=4096,
            evaluation_manifest=manifest)
        self.journal.register(plan_id, adapter=adapter, **options)
        return plan_id, adapter, transport, options

    def registry(self):
        registry = cohort.CohortRegistry(Path(self.dir) / "selected-cohorts.sqlite", initialize=True)
        self.addCleanup(registry.close)
        return registry

    def freeze(self, registry, plans, cohort_id="selected-cohort"):
        bridges = {plan_id: self.bridge for plan_id in plans}
        members = [cohort.member_identity(self.journal, plan_id, self.bridge) for plan_id in plans]
        document = registry.register(cohort_id, journal=self.journal, members=members, bridges=bridges)
        return document, bridges

    def test_default_v1_is_still_only_borderline_and_probe_three_preserves_target_requests(self):
        old_summary, old = self.prepare()
        new_summary, new = self.prepare(3)
        self.assertEqual((old["protocol"], old_summary["protocol"], old["issue"]["number"],
                          old["score"], old["band"]),
                         (child.OUTPUT_PROTOCOL, capture.CHECK_PROTOCOL, 3, 0.5, "borderline"))
        self.assertEqual(set(old), child.OUTPUT_KEYS)
        self.assertNotIn("selected_issue_probe", old_summary)
        self.assertEqual(new["arms"], old["arms"])
        self.assertEqual(new["reasons"], old["reasons"])
        self.assertEqual(new_summary["protocol"], capture.PROBE_CHECK_PROTOCOL)
        self.assertFalse(new["probe_provenance"]["normal_automatic_triage"])
        self.assertIsNone(new["verdict"])
        self.validate(old)
        with self.assertRaises(capture.CheckError):
            self.validate(new)  # explicit expected selection required by validator

    def test_all_builtin_issues_use_actual_scores_bands_judge_and_prompt_without_a_reply(self):
        expected = {1: (0.65, "accept"), 2: (0.0, "skip"), 3: (0.5, "borderline"),
                    4: (0.65, "accept"), 5: (0.65, "accept")}
        for number, scored in expected.items():
            with self.subTest(number=number):
                summary, doc = self.prepare(number)
                selection = capture.selected_issue_probe(number)
                self.assertEqual((doc["score"], doc["band"]), scored)
                self.assertEqual(doc["issue"], child.synthetic_issue(number))
                self.assertEqual(selection["issue_sha256"], worker.digest(worker.encoded(doc["issue"])))
                self.assertEqual(doc["selected_issue_probe"], selection)
                self.assertEqual(doc["probe_provenance"], child.PROBE_PROVENANCE)
                self.assertEqual(summary["band"], scored[1])
                self.assertEqual(summary["selected_issue_probe"], selection)
                self.assertEqual(doc["target_calls"]["src/collector/triager.py:score_issue_ref"], 5)
                for name in child.REQUIRED_TRACE:
                    self.assertEqual(doc["target_calls"][name], 2)
                self.validate(doc, selection)
                for arm in doc["arms"].values():
                    prompt = child.prompt_of(arm["payload"])
                    self.assertIn("Rule-based score: %.2f (borderline band)" % scored[0], prompt)
                    self.assertEqual((arm["transport_calls"], arm["outcome"], arm["verdict"]),
                                     (1, child.NO_VERDICT, None))
                self.assertNotIn(store_fixtures.CLAIM, child.prompt_of(doc["arms"]["baseline"]["payload"]))
                self.assertIn(self.reference.decode(), child.prompt_of(doc["arms"]["reference"]["payload"]))

    def test_selection_types_bounds_and_hashes_fail_before_retrieval_git_or_launch(self):
        for number in (True, False, 0, 6, -1, 1.0, "1", None, [], 10**100):
            with self.subTest(number=number), self.assertRaises(ValueError):
                capture.selected_issue_probe(number)
        good = capture.selected_issue_probe(1)
        invalid = [dict(good, issue_number=True), dict(good, issue_number=2),
                   dict(good, issue_sha256="0" * 64), dict(good, task_sha256="0" * 64),
                   dict(good, protocol="unknown"), dict(good, extra=False), {}, []]
        self.freeze_sources.reset_mock()
        with mock.patch.object(parent, "launch") as launch, mock.patch.object(
                self.bridge, "reference_context") as retrieve:
            for selection in invalid:
                with self.subTest(selection=selection):
                    with self.assertRaises(capture.CheckError):
                        capture.prepare(self.dir, self.reference, selected_issue_probe=selection)
                    with self.assertRaises(capture.CheckError):
                        capture.prepare_from_bridge(self.bridge, self.dir,
                            query=store_fixtures.QUERY, max_bytes=32768, selected_issue_probe=selection)
            retrieve.assert_not_called()
            launch.assert_not_called()
            self.freeze_sources.assert_not_called()
        base_payload = worker.strict_json(parent.prepare_payload(self.sources, self.reference))
        for selection in invalid:
            payload = dict(protocol=child.PROBE_INPUT_PROTOCOL, payload=base_payload,
                           selected_issue_probe=selection)
            with self.assertRaises(ValueError), mock.patch.object(worker, "load_sources") as load:
                child.run(payload)
            load.assert_not_called()

    def test_selected_identity_mismatches_including_identical_task_text_are_rejected(self):
        _, doc = self.prepare(1)
        selection = capture.selected_issue_probe(1)
        for changes in (
                dict(issue=child.synthetic_issue(4)),
                dict(selected_issue_probe=capture.selected_issue_probe(4)),
                dict(issue=dict(doc["issue"], number=True)),
                dict(issue=dict(doc["issue"], labels=[])),
                dict(task_sha256="0" * 64), dict(band="borderline"), dict(score=0.5),
                dict(probe_provenance=dict(child.PROBE_PROVENANCE, normal_automatic_triage=True)),
                dict(probe_provenance=dict(child.PROBE_PROVENANCE, normal_automatic_triage=0)),
                dict(target_calls={name: 2 for name in child.REQUIRED_TRACE})):
            bad = copy.deepcopy(doc)
            bad.update(changes)
            with self.subTest(changes=changes), self.assertRaises(capture.CheckError):
                self.validate(bad, selection)
        with self.assertRaises(capture.CheckError):
            self.validate(doc, capture.selected_issue_probe(4))

    def test_strict_v1_v2_payload_output_and_summary_boundaries(self):
        old_summary, old = self.prepare()
        summary, doc = self.prepare(3)
        selection = capture.selected_issue_probe(3)
        for bad, expected in ((dict(old, selected_issue_probe=selection), None),
                              (dict(doc, protocol=child.OUTPUT_PROTOCOL), selection),
                              (dict(old, protocol=child.PROBE_OUTPUT_PROTOCOL), selection),
                              (old, selection)):
            with self.subTest(protocol=bad["protocol"]), self.assertRaises(capture.CheckError):
                self.validate(bad, expected)
        payload = worker.strict_json(parent.prepare_payload(self.sources, self.reference))
        wrapped = dict(protocol=child.PROBE_INPUT_PROTOCOL, selected_issue_probe=selection, payload=payload)
        with self.assertRaises(ValueError):
            worker.validate_payload(wrapped)  # the base worker never accepts v2
        for bad in (dict(wrapped, extra=True), dict(wrapped, protocol="unknown"),
                    dict(payload, selected_issue_probe=selection)):
            with self.assertRaises(ValueError):
                child.validate_payload(bad)
        for summary_value, doc_value in ((old_summary, doc), (summary, old),
                (dict(summary, probe_provenance={}), doc),
                (dict(summary, selected_issue_probe=capture.selected_issue_probe(1)), doc)):
            with self.assertRaises(capture.CheckError):
                self.register(3, capture_pair=(summary_value, doc_value))
        self.assertEqual(self.journal._db.execute("SELECT COUNT(*) FROM plans").fetchone()[0], 0)

    def test_probe_adapter_and_frozen_journal_reject_changed_selection_before_transport(self):
        plan_id, adapter, transport, options = self.register(1)
        bad = copy.deepcopy(options["capture_doc"])
        bad["selected_issue_probe"] = capture.selected_issue_probe(4)
        with self.assertRaises(capture.CheckError):
            adapter.complete(bad, reference=self.reference, arm="baseline", max_output_bytes=4096)
        self.assertEqual((adapter.calls, transport.calls), (0, []))
        summary, doc = self.prepare(2)
        changed = dict(options, summary=summary, capture_doc=doc,
            evaluation_manifest=evaluation.freeze_manifest(dataset_id="selected-probes-v1",
                expected_accept=True, task_sha256=doc["task_sha256"], issue_number=2))
        with self.assertRaises(execution.PlanConflict):
            self.journal.register(plan_id, adapter=adapter, **changed)
        report = self.journal.run(plan_id, self.bridge, adapter, limit=1)
        receipt = report["arms"]["baseline"]["receipt"]
        self.assertEqual(receipt["selected_issue_probe"], options["capture_doc"]["selected_issue_probe"])
        self.assertEqual(receipt["probe_provenance"], child.PROBE_PROVENANCE)
        self.assertEqual((receipt["score"], receipt["band"]), (0.65, "accept"))
        self.assertIn("not_normal_target_execution", report["worker"]["target_integration"])
        self.assertEqual(transport.calls[0][0][-1],
                         child.prompt_of(options["capture_doc"]["arms"]["baseline"]["payload"]))

    def test_real_five_task_capture_journal_restart_and_cohort_flow_with_injected_replies(self):
        plans = [self.register(number, expected=(number != 2)) for number in range(1, 6)]
        registry = self.registry()
        frozen, bridges = self.freeze(registry, [plan[0] for plan in plans])
        self.assertEqual(frozen["registered_tasks"], 5)
        self.assertEqual(frozen["protocol"], cohort.PROBE_PROTOCOL)
        self.assertEqual(frozen["probe_provenance"], child.PROBE_PROVENANCE)
        plan_id, adapter, transport, options = plans[0]
        self.journal.run(plan_id, self.bridge, adapter, limit=1)
        self.journal.close()
        self.journal = self.open_journal()
        self.journal.run(plan_id, self.bridge, self.make_adapter(transport))
        for plan_id, adapter, transport, options in plans[1:4]:
            if plan_id == "selected-4":
                transport.result = envelope(text="intentionally invalid synthetic verdict")
            self.journal.run(plan_id, self.bridge, adapter)
        report = registry.report("selected-cohort", journal=self.journal, bridges=bridges)
        self.assertEqual((report["registered_tasks"], report["complete_tasks"]), (5, 4))
        self.assertIsNone(report["reference_minus_baseline"])
        plan_id, adapter, transport, _ = plans[4]
        self.journal.run(plan_id, self.bridge, adapter)
        report = registry.report("selected-cohort", journal=self.journal, bridges=bridges)
        self.assertEqual((report["status"], report["complete_tasks"]), ("complete", 5))
        self.assertFalse(report["probe_provenance"]["normal_automatic_triage"])
        for arm in cohort.ARMS:
            self.assertEqual(report["arms"][arm], dict(registered_tasks=5, scored_tasks=5,
                observed_successes=4, invalid_verdicts=1, mean_score=0.8))
        self.assertEqual(report["reference_minus_baseline"], 0)
        self.assertNotIn("rationale", repr(report))
        self.assertNotIn("expected_accept", repr(frozen))
        self.assertEqual(sum(len(plan[2].calls) for plan in plans), 10)
        for plan_id, _, _, _ in plans:
            fresh = Transport()
            self.journal.run(plan_id, self.bridge, self.make_adapter(fresh))
            self.assertEqual(fresh.calls, [])
        self.assertEqual(registry.report("selected-cohort", journal=self.journal, bridges=bridges), report)
        # A fresh cohort after execution and a changed frozen membership both fail.
        with self.assertRaises(cohort.CohortError):
            self.freeze(registry, [plan[0] for plan in plans], "too-late")
        with self.assertRaises(cohort.CohortError):
            self.freeze(registry, [plan[0] for plan in plans[:2]])

    def test_selected_cohorts_refuse_mixed_versions_settings_and_extra_insertions(self):
        first = self.register(1)
        old = self.register(3, plan_id="old-three", capture_pair=self.prepare())
        registry = self.registry()
        with self.assertRaisesRegex(cohort.CohortError, "settings"):
            self.freeze(registry, [first[0], old[0]])
        second = self.register(2)
        binding, _, _ = self.journal._binding(second[0], self.bridge)
        original = cohort._comparison(binding)
        binding["adapter"]["timeout_seconds"] -= 1
        self.assertNotEqual(cohort._comparison(binding), original)
        binding["capture_doc"]["probe_provenance"]["normal_automatic_triage"] = True
        with self.assertRaises(execution.JournalError):
            cohort._comparison(binding)
        _, doc = self.prepare(2)
        notes = child.reference_notes(self.reference)
        payload = copy.deepcopy(doc["arms"]["reference"]["payload"])
        payload["messages"][0]["content"] = child.prompt_of(payload).replace(
            "\nProject notes:\n", "\nExtra task instructions\nProject notes:\n")
        doc["arms"]["reference"] = child.arm_artifact("reference", child.MOCK_URL,
            doc["arms"]["reference"]["header_names"], payload, notes)
        doc["comparability"] = child.comparability(doc["arms"]["baseline"]["payload"], payload, notes)
        with self.assertRaises(capture.CheckError):
            self.validate(doc, capture.selected_issue_probe(2))
        self.assertEqual(first[2].calls + old[2].calls + second[2].calls, [])

    def test_new_cohort_documents_keep_exact_version_and_forced_probe_provenance(self):
        plans = [self.register(number)[0] for number in (1, 2)]
        registry = self.registry()
        frozen, _ = self.freeze(registry, plans)
        cohort._document(frozen)
        for bad in (dict(frozen, protocol=cohort.PROTOCOL),
                    dict(frozen, selection_contract="unknown"),
                    dict(frozen, probe_provenance=dict(child.PROBE_PROVENANCE, normal_automatic_triage=0)),
                    dict(frozen, extra=True)):
            with self.subTest(keys=set(bad)), self.assertRaises(cohort.CohortError):
                cohort._document(bad)

    def test_probe_unknown_outcomes_and_current_policy_keep_full_cohort_denominator(self):
        first, second = self.register(1), self.register(2)
        registry = self.registry()
        _, bridges = self.freeze(registry, [first[0], second[0]])
        failed = Transport(error=TimeoutError("private transport detail"))
        self.journal.run(first[0], self.bridge, self.make_adapter(failed))
        self.journal.run(second[0], self.bridge, second[1])
        healthy = Transport()
        self.journal.run(first[0], self.bridge, self.make_adapter(healthy))
        self.assertEqual((len(failed.calls), healthy.calls), (1, []))
        report = registry.report("selected-cohort", journal=self.journal, bridges=bridges)
        self.assertEqual((report["registered_tasks"], report["complete_tasks"]), (2, 1))
        self.assertIsNone(report["reference_minus_baseline"])
        self.exclude_memory()
        report = registry.report("selected-cohort", journal=self.journal, bridges=bridges)
        self.assertEqual(report["registered_tasks"], 2)
        self.assertTrue(all(item["scored_tasks"] == 0 for item in report["arms"].values()))
        saved = self.journal.report(second[0], self.bridge)
        self.assertIsNone(saved["arms"]["baseline"]["receipt"])
        self.assertIsNone(saved["arms"]["reference"]["reply_body"])
        self.assertNotIn("private transport", repr(report))

    def test_saved_v1_execution_reopens_and_replays_unchanged_alongside_probe_plans(self):
        old = self.register(3, plan_id="saved-v1", capture_pair=self.prepare())
        self.journal.run(old[0], self.bridge, old[1], limit=1)
        self.register(2)
        self.journal.close()
        self.journal = self.open_journal()
        report = self.journal.run(old[0], self.bridge, self.make_adapter(old[2]))
        self.assertEqual(report["plan_status"], "complete")
        self.assertNotIn("selected_issue_probe", report)
        self.assertNotIn("probe_provenance", report["arms"]["baseline"]["receipt"])
        self.assertEqual(len(old[2].calls), 2)
        fresh = Transport()
        self.assertEqual(self.journal.run(old[0], self.bridge, self.make_adapter(fresh))["arms"],
                         report["arms"])
        self.assertEqual(fresh.calls, [])
