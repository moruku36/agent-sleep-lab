"""Four selected presentation checks; no live providers or existing stores."""
from contextlib import ExitStack
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch

import support  # noqa: F401
from agent_sleep_lab import offline_demo as demo
from agent_sleep_lab.ab_comparison import FakeTaskProvider
from agent_sleep_lab.cli import EXIT_ERROR, EXIT_OK
from agent_sleep_lab.demo_text import format_demo_text
from agent_sleep_lab.raw_baseline import RawBaselineComparison
from agent_sleep_lab.sleep_coordinator import FakeProvider
from test_offline_demo import call, tracked_directories


class DemoTextTests(unittest.TestCase):
    def test_default_and_explicit_json_preserve_exact_serialization(self):
        result = {"status": "completed", "synthetic_only": True,
                  "nested": {"unicode": "\u96ea", "unknown": None}, "calls": [2, 4]}
        expected = json.dumps(result, ensure_ascii=True, sort_keys=True) + "\n"
        with patch.object(demo, "run_demo", return_value=result) as run:
            self.assertEqual(call("demo"), (EXIT_OK, expected, ""))
            self.assertEqual(call("demo", "--format", "json"), (EXIT_OK, expected, ""))
        self.assertEqual(run.call_count, 2)

    def test_text_uses_single_actual_result_without_extra_dispatch(self):
        observed = []
        original = demo.run_demo

        def run_once():
            result = original()
            observed.append(copy.deepcopy(result))
            return result

        propose, reply = FakeProvider.propose, FakeTaskProvider.reply
        forbidden = ("socket.socket", "socket.create_connection", "socket.getaddrinfo",
                     "subprocess.Popen", "urllib.request.urlopen",
                     "agent_sleep_lab.runtime_cli.execute",
                     "agent_sleep_lab.mimo_provider.OpenClawMimoProvider.__init__")
        with ExitStack() as stack:
            guards = [stack.enter_context(patch(target, side_effect=AssertionError(target)))
                      for target in forbidden]
            run = stack.enter_context(patch.object(demo, "run_demo", side_effect=run_once))
            sleep = stack.enter_context(patch.object(FakeProvider, "propose", autospec=True,
                                                    side_effect=propose))
            task = stack.enter_context(patch.object(FakeTaskProvider, "reply", autospec=True,
                                                   side_effect=reply))
            status, out, err = call("demo", "--format", "text")
            self.assertEqual((status, err), (EXIT_OK, ""))
            run.assert_called_once_with()
            result = observed[0]
            self.assertEqual(sleep.call_count, result["calls"]["scripted_sleep"])
            self.assertEqual(task.call_count, result["calls"]["scripted_task"])
            before = copy.deepcopy(result)
            self.assertEqual(out, format_demo_text(result) + "\n")
            self.assertEqual(result, before)
            self.assertEqual(sleep.call_count, 2)
            self.assertEqual(task.call_count, 4)
            for guard in guards:
                guard.assert_not_called()
        for phrase in ("Capture: 2", "Light: deep; Deep: ready", "Candidates: 1",
                       "pending verification=1", "Atomic adoption: adopted",
                       "Retrieval: 1", "completed=2/2", "timeout=0",
                       "scripted exact-match pass=2/2", "synthetic_zero",
                       "total=unavailable", "not performance improvement",
                       "Temporary state removed: true"):
            self.assertIn(phrase, out)
        # Vary the saved result, without another execution, to catch hardcoded summaries.
        changed = copy.deepcopy(result)
        changed["capture"]["count"] = 7
        changed["comparison"]["report"]["outcomes"]["A"]["timeout"] = 1
        changed["temporary_state_removed"] = False
        rendered = format_demo_text(changed)
        self.assertIn("Capture: 7", rendered)
        self.assertIn("timeout=1", rendered)
        self.assertIn("Temporary state removed: false", rendered)

    def test_invalid_format_rejected_before_execution(self):
        with patch.object(demo, "run_demo") as run:
            status, out, err = call("demo", "--format", "yaml")
        self.assertEqual(status, EXIT_ERROR)
        self.assertEqual(out, "")
        self.assertIn("invalid choice", err)
        run.assert_not_called()

    def test_text_failure_keeps_exit_and_closes_removes_temporary_state(self):
        connections = []
        connect = sqlite3.connect

        def track(*args, **kwargs):
            connection = connect(*args, **kwargs)
            connections.append(connection)
            return connection

        with tracked_directories() as paths, patch("sqlite3.connect", track), \
                patch.object(RawBaselineComparison, "run",
                             side_effect=OSError("synthetic comparison failure")):
            status, out, err = call("demo", "--format", "text")
        self.assertEqual(status, EXIT_ERROR)
        self.assertEqual(out, "")
        self.assertIn("error[runtime]: synthetic comparison failure", err)
        self.assertTrue(paths)
        self.assertTrue(all(not path.exists() for path in paths))
        self.assertTrue(connections)
        for connection in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")
