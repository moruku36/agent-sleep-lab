"""Synthetic demo contract tests; execution evidence lives in implementation status.

Spies and failure injection belong to these tests; the demo uses real production
APIs, real temporary SQLite stores and existing scripted provider implementations.
"""
from contextlib import ExitStack, chdir, contextmanager, redirect_stderr
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import support  # noqa: F401 (make src importable, no imported TestCase fixtures)
from agent_sleep_lab import offline_demo as demo
from agent_sleep_lab.ab_comparison import FakeTaskProvider
from agent_sleep_lab.adoption_candidates import parse_canonical
from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.cli import EXIT_ERROR, EXIT_OK, main
from agent_sleep_lab.provenance import canonical_json, parse_timestamp, sha256_hex
from agent_sleep_lab.raw_baseline import RawBaselineComparison
from agent_sleep_lab.sleep_coordinator import FakeProvider


@contextmanager
def tracked_directories():
    paths = []

    @contextmanager
    def temporary(*args, **kwargs):
        with tempfile.TemporaryDirectory(*args, **kwargs) as directory:
            paths.append(Path(directory))
            yield directory

    with patch.object(demo, "TemporaryDirectory", temporary):
        yield paths


def call(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stderr(err):
        status = main(list(args), stdout=out, stderr=err)
    return status, out.getvalue(), err.getvalue()


class OfflineDemoTests(unittest.TestCase):
    def test_full_chain_uses_registered_receipts_and_normal_atomic_writer(self):
        commits = []
        original = AdoptionStore.commit_adoption

        def commit(store, **payload):
            request = parse_canonical("adoption_request", payload["request_bytes"])
            manifest = parse_canonical("operation_manifest", payload["manifest_bytes"])
            source = parse_canonical("source_manifest", payload["source_manifest_bytes"])
            scope = request["scope"]
            self.assertIsNone(store.current_snapshot(scope))
            operation = manifest["operations"][0]
            memory = json.loads(payload["memory_bytes"][operation["memory_id"]])
            self.assertEqual(memory["status"], "candidate")
            self.assertEqual(memory["verification"]["result"], "pending")
            ref = operation["receipt"]
            vr = store.resolve_receipt("verification", ref["receipt_id"], ref["receipt_sha256"])
            ref = request["evaluation_receipt"]
            er = store.resolve_receipt("evaluation", ref["receipt_id"], ref["receipt_sha256"])
            self.assertEqual(vr["boundary"]["boundary_id"], "synthetic-demo-verifier")
            self.assertEqual(vr["outcome"], "confirmed")
            self.assertEqual(vr["evidence"], source["entries"][0]["evidence"])
            authorization = store.get(vr["evidence"][0]["event_id"]).provenance["authorization"]
            self.assertEqual(authorization["retention"], "until_expiry")
            self.assertGreater(parse_timestamp(authorization["expires_at"]), demo._clock())
            self.assertEqual(vr["memory_sha256"], sha256_hex(payload["memory_bytes"][memory["memory_id"]]))
            self.assertEqual(er["boundary"]["boundary_id"], "synthetic-demo-evaluator")
            self.assertEqual(er["result"], "passed")
            self.assertEqual(er["snapshot_sha256"], request["candidate_snapshot_sha256"])
            result = original(store, **payload)
            self.assertEqual(result.status, "created")
            commits.append(result)
            return result

        with patch.object(AdoptionStore, "commit_adoption", commit):
            result = demo.run_demo()
        self.assertEqual(len(commits), 1)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["capture"]["count"], 2)
        self.assertTrue(all(r["status"] == "created" for r in result["capture"]["results"]))
        self.assertEqual(result["sleep"]["stages_called"], ["light", "deep"])
        self.assertEqual(result["sleep"]["light"]["status"], "deep")
        self.assertEqual(result["sleep"]["deep"]["status"], "ready")
        self.assertTrue(all(result["fixture_registration"]["checks"].values()))
        snapshot = result["bindings"]["snapshot_sha256"]
        self.assertEqual(result["adoption"]["receipt"]["snapshot_sha256"], snapshot)
        bundle = result["retrieval"]["bundle"]
        self.assertEqual(bundle["snapshot_sha256"], snapshot)
        self.assertEqual(bundle["records"][0]["evidence"], result["bindings"]["evidence"])
        self.assertEqual(bundle["records"][0]["eligibility"], "verified")
        comparison = result["comparison"]
        frozen, audit, report = (comparison[name] for name in ("frozen_context", "audit", "report"))
        self.assertEqual(frozen["snapshot_sha256"], snapshot)
        self.assertEqual(frozen["snapshot_binding"], snapshot)
        self.assertEqual(frozen["policy_sha256"], result["policy"]["sha256"])
        self.assertEqual(audit["context_sha256"], sha256_hex(canonical_json(frozen)))
        self.assertEqual(report["context_sha256"], audit["context_sha256"])
        self.assertEqual(report["plan_sha256"], audit["plan_sha256"])
        self.assertEqual(comparison["frozen_evidence"], frozen["events"])
        self.assertEqual(comparison["frozen_memories"], frozen["memories"])
        self.assertEqual(frozen["memories"], [{"memory_id": result["candidates"][0]["memory_id"],
                                            "memory_sha256": result["candidates"][0]["memory_sha256"]}])
        self.assertEqual(frozen["events"][0], result["bindings"]["evidence"][0])
        self.assertEqual(len(audit["arms"]), 4)
        for arm in audit["arms"]:
            self.assertEqual(arm["status"], "completed")
            self.assertEqual(arm["raw_present"], frozen["events"])
            self.assertEqual(arm["memories_present"], frozen["memories"] if arm["arm"] == "B" else [])
            self.assertEqual(arm["raw_dropped"], [])
            self.assertEqual(arm["memories_dropped"], [])
        self.assertTrue(result["temporary_state_removed"])

    def test_paired_requests_share_whole_raw_prefix_add_memory_and_exclude_answers(self):
        requests, sleep_requests = [], []
        reply, propose = FakeTaskProvider.reply, FakeProvider.propose

        def capture_reply(provider, request, max_output_bytes):
            requests.append((request, max_output_bytes))
            return reply(provider, request, max_output_bytes)

        def capture_proposal(provider, stage, request, max_output_bytes):
            sleep_requests.append((request, max_output_bytes))
            return propose(provider, stage, request, max_output_bytes)

        with patch.object(FakeTaskProvider, "reply", capture_reply), \
                patch.object(FakeProvider, "propose", capture_proposal):
            result = demo.run_demo()
        self.assertEqual(result["calls"], {"scripted_sleep": 2, "scripted_task": 4,
                                          "paired_evaluator": 4})
        comparison = result["comparison"]
        self.assertEqual(comparison["input_bytes"], sum(len(r) for r, _ in requests))
        self.assertEqual(result["sleep"]["deep"]["input_bytes"],
                         sum(len(r) for r, _ in sleep_requests))
        budget = comparison["budget"]
        for request, cap in requests:
            self.assertLessEqual(len(request), budget["request_bytes"])
            self.assertEqual(cap, budget["reply_bytes"])
        for request, _ in requests + sleep_requests:
            self.assertNotIn(b"synthetic-scripted-reply", request)
            self.assertNotIn(b'"answers"', request)
            self.assertNotIn(b'"rubric"', request)
        self.assertEqual({sha256_hex(r) for r, _ in requests},
                         {a["request_sha256"] for a in comparison["audit"]["arms"]})
        # Runtime dispatch order alternates AB then BA, with no shared reply history.
        parsed = [json.loads(r) for r, _ in requests]
        for a, b in ((parsed[0], parsed[1]), (parsed[3], parsed[2])):
            self.assertEqual(set(a), {"task_id", "prompt", "context", "reference_data_only"})
            self.assertEqual(a["task_id"], b["task_id"])
            self.assertEqual(a["prompt"], b["prompt"])
            self.assertEqual(b["context"][:len(a["context"])], a["context"])
            self.assertEqual(len(a["context"]), 2)
            self.assertEqual(len(b["context"]), 3)
            self.assertTrue(all(json.loads(c)["kind"] == "raw_source" for c in a["context"]))
            self.assertEqual(json.loads(b["context"][-1])["kind"], "consolidated_record")
        # The uncited second experience is still in both independent raw arms.
        self.assertEqual(len(comparison["frozen_evidence"]), 2)
        self.assertEqual(len(result["bindings"]["evidence"]), 1)
        report = comparison["report"]
        self.assertTrue(report["comparable"])
        self.assertTrue(report["all_outcomes_scored"])
        self.assertEqual(report["comparison"]["paired"],
                         {"denominator": 2, "both": 2, "a_only": 0, "b_only": 0, "neither": 0})
        self.assertEqual(report["comparison"]["order"], {"AB": 1, "BA": 1})

    def test_cli_labels_and_no_network_subprocess_or_runtime_provider_dispatch(self):
        forbidden = ("socket.socket", "socket.create_connection", "socket.getaddrinfo",
                     "subprocess.Popen", "urllib.request.urlopen",
                     "agent_sleep_lab.runtime_cli.execute",
                     "agent_sleep_lab.mimo_provider.OpenClawMimoProvider.__init__")
        with ExitStack() as stack:
            guards = [stack.enter_context(patch(target, side_effect=AssertionError(target)))
                      for target in forbidden]
            status, out, err = call("demo")
        self.assertEqual((status, err), (EXIT_OK, ""))
        result = json.loads(out)
        self.assertIs(result["synthetic_only"], True)
        for label in ("live_provider_verified", "existing_agent_integration_verified", "performance_claim"):
            self.assertIs(result[label], False)
        self.assertTrue(result["comparison"]["report"]["scores_are_synthetic"])
        self.assertFalse(result["comparison"]["report"]["independent_holdout"])
        self.assertIsNone(result["comparison"]["report"]["measured_savings"])
        self.assertEqual(result["comparison"]["report"]["cost"]["B"]["total"]["label"], "unavailable")
        for guard in guards:
            guard.assert_not_called()

    def test_temporary_isolation_cleanup_and_repeatable_bindings(self):
        opened = []
        connect = sqlite3.connect

        def track_connect(database, *args, **kwargs):
            if str(database) != ":memory:":
                opened.append(Path(database))
            return connect(database, *args, **kwargs)

        with tempfile.TemporaryDirectory() as caller, chdir(caller):
            sentinel = Path(caller) / "caller.sqlite"
            sentinel.write_bytes(b"caller state must remain untouched")
            with tracked_directories() as paths, patch("sqlite3.connect", track_connect):
                first = demo.run_demo()
                second = demo.run_demo()
            self.assertEqual(sentinel.read_bytes(), b"caller state must remain untouched")
            self.assertEqual(list(Path(caller).iterdir()), [sentinel])
        self.assertEqual(len(paths), 2)
        self.assertNotEqual(paths[0], paths[1])
        self.assertTrue(all(not path.exists() for path in paths))
        self.assertTrue(opened)
        self.assertTrue(all(path.parent in paths for path in opened))
        for directory in paths:
            self.assertEqual({path.name for path in opened if path.parent == directory},
                             {"adoption.sqlite", "sleep.sqlite", "comparison.sqlite"})
        self.assertEqual(first, second)
        self.assertNotIn(str(paths[0]), json.dumps(first))

    def test_cli_rejects_all_caller_inputs_and_live_options_before_demo(self):
        with patch.object(demo, "run_demo", side_effect=AssertionError("must not run")) as run:
            for option in ("--store-config", "--provider", "--path", "--manifest",
                           "--journal", "--agent", "--content", "--live", "--output"):
                with self.subTest(option=option):
                    self.assertEqual(call("demo", option, "arbitrary")[0], EXIT_ERROR)
            self.assertEqual(call("demo", "arbitrary")[0], EXIT_ERROR)
            self.assertEqual(call("demo", "--help")[0], EXIT_OK)
            run.assert_not_called()

    def test_oversized_stage_reply_fails_nonzero_and_cleans_all_state(self):
        with tracked_directories() as paths, \
                patch.object(FakeProvider, "propose", return_value=b"x" * 2049):
            status, out, err = call("demo")
        self.assertEqual(status, EXIT_ERROR)
        self.assertEqual(out, "")
        self.assertIn("error[runtime]", err)
        self.assertTrue(paths)
        self.assertTrue(all(not path.exists() for path in paths))

    def test_ungrounded_scripted_claim_cannot_register_receipts(self):
        propose = FakeProvider.propose

        def changed_claim(provider, stage, request, max_output_bytes):
            raw = propose(provider, stage, request, max_output_bytes)
            if stage == "deep":
                doc = json.loads(raw)
                doc["operations"][0]["claim"] = "An unsupported synthetic claim"
                return json.dumps(doc).encode("utf-8")
            return raw

        with tracked_directories() as paths, \
                patch.object(FakeProvider, "propose", changed_claim), \
                patch.object(AdoptionStore, "register_verification") as register:
            status, out, err = call("demo")
        self.assertEqual(status, EXIT_ERROR)
        self.assertEqual(out, "")
        self.assertIn("source equality check failed", err)
        register.assert_not_called()
        self.assertTrue(all(not path.exists() for path in paths))

    def test_failure_after_adoption_closes_connections_removes_state_and_reports_no_success(self):
        connections = []
        connect = sqlite3.connect

        def track_connect(*args, **kwargs):
            connection = connect(*args, **kwargs)
            connections.append(connection)
            return connection

        with tracked_directories() as paths, patch("sqlite3.connect", track_connect), \
                patch.object(RawBaselineComparison, "run", side_effect=OSError("synthetic dispatch failure")):
            status, out, err = call("demo")
        self.assertEqual(status, EXIT_ERROR)
        self.assertEqual(out, "")
        self.assertIn("synthetic dispatch failure", err)
        self.assertTrue(paths)
        self.assertTrue(all(not path.exists() for path in paths))
        self.assertTrue(connections)
        for connection in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")
