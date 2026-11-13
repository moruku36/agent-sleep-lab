"""Offline measurement contracts, not model latency or live billing tests."""
import unittest
from unittest.mock import patch

import support  # noqa: F401
import test_ab_comparison as ab
import test_runtime_review as runtime
from agent_sleep_lab.mimo_provider import OpenClawMimoProvider, MODEL


class MeasurementTests(unittest.TestCase):
    def test_utf8_prompt_bytes_and_monotonic_process_time_without_usage_inference(self):
        seen = []
        def transport(argv, **kwargs):
            seen.append(argv)
            return runtime.envelope("ok")
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=1, transport=transport)
        request = "記録".encode("utf-8")
        with patch("agent_sleep_lab.mimo_provider.time.monotonic_ns", side_effect=[100, 350]):
            self.assertEqual(p.reply(request, 100), b"ok")
        receipt = p.receipts[0]
        self.assertEqual(receipt["request_bytes"], 6)
        self.assertEqual(receipt["cli_prompt_bytes"], len(seen[0][-1].encode("utf-8")))
        self.assertGreater(receipt["cli_prompt_bytes"], receipt["request_bytes"])
        self.assertEqual(receipt["transport_elapsed_ns"], 250)
        self.assertIn("not_provider_latency", receipt["timing_basis"])
        self.assertIsNone(receipt["cost"])
        self.assertIsNone(receipt["usage"])
        self.assertEqual(receipt["transport_source"], "injected_transport_not_live_verified")

    def test_transport_failure_retains_elapsed_and_intent_without_retry_or_exception_text(self):
        def timeout(*args, **kwargs):
            raise TimeoutError("PRIVATE")
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=1, transport=timeout)
        with patch("agent_sleep_lab.mimo_provider.time.monotonic_ns", side_effect=[10, 90]):
            with self.assertRaisesRegex(RuntimeError, "unknown") as error:
                p.reply(b"task", 100)
        self.assertNotIn("PRIVATE", str(error.exception))
        self.assertEqual(p.receipts[0]["transport_elapsed_ns"], 80)
        self.assertEqual(p.receipts[0]["status"], "outcome_unknown")
        with self.assertRaisesRegex(ValueError, "budget"):
            p.reply(b"task", 100)
        self.assertEqual(p.calls, 1)


class MeasurementJournalTests(unittest.TestCase):
    setUp = ab.ComparisonTests.setUp
    store = ab.ComparisonTests.store
    params = ab.ComparisonTests.params
    observe = ab.ComparisonTests.observe

    def test_rejected_output_measurement_survives_journal_reopen_without_redispatch(self):
        store = self.store()
        store.plan(**self.params(model=MODEL, tasks=ab.tasks(1)))
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=1,
                                transport=lambda *a, **kw: runtime.envelope("x" * 65))
        with patch("agent_sleep_lab.mimo_provider.time.monotonic_ns", side_effect=[100, 700]):
            with self.assertRaises(ValueError):
                store.run("plan-1", p, ab.evaluator, self.observe)
        store.close()
        reopened = self.store()
        report = reopened.report("plan-1", self.observe)
        receipt = report["provider_receipts"][0]["receipt"]
        self.assertEqual(receipt["transport_elapsed_ns"], 600)
        self.assertEqual(receipt["output_bytes"], 65)
        self.assertEqual(report["outcomes"]["A"]["unknown"], 1)
        reopened.run("plan-1", p, ab.evaluator, self.observe)
        self.assertEqual(p.calls, 1)
