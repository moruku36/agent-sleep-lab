"""Runtime command integration, explicit synthetic receipts and no network."""
import io
import json
from pathlib import Path
import support
from evidence_support import StoreCase
import test_adoption_store as fixtures
from agent_sleep_lab.cli import main
from agent_sleep_lab.sleep_coordinator import SleepCoordinator
from agent_sleep_lab.ab_comparison import ComparisonStore

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
