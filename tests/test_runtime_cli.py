"""Runtime command integration, explicit synthetic receipts and no network."""
import io
import json
from pathlib import Path
from unittest.mock import patch
import support
from evidence_support import StoreCase, make_item
import test_adoption_store as fixtures
import test_retrieval as retrieval_fixtures
from agent_sleep_lab.cli import main
from agent_sleep_lab.sleep_coordinator import SleepCoordinator
from agent_sleep_lab.ab_comparison import ComparisonStore, FakeTaskProvider, _encode
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.raw_baseline import RANKED_ORDER, RawBaselineComparison

ROOT = Path(__file__).resolve().parent.parent


class RuntimeCommandTests(StoreCase):
    open_adoption = fixtures.AdoptionTests.open_adoption
    setup_store = fixtures.AdoptionTests.setup_store

    def write(self, name, value):
        path = Path(self.dir) / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)

    def config(self):
        config = json.loads((ROOT / "configs/runtime-store.example.json").read_text())
        config["path"] = str(self.path)
        return self.write("store.json", config)

    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        status = main(list(args), out, err)
        self.assertEqual(status, 0, err.getvalue())
        return json.loads(out.getvalue())

    def test_script_sleep_status_and_repeat_are_body_bound_no_adoption(self):
        store = self.setup_store()
        config = self.config()
        manifest = ROOT / "configs/sleep.example.json"
        replies = ROOT / "configs/sleep-replies.example.json"
        journal = str(Path(self.dir) / "sleep.sqlite")
        args = ("sleep", "--store-config", config, "--manifest", str(manifest),
                "--journal", journal, "--provider", "script", "--replies", str(replies))
        first = self.call(*args)
        self.assertEqual(first["status"], "ready")
        self.assertEqual(first["calls"], 2)
        self.assertEqual(first["candidate_memories"]["m-1"]["claim"],
                         first["deep"]["operations"][0]["claim"])
        self.assertEqual(first, self.call(*args))
        state = self.call("sleep-status", "--journal", journal, "--run-id", "sleep-public-fixture-1")
        self.assertEqual(state["status"], "ready")
        self.assertIsNone(store.current_snapshot({"project": "p", "task_family": "t"}))

    def test_adopt_existing_independently_prepared_receipts_then_retrieve(self):
        store = self.setup_store()
        payload = fixtures.AdoptionTests.proposal(self, store)
        encoded = {k: v.hex() for k, v in payload.items() if k != "memory_bytes"}
        encoded["memory_bytes"] = {k: v.hex() for k, v in payload["memory_bytes"].items()}
        config = self.config()
        result = self.call("adopt", "--store-config", config,
                           "--manifest", self.write("adoption.json", encoded))
        self.assertEqual(result["status"], "created")
        bundle = self.call("retrieve", "--store-config", config,
                           "--manifest", self.write("retrieve.json",
                            {"scope": {"project": "p", "task_family": "t"}, "query": "thing", "max_bytes": 32768}))
        self.assertEqual([r["memory_id"] for r in bundle["records"]], ["m-1"])

    def test_journals_refuse_evidence_database_without_schema_mutation(self):
        store = self.setup_store()
        before = store._rows("SELECT name FROM sqlite_master ORDER BY name")
        for constructor in (SleepCoordinator, ComparisonStore):
            with self.assertRaisesRegex(ValueError, "foreign database"):
                constructor(self.path)
        self.assertEqual(store._rows("SELECT name FROM sqlite_master ORDER BY name"), before)
        err = io.StringIO()
        status = main(["sleep", "--store-config", self.config(),
                       "--manifest", str(ROOT / "configs/sleep.example.json"),
                       "--journal", str(self.path), "--provider", "script",
                       "--replies", str(ROOT / "configs/sleep-replies.example.json")], io.StringIO(), err)
        self.assertEqual(status, 2)
        self.assertIn("separate", err.getvalue())
        self.assertEqual(store._rows("SELECT name FROM sqlite_master ORDER BY name"), before)

    def test_compare_manifest_opt_in_ranking_uses_only_existing_fake_provider_route(self):
        store = self.setup_store()
        self.put(store, make_item("e-9", text="thing synthetic source"))
        retrieval_fixtures.RetrievalTests.adopt(self, store, "m-1", "e-1", claim="do the thing")
        rubric = {"cli-task": "fixture-evaluator-secret-answer"}
        manifest = dict(
            plan_id="ranked-cli", tasks=[dict(task_id="cli-task", prompt="Synthetic task")],
            retrieval=dict(scope={"project": "p", "task_family": "t"}, max_bytes=32768,
                           query="thing", raw_order=RANKED_ORDER),
            budget=dict(calls=1, request_bytes=65536, reply_bytes=64),
            evaluator_identity=dict(name="cli-fixture", version="1",
                                    protocol_sha256=sha256_hex(_encode(rubric))))
        path = self.write("comparison.json", manifest)
        journal = str(Path(self.dir) / "comparison.sqlite")
        args = ("compare", "--store-config", self.config(), "--manifest", path,
                "--journal", journal, "--provider", "script", "--rubric", self.write("rubric.json", rubric))
        provider = FakeTaskProvider()
        head = store.current_snapshot({"project": "p", "task_family": "t"})
        with patch("agent_sleep_lab.runtime_cli.FakeTaskProvider", return_value=provider):
            report = self.call(*args)
            self.assertEqual(report["status"], "complete")
            self.assertEqual(report["rules"]["order"], RANKED_ORDER)
            self.assertEqual(report["raw_counts"]["eligible"], 2)
            self.assertEqual(len(provider.requests), 2)
            self.assertEqual(self.call(*args), report)  # saved replay; no additional calls
            for changed in (dict(query="THING"), dict(raw_order="event_id_ascending")):
                manifest["retrieval"].update(changed)
                self.write("comparison.json", manifest)
                err = io.StringIO()
                self.assertEqual(main(list(args), io.StringIO(), err), 2)
                self.assertIn("plan binding conflict", err.getvalue())
                manifest["retrieval"].update(query="thing", raw_order=RANKED_ORDER)
        self.assertEqual(len(provider.requests), 2)
        for request in provider.requests:
            self.assertNotIn(rubric["cli-task"].encode("utf-8"), request)
        comparison = ComparisonStore(journal)
        self.addCleanup(comparison.close)
        baseline = RawBaselineComparison(store, comparison, **manifest["retrieval"])
        frozen = baseline.frozen("ranked-cli")
        self.assertEqual([row["event_id"] for row in frozen["events"]], ["e-9", "e-1"])
        for arm in baseline.audit("ranked-cli")["arms"]:
            self.assertEqual(arm["raw_present"], frozen["events"])
        self.assertEqual(store.current_snapshot({"project": "p", "task_family": "t"}), head)
