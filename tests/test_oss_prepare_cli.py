"""Read-only preparation contracts with real adopted stores and labelled stand-ins.

No target execution, live model, private data or performance evaluation.
Fixture cases are composed, not inherited or re-exported for collection.
"""
import copy
import io
import json
from pathlib import Path
import sqlite3
from unittest import TestCase, mock

import test_oss_adopted_reference as fixtures
from runtime_support import make_control, policy_body
from agent_sleep_lab import oss_prepare_cli as reader
from agent_sleep_lab import oss_prompt_capture as capture
from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.cli import main

ROOT = Path(__file__).resolve().parent.parent


class PreparationTests(TestCase):
    def setUp(self):
        self.f = fixtures.AdoptedReferencePreparationTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.f.adopt(self.f.store, "m-1", "e-1", claim=fixtures.CLAIM)
        self.directory = Path(self.f.dir)
        config = json.loads((ROOT / "configs/runtime-store.example.json").read_text())
        config["path"] = str(self.f.path)
        self.config = config
        self.config_path = self.write("config.json", config)
        self.manifest = dict(protocol=reader.PROTOCOL, target_repo=str(self.directory),
            bridge=dict(scope=fixtures.SCOPE.copy(), repository=worker.REPOSITORY,
                        agent_commit=worker.AGENT_COMMIT),
            retrieval=dict(query="duplicate", max_bytes=32768, max_records=16))
        self.manifest_path = self.write("manifest.json", self.manifest)
        patch = mock.patch("agent_sleep_lab.evidence_store._utc_now", self.f.clock)
        patch.start()
        self.addCleanup(patch.stop)

    def write(self, name, value):
        path = self.directory / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)

    def run_cli(self, manifest=None):
        if manifest is not None:
            self.write("manifest.json", manifest)
        out, err = io.StringIO(), io.StringIO()
        code = main(["oss-prepare", "--manifest", self.manifest_path,
                     "--store-config", self.config_path], out, err)
        return code, out.getvalue(), err.getvalue()

    def execute(self):
        return reader.execute(self.manifest_path, store_config_path=self.config_path)

    def stand_in_prepare(self, repo, reference, **kwargs):
        return self.real_prepare(repo, reference, worker_argv=["/synthetic/stand-in"], **kwargs)

    def test_nonempty_adopted_reference_exact_artifacts_one_launch_and_no_mutation(self):
        before = tuple(self.f.store._db().iterdump())
        self.real_prepare = capture.prepare
        pins, freeze, launch = self.f.patched()
        with pins, freeze, launch as launched, \
             mock.patch.object(capture, "prepare", side_effect=self.stand_in_prepare), \
             mock.patch.object(AdoptionStore, "commit_adoption", side_effect=AssertionError("write")):
            code, raw, error = self.run_cli()
        self.assertEqual((code, error, launched.call_count), (0, "", 1))
        result = json.loads(raw)
        self.assertEqual(result["protocol"], reader.OUTPUT_PROTOCOL)
        self.assertEqual(result["summary"]["worker_launch"], capture.STAND_IN_WORKER)
        self.assertEqual(result["summary"]["reference_records"], 1)
        self.assertFalse(result["summary"]["delivery_and_use_verified"])
        self.assertFalse(result["summary"]["dispatch_authorization"])
        a, b = self.f.prompts(result["capture"])
        self.assertNotIn(fixtures.CLAIM, a)
        self.assertIn(fixtures.CLAIM, b)
        self.assertEqual(tuple(self.f.store._db().iterdump()), before)

    def test_empty_foreign_scope_and_excluded_memory_refuse_before_preparation(self):
        with mock.patch.object(capture, "prepare") as prepare:
            doc = copy.deepcopy(self.manifest)
            doc["bridge"]["scope"] = dict(project="other", task_family="t")
            self.assertEqual(self.run_cli(doc)[0], 2)
            self.write("manifest.json", self.manifest)
            self.f.store.set_policy(make_control(), policy_body(memory_ids=("m-1",)), expected_revision=1)
            self.assertEqual(self.run_cli()[0], 2)
            prepare.assert_not_called()

    def test_strict_manifest_bounds_pins_and_dispatch_options_refused_prelaunch(self):
        variants = []
        for key, value in (("provider", "mimo"), ("worker_argv", ["/bad"]),
                           ("protocol", "wrong"), ("target_repo", "relative")):
            variants.append(self.manifest | {key: value})
        for key, value in (("max_bytes", True), ("max_records", 257), ("query", ""),
                           ("query", "x"*1025)):
            doc = copy.deepcopy(self.manifest)
            doc["retrieval"][key] = value
            variants.append(doc)
        doc = copy.deepcopy(self.manifest)
        doc["bridge"]["agent_commit"] = "a"*40
        variants.append(doc)
        with mock.patch.object(capture, "prepare") as prepare:
            for doc in variants:
                with self.subTest(doc=doc):
                    code, output, error = self.run_cli(doc)
                    self.assertEqual((code, output), (2, ""))
                    self.assertIn("preparation refused", error)
            Path(self.manifest_path).write_text('{"protocol":"a","protocol":"b"}')
            self.assertEqual(self.run_cli()[0], 2)
            prepare.assert_not_called()

    def test_missing_empty_foreign_database_never_created_or_initialized(self):
        missing = self.directory / "absent.sqlite"
        empty = self.directory / "empty.sqlite"
        empty.touch()
        foreign = self.directory / "foreign.sqlite"
        with sqlite3.connect(foreign) as db:
            db.execute("CREATE TABLE foreign_data (value)")
        with mock.patch.object(capture, "prepare") as prepare:
            for path in (missing, empty, foreign):
                before = path.read_bytes() if path.exists() else None
                self.write("config.json", self.config | {"path": str(path)})
                self.assertEqual(self.run_cli()[0], 2)
                self.assertEqual(path.read_bytes() if path.exists() else None, before)
            prepare.assert_not_called()
        self.assertFalse(missing.exists())

    def test_policy_change_during_preparation_refuses_all_output(self):
        def change(*args, **kwargs):
            self.f.store.set_policy(make_control(), policy_body(memory_ids=("m-1",)), expected_revision=1)
            return {"private": "marker"}, {"private": "marker"}
        with mock.patch.object(capture, "prepare", side_effect=change) as prepare:
            code, output, error = self.run_cli()
        self.assertEqual((code, output, prepare.call_count), (2, "", 1))
        self.assertNotIn("marker", error)

    def test_readonly_store_open_and_sanitized_failure_without_retry(self):
        actual = AdoptionStore
        seen = []
        def opened(*args, **kwargs):
            seen.append(kwargs.get("read_only"))
            store = actual(*args, **kwargs)
            self.assertEqual(store._db().execute("PRAGMA query_only").fetchone()[0], 1)
            return store
        with mock.patch.object(reader, "AdoptionStore", side_effect=opened), \
             mock.patch.object(capture, "prepare", side_effect=RuntimeError("PRIVATE-DETAIL")) as prepare:
            code, output, error = self.run_cli()
        self.assertEqual((code, output, seen, prepare.call_count), (2, "", [True], 1))
        self.assertNotIn("PRIVATE-DETAIL", error)
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(main(["oss-prepare", "--provider", "PRIVATE-DETAIL"], out, err), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn("PRIVATE-DETAIL", err.getvalue())

    def test_expired_memory_after_preparation_is_not_emitted(self):
        from datetime import timedelta
        start = self.f.clock()
        times = [start]
        with mock.patch("agent_sleep_lab.evidence_store._utc_now", side_effect=lambda: times[0]):
            def advance(*args, **kwargs):
                times[0] = start + timedelta(days=800)
                return {}, {}
            with mock.patch.object(capture, "prepare", side_effect=advance) as prepare:
                code, output, _ = self.run_cli()
        self.assertEqual((code, output, prepare.call_count), (2, "", 1))
