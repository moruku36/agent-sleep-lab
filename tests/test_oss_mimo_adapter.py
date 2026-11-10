"""Exact-prompt adapter contracts; injected transport only, no inference.

Capture documents below are test-authored stand-ins, NOT target execution.
"""
import copy
import subprocess
import unittest

import support  # noqa: F401
import test_oss_prompt_capture as fixtures
from agent_sleep_lab import oss_mimo_adapter as adapter
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_prompt_capture_worker as child


def envelope(text="合成返答", **changes):
    result = dict(ok=True, provider="xiaomi", model="mimo-v2.6-pro", attempts=[],
                  outputs=[dict(text=text, mediaUrl=None)])
    result.update(changes)
    return result


class Transport:
    def __init__(self, result=None, error=None):
        self.result = envelope() if result is None else result
        self.error = error
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if self.error is not None:
            raise self.error
        return subprocess.CompletedProcess(argv, 0, worker.encoded(self.result), b"private stderr")


class OSSMimoAdapterTests(unittest.TestCase):
    def setUp(self):
        helper = fixtures.PromptCaptureTests()
        self.reference = helper.reference()
        self.doc = helper.output()
        notes = child.reference_notes(self.reference)
        for arm in ("baseline", "reference"):
            item = self.doc["arms"][arm]
            payload = copy.deepcopy(item["payload"])
            payload["messages"][0]["content"] += "\n日本語 café  spacing\n"
            self.doc["arms"][arm] = child.arm_artifact(
                arm, child.MOCK_URL, item["header_names"], payload,
                "" if arm == "baseline" else notes)
        self.doc["comparability"] = child.comparability(
            self.doc["arms"]["baseline"]["payload"],
            self.doc["arms"]["reference"]["payload"], notes)

    def make(self, transport, **changes):
        options = dict(agent="synthetic-agent", max_calls=2,
                       acknowledge_paid_execution=True,
                       acknowledge_uncapped_generation=True, transport=transport)
        options.update(changes)
        return adapter.OSSMimoAdapter(**options)

    def run_arm(self, instance, arm="reference", **changes):
        options = dict(reference=self.reference, arm=arm, max_output_bytes=4096)
        options.update(changes)
        return instance.complete(self.doc, **options)

    def test_exact_unicode_prompts_and_sanitized_request_source_receipts(self):
        transport = Transport()
        instance = self.make(transport)
        for arm in ("baseline", "reference"):
            reply, receipt = self.run_arm(instance, arm)
            argv, kwargs = transport.calls[-1]
            self.assertEqual(argv[argv.index("--prompt") + 1],
                             child.prompt_of(self.doc["arms"][arm]["payload"]))
            self.assertEqual(argv[argv.index("--model") + 1], "xiaomi/mimo-v2.6-pro")
            self.assertEqual(kwargs, dict(capture_output=True, timeout=120, check=False))
            self.assertEqual(reply, "合成返答".encode())
            self.assertEqual(receipt["request_sha256"], self.doc["arms"][arm]["request_sha256"])
            self.assertEqual(receipt["prompt_sha256"], self.doc["arms"][arm]["prompt_sha256"])
            self.assertEqual(receipt["capture_document_sha256"], worker.digest(worker.encoded(self.doc)))
            self.assertEqual(receipt["source_sha256"], dict(worker.SOURCE_HASHES))
            self.assertEqual(receipt["task_sha256"], self.doc["task_sha256"])
            self.assertEqual(receipt["reference_sha256"], worker.digest(self.reference))
            self.assertEqual(receipt["output_sha256"], worker.digest(reply))
            self.assertEqual(receipt["transport"], adapter.TRANSPORT_TEST)
            self.assertEqual((receipt["provider"], receipt["model"]), ("xiaomi", "mimo-v2.6-pro"))
            self.assertFalse(receipt["http_wire_equivalent"])
            self.assertIsNone(receipt["verdict"])
            self.assertNotIn("private stderr", repr(receipt))
        self.assertEqual(len(transport.calls), 2)
        with self.assertRaisesRegex(adapter.AdapterError, "budget"):
            self.run_arm(instance)
        self.assertEqual(len(transport.calls), 2)

    def test_strict_acknowledgments_and_constructor_budgets_reject_without_dispatch(self):
        transport = Transport()
        for changes in [
            dict(acknowledge_paid_execution=False), dict(acknowledge_paid_execution=1),
            dict(acknowledge_uncapped_generation="yes"), dict(max_calls=True),
            dict(max_calls=3), dict(timeout=121), dict(timeout=float("nan")),
            dict(max_request_bytes=0), dict(agent="bad --argument"),
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.make(transport, **changes)
        self.assertEqual(transport.calls, [])

    def test_full_capture_bindings_and_input_bounds_fail_before_reservation(self):
        transport = Transport()
        original = copy.deepcopy(self.doc)
        instance = self.make(transport)
        for field, value in [
            ("reference_sha256", "0" * 64), ("task_sha256", "0" * 64),
            ("executed_source_sha256", {}), ("dispatch_authorization", True),
        ]:
            self.doc = copy.deepcopy(original)
            self.doc[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_arm(instance)
        self.doc = copy.deepcopy(original)
        self.doc["arms"]["reference"]["payload"]["messages"][0]["content"] += "tamper"
        with self.assertRaises(ValueError):
            self.run_arm(instance)
        self.doc = original
        for options in [dict(reference=self.reference + b" "), dict(arm="other"),
                        dict(max_output_bytes=True), dict(max_output_bytes=65537)]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.run_arm(instance, **options)
        with self.assertRaises(ValueError):
            self.run_arm(self.make(transport, max_request_bytes=16))
        self.assertEqual((instance.calls, instance.stopped, transport.calls), (0, False, []))

    def test_mismatch_fallback_malformed_and_oversized_outcomes_permanently_stop(self):
        for result in [
            envelope(provider="other"), envelope(model="other"), envelope(ok=1),
            envelope(attempts=[dict(model="fallback")]), envelope(attempts=None),
            envelope(outputs=[]), envelope(outputs=[dict(text="x", mediaUrl="private")]),
            envelope(text=""), envelope(text="x" * 4097),
        ]:
            with self.subTest(result_kind=list(result)):
                transport = Transport(result)
                instance = self.make(transport)
                with self.assertRaises(adapter.AdapterError):
                    self.run_arm(instance)
                self.assertTrue(instance.stopped)
                with self.assertRaises(adapter.AdapterError):
                    self.run_arm(instance)
                self.assertEqual(len(transport.calls), 1)
                self.assertEqual(instance.receipts[0]["status"], "outcome_unknown")
                self.assertNotIn("outputs", instance.receipts[0])

    def test_timeout_and_interrupt_reserve_once_and_do_not_expose_private_errors(self):
        for error in (TimeoutError("private-account"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                transport = Transport(error=error)
                instance = self.make(transport)
                expected = adapter.AdapterError if isinstance(error, Exception) else KeyboardInterrupt
                with self.assertRaises(expected) as seen:
                    self.run_arm(instance)
                self.assertNotIn("private-account", str(seen.exception))
                self.assertTrue(instance.stopped)
                with self.assertRaises(adapter.AdapterError):
                    self.run_arm(instance)
                self.assertEqual((instance.calls, len(transport.calls)), (1, 1))

    def test_unavailable_usage_cost_and_unrecognized_metadata_are_not_fabricated_or_copied(self):
        for result in [envelope(), envelope(usage=dict(account="private-account"),
                                           cost=dict(token="private-value"))]:
            transport = Transport(result)
            reply, receipt = self.run_arm(self.make(transport))
            self.assertEqual((receipt["usage"], receipt["cost"]), ("unavailable", "unavailable"))
            self.assertEqual((receipt["generation_token_cap"], receipt["monetary_cap"]), (None, None))
            self.assertNotIn("private-account", repr(receipt))
            self.assertNotIn("private-value", repr(receipt))
            self.assertTrue(reply)
