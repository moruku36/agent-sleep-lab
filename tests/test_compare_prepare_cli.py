"""Offline predispatch behavior over real temporary stores and synthetic fixtures.

Fixture receipts are test-created, not live acceptance. No shell, external
transport, agent, credential access or paid inference. Fixture cases are composed
rather than inherited/re-exported for test collection.
"""
import copy
import io
import json
from pathlib import Path
import sqlite3
from unittest import TestCase, mock

import test_retrieval as fixtures
from evidence_support import make_item
from runtime_support import make_control, policy_body
from agent_sleep_lab import comparison_prepare as prepare
from agent_sleep_lab import runtime_cli
from agent_sleep_lab.ab_comparison import ComparisonStore, FakeTaskProvider, _encode
from agent_sleep_lab.cli import main
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.raw_baseline import RawBaselineComparison, RANKED_ORDER

ROOT = Path(__file__).resolve().parent.parent
SCOPE = dict(project="p", task_family="t")


class ComparePreparationTests(TestCase):
    def setUp(self):
        self.f = fixtures.RetrievalTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.store = self.f.setup_store()
        self.f.put(self.store, make_item("e-9", text="PRIVATE-SYNTHETIC-RAW duplicate"))
        self.f.adopt(self.store, "m-1", "e-1", claim="PRIVATE-SYNTHETIC-MEMORY duplicate")
        self.directory = Path(self.f.dir)
        self.key = {f"task-{i}": f"EVALUATOR-ONLY-ANSWER-{i}" for i in range(5)}
        self.manifest = dict(
            plan_id="prepare-five", tasks=[dict(task_id=tid, prompt="PRIVATE-TASK " + tid)
                                           for tid in self.key],
            retrieval=dict(scope=SCOPE, query="duplicate", raw_order=RANKED_ORDER,
                           max_bytes=32768, scan_limit=256, max_raw=16, max_records=16),
            budget=dict(calls=5, request_bytes=65536, reply_bytes=64), config={"fixture": "offline"},
            evaluator_identity=dict(name="fixture-exact", version="1",
                                    protocol_sha256=sha256_hex(_encode(self.key))))
        self.manifest_path = self.write("comparison.json", self.manifest)
        self.config = json.loads((ROOT / "configs/runtime-store.example.json").read_text())
        self.config["path"] = str(self.f.path)
        self.config_path = self.write("config.json", self.config)
        self.journal = self.directory / "comparison.sqlite"
        clock = mock.patch("agent_sleep_lab.evidence_store._utc_now", self.f.clock)
        clock.start()
        self.addCleanup(clock.stop)

    def write(self, name, value):
        path = self.directory / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)

    def call(self, *, model="xiaomi/mimo-v2.6-pro", journal=None, extra=()):
        out, err = io.StringIO(), io.StringIO()
        code = main(["compare-prepare", "--manifest", self.manifest_path,
                     "--store-config", self.config_path, "--journal", str(journal or self.journal),
                     "--model", model, *extra], out, err)
        return code, out.getvalue(), err.getvalue()

    def success(self, **kwargs):
        code, output, error = self.call(**kwargs)
        self.assertEqual((code, error), (0, ""))
        return json.loads(output)

    def refused(self, **kwargs):
        code, output, error = self.call(**kwargs)
        self.assertEqual((code, output), (2, ""))
        self.assertEqual(error, "error[compare-prepare]: preparation refused; check strict inputs, "
                         "distinct databases, frozen bindings, budgets and current eligible memory\n")

    def journal_dump(self):
        with sqlite3.connect(self.journal) as db:
            return tuple(db.iterdump())

    def test_five_pairs_freeze_all_ten_slots_no_provider_key_or_adoption_writes(self):
        before = tuple(self.store._db().iterdump())
        before_bytes = Path(self.f.path).read_bytes()
        actual_open = prepare.open_store
        opened = []

        def readonly(*args, **kwargs):
            self.assertIs(kwargs.get("read_only"), True)
            store = actual_open(*args, **kwargs)
            opened.append(store.read_only)
            self.assertEqual(store._db().execute("PRAGMA query_only").fetchone()[0], 1)
            return store

        with mock.patch.object(prepare, "open_store", side_effect=readonly), \
             mock.patch.object(runtime_cli, "OpenClawMimoProvider", side_effect=AssertionError("provider")), \
             mock.patch.object(runtime_cli, "FakeTaskProvider", side_effect=AssertionError("provider")), \
             mock.patch.object(runtime_cli, "SyntheticEvaluator", side_effect=AssertionError("evaluator")), \
             mock.patch.object(runtime_cli, "read_json", side_effect=AssertionError("rubric read")), \
             mock.patch.object(ComparisonStore, "run", side_effect=AssertionError("dispatch")), \
             mock.patch.object(ComparisonStore, "report", side_effect=AssertionError("status write")):
            result = self.success()
        self.assertEqual(opened, [True])
        self.assertEqual(result["planned_denominator"], dict(task_pairs=5, per_arm=5, total_arms=10))
        self.assertEqual([t["order"] for t in result["task_order"]], ["AB", "BA", "AB", "BA", "AB"])
        self.assertEqual(len(result["arms"]), 10)
        self.assertEqual({a["status"] for a in result["arms"]}, {"planned_not_dispatched"})
        self.assertEqual(result["per_arm_caps"], {a: self.manifest["budget"] for a in "AB"})
        self.assertEqual(result["reply_byte_check"], "post_generation")
        self.assertFalse(result["byte_caps_are_token_caps"])
        self.assertFalse(result["byte_caps_are_monetary_caps"])
        self.assertIsNone(result["generation_token_cap"])
        self.assertIsNone(result["monetary_cap"])
        self.assertEqual(result["cost"], {"label": "unavailable", "value": None})
        self.assertIsNone(result["usage"])
        self.assertTrue(result["current_validity"]["valid"])
        self.assertFalse(result["dispatch_authorization"])
        self.assertFalse(result["acceptance_complete"])
        with sqlite3.connect(self.journal) as db:
            for table, count in (("comparison_plans", 1), ("evaluation_contacts", 1),
                                 ("frozen_contexts", 1), ("comparison_arms", 0),
                                 ("comparison_provider_receipts", 0)):
                self.assertEqual(db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0], count)
            plan_blob, digest = db.execute("SELECT plan, plan_sha256 FROM comparison_plans").fetchone()
            plan = json.loads(plan_blob)
            self.assertEqual(result["plan_sha256"], digest)
            self.assertEqual(sha256_hex(plan_blob), digest)
            for name in ("config_sha256", "taskset_sha256", "policy_sha256", "snapshot_sha256"):
                self.assertEqual(result[name], plan[name])
            self.assertTrue(all(c["label"] == "unavailable"
                                for phases in plan["cost"].values() for c in phases.values()))
            for task, a, b in zip(plan["tasks"], result["arms"][::2], result["arms"][1::2]):
                raw = json.loads(task["A"]["request"])["context"]
                memory = json.loads(task["B"]["request"])["context"]
                self.assertEqual(memory[:len(raw)], raw)
                self.assertGreater(len(memory), len(raw))
                self.assertEqual(a["raw_present"], b["raw_present"])
                self.assertEqual({r["event_id"] for r in a["raw_present"]}, {"e-1", "e-9"})
                self.assertEqual([m["memory_id"] for m in b["memories_present"]], ["m-1"])
                self.assertNotEqual(a["request_sha256"], b["request_sha256"])
                self.assertEqual(a["request_bytes"], len(task["A"]["request"].encode("ascii")))
        text = json.dumps(result)
        for secret in ("PRIVATE-SYNTHETIC-RAW", "PRIVATE-SYNTHETIC-MEMORY", "PRIVATE-TASK",
                       "EVALUATOR-ONLY-ANSWER", "duplicate"):
            self.assertNotIn(secret, text)
        self.assertEqual(tuple(self.store._db().iterdump()), before)
        self.assertEqual(Path(self.f.path).read_bytes(), before_bytes)

    def test_identical_reopen_and_changed_manifest_model_bindings_without_status_reset(self):
        first = self.success(model="fake-model-1")
        frozen = self.journal_dump()
        self.assertEqual(first, self.success(model="fake-model-1"))
        self.assertEqual(self.journal_dump(), frozen)
        variants = []
        for path, value in ((["config", "fixture"], "changed"),
                            (["budget", "reply_bytes"], 65),
                            (["retrieval", "query"], "DUPLICATE"),
                            (["evaluator_identity", "protocol_sha256"], "b" * 64)):
            doc = copy.deepcopy(self.manifest)
            doc[path[0]][path[1]] = value
            variants.append(doc)
        doc = copy.deepcopy(self.manifest)
        doc["tasks"][0]["prompt"] += " changed"
        variants.append(doc)
        for doc in variants:
            self.write("comparison.json", doc)
            self.refused(model="fake-model-1")
            self.assertEqual(self.journal_dump(), frozen)
        self.write("comparison.json", self.manifest)
        self.refused()  # Same plan ID cannot switch from fake to MiMo.
        self.assertEqual(self.journal_dump(), frozen)
        self.assertEqual(first, self.success(model="fake-model-1"))

    def test_tamper_and_stale_context_refused_without_invalidating_or_rewriting(self):
        self.success()
        with sqlite3.connect(self.journal) as db:
            context, digest = db.execute("SELECT context, context_sha256 FROM frozen_contexts").fetchone()
            db.execute("UPDATE frozen_contexts SET context=?", (context + b" ",))
        tampered = self.journal_dump()
        self.refused()
        self.assertEqual(self.journal_dump(), tampered)
        with sqlite3.connect(self.journal) as db:
            db.execute("UPDATE frozen_contexts SET context=?, context_sha256=?", (context, digest))
            plan_hash = db.execute("SELECT plan_sha256 FROM comparison_plans").fetchone()[0]
            db.execute("UPDATE comparison_plans SET plan_sha256=?", ("0" * 64,))
        tampered = self.journal_dump()
        self.refused()
        self.assertEqual(self.journal_dump(), tampered)
        with sqlite3.connect(self.journal) as db:
            db.execute("UPDATE comparison_plans SET plan_sha256=?", (plan_hash,))
        # Membership changes with the SAME policy and adopted head are stale too.
        self.f.put(self.store, make_item("e-8", text="new uncited synthetic raw"))
        frozen = self.journal_dump()
        self.refused()
        self.assertEqual(self.journal_dump(), frozen)
        self.store.set_policy(make_control(), policy_body(memory_ids=("m-1",)), expected_revision=1)
        self.refused()
        self.assertEqual(self.journal_dump(), frozen)

    def test_aliases_hardlinks_and_foreign_databases_refused_without_mutation(self):
        source = Path(self.f.path)
        symlink = self.directory / "source-link.sqlite"
        symlink.symlink_to(source)
        hardlink = self.directory / "source-hardlink.sqlite"
        hardlink.hardlink_to(source)
        before = source.read_bytes()
        for path in (source, symlink, hardlink):
            self.refused(journal=path)
            self.assertEqual(source.read_bytes(), before)
        foreign = self.directory / "foreign.sqlite"
        with sqlite3.connect(foreign) as db:
            db.execute("CREATE TABLE private_foreign_data (value)")
        foreign_bytes = foreign.read_bytes()
        self.refused(journal=foreign)
        self.assertEqual(foreign.read_bytes(), foreign_bytes)
        for target in (foreign, self.directory / "missing.sqlite"):
            self.write("config.json", self.config | {"path": str(target)})
            self.refused()
            self.assertFalse(self.journal.exists())
        self.assertEqual(foreign.read_bytes(), foreign_bytes)
        self.assertFalse((self.directory / "missing.sqlite").exists())

    def test_strict_input_budget_and_private_argparse_rejection_before_journal(self):
        variants = [self.manifest | {k: "PRIVATE-DETAIL"} for k in
                    ("provider", "agent", "live", "dispatch", "rubric", "execution", "model", "unknown")]
        for key, value in (("calls", True), ("calls", 4), ("calls", 65),
                           ("request_bytes", 0), ("request_bytes", 1048577),
                           ("reply_bytes", -1), ("reply_bytes", 65537), ("unknown", 1)):
            variants.append(self.manifest | {"budget": self.manifest["budget"] | {key: value}})
        for key, value in (("max_bytes", True), ("scan_limit", 1025), ("max_raw", 65),
                           ("query", "x" * 1025), ("raw_order", "unknown"), ("provider", "mimo")):
            variants.append(self.manifest | {"retrieval": self.manifest["retrieval"] | {key: value}})
        for tasks in ([], self.manifest["tasks"] + [dict(task_id="six", prompt="six")],
                      [self.manifest["tasks"][0]] * 2,
                      [self.manifest["tasks"][0] | {"answer": "PRIVATE-DETAIL"}]):
            variants.append(self.manifest | {"tasks": tasks})
        variants.append(self.manifest | {"evaluator_identity": self.manifest["evaluator_identity"] |
                                        {"answer_key": "PRIVATE-DETAIL"}})
        for doc in variants:
            self.write("comparison.json", doc)
            self.refused()
            self.assertFalse(self.journal.exists())
        for raw in (b'{"plan_id":"PRIVATE-DETAIL","plan_id":"duplicate"}',
                    b'{"private":NaN}', b"x" * 1048577):
            Path(self.manifest_path).write_bytes(raw)
            self.refused()
            self.assertFalse(self.journal.exists())
        self.write("comparison.json", self.manifest)
        self.write("config.json", self.config | {"private_unknown": "PRIVATE-DETAIL"})
        self.refused()
        self.write("config.json", self.config)
        for option in ("--provider", "--agent", "--live", "--dispatch", "--rubric", "--execution",
                       "--mod"):
            code, output, error = self.call(extra=(option, "PRIVATE-DETAIL"))
            self.assertEqual((code, output), (2, ""))
            self.assertEqual(error, "error[compare-prepare]: invalid command arguments\n")
        self.assertEqual(self.call(model="PRIVATE-DETAIL")[2],
                         "error[compare-prepare]: invalid command arguments\n")
        self.assertFalse(self.journal.exists())
        # A current query without eligible memory, and an undersized shared cap,
        # cannot produce a comparable registered plan (diagnostic mode is absent).
        for doc in (self.manifest | {"retrieval": self.manifest["retrieval"] | {"query": "nomatch"}},
                    self.manifest | {"budget": self.manifest["budget"] | {"request_bytes": 128}}):
            self.write("comparison.json", doc)
            self.refused()
        with sqlite3.connect(self.journal) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM comparison_plans").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM evaluation_contacts").fetchone()[0], 0)

    def test_unknown_intent_and_all_existing_execution_states_are_only_inspected(self):
        first = self.success()
        with sqlite3.connect(self.journal) as db:
            for arm, state in zip(first["arms"], ("intent", "completed", "replied", "timeout",
                                                   "missing", "invalid")):
                db.execute("INSERT INTO comparison_arms VALUES (?,?,?,?,?,?,?,?)",
                           (self.manifest["plan_id"], arm["task_index"], arm["arm"], arm["position"],
                            state, arm["request_sha256"], b"PRIVATE-REPLY", None))
        for status in ("running", "incomplete", "complete", "invalidated"):
            with sqlite3.connect(self.journal) as db:
                db.execute("UPDATE comparison_plans SET status=?, reason=?", (status, "PRIVATE-REASON"))
            before = self.journal_dump()
            result = self.success()
            self.assertEqual(result["status"], status)
            self.assertEqual(result["arms"][0]["status"], "dispatch_intent_outcome_unknown")
            self.assertFalse(result["arms"][0]["outcome_known"])
            self.assertEqual([a["status"] for a in result["arms"]][1:6],
                             ["completed", "replied", "timeout", "missing", "invalid"])
            self.assertNotIn("PRIVATE-REPLY", json.dumps(result))
            self.assertNotIn("PRIVATE-REASON", json.dumps(result))
            self.assertEqual(self.journal_dump(), before)
            self.assertEqual(result, self.success())

    def test_same_frozen_manifest_consumed_by_script_compare_with_separate_rubric(self):
        # No rubric file exists while preparing; only its predeclared hash is read.
        rubric_path = str(self.directory / "rubric.json")
        first = self.success(model="fake-model-1")
        self.assertEqual(first["evaluator_protocol_sha256"], sha256_hex(_encode(self.key)))
        provider = FakeTaskProvider()
        args = ["compare", "--manifest", self.manifest_path, "--store-config", self.config_path,
                "--journal", str(self.journal), "--provider", "script", "--rubric", rubric_path]
        self.write("rubric.json", {"task-0": "wrong-protocol-key"})
        frozen = self.journal_dump()
        with mock.patch.object(runtime_cli, "FakeTaskProvider", return_value=provider) as constructor:
            self.assertEqual(main(args, io.StringIO(), io.StringIO()), 2)
            constructor.assert_not_called()
        self.assertEqual(self.journal_dump(), frozen)
        self.write("rubric.json", self.key)
        with mock.patch.object(runtime_cli, "FakeTaskProvider", return_value=provider):
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(main(args, out, err), 0, err.getvalue())
            report = json.loads(out.getvalue())
            self.assertEqual(report["plan_sha256"], first["plan_sha256"])
            self.assertEqual(report["status"], "complete")
            self.assertEqual(len(provider.requests), 10)
            self.assertEqual(main(args, io.StringIO(), io.StringIO()), 0)
            self.assertEqual(len(provider.requests), 10)
        for request in provider.requests:
            self.assertNotIn(b"EVALUATOR-ONLY-ANSWER", request)
        reopened = self.success(model="fake-model-1")
        self.assertEqual(reopened["plan_sha256"], first["plan_sha256"])
        self.assertEqual({a["status"] for a in reopened["arms"]}, {"completed"})
        # A concurrent policy change after audit is caught by the final current()
        # recheck; no result/status update is produced by preparation itself.
        audit = RawBaselineComparison.audit

        def revoke(baseline, plan_id):
            result = audit(baseline, plan_id)
            self.store.set_policy(make_control(), policy_body(memory_ids=("m-1",)), expected_revision=1)
            return result

        before = self.journal_dump()
        with mock.patch.object(RawBaselineComparison, "audit", revoke):
            self.refused(model="fake-model-1")
        self.assertEqual(self.journal_dump(), before)
