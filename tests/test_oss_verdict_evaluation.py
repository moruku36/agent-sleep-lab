"""Strict verdict / frozen fixture evaluation; mocks, not performance evidence."""
import copy
from pathlib import Path
from unittest import TestCase, mock

import support  # noqa: F401
import test_oss_execution_journal as execution_fixtures
import test_oss_paired_outcome as capture_fixtures
from evidence_support import StoreCase
from agent_sleep_lab import oss_verdict_evaluation as evaluation
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_prompt_capture as capture
from test_oss_mimo_adapter import Transport, envelope


def reply(accepted):
    return worker.encoded(dict(accept=accepted, rationale="合成の理由 café")).decode()


class VerdictParserTests(TestCase):
    def test_valid_boolean_unicode_and_normalized_rationale(self):
        for decision in (False, True):
            parsed = evaluation.parse_verdict(worker.encoded(
                dict(accept=decision, rationale="  合成 café\n")))
            self.assertIs(parsed.accepted, decision)
            self.assertEqual(parsed.rationale, "合成 café")
        self.assertEqual(evaluation.IMPLEMENTATION_SHA256,
                         worker.digest(Path(evaluation.__file__).read_bytes()))

    def test_untrusted_json_shapes_types_bytes_and_surrogates_fail_without_excerpt(self):
        for raw in [
            b"", b"null", b"[]", b"private text", b"\xff", b"\xef\xbb\xbf{}",
            b'{"accept":1,"rationale":"private"}',
            b'{"accept":true,"rationale":1}',
            b'{"accept":true,"rationale":" "}',
            b'{"accept":true,"rationale":"private","extra":1}',
            b'{"accept":true,"accept":false,"rationale":"private"}',
            b'{"accept":true,"rationale":NaN}',
            b'{"accept":true,"rationale":"\\ud800"}',
            b'prefix {"accept":true,"rationale":"private"} suffix',
            b'```json\n{"accept":true,"rationale":"private"}\n```',
            worker.encoded(dict(accept=True, rationale="x" * 8193)),
            b"x" * 65537,
        ]:
            with self.subTest(size=len(raw)), self.assertRaises(evaluation.VerdictError) as seen:
                evaluation.parse_verdict(raw)
            self.assertNotIn("private", str(seen.exception))


class FrozenVerdictJournalTests(StoreCase):
    setup_store = capture_fixtures.PairedOutcomeJournalTests.setup_store
    open_adoption = capture_fixtures.PairedOutcomeJournalTests.open_adoption
    adopt = capture_fixtures.PairedOutcomeJournalTests.adopt
    make_bridge = capture_fixtures.PairedOutcomeJournalTests.make_bridge
    stand_in = capture_fixtures.PairedOutcomeJournalTests.stand_in
    exclude_memory = capture_fixtures.PairedOutcomeJournalTests.exclude_memory
    make_adapter = execution_fixtures.ExecutionJournalTests.make_adapter
    open_journal = execution_fixtures.ExecutionJournalTests.open_journal
    register = execution_fixtures.ExecutionJournalTests.register

    def setUp(self):
        super().setUp()
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
        self.summary, self.doc = capture.prepare_from_bridge(
            self.bridge, self.dir, query=capture_fixtures.QUERY,
            max_bytes=worker.MAX_REFERENCE_BYTES, worker_argv=["/synthetic/stand-in"])
        self.reference = self.delivered[-1]
        self.path = str(Path(self.dir) / "evaluation-execution.sqlite")
        self.journal = self.open_journal(initialize=True)
        self.manifest = evaluation.freeze_manifest(
            dataset_id="synthetic-fixture-v1", expected_accept=True,
            task_sha256=self.doc["task_sha256"], issue_number=self.doc["issue"]["number"])

    def register_scored(self, instance, **changes):
        return self.register(instance, evaluation_manifest=self.manifest, **changes)

    def test_manifest_freezes_before_intent_never_reaches_prompt_and_replay_scores_stably(self):
        transport = Transport(envelope(text=reply(False)))
        first = self.make_adapter(transport)
        initial = self.register_scored(first)
        self.assertEqual(initial["verdict_evaluation"]["status"], "incomplete")
        self.journal.run("plan-1", self.bridge, first, limit=1)
        changed = dict(self.manifest, expected_accept=False)
        with self.assertRaises(execution_fixtures.execution.PlanConflict):
            self.register(first, evaluation_manifest=changed)
        self.journal.close()
        again = self.open_journal()
        transport.result = envelope(text=reply(True))
        report = again.run("plan-1", self.bridge, self.make_adapter(transport))
        scored = report["verdict_evaluation"]
        self.assertEqual(scored["status"], "complete")
        self.assertEqual([scored["arms"][a]["score"] for a in evaluation.ARMS], [0, 1])
        self.assertEqual(scored["reference_minus_baseline"], 1)  # deliberately authored mock
        for index, arm in enumerate(evaluation.ARMS):
            argv = transport.calls[index][0]
            self.assertEqual(argv[-1], self.doc["arms"][arm]["payload"]["messages"][0]["content"])
            self.assertNotIn("expected_accept", argv[-1])
            self.assertNotIn("synthetic-fixture-v1", argv[-1])
        self.assertEqual(again.run("plan-1", self.bridge, self.make_adapter(transport))
                         ["verdict_evaluation"], scored)
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual((report["verdict"], report["performance_improvement"],
                          report["usage"], report["cost"]),
                         (None, "not_evaluated", "unavailable", "unavailable"))

    def test_manifest_types_task_version_extra_fields_fail_before_registration_or_calls(self):
        transport = Transport()
        instance = self.make_adapter(transport)
        for key, value in [
            ("expected_accept", 1), ("task_sha256", "0" * 64), ("issue_number", 2),
            ("implementation_sha256", "0" * 64), ("strict_json_sha256", "0" * 64),
            ("partition", "evaluation"),
            ("invalid_verdict_score", False), ("max_reply_bytes", True),
            ("provider_generated_label", True),
        ]:
            changed = dict(self.manifest, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.register(instance, evaluation_manifest=changed)
        self.assertEqual(transport.calls, [])
        with self.assertRaises(execution_fixtures.execution.JournalError):
            self.journal.report("plan-1", self.bridge)

    def test_invalid_verdict_counts_as_failure_without_retry_or_denominator_shrinkage(self):
        transport = Transport(envelope(text="not a verdict; private"))
        instance = self.make_adapter(transport)
        self.register_scored(instance)
        report = self.journal.run("plan-1", self.bridge, instance)
        scored = report["verdict_evaluation"]
        self.assertEqual(scored["status"], "complete_with_invalid_verdict")
        self.assertEqual(scored["total_arms"], 2)
        self.assertEqual([scored["arms"][a]["score"] for a in evaluation.ARMS], [0, 0])
        self.assertEqual(scored["reference_minus_baseline"], 0)
        self.assertNotIn("private", repr(scored))
        self.journal.run("plan-1", self.bridge, instance)
        self.assertEqual(len(transport.calls), 2)

    def test_unknown_or_missing_second_outcome_never_creates_a_pair_score(self):
        transport = Transport(envelope(text=reply(True)))
        instance = self.make_adapter(transport)
        self.register_scored(instance)
        report = self.journal.run("plan-1", self.bridge, instance, limit=1)
        self.assertIsNone(report["verdict_evaluation"]["reference_minus_baseline"])
        failed = Transport(error=TimeoutError("private"))
        report = self.journal.run("plan-1", self.bridge, self.make_adapter(failed))
        self.assertEqual(report["verdict_evaluation"]["status"], "incomplete")
        self.assertIsNone(report["verdict_evaluation"]["arms"]["reference"]["score"])
        self.assertIsNone(report["verdict_evaluation"]["reference_minus_baseline"])
        self.assertEqual(len(failed.calls), 1)

    def test_context_revocation_or_unavailability_withholds_parsed_rationales_and_scores(self):
        instance = self.make_adapter(Transport(envelope(text=reply(True))))
        self.register_scored(instance)
        self.journal.run("plan-1", self.bridge, instance)
        with mock.patch.object(self.bridge, "reference_context", side_effect=ValueError("unavailable")):
            scored = self.journal.report("plan-1", self.bridge)["verdict_evaluation"]
            self.assertEqual(scored["status"], "withheld_context")
            self.assertEqual(scored["arms"], {})
            self.assertIsNone(scored["reference_minus_baseline"])
        self.exclude_memory()
        scored = self.journal.report("plan-1", self.bridge)["verdict_evaluation"]
        self.assertEqual(scored["status"], "withheld_context")
        self.assertNotIn("合成の理由", repr(scored))

    def test_old_unscored_plans_cannot_be_relabelled_and_changed_code_is_not_used(self):
        instance = self.make_adapter(Transport(envelope(text=reply(True))))
        self.register(instance, plan_id="unscored")
        self.journal.run("unscored", self.bridge, instance)
        with self.assertRaises(execution_fixtures.execution.PlanConflict):
            self.register_scored(instance, plan_id="unscored")
        report = self.journal.report("unscored", self.bridge)
        self.assertEqual(report["verdict_evaluation"]["status"], "not_configured")
        scored_instance = self.make_adapter(Transport(envelope(text=reply(True))))
        self.register_scored(scored_instance)
        self.journal.run("plan-1", self.bridge, scored_instance)
        with mock.patch.object(evaluation, "IMPLEMENTATION_SHA256", "0" * 64):
            scored = self.journal.report("plan-1", self.bridge)["verdict_evaluation"]
            self.assertEqual(scored["status"], "unavailable_evaluator_version_or_manifest")
            self.assertIsNone(scored["reference_minus_baseline"])
