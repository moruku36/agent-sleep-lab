"""Private same-run CLI contracts; all receipts below are test-authored fixtures."""
import copy
import io
import json
from contextlib import ExitStack, closing
from pathlib import Path
from unittest.mock import patch

import support
import test_adoption_store as fixtures
from evidence_support import StoreCase
from runtime_support import make_control, policy_body
from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.cli import main
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.retrieval import retrieve_reference_bundle
from agent_sleep_lab.runtime_artifacts import encode_artifact
from agent_sleep_lab.sleep_coordinator import FakeProvider, SleepCoordinator, _encode
from agent_sleep_lab.sleep_evidence import bind_from_store, current_store
from agent_sleep_lab.strictjson import loads_strict_bytes

SCOPE = {"project": "p", "task_family": "t"}
ROOT = Path(__file__).resolve().parent.parent


class SleepReviewCLITests(StoreCase):
    open_adoption = fixtures.AdoptionTests.open_adoption
    setup_store = fixtures.AdoptionTests.setup_store

    def setUp(self):
        super().setUp()
        clock = patch("agent_sleep_lab.evidence_store._utc_now", self.clock)
        clock.start()
        self.addCleanup(clock.stop)

    def write(self, name, document):
        path = Path(self.dir) / name
        path.write_text(json.dumps(document), encoding="utf-8")
        return str(path)

    def ready(self, label="run-1"):
        self.path = str(Path(self.dir) / (label + "-store.sqlite"))
        store = self.setup_store()
        journal = str(Path(self.dir) / (label + "-sleep.sqlite"))
        c = SleepCoordinator(journal)
        self.addCleanup(c.close)
        bind_from_store(c, store, run_id=label, scope=SCOPE, event_ids=["e-1"],
                        config={"observed_at": "2026-11-10T00:00:00Z"})
        provider = FakeProvider(_encode({"event_ids": ["e-1"]}), _encode({"operations": [
            {"op": "add", "memory_id": "m-1", "event_ids": ["e-1"], "claim": "do the thing"}]}))
        current = current_store(store, scope=SCOPE, event_ids=["e-1"])
        c.advance(label, provider, current=current)
        self.assertEqual(c.advance(label, provider, current=current)["status"], "ready")
        config = json.loads((ROOT / "configs/runtime-store.example.json").read_text())
        config["path"] = self.path
        config_path = self.write(label + "-config.json", config)
        args = ["--journal", journal, "--run-id", label, "--store-config", config_path]
        return store, c, args

    def call(self, command, args, *, ok=True):
        out, err = io.StringIO(), io.StringIO()
        code = main([command, *args], out, err)
        self.assertEqual(code, 0 if ok else 2, err.getvalue())
        if ok:
            self.assertEqual(err.getvalue(), "")
            return json.loads(out.getvalue())
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn("do the thing", err.getvalue())
        self.assertNotIn("raw source", err.getvalue())
        return err.getvalue()

    def artifact(self, store, packet, name="prepared.json"):
        # Independent synthetic fixture setup happens BEFORE calling the product CLI.
        payload = fixtures.AdoptionTests.proposal(
            self, store, operation_id=packet["operation_id"], run_id=packet["run_id"])
        doc = {key: blob.hex() for key, blob in payload.items() if key != "memory_bytes"}
        doc["memory_bytes"] = {mid: blob.hex() for mid, blob in payload["memory_bytes"].items()}
        return payload, doc, self.write(name, doc)

    def no_dispatch_or_registration(self):
        stack = ExitStack()
        for owner, method in ((FakeProvider, "propose"), (SleepCoordinator, "advance"),
                              (AdoptionStore, "register_verification"),
                              (AdoptionStore, "register_evaluation")):
            stack.enter_context(patch.object(owner, method, side_effect=AssertionError(method)))
        stack.enter_context(patch("agent_sleep_lab.mimo_provider.OpenClawMimoProvider",
                                  side_effect=AssertionError("live provider")))
        return stack

    def test_private_review_preserves_pending_prose_evidence_and_prepare_identity(self):
        store, c, args = self.ready()
        before = c.inspect("run-1")
        with self.no_dispatch_or_registration(), patch.object(
                AdoptionStore, "commit_adoption", side_effect=AssertionError("write")):
            packet = self.call("sleep-review", args)
            self.assertEqual(self.call("sleep-review", args), packet)
        raw_binding = c._read("run-1")[0]
        self.assertTrue(packet["private_output"])
        self.assertFalse(packet["publication_authorized"])
        self.assertTrue(packet["independent_verification_required"])
        self.assertTrue(packet["independent_evaluation_required"])
        self.assertEqual(packet["binding_sha256"], sha256_hex(raw_binding))
        self.assertEqual(packet["proposal_sha256"], sha256_hex(_encode(before["deep"])))
        event = packet["binding"]["events"][0]
        self.assertEqual(event["source"].encode(), store.get("e-1").source_bytes)
        self.assertEqual(event["source_sha256"], store.get("e-1").source_sha256)
        memory = packet["candidate_memories"]["m-1"]
        self.assertEqual(memory["claim"], before["deep"]["operations"][0]["claim"])
        self.assertEqual((memory["status"], memory["verification"]["result"]), ("candidate", "pending"))
        self.assertEqual(packet["candidate_sha256"]["m-1"], sha256_hex(_encode(memory)))
        self.assertEqual(c.inspect("run-1"), before)
        with closing(SleepCoordinator(args[1], read_only=True)) as ro:
            self.assertEqual(ro.db.execute("PRAGMA query_only").fetchone()[0], 1)
            with self.assertRaises(Exception):
                ro.db.execute("DELETE FROM sleep_runs")
        payload, _, _ = self.artifact(store, packet)
        c.prepare("run-1", lambda operation_id, *_: (
            self.assertEqual(operation_id, packet["operation_id"]) or payload))
        self.assertIsNone(store.current_snapshot(SCOPE))

    def test_review_and_adopt_refuse_invalid_inflight_unbound_empty_and_oversized_runs(self):
        store, c, args = self.ready()
        original_binding, original_state = c._read("run-1")
        packet = self.call("sleep-review", args)
        _, _, artifact = self.artifact(store, packet)
        binding = loads_strict_bytes(original_binding)
        cases = []
        for status in ("invalidated", "light_inflight", "deep_inflight", "preparing", "incomplete", "failed", "light"):
            cases.append((original_binding, _encode(dict(original_state, status=status))))
        for field, value in (("version", 1), ("store_binding", None), ("events", [])):
            cases.append((_encode(dict(binding, **{field: value})), _encode(original_state)))
        empty = dict(original_state, deep={"operations": []})
        cases.extend([(original_binding, _encode(empty)), (b" " * 1048577, _encode(original_state))])
        for bound, state in cases:
            with self.subTest(state=state[:60], binding_bytes=len(bound)):
                c.db.execute("UPDATE sleep_runs SET binding=?,state=? WHERE run_id='run-1'", (bound, state))
                with self.no_dispatch_or_registration():
                    self.call("sleep-review", args, ok=False)
                    self.call("sleep-adopt", [*args, "--artifact", artifact], ok=False)
                self.assertIsNone(store.current_snapshot(SCOPE))
        c.db.execute("UPDATE sleep_runs SET binding=?,state=? WHERE run_id='run-1'",
                     (original_binding, _encode(original_state)))

    def test_changed_evidence_policy_or_head_refuses_before_preparation(self):
        for change in ("evidence", "policy", "head"):
            with self.subTest(change=change):
                store, c, args = self.ready(change)
                packet = self.call("sleep-review", args)
                _, _, path = self.artifact(store, packet, change + "-prepared.json")
                if change == "evidence":
                    conn = self.raw()
                    triggers = [row[0] for row in conn.execute(
                        "SELECT sql FROM sqlite_master WHERE type='trigger'")]
                    self.drop_triggers(conn)
                    conn.execute("UPDATE source_blobs SET source_bytes=? WHERE event_id='e-1'", (b"changed private source",))
                    for statement in triggers:
                        conn.execute(statement)
                elif change == "policy":
                    store.set_policy(make_control(), policy_body(event_ids=("e-1",)), expected_revision=1)
                else:
                    winner = fixtures.AdoptionTests.proposal(self, store, operation_id="other-writer", mid="m-2")
                    store.commit_adoption(**winner)
                head = store.current_snapshot(SCOPE)
                with self.no_dispatch_or_registration(), patch.object(
                        SleepCoordinator, "prepare", side_effect=AssertionError("stale preparation")) as prepare:
                    self.call("sleep-review", args, ok=False)
                    self.call("sleep-adopt", [*args, "--artifact", path], ok=False)
                    prepare.assert_not_called()
                self.assertEqual(c.inspect(change)["status"], "ready")
                self.assertEqual(store.current_snapshot(SCOPE), head)

    def test_exact_independently_prepared_same_run_adoption_and_replay(self):
        store, c, args = self.ready()
        packet = self.call("sleep-review", args)
        _, _, artifact = self.artifact(store, packet)
        with self.no_dispatch_or_registration():
            adopted = self.call("sleep-adopt", [*args, "--artifact", artifact])
            self.assertEqual(self.call("sleep-adopt", [*args, "--artifact", artifact]), adopted)
        self.assertEqual(adopted["status"], "adopted")
        self.assertEqual(adopted["operation_id"], packet["operation_id"])
        self.assertEqual(c.inspect("run-1")["status"], "adopted")
        self.assertEqual(self.count("adoption_journal"), 1)
        bundle = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=32768)
        self.assertEqual([r["memory_id"] for r in bundle.document["records"]], ["m-1"])
        self.assertEqual(bundle.document["records"][0]["memory"]["claim"], "do the thing")

    def test_substituted_prose_source_and_parent_refuse_without_writer(self):
        for change in ("prose", "source", "parent"):
            with self.subTest(change=change):
                store, c, args = self.ready(change)
                packet = self.call("sleep-review", args)
                payload, doc, _ = self.artifact(store, packet, change + ".json")
                if change == "prose":
                    memory = loads_strict_bytes(payload["memory_bytes"]["m-1"])
                    memory["claim"] = "substituted private prose"
                    doc["memory_bytes"]["m-1"] = _encode(memory).hex()
                else:
                    key, kind = (("source_manifest_bytes", "source_manifest") if change == "source"
                                 else ("request_bytes", "adoption_request"))
                    value = loads_strict_bytes(payload[key])
                    if change == "source":
                        value["entries"][0]["evidence"][0]["event_sha256"] = "a" * 64
                    else:
                        value["expected_parent_snapshot_sha256"] = "a" * 64
                    doc[key] = encode_artifact(kind, value).hex()
                path = self.write(change + "-changed.json", doc)
                with self.no_dispatch_or_registration(), patch.object(
                        AdoptionStore, "commit_adoption", side_effect=AssertionError("writer")) as writer:
                    self.call("sleep-adopt", [*args, "--artifact", path], ok=False)
                    writer.assert_not_called()
                self.assertEqual(c.inspect(change)["status"], "failed")
                self.assertIsNone(store.current_snapshot(SCOPE))

    def test_lost_ack_reconciles_exact_operation_after_revocation_without_reactivation(self):
        store, c, args = self.ready()
        packet = self.call("sleep-review", args)
        _, doc, artifact = self.artifact(store, packet)
        commit = AdoptionStore.commit_adoption
        def lost_ack(instance, **payload):
            commit(instance, **payload)
            raise OSError("test ACK loss")
        with self.no_dispatch_or_registration(), patch.object(AdoptionStore, "commit_adoption", lost_ack):
            self.call("sleep-adopt", [*args, "--artifact", artifact], ok=False)
        self.assertEqual(c.inspect("run-1")["status"], "handoff")
        head = store.current_snapshot(SCOPE)
        store.set_policy(make_control(), policy_body(event_ids=("e-1",)), expected_revision=1)
        substituted = copy.deepcopy(doc)
        memory = loads_strict_bytes(bytes.fromhex(substituted["memory_bytes"]["m-1"]))
        memory["claim"] = "different replay prose"
        substituted["memory_bytes"]["m-1"] = _encode(memory).hex()
        with self.no_dispatch_or_registration():
            self.call("sleep-adopt", [*args, "--artifact", self.write("other.json", substituted)], ok=False)
            result = self.call("sleep-adopt", [*args, "--artifact", artifact])
            self.assertEqual(self.call("sleep-adopt", [*args, "--artifact", artifact]), result)
        self.assertEqual(result["status"], "adopted")
        self.assertEqual(self.count("adoption_journal"), 1)
        self.assertEqual(store.current_snapshot(SCOPE), head)
        self.assertEqual(store.current_policy().revision, 2)
        self.assertEqual(retrieve_reference_bundle(store, scope=SCOPE, max_bytes=32768).document["records"], [])

    def test_concurrent_prepare_does_not_adopt_a_different_supplied_artifact(self):
        store, c, args = self.ready()
        packet = self.call("sleep-review", args)
        payload, doc, _ = self.artifact(store, packet)
        altered = copy.deepcopy(doc)
        memory = loads_strict_bytes(bytes.fromhex(altered["memory_bytes"]["m-1"]))
        memory["claim"] = "different caller artifact"
        altered["memory_bytes"]["m-1"] = _encode(memory).hex()
        path = self.write("concurrent-different.json", altered)
        prepare = SleepCoordinator.prepare

        def competing_prepare(instance, run_id, callback):
            # Another caller wins after the CLI read ready but before prepare reads.
            return prepare(instance, run_id, lambda *_: payload)

        with self.no_dispatch_or_registration(), patch.object(
                SleepCoordinator, "prepare", competing_prepare), patch.object(
                AdoptionStore, "commit_adoption", side_effect=AssertionError("writer")) as writer:
            self.call("sleep-adopt", [*args, "--artifact", path], ok=False)
            writer.assert_not_called()
        self.assertEqual(c.inspect("run-1")["status"], "handoff")
        self.assertIsNone(store.current_snapshot(SCOPE))

    def test_missing_foreign_aliased_inputs_and_execution_options_are_refused(self):
        store, c, args = self.ready()
        packet = self.call("sleep-review", args)
        _, _, artifact = self.artifact(store, packet)
        missing = str(Path(self.dir) / "missing.sqlite")
        empty = Path(self.dir) / "empty.sqlite"
        empty.touch()
        foreign = Path(self.dir) / "foreign.sqlite"
        foreign.write_bytes(Path(self.path).read_bytes())
        for journal in (missing, str(empty), str(foreign), self.path):
            changed = list(args)
            changed[1] = journal
            self.call("sleep-review", changed, ok=False)
            self.call("sleep-adopt", [*changed, "--artifact", artifact], ok=False)
        self.assertFalse(Path(missing).exists())
        self.assertEqual(empty.stat().st_size, 0)
        for command in ("sleep-review", "sleep-adopt"):
            base = args + (["--artifact", artifact] if command == "sleep-adopt" else [])
            with self.no_dispatch_or_registration():
                for option in ("--provider", "--callback", "--register-receipt"):
                    self.call(command, [*base, option, "private-forbidden-value"], ok=False)
        too_large = Path(self.dir) / "large.json"
        too_large.write_bytes(b" " * 1048577)
        self.call("sleep-adopt", [*args, "--artifact", str(too_large)], ok=False)
        forged = self.write("model-decision.json", {"verified": True, "receipt_id": "model-claim"})
        self.call("sleep-adopt", [*args, "--artifact", forged], ok=False)
        self.assertEqual(c.inspect("run-1")["status"], "ready")
        self.assertIsNone(store.current_snapshot(SCOPE))
