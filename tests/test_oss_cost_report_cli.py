"""Read-only CLI contracts; synthetic stores and injected fixture replies only.

Fixture helpers are composed, never inherited/imported as collected case aliases.
No worker, live provider, external service or paid measurement runs in these cases.
"""
import copy
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import sqlite3
from unittest import TestCase, mock

import test_oss_fixture_cohort as fixtures
from evidence_support import make_boundary
from runtime_support import make_control, make_evaluator, make_verifier, policy_body
from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.cli import main
from agent_sleep_lab import oss_cost_accounting as accounting
from agent_sleep_lab import oss_cost_report_cli as reader
from agent_sleep_lab import oss_execution_journal as execution
from agent_sleep_lab import oss_fixture_cohort as cohort
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab.provenance import StorageError
from agent_sleep_lab.runtime_store import RuntimeStore
from test_oss_cost_accounting import observation
from test_oss_mimo_adapter import envelope

ROOT = Path(__file__).resolve().parent.parent


class ReadOnlyCostReportTests(TestCase):
    def setUp(self):
        self.fixture = fixtures.FixtureCohortTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.directory = Path(self.fixture.dir)
        config = json.loads((ROOT / "configs/runtime-store.example.json").read_text())
        config["path"] = str(self.fixture.store._db().execute("PRAGMA database_list").fetchone()[2])
        self.store_path = Path(config["path"])
        self.config = config
        self.config_path = self.write("store.json", config)
        self.manifest_path = self.directory / "report.json"

    def write(self, name, doc):
        path = self.directory / name
        path.write_text(json.dumps(doc), encoding="utf-8")
        return str(path)

    def manifest(self, kind="pair", bridges=None):
        f = self.fixture
        ids = [m["plan_id"] for m in f.members] if bridges is None else bridges
        identity = dict(scope=dict(f.bridge.scope), repository=f.bridge.repository,
                        agent_commit=f.bridge.agent_commit)
        doc = dict(protocol=reader.PROTOCOL, target=dict(kind=kind, id="plan-1" if kind == "pair" else "cohort-1"),
                   store_config=self.config_path, journal=str(f.path),
                   bridges={plan: copy.deepcopy(identity) for plan in ids})
        if kind == "pair":
            doc["bridges"] = {"plan-1": copy.deepcopy(identity)}
        else:
            doc["cohort_registry"] = str(f.registry_path)
        return doc

    def invoke(self, doc, *, artifact=None, success=True):
        self.manifest_path.write_text(json.dumps(doc), encoding="utf-8")
        args = ["oss-cost-report", "--manifest", str(self.manifest_path)]
        if artifact is not None:
            path = self.directory / "observations.json"
            path.write_bytes(artifact)
            args += ["--observations", str(path)]
        out, err = io.StringIO(), io.StringIO()
        # Keep synthetic expiry checks independent of the date of a later run.
        with mock.patch("agent_sleep_lab.evidence_store._utc_now", self.fixture.clock):
            code = main(args, out, err)
        self.assertEqual(code, 0 if success else 2, err.getvalue())
        if success:
            self.assertEqual(err.getvalue(), "")
            return json.loads(out.getvalue())
        self.assertEqual(out.getvalue(), "")
        self.assertIn("error[oss-cost-report]: report refused", err.getvalue())
        return err.getvalue()

    def dump(self):
        f = self.fixture
        return tuple(tuple(db.iterdump()) for db in (f.store._db(), f.journal._db, f.registry._db))

    def open_store(self, path=None, **changes):
        options = dict(verifier=make_verifier(), evaluator=make_evaluator(),
                       evaluation_protocol=("fixture-protocol", "1", "d" * 64),
                       clock=self.fixture.clock, read_only=True)
        return AdoptionStore(path or self.store_path, make_boundary(), **(options | changes))

    def test_pair_cli_is_exact_allowlisted_report_with_zero_execution_or_adoption_effects(self):
        f = self.fixture
        f.add_plan(1)
        f.transports["plan-1"].result = envelope(text="private synthetic invalid rationale")
        f.journal.run("plan-1", f.bridge, f.instances["plan-1"], limit=1)
        f.transports["plan-1"].result = envelope(text=fixtures.verdict_fixtures.reply(True))
        f.journal.run("plan-1", f.bridge, f.instances["plan-1"])
        expected = accounting.pair_report(f.journal, "plan-1", f.bridge)
        before, calls = self.dump(), len(f.transports["plan-1"].calls)
        with mock.patch.object(execution.ExecutionJournal, "run", side_effect=AssertionError("dispatch")), \
             mock.patch.object(execution.ExecutionJournal, "register", side_effect=AssertionError("intent")), \
             mock.patch.object(cohort.CohortRegistry, "register", side_effect=AssertionError("registration")), \
             mock.patch.object(AdoptionStore, "commit_adoption", side_effect=AssertionError("adoption")), \
             mock.patch("agent_sleep_lab.oss_mimo_adapter.OSSMimoAdapter.__init__", side_effect=AssertionError("adapter")):
            report = self.invoke(self.manifest())
            self.assertEqual(report, expected)
            self.assertEqual(self.invoke(self.manifest()), report)
        self.assertEqual(report["tasks"][0]["arms"]["baseline"]["verdict_status"], "invalid_verdict")
        for forbidden in ("private synthetic", "rationale", "expected_accept", "reply_body", "capture_doc",
                          "request_hex", "reference_hex", "prompt", "合成の理由"):
            self.assertNotIn(forbidden, json.dumps(report, ensure_ascii=False))
        self.assertIsNone(report["totals"]["cost"])
        self.assertEqual((self.dump(), len(f.transports["plan-1"].calls)), (before, calls))

    def test_cohort_reopening_keeps_every_registered_invalid_unknown_missing_and_corrupt_task(self):
        f = self.fixture
        for number in range(1, 6):
            f.add_plan(number)
        f.freeze()
        f.transports["plan-1"].result = envelope(text="invalid synthetic verdict")
        f.journal.run("plan-1", f.bridge, f.instances["plan-1"])
        f.journal._db.execute("INSERT INTO arms (plan_id,arm,state) VALUES ('plan-2','baseline','intent')")
        f.journal._db.execute("DELETE FROM plans WHERE plan_id='plan-3'")
        f.finish(4)
        f.journal._db.execute("UPDATE arms SET receipt=? WHERE plan_id='plan-4'", (b"bad",))
        doc = self.manifest("cohort", bridges=["plan-1", "plan-2", "plan-3", "plan-4"])
        expected = accounting.cohort_report(f.registry, "cohort-1", journal=f.journal,
                                            bridges={plan: f.bridge for plan in doc["bridges"]})
        before = self.dump()
        report = self.invoke(doc)
        self.assertEqual(report, expected)
        self.assertEqual([task["status"] for task in report["tasks"]], ["complete_with_invalid_verdict",
                         "incomplete", "missing_plan", "unavailable_journal_integrity", "unavailable_context"])
        self.assertEqual((report["registered_tasks"], report["totals"]["stage_slots"]), (5, 70))
        self.assertEqual(report["tasks"][1]["plan_status"], "stopped")
        self.assertEqual(report["tasks"][1]["arms"]["baseline"]["execution_status"], "unknown")
        self.assertIsNone(report["reference_minus_baseline_cost"])
        self.assertEqual(self.invoke(doc), report)
        self.assertEqual(self.dump(), before)  # No persisted intent recovery or denominator repair.
        missing_bridges = self.invoke(doc | {"bridges": {}})
        self.assertEqual(missing_bridges["registered_tasks"], 5)
        self.assertEqual([task["status"] for task in missing_bridges["tasks"]], ["unavailable_context"] * 5)
        self.assertEqual(f.journal._db.execute("SELECT state FROM arms WHERE plan_id='plan-2'").fetchone()[0], "intent")
        self.assertEqual(f.instances["plan-2"].calls, 0)

    def test_pair_exact_canonical_observation_bytes_and_stale_outcomes(self):
        f = self.fixture
        f.add_plan(1)
        doc = self.manifest()
        target = self.invoke(doc)
        raw = accounting.freeze_observations(target["target"], currency="USD", observations=[observation()])
        report = self.invoke(doc, artifact=raw)
        self.assertEqual(report["artifact_sha256"], worker.digest(raw))
        self.assertEqual(report, accounting.pair_report(f.journal, "plan-1", f.bridge, artifact=raw))
        self.assertEqual(report["totals"]["observed_cost_slots"], 1)
        self.assertIsNone(report["totals"]["cost"])
        before = self.dump()
        for bad in (raw + b"\n", raw.replace(b'"currency":"USD"', b'"currency":"USD","currency":"USD"'),
                    b"x" * (accounting.MAX_ARTIFACT_BYTES + 1)):
            self.invoke(doc, artifact=bad, success=False)
        self.assertEqual(self.dump(), before)
        f.journal.run("plan-1", f.bridge, f.instances["plan-1"], limit=1)
        before = self.dump()
        self.invoke(doc, artifact=raw, success=False)
        self.assertEqual(self.dump(), before)
        self.assertNotEqual(self.invoke(doc)["target"]["report_sha256"], target["target"]["report_sha256"])
        self.assertEqual(len(f.transports["plan-1"].calls), 1)
        # Same plan ID in another existing journal cannot reuse observations
        # against a different frozen binding, even before either arm runs.
        other_path = self.directory / "alternate-execution.sqlite"
        other = execution.ExecutionJournal(other_path, initialize=True)
        self.addCleanup(other.close)
        binding = worker.strict_json(f.journal._db.execute("SELECT binding FROM plans WHERE plan_id='plan-1'").fetchone()[0])
        f.register(f.make_adapter(), journal=other, max_reply_bytes=4095,
                   evaluation_manifest=binding["evaluation_manifest"])
        alternate = doc | {"journal": str(other_path)}
        self.invoke(alternate, artifact=raw, success=False)
        self.assertNotEqual(self.invoke(alternate)["target"]["frozen_sha256"], target["target"]["frozen_sha256"])

    def test_complete_cohort_exact_costs_and_changed_member_artifact_refusal(self):
        f = self.fixture
        for number in (1, 2):
            f.add_plan(number)
        f.freeze()
        doc = self.manifest("cohort")
        target = self.invoke(doc)
        rows = [observation(plan, arm, stage, cost="0.1" if arm == "baseline" else "0.2")
                for plan in doc["bridges"] for arm in accounting.ARMS for stage in accounting.STAGES]
        stale = accounting.freeze_observations(target["target"], currency="USD", observations=rows)
        for number in (1, 2):
            f.finish(number)
        self.invoke(doc, artifact=stale, success=False)
        raw = accounting.freeze_observations(self.invoke(doc)["target"], currency="USD", observations=rows)
        before = self.dump()
        result = self.invoke(doc, artifact=raw)
        self.assertEqual((result["registered_tasks"], result["totals"]["cost"],
                          result["reference_minus_baseline_cost"]), (2, "4.2", "1.4"))
        self.assertEqual(result["artifact_sha256"], worker.digest(raw))
        self.assertEqual(self.invoke(doc, artifact=raw), result)
        self.assertEqual(self.dump(), before)
        self.assertEqual(sum(len(t.calls) for t in f.transports.values()), 4)

    def test_read_only_connections_are_query_only_and_sqlite_mode_ro(self):
        f = self.fixture
        store = self.open_store()
        journal = execution.ExecutionJournal(f.path, read_only=True)
        registry = cohort.CohortRegistry(f.registry_path, read_only=True)
        for instance in (store, journal, registry):
            self.addCleanup(instance.close)
        before = self.dump()
        for db, table in ((store._db(), "policy_revisions"), (journal._db, "plans"), (registry._db, "cohorts")):
            self.assertEqual(db.execute("PRAGMA query_only").fetchone()[0], 1)
            for query_only in (True, False):
                if not query_only:
                    db.execute("PRAGMA query_only=OFF")
                with self.assertRaises(sqlite3.OperationalError):
                    db.execute("DELETE FROM " + table)
            self.assertEqual(db.total_changes, 0)
        self.assertEqual(self.dump(), before)

    def test_read_only_mutators_refuse_before_validation_intents_budget_or_transport(self):
        f = self.fixture
        f.add_plan(1)
        f.add_plan(2)
        f.freeze()
        journal = execution.ExecutionJournal(f.path, read_only=True)
        registry = cohort.CohortRegistry(f.registry_path, read_only=True)
        store = self.open_store()
        for instance in (store, journal, registry):
            self.addCleanup(instance.close)
        trace = []
        journal._db.set_trace_callback(trace.append)
        before = self.dump()
        adapter = f.instances["plan-1"]
        with mock.patch.object(adapter, "complete", side_effect=AssertionError("transport")), \
             mock.patch.object(execution, "adapter_spec", side_effect=AssertionError("adapter validation")):
            for action in (lambda: journal.run("plan-1", f.bridge, adapter),
                           lambda: journal.register("new", adapter=adapter),
                           lambda: registry.register("new", journal=f.journal, members=[], bridges={}),
                           lambda: f.registry.register("new", journal=journal, members=f.members,
                                                        bridges={m["plan_id"]: f.bridge for m in f.members})):
                with self.assertRaisesRegex((execution.JournalError, cohort.CohortError), "read-only"):
                    action()
        class ForeignJournal:
            def _require_writable(self):
                raise AssertionError("foreign journal method must not execute")

        for foreign in (None, object(), ForeignJournal()):
            with self.assertRaises(cohort.CohortError):
                f.registry.register("foreign", journal=foreign, members=f.members,
                                    bridges={m["plan_id"]: f.bridge for m in f.members})
        for action in (lambda: store.capture(event_bytes=b"", source_bytes=b"", claim={}),
                       lambda: store.register_verification(None, {}),
                       lambda: store.register_evaluation(None, {}),
                       lambda: store.set_policy(None, {}, expected_revision=0),
                       lambda: store.commit_adoption(request_bytes=b"", manifest_bytes=b"",
                                                      source_manifest_bytes=b"", memory_bytes={}),
                       lambda: store.commit_rollback(request_bytes=b""),
                       lambda: store.commit_forget(request_bytes=b"", control=None)):
            with self.assertRaises(StorageError) as caught:
                action()
            self.assertEqual(caught.exception.code, "storage.read_only")
        self.assertEqual(trace, [])  # No BEGIN IMMEDIATE, reads or reservations.
        self.assertEqual((adapter.calls, f.transports["plan-1"].calls), (0, []))
        self.assertEqual(self.dump(), before)

    def test_read_only_initialization_missing_empty_foreign_and_old_schema_refuse_without_mutation(self):
        empty, foreign, missing = [self.directory / (name + ".sqlite") for name in ("empty", "foreign", "missing")]
        empty.touch()
        with sqlite3.connect(foreign) as db:
            db.execute("CREATE TABLE unrelated (private_body TEXT)")
        constructors = (self.open_store,
                        lambda p, **kw: execution.ExecutionJournal(p, read_only=True, **kw),
                        lambda p, **kw: cohort.CohortRegistry(p, read_only=True, **kw))
        for constructor in constructors:
            for path in (empty, foreign, missing):
                before = path.read_bytes() if path.exists() else None
                with self.subTest(constructor=constructor, path=path), self.assertRaises(
                        (StorageError, execution.JournalError, cohort.CohortError, sqlite3.DatabaseError)):
                    constructor(path)
                self.assertEqual(path.read_bytes() if path.exists() else None, before)
            with self.assertRaises((execution.JournalError, cohort.CohortError, TypeError)):
                constructor(missing, initialize=True)
            self.assertFalse(missing.exists())
        # Exact saved schemas are still required; no upgrade from evidence/runtime v1/v2.
        old = self.directory / "old.sqlite"
        RuntimeStore(old, make_boundary(), clock=self.fixture.clock).close()
        before = old.read_bytes()
        with self.assertRaises(StorageError):
            self.open_store(old)
        self.assertEqual(old.read_bytes(), before)

    def test_cli_bad_database_roles_never_create_initialize_or_modify_files(self):
        f = self.fixture
        f.add_plan(1)
        f.add_plan(2)
        f.freeze()
        empty, foreign, missing = [self.directory / (name + ".sqlite") for name in ("empty", "foreign", "missing")]
        empty.touch()
        foreign.write_bytes(b"synthetic foreign non-database")
        saved = self.dump()
        for role in ("store", "journal", "cohort_registry"):
            for path in (empty, foreign, missing):
                doc, config = self.manifest("cohort"), copy.deepcopy(self.config)
                if role == "store":
                    config["path"] = str(path)
                else:
                    doc[role] = str(path)
                self.write("store.json", config)
                before = {p: p.read_bytes() for p in (empty, foreign)}
                with self.subTest(role=role, path=path):
                    self.invoke(doc, success=False)
                self.assertFalse(missing.exists())
                self.assertEqual({p: p.read_bytes() for p in before}, before)
        self.assertEqual(self.dump(), saved)

    def test_all_database_alias_pairs_and_same_file_links_refuse_before_store_construction(self):
        f = self.fixture
        f.add_plan(1)
        doc = self.manifest("cohort")
        paths = dict(store=self.store_path, journal=Path(f.path), cohort_registry=f.registry_path)
        before = self.dump()
        for first, second in (("store", "journal"), ("store", "cohort_registry"), ("journal", "cohort_registry")):
            for kind in ("same", "symlink", "hardlink"):
                alias = paths[first]
                if kind != "same":
                    alias = self.directory / (first + second + kind)
                    if kind == "symlink":
                        alias.symlink_to(paths[first])
                    else:
                        os.link(paths[first], alias)
                changed, config = copy.deepcopy(doc), copy.deepcopy(self.config)
                if second == "store":
                    config["path"] = str(alias)
                else:
                    changed[second] = str(alias)
                self.write("store.json", config)
                with mock.patch.object(reader, "AdoptionStore") as adoption, \
                     mock.patch.object(reader, "ExecutionJournal") as journal, \
                     mock.patch.object(reader, "CohortRegistry") as registry:
                    self.invoke(changed, success=False)
                    for constructor in (adoption, journal, registry):
                        constructor.assert_not_called()
        self.assertEqual(self.dump(), before)

    def test_strict_bounded_manifest_config_and_incompatible_cli_options(self):
        self.fixture.add_plan(1)
        good = self.manifest()
        bad_docs = [dict(good, unexpected="private synthetic body"),
                    {k: v for k, v in good.items() if k != "journal"},
                    dict(good, cohort_registry=str(self.fixture.registry_path)),
                    dict(good, target=dict(kind="pair", id="plan-1", cohort_id="cohort-1")),
                    dict(good, target=dict(kind="cohort", id="cohort-1")),
                    dict(good, bridges={}), dict(good, bridges=[])]
        for field in ("scope", "repository", "agent_commit"):
            doc = copy.deepcopy(good)
            del doc["bridges"]["plan-1"][field]
            bad_docs.append(doc)
        doc = copy.deepcopy(good)
        doc["bridges"]["plan-1"]["plugin"] = "private.synthetic:execute"
        bad_docs.append(doc)
        before = self.dump()
        with mock.patch.object(reader, "AdoptionStore") as constructor:
            for doc in bad_docs:
                error = self.invoke(doc, success=False)
                self.assertNotIn("private synthetic body", error)
            for config in (dict(self.config, write=True),
                           self.config | {"capture": self.config["capture"] | {"initialize": True}},
                           self.config | {"evaluation_protocol": "implicit"}):
                self.write("store.json", config)
                self.invoke(good, success=False)
            self.write("store.json", self.config)
            for raw in (b"x" * (reader.MAX_INPUT_BYTES + 1),
                        b'{"protocol":"private synthetic body","protocol":"duplicate"}'):
                self.manifest_path.write_bytes(raw)
                out, err = io.StringIO(), io.StringIO()
                self.assertEqual(main(["oss-cost-report", "--manifest", str(self.manifest_path)], out, err), 2)
                self.assertEqual(out.getvalue(), "")
                self.assertNotIn("private synthetic body", err.getvalue())
            constructor.assert_not_called()
        for option in ("--provider", "--agent", "--initialize", "--run", "--adopt", "--write", "--journal"):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["oss-cost-report", "--manifest", str(self.manifest_path), option, "x"],
                                      io.StringIO(), io.StringIO()), 2)
        self.assertEqual(self.dump(), before)

    def test_wal_current_policy_visible_on_open_connection_and_cli_restart_withholding(self):
        f = self.fixture
        for number in (1, 2):
            f.add_plan(number)
        f.freeze()
        f.finish(1)
        f.finish(2)
        self.assertEqual(f.store._db().execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
        store = self.open_store()
        self.addCleanup(store.close)
        self.assertEqual(store.current_policy().revision, 1)
        pair_doc, cohort_doc = self.manifest(), self.manifest("cohort")
        old_pair, old_cohort = self.invoke(pair_doc), self.invoke(cohort_doc)
        pair_artifact = accounting.freeze_observations(old_pair["target"], currency="USD", observations=[observation()])
        cohort_artifact = accounting.freeze_observations(old_cohort["target"], currency="USD", observations=[observation()])
        f.exclude_memory()  # Explicit synthetic fixture mutation, outside the report command.
        self.assertEqual(store.current_policy().revision, 2)  # Reads WAL; no immutable snapshot.
        before = self.dump()
        for doc, artifact in ((pair_doc, pair_artifact), (cohort_doc, cohort_artifact)):
            self.invoke(doc, artifact=artifact, success=False)
            result = self.invoke(doc)
            self.assertTrue(all(task["context_current"] is False for task in result["tasks"]))
            self.assertTrue(all(task["status"] == "withheld_context" for task in result["tasks"]))
            self.assertIsNone(result["totals"]["cost"])
            self.assertEqual(self.invoke(doc), result)
        self.assertEqual(self.dump(), before)
        self.assertEqual(sum(len(t.calls) for t in f.transports.values()), 4)

    def test_default_writer_initialization_and_saved_contract_replay_remain_compatible(self):
        f = self.fixture
        for number in (1, 2):
            f.add_plan(number)
        frozen = f.freeze()
        binding = bytes(f.journal._db.execute("SELECT binding FROM plans WHERE plan_id='plan-2'").fetchone()[0])
        self.invoke(self.manifest("cohort"))
        journal = execution.ExecutionJournal(f.path)
        registry = cohort.CohortRegistry(f.registry_path)
        self.addCleanup(journal.close)
        self.addCleanup(registry.close)
        f.register(f.instances["plan-2"], journal=journal, plan_id="plan-2",
                   evaluation_manifest=worker.strict_json(binding)["evaluation_manifest"])
        self.assertEqual(registry.register("cohort-1", journal=journal, members=f.members,
                         bridges={m["plan_id"]: f.bridge for m in f.members}), frozen)
        self.assertEqual(bytes(journal._db.execute("SELECT binding FROM plans WHERE plan_id='plan-2'").fetchone()[0]), binding)
        self.assertEqual(journal.run("plan-2", f.bridge, f.instances["plan-2"])["plan_status"], "complete")
        fresh_path = self.directory / "fresh-default-writer.sqlite"
        store = self.open_store(fresh_path, read_only=False)
        self.addCleanup(store.close)
        self.assertFalse(store.read_only)
        self.assertEqual(store._db().execute("PRAGMA user_version").fetchone()[0], 3)
        store.set_policy(make_control(), policy_body(), expected_revision=0)
        reopened = self.open_store(fresh_path, read_only=False)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.current_policy().revision, 1)
