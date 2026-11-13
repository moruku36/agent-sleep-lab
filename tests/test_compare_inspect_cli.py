"""Saved-comparison reader contracts; fixtures and scores are synthetic."""
from contextlib import closing
import io
import json
from pathlib import Path
import sqlite3
from unittest import TestCase, mock

import test_compare_prepare_cli as fixtures
from agent_sleep_lab import comparison_inspect as inspect
from agent_sleep_lab import runtime_cli
from agent_sleep_lab.ab_comparison import ComparisonStore, FakeTaskProvider
from agent_sleep_lab.cli import main
from evidence_support import make_item
from runtime_support import make_control, policy_body


class CompareInspectionTests(TestCase):
    def setUp(self):
        self.f = fixtures.ComparePreparationTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    def call(self, *, journal=None, plan_id=None, extra=()):
        out, err = io.StringIO(), io.StringIO()
        code = main(["compare-inspect", "--store-config", self.f.config_path,
                     "--journal", str(journal or self.f.journal),
                     "--plan-id", plan_id or self.f.manifest["plan_id"], *extra], out, err)
        return code, out.getvalue(), err.getvalue()

    def success(self, **kwargs):
        code, output, error = self.call(**kwargs)
        self.assertEqual((code, error), (0, ""))
        return json.loads(output)

    def refused(self, **kwargs):
        code, output, error = self.call(**kwargs)
        self.assertEqual((code, output), (2, ""))
        self.assertEqual(error, "error[compare-inspect]: inspection refused; check strict inputs, "
                         "existing distinct databases and saved comparison integrity\n")

    def assert_private(self, result):
        text = json.dumps(result)
        for private in ("PRIVATE-SYNTHETIC-RAW", "PRIVATE-SYNTHETIC-MEMORY", "PRIVATE-TASK",
                        "PRIVATE-REPLY", "PRIVATE-REASON", "PRIVATE-RECEIPT",
                        "EVALUATOR-ONLY-ANSWER", "duplicate"):
            self.assertNotIn(private, text)

    def test_planned_inspection_is_readonly_no_provider_evaluator_recovery_or_new_contacts(self):
        prepared = self.f.success()
        before = self.f.journal_dump()
        source_bytes = Path(self.f.f.path).read_bytes()
        journal_bytes = self.f.journal.read_bytes()
        actual_open = inspect.open_store
        actual_comparisons = inspect.ComparisonStore
        opened = []

        def readonly_store(*args, **kwargs):
            self.assertIs(kwargs.get("read_only"), True)
            store = actual_open(*args, **kwargs)
            self.assertEqual(store._db().execute("PRAGMA query_only").fetchone()[0], 1)
            opened.append("store")
            return store

        def readonly_journal(*args, **kwargs):
            self.assertIs(kwargs.get("read_only"), True)
            journal = actual_comparisons(*args, **kwargs)
            self.assertEqual(journal.db.execute("PRAGMA query_only").fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError):
                journal.db.execute("DELETE FROM evaluation_contacts")
            opened.append("journal")
            return journal

        with mock.patch.object(inspect, "open_store", side_effect=readonly_store), \
             mock.patch.object(inspect, "ComparisonStore", side_effect=readonly_journal), \
             mock.patch.object(runtime_cli, "OpenClawMimoProvider", side_effect=AssertionError("provider")), \
             mock.patch.object(runtime_cli, "FakeTaskProvider", side_effect=AssertionError("provider")), \
             mock.patch.object(runtime_cli, "SyntheticEvaluator", side_effect=AssertionError("evaluator")), \
             mock.patch.object(runtime_cli, "read_json", side_effect=AssertionError("rubric")), \
             mock.patch.object(ComparisonStore, "plan", side_effect=AssertionError("plan")), \
             mock.patch.object(ComparisonStore, "run", side_effect=AssertionError("run")), \
             mock.patch.object(ComparisonStore, "report", side_effect=AssertionError("report")):
            result = self.success()
        self.assertEqual(opened, ["store", "journal"])
        self.assertEqual(result["input_volume"], prepared["input_volume"])
        self.assertEqual(result["planned_denominator"], prepared["planned_denominator"])
        self.assertEqual(result["status"], "planned")
        self.assertEqual(len(result["arms"]), 10)
        self.assertTrue(result["read_only"])
        self.assertFalse(result["dispatch_authorization"])
        self.assertFalse(result["all_outcomes_scored"])
        self.assertTrue(result["current_validity"]["valid"])
        self.assertEqual(result["cost"], {"label": "unavailable", "value": None})
        self.assertIsNone(result["usage"])
        for arm in "AB":
            self.assertEqual(result["outcomes"][arm]["planned_not_dispatched"], 5)
        self.assert_private(result)
        self.assertEqual(self.f.journal_dump(), before)
        self.assertEqual(self.f.journal.read_bytes(), journal_bytes)
        self.assertEqual(Path(self.f.f.path).read_bytes(), source_bytes)
        self.assertEqual(result, self.success())

    def test_mixed_unknown_replied_and_missing_slots_keep_fixed_denominators_and_saved_status(self):
        prepared = self.f.success()
        states = ("intent", "completed", "replied", "timeout", "missing", "invalid")
        with sqlite3.connect(self.f.journal) as db:
            for entry, state in zip(prepared["arms"], states):
                db.execute("INSERT INTO comparison_arms VALUES (?,?,?,?,?,?,?,?)",
                           (self.f.manifest["plan_id"], entry["task_index"], entry["arm"],
                            entry["position"], state, entry["request_sha256"],
                            b"PRIVATE-REPLY", 1 if state == "completed" else None))
            db.execute("INSERT INTO comparison_provider_receipts VALUES (?,?,?,?)",
                       (self.f.manifest["plan_id"], 0, "A", b"PRIVATE-RECEIPT not parsed"))
        for status in ("running", "incomplete", "complete", "invalidated"):
            with sqlite3.connect(self.f.journal) as db:
                db.execute("UPDATE comparison_plans SET status=?, reason=?", (status, "PRIVATE-REASON"))
            before = self.f.journal_dump()
            result = self.success()
            self.assertEqual(result["status"], status)
            self.assertEqual(result["input_volume"], prepared["input_volume"])
            self.assertEqual([a["status"] for a in result["arms"]][:6],
                             ["dispatch_intent_outcome_unknown", *states[1:]])
            self.assertFalse(result["arms"][0]["outcome_known"])
            self.assertIsNone(result["arms"][0]["score"])
            self.assertEqual(result["arms"][1]["score"], 1)
            self.assertFalse(result["all_outcomes_scored"])
            self.assertIsNone(result["comparison"])
            for arm in "AB":
                counts = result["outcomes"][arm]
                self.assertEqual(counts["denominator"], 5)
                self.assertEqual(sum(counts[s] for s in inspect.STATES), 5)
            self.assertEqual(result["outcomes"]["B"]["evaluator_pass"], 1)
            self.assert_private(result)
            self.assertEqual(self.f.journal_dump(), before)

    def test_completed_script_run_inspected_without_rubric_or_redispatch(self):
        prepared = self.f.success(model="fake-model-1")
        rubric = Path(self.f.write("rubric.json", self.f.key))
        provider = FakeTaskProvider(script={0: b"EVALUATOR-ONLY-ANSWER-0"})
        with mock.patch.object(runtime_cli, "FakeTaskProvider", return_value=provider):
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(main(["compare", "--store-config", self.f.config_path,
                "--manifest", self.f.manifest_path, "--journal", str(self.f.journal),
                "--provider", "script", "--rubric", str(rubric)], out, err), 0, err.getvalue())
        self.assertEqual(len(provider.requests), 10)
        rubric.unlink()
        before = self.f.journal_dump()
        with mock.patch.object(ComparisonStore, "run", side_effect=AssertionError("redispatch")), \
             mock.patch.object(ComparisonStore, "report", side_effect=AssertionError("mutation")):
            result = self.success()
        self.assertEqual(result["plan_sha256"], prepared["plan_sha256"])
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["all_outcomes_scored"])
        self.assertEqual(result["outcomes"]["A"]["completed"], 5)
        self.assertEqual(result["outcomes"]["A"]["evaluator_pass"], 1)
        self.assertEqual(result["outcomes"]["B"]["evaluator_pass"], 0)
        self.assertTrue(result["scores_are_synthetic"])
        self.assertIsNone(result["performance_claim"])
        self.assertFalse(result["acceptance_complete"])
        self.assertIsNone(result["comparison"])
        self.assert_private(result)
        self.assertEqual(self.f.journal_dump(), before)

    def test_changed_eligible_context_and_revocation_are_observed_without_invalidation(self):
        self.f.success()
        before = self.f.journal_dump()
        self.f.f.put(self.f.store, make_item("e-8", text="new uncited synthetic raw"))
        changed = self.success()
        self.assertFalse(changed["current_validity"]["valid"])
        self.assertEqual(changed["status"], "planned")
        self.assertEqual(self.f.journal_dump(), before)
        self.f.store.set_policy(make_control(), policy_body(memory_ids=("m-1",)), expected_revision=1)
        source_bytes = Path(self.f.f.path).read_bytes()
        revoked = self.success()
        self.assertFalse(revoked["current_validity"]["valid"])
        self.assertEqual(revoked["status"], "planned")
        self.assertEqual(self.f.journal_dump(), before)
        self.assertEqual(Path(self.f.f.path).read_bytes(), source_bytes)

    def test_corrupt_hashes_arms_scores_and_foreign_schema_refuse_without_repair(self):
        prepared = self.f.success()
        with sqlite3.connect(self.f.journal) as db:
            db.execute("INSERT INTO comparison_arms VALUES (?,?,?,?,?,?,?,?)",
                       (self.f.manifest["plan_id"], 0, "A", 0, "completed",
                        prepared["arms"][0]["request_sha256"], b"PRIVATE-REPLY", 1))
        mutations = [
            ("comparison_plans", "plan_sha256", "0" * 64),
            ("frozen_contexts", "context_sha256", "0" * 64),
            ("comparison_arms", "request_sha256", "0" * 64),
            ("comparison_arms", "position", 1),
            ("comparison_arms", "task_index", 99),
            ("comparison_arms", "status", "PRIVATE-INVALID-STATUS"),
            ("comparison_arms", "score", None),
            ("comparison_arms", "score", 2),
        ]
        for table, column, value in mutations:
            with self.subTest(table=table, column=column, value=value):
                with sqlite3.connect(self.f.journal) as db:
                    original = db.execute("SELECT " + column + " FROM " + table).fetchone()[0]
                    db.execute("UPDATE " + table + " SET " + column + "=?", (value,))
                before = self.f.journal_dump()
                self.refused()
                self.assertEqual(self.f.journal_dump(), before)
                with sqlite3.connect(self.f.journal) as db:
                    db.execute("UPDATE " + table + " SET " + column + "=?", (original,))
        with sqlite3.connect(self.f.journal) as db:
            db.execute("CREATE VIEW PRIVATE_VIEW AS SELECT 1")
        before_bytes = self.f.journal.read_bytes()
        self.refused()
        self.assertEqual(self.f.journal.read_bytes(), before_bytes)

    def test_missing_alias_foreign_inputs_and_private_options_never_initialize_or_echo(self):
        missing = self.f.directory / "missing.sqlite"
        self.refused(journal=missing)
        self.assertFalse(missing.exists())
        empty = self.f.directory / "empty.sqlite"
        empty.touch()
        self.refused(journal=empty)
        self.assertEqual(empty.read_bytes(), b"")
        foreign = self.f.directory / "foreign.sqlite"
        with sqlite3.connect(foreign) as db:
            db.execute("CREATE TABLE private_foreign_data (value)")
        before = foreign.read_bytes()
        self.refused(journal=foreign)
        self.assertEqual(foreign.read_bytes(), before)
        source = Path(self.f.f.path)
        link = self.f.directory / "source-hardlink.sqlite"
        link.hardlink_to(source)
        symlink = self.f.directory / "source-link.sqlite"
        symlink.symlink_to(source)
        source_bytes = source.read_bytes()
        for target in (source, link, symlink):
            self.refused(journal=target)
        self.assertEqual(source.read_bytes(), source_bytes)
        self.f.success()
        before = self.f.journal_dump()
        self.refused(plan_id="unknown-plan")
        self.refused(plan_id="PRIVATE-INVALID PLAN")
        for option in ("--provider", "--agent", "--rubric", "--manifest", "--live", "--plan"):
            code, output, error = self.call(extra=(option, "PRIVATE-DETAIL"))
            self.assertEqual((code, output), (2, ""))
            self.assertEqual(error, "error[compare-inspect]: invalid command arguments\n")
        self.assertEqual(self.f.journal_dump(), before)
        with closing(ComparisonStore(self.f.journal, read_only=True)) as reader:
            with self.assertRaisesRegex(ValueError, "cannot run"):
                reader.run(self.f.manifest["plan_id"], None, None, None)
            with self.assertRaisesRegex(ValueError, "cannot plan"):
                reader.plan(plan_id="unused", tasks=[], raw_references=[], consolidated_records=[],
                            config={}, model="fake-model-1", scope={},
                            snapshot_sha256="", policy_sha256="", evaluator_identity={})
