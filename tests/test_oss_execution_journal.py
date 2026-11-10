"""Durable driver acceptance, temporary stores and injected process envelopes.

No target source/model/credential/network use. Capture/adoption/verifier data
are test-authored fixtures borrowed as helper methods, not collected aliases.
"""
import copy
import os
import sqlite3
from unittest import mock

import support  # noqa: F401
import test_oss_paired_outcome as fixtures
from evidence_support import StoreCase
from agent_sleep_lab import oss_execution_journal as execution
from agent_sleep_lab import oss_mimo_adapter as adapter_module
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_paired_outcome as paired
from agent_sleep_lab import oss_prompt_capture as capture
from test_oss_mimo_adapter import Transport, envelope


class ExecutionJournalTests(StoreCase):
    setup_store = fixtures.PairedOutcomeJournalTests.setup_store
    open_adoption = fixtures.PairedOutcomeJournalTests.open_adoption
    adopt = fixtures.PairedOutcomeJournalTests.adopt
    make_bridge = fixtures.PairedOutcomeJournalTests.make_bridge
    stand_in = fixtures.PairedOutcomeJournalTests.stand_in
    exclude_memory = fixtures.PairedOutcomeJournalTests.exclude_memory

    def setUp(self):
        super().setUp()
        self.store = self.setup_store()
        self.adopt(self.store, "m-1", "e-1", claim=fixtures.CLAIM)
        self.sources = {name: ("# stand-in: " + name).encode() for name in worker.SOURCE_HASHES}
        pins = {name: worker.digest(body) for name, body in self.sources.items()}
        self.delivered = []
        for patch in (
            mock.patch.object(worker, "SOURCE_HASHES", pins),
            mock.patch.object(fixtures.parent, "freeze_sources", return_value=self.sources),
            mock.patch.object(fixtures.parent, "launch", side_effect=self.stand_in),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        self.bridge = self.make_bridge()
        self.summary, self.doc = capture.prepare_from_bridge(
            self.bridge, self.dir, query=fixtures.QUERY, max_bytes=worker.MAX_REFERENCE_BYTES,
            worker_argv=["/synthetic/stand-in"])
        self.reference = self.delivered[-1]
        self.path = os.path.join(self.dir, "execution.sqlite")
        self.journal = self.open_journal(initialize=True)

    def open_journal(self, initialize=False):
        journal = execution.ExecutionJournal(self.path, initialize=initialize)
        self.addCleanup(journal.close)
        return journal

    def make_adapter(self, transport=None, **changes):
        options = dict(agent="synthetic-agent", max_calls=2,
                       acknowledge_paid_execution=True, acknowledge_uncapped_generation=True,
                       transport=Transport() if transport is None else transport)
        options.update(changes)
        return adapter_module.OSSMimoAdapter(**options)

    def register(self, instance, journal=None, plan_id="plan-1", **changes):
        options = dict(summary=self.summary, capture_doc=self.doc,
                       reference=self.reference, bridge=self.bridge, query=fixtures.QUERY,
                       max_bytes=worker.MAX_REFERENCE_BYTES, max_records=16,
                       max_request_bytes=adapter_module.MAX_REQUEST_BYTES, max_reply_bytes=4096)
        options.update(changes)
        return (journal or self.journal).register(plan_id, adapter=instance, **options)

    def test_durable_first_result_restart_second_only_and_replay_without_calls(self):
        transport = Transport()
        first = self.make_adapter(transport)
        self.register(first)
        report = self.journal.run("plan-1", self.bridge, first, limit=1)
        self.assertEqual(report["arms"]["baseline"]["status"], "completed")
        self.assertEqual(len(transport.calls), 1)
        self.journal.close()
        again = self.open_journal()
        second = self.make_adapter(transport)
        self.register(second, again)
        report = again.run("plan-1", self.bridge, second)
        self.assertEqual(report["plan_status"], "complete")
        self.assertEqual(len(transport.calls), 2)
        for index, arm in enumerate(paired.ARMS):
            argv = transport.calls[index][0]
            self.assertEqual(argv[-1], self.doc["arms"][arm]["payload"]["messages"][0]["content"])
            receipt = report["arms"][arm]["receipt"]
            self.assertEqual(receipt["transport"], adapter_module.TRANSPORT_TEST)
            self.assertEqual(receipt["request_sha256"], self.doc["arms"][arm]["request_sha256"])
            self.assertEqual((receipt["usage"], receipt["cost"]), ("unavailable", "unavailable"))
        self.assertEqual((report["usage"], report["cost"], report["verdict"]),
                         ("unavailable", "unavailable", None))
        again.close()
        last = self.open_journal()
        healthy = Transport()
        replay = last.run("plan-1", self.bridge, self.make_adapter(healthy))
        self.assertEqual(replay["arms"], report["arms"])
        self.assertEqual(healthy.calls, [])

    def test_timeout_interrupt_and_process_loss_intents_are_never_redispatched(self):
        for index, error in enumerate((TimeoutError("private"), KeyboardInterrupt())):
            plan_id = "failure-" + str(index)
            transport = Transport(error=error)
            instance = self.make_adapter(transport)
            self.register(instance, plan_id=plan_id)
            if isinstance(error, Exception):
                report = self.journal.run(plan_id, self.bridge, instance)
            else:
                with self.assertRaises(KeyboardInterrupt):
                    self.journal.run(plan_id, self.bridge, instance)
                report = self.journal.report(plan_id, self.bridge)
            self.assertEqual(report["plan_status"], "stopped")
            self.assertEqual(report["arms"]["baseline"]["status"], "unknown")
            self.assertNotIn("private", repr(report))
            healthy = Transport()
            self.journal.run(plan_id, self.bridge, self.make_adapter(healthy))
            self.assertEqual((len(transport.calls), healthy.calls), (1, []))
        self.register(self.make_adapter(), plan_id="lost")
        self.journal._db.execute(
            "INSERT INTO arms (plan_id,arm,state) VALUES ('lost','baseline','intent')")
        self.assertEqual(self.journal.report("lost", self.bridge)["plan_status"], "stopped")
        self.journal.close()
        again = self.open_journal()
        healthy = Transport()
        report = again.run("lost", self.bridge, self.make_adapter(healthy))
        self.assertEqual(report["stop_reason"], "interrupted_baseline")
        self.assertEqual(healthy.calls, [])

    def test_revocation_before_second_arm_withholds_saved_body_and_receipt(self):
        transport = Transport()
        instance = self.make_adapter(transport)
        self.register(instance)
        self.journal.run("plan-1", self.bridge, instance, limit=1)
        self.exclude_memory()
        report = self.journal.report("plan-1", self.bridge)
        self.assertFalse(report["context_current"])
        self.assertIsNone(report["arms"]["baseline"]["reply_body"])
        self.assertIsNone(report["arms"]["baseline"]["receipt"])
        report = self.journal.run("plan-1", self.bridge, instance)
        self.assertEqual(report["stop_reason"], "context_changed_before_reference")
        self.assertEqual(len(transport.calls), 1)
        with self.assertRaises(execution.JournalError):
            self.register(instance, plan_id="stale")
        with mock.patch.object(self.bridge, "reference_context", side_effect=ValueError("unavailable")):
            self.assertIsNone(self.journal.report("plan-1", self.bridge)["arms"]["baseline"]["receipt"])

    def test_revocation_during_transport_stores_hash_status_only(self):
        transport = Transport()
        def revoke(argv, **kwargs):
            self.exclude_memory()
            return transport(argv, **kwargs)
        instance = self.make_adapter(revoke)
        self.register(instance)
        report = self.journal.run("plan-1", self.bridge, instance)
        self.assertEqual(report["stop_reason"], "context_changed_after_baseline")
        self.assertEqual(report["arms"]["baseline"]["status"], "invalidated")
        self.assertTrue(report["arms"]["baseline"]["reply_sha256"])
        saved = self.journal._db.execute("SELECT reply,receipt FROM arms").fetchall()
        self.assertEqual([tuple(r) for r in saved], [(None, None)])
        self.assertEqual(len(transport.calls), 1)

    def test_foreign_database_is_unchanged_and_schema_identity_is_checked(self):
        foreign = os.path.join(self.dir, "foreign.sqlite")
        with sqlite3.connect(foreign) as db:
            db.execute("CREATE TABLE unrelated (value TEXT)")
        from pathlib import Path
        before = Path(foreign).read_bytes()
        with self.assertRaises(execution.JournalError):
            execution.ExecutionJournal(foreign, initialize=True)
        self.assertEqual(Path(foreign).read_bytes(), before)
        with self.assertRaises(execution.JournalError):
            execution.ExecutionJournal(os.path.join(self.dir, "missing.sqlite"))
        self.assertEqual(self.journal._db.execute("PRAGMA synchronous").fetchone()[0], 2)
        self.assertEqual(self.journal._db.execute("PRAGMA fullfsync").fetchone()[0], 1)
        self.journal._db.execute("CREATE TABLE unexpected (value TEXT)")
        with self.assertRaises(execution.JournalError):
            self.open_journal()

    def test_frozen_bindings_and_saved_receipt_corruption_prevent_second_dispatch(self):
        transport = Transport()
        instance = self.make_adapter(transport)
        self.register(instance)
        with self.assertRaises(execution.PlanConflict):
            self.register(instance, max_reply_bytes=4095)
        with self.assertRaises(execution.PlanConflict):
            self.journal.run("plan-1", self.bridge,
                             self.make_adapter(transport, agent="different-agent"))
        self.assertEqual(transport.calls, [])
        self.journal.run("plan-1", self.bridge, instance, limit=1)
        self.journal._db.execute("UPDATE arms SET receipt=? WHERE plan_id=?",
                                 (b'{"tampered":true}', "plan-1"))
        with self.assertRaisesRegex(execution.JournalError, "integrity"):
            self.journal.run("plan-1", self.bridge, self.make_adapter(transport))
        self.assertEqual(len(transport.calls), 1)

    def test_invalid_output_and_duplicate_driver_do_not_redispatch_or_store_body(self):
        transport = Transport(envelope(text="x" * 4097))
        instance = self.make_adapter(transport)
        self.register(instance)
        report = self.journal.run("plan-1", self.bridge, instance)
        self.assertEqual(report["plan_status"], "stopped")
        self.assertIsNone(report["arms"]["baseline"]["reply_body"])
        self.assertIsNone(report["arms"]["baseline"]["receipt"])
        self.assertEqual(len(transport.calls), 1)

        other = self.open_journal()
        secondary = Transport()
        def compete(argv, **kwargs):
            # The first driver already committed intent; no lock spans transport.
            seen = other.run("race", self.bridge, self.make_adapter(secondary))
            self.assertEqual(seen["plan_status"], "stopped")
            return Transport()(argv, **kwargs)
        racing = self.make_adapter(compete)
        self.register(racing, plan_id="race")
        with self.assertRaises(execution.JournalError):
            self.journal.run("race", self.bridge, racing)
        self.assertEqual(secondary.calls, [])
        self.assertEqual(self.journal.report("race", self.bridge)["plan_status"], "stopped")

    def test_live_choice_and_adapter_budget_are_distinct_from_durable_authority(self):
        # Construct only; registered CLI is NEVER called.
        live = self.make_adapter()
        live.transport_kind = adapter_module.TRANSPORT_CLI
        with self.assertRaises(execution.JournalError):
            self.register(live)
        transport = Transport()
        used = self.make_adapter(transport, max_calls=1)
        self.register(used)
        with self.assertRaisesRegex(execution.JournalError, "budget"):
            self.journal.run("plan-1", self.bridge, used)
        self.assertEqual(transport.calls, [])
        report = self.journal.run("plan-1", self.bridge, used, limit=1)
        self.assertEqual(report["plan_status"], "open")
        self.assertEqual(len(transport.calls), 1)
