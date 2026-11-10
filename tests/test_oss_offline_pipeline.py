"""Coordinator acceptance of partial Fable output; mock checker, real stores/journal.
No target execution, adoption, model, network or verification receipts.
"""
from pathlib import Path
from unittest import mock

import support
import test_adoption_store as fixtures
from evidence_support import StoreCase, make_boundary
from runtime_support import make_control, policy_body
from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab.oss_bridge import CollectOnlyBridge
from agent_sleep_lab.oss_offline_pipeline import OfflinePipeline
from agent_sleep_lab.provenance import BoundaryViolation, sha256_hex
from agent_sleep_lab.reference_use import ReferenceUseJournal


class PipelineTests(StoreCase):
    open_adoption = fixtures.AdoptionTests.open_adoption
    setup_store = fixtures.AdoptionTests.setup_store

    def setUp(self):
        super().setUp()
        self.store = self.setup_store()
        self.bridge = CollectOnlyBridge(
            self.store, scope={"project": "p", "task_family": "t"},
            repository=worker.REPOSITORY, agent_commit=worker.AGENT_COMMIT)
        self.journal_path = str(Path(self.dir) / "uses.sqlite")
        self.journal = self.reopen()
        self.calls = 0

    def reopen(self):
        journal = ReferenceUseJournal(self.journal_path)
        self.addCleanup(journal.close)
        return journal

    def pipeline(self, journal=None, **overrides):
        options = dict(
            use_id="pipeline-1", repo=self.dir, query="duplicate checks", max_bytes=32768,
            session_id="synthetic-session", observed_at="2026-11-10T00:00:00Z",
            captured_at="2026-11-10T00:01:00Z",
            authorization=dict(ref="auth-1", revision=1, purpose="offline_consolidation",
                               retention="until_expiry", expires_at="2027-01-01T00:00:00Z"),
            worker_argv=["/synthetic/stand-in"])
        options.update(overrides)
        return OfflinePipeline(journal or self.journal, self.bridge, **options)

    def checker(self, repo, reference_bytes, **kwargs):
        self.calls += 1
        doc = dict(decisions=[
            dict(repo=worker.REPOSITORY, number=n, title="Synthetic issue", url="fixture://issue/"+str(n),
                 score=0.8, outcome="candidate", reasons=["synthetic observation"],
                 llm_rationale="", is_new=True) for n in (1, 2)])
        summary = dict(
            protocol=parent.CHECK_PROTOCOL, worker_launch=parent.STAND_IN_WORKER,
            task_sha256=sha256_hex(parent.builtin_task()), reference_sha256=sha256_hex(reference_bytes),
            decisions=2, delivery_and_use_verified=False,
            semantic_memory_use="not_evaluated", performance_improvement="not_evaluated")
        return summary, doc

    def test_dispatch_capture_and_reopen_replay_without_adoption(self):
        with mock.patch.object(parent, "check", side_effect=self.checker):
            result = self.pipeline().run()
            self.assertEqual(result["capture"], "captured_unverified_observations")
            self.assertEqual([e["status"] for e in result["events"]], ["created", "created"])
            replay = self.pipeline(self.reopen()).run()
        self.assertEqual(self.calls, 1)
        self.assertEqual([e["status"] for e in replay["events"]], ["replayed", "replayed"])
        self.assertEqual(self.count("evidence"), 3)
        self.assertEqual(self.count("adoption_journal"), 0)
        self.assertEqual(self.count("receipts"), 0)
        self.assertFalse(result["delivery_and_use_verified"])

    def test_partial_capture_recovery_uses_persisted_decisions(self):
        original = self.bridge.capture_decision
        seen = []
        def interrupted(decision, **kwargs):
            seen.append(decision["number"])
            if decision["number"] == 2:
                raise RuntimeError("capture interrupted")
            return original(decision, **kwargs)
        with mock.patch.object(parent, "check", side_effect=self.checker):
            with mock.patch.object(self.bridge, "capture_decision", side_effect=interrupted):
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    self.pipeline().run()
            self.assertEqual(self.journal.status("pipeline-1")["status"], "received_unreviewed")
            replay = self.pipeline(self.reopen()).run()
        self.assertEqual(self.calls, 1)
        self.assertEqual([e["status"] for e in replay["events"]], ["replayed", "created"])
        self.assertEqual(self.count("evidence"), 3)

    def test_changed_contract_fields_cannot_remap_saved_output(self):
        with mock.patch.object(parent, "check", side_effect=self.checker):
            self.pipeline().run()
            for change in (
                dict(captured_at="2026-11-10T00:02:00Z"), dict(session_id="other"),
                dict(repo=str(Path(self.dir) / "other")), dict(max_bytes=16000),
                dict(worker_argv=["/different/stand-in"]), dict(timeout=2),
                dict(authorization=dict(ref="auth-1", revision=2, purpose="offline_consolidation",
                                        retention="until_expiry", expires_at="2027-01-01T00:00:00Z"))):
                with self.subTest(change=change), self.assertRaisesRegex(ValueError, "conflict"):
                    self.pipeline(self.reopen(), **change).run()
        self.assertEqual(self.calls, 1)

    def test_unknown_result_is_never_redispatched(self):
        with mock.patch.object(parent, "check", side_effect=RuntimeError("lost output")) as check:
            result = self.pipeline().run()
            replay = self.pipeline(self.reopen()).run()
        self.assertEqual(check.call_count, 1)
        self.assertEqual(result["status"], "dispatch_outcome_unknown")
        self.assertEqual(replay["dispatches"], 1)
        self.assertEqual(self.count("evidence"), 1)

    def test_changed_context_during_dispatch_prevents_capture(self):
        def changed(*args, **kwargs):
            result = self.checker(*args, **kwargs)
            self.store.set_policy(make_control(), policy_body(event_ids=("e-1",)), expected_revision=1)
            return result
        with mock.patch.object(parent, "check", side_effect=changed):
            result = self.pipeline().run()
            replay = self.pipeline(self.reopen()).run()
        self.assertEqual(result["status"], "invalidated")
        self.assertEqual(replay["capture"], "not_captured")
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.count("evidence"), 1)

    def test_current_context_and_capture_authorization_rechecked_on_replay(self):
        with mock.patch.object(parent, "check", side_effect=self.checker):
            self.pipeline().run()
        self.store._boundary = make_boundary(revision=2)
        with self.assertRaises(BoundaryViolation):
            self.pipeline(self.reopen()).capture()
        self.store._boundary = make_boundary()
        self.store.set_policy(make_control(), policy_body(event_ids=("e-1",)), expected_revision=1)
        result = self.pipeline(self.reopen()).capture()
        self.assertEqual(result["capture"], "not_captured")
        self.assertEqual(self.calls, 1)

    def test_policy_change_mid_capture_stops_remaining_batch(self):
        original = self.bridge.capture_decision
        def changed(decision, **kwargs):
            result = original(decision, **kwargs)
            self.store.set_policy(make_control(), policy_body(event_ids=("e-1",)), expected_revision=1)
            return result
        with mock.patch.object(parent, "check", side_effect=self.checker):
            with mock.patch.object(self.bridge, "capture_decision", side_effect=changed):
                result = self.pipeline().run()
            replay = self.pipeline(self.reopen()).run()
        self.assertEqual(result["capture"], "partial_unverified_observations")
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(replay["capture"], "not_captured")
        self.assertEqual(self.count("evidence"), 2)
        self.assertEqual(self.calls, 1)

    def test_identity_and_worker_caps_rejected_before_dispatch(self):
        for options in (dict(max_bytes=32769), dict(max_records=257),
                        dict(timeout=float("inf")), dict(max_bytes=True)):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.pipeline(**options)
        original = self.bridge.agent_commit
        self.bridge.agent_commit = "0" * 40
        with self.assertRaisesRegex(ValueError, "pinned task"):
            self.pipeline()
        self.bridge.agent_commit = original
        self.assertEqual(self.journal.db.execute("SELECT COUNT(*) FROM reference_uses").fetchone()[0], 0)

    def test_oversized_consumer_output_stays_unknown_not_truncated(self):
        def oversized(*args, **kwargs):
            summary, doc = self.checker(*args, **kwargs)
            doc["decisions"][0]["title"] = "x" * 65536
            return summary, doc
        with mock.patch.object(parent, "check", side_effect=oversized):
            result = self.pipeline().run()
            self.pipeline(self.reopen()).run()
        self.assertEqual(result["status"], "dispatch_outcome_unknown")
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.count("evidence"), 1)
