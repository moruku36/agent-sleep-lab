"""Three bounded fictional scenarios, mocked CLI only; no live calls."""
from dataclasses import replace
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import test_public_document_sleep as fixtures
from agent_sleep_lab.public_document_model import (
    InvocationPermission, invoke_stage, inspect_journal,
)
from agent_sleep_lab.provenance import canonical_json, sha256_hex
from agent_sleep_lab.public_document_runtime import EMPTY_HEAD


class PublicDocumentModelTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.PublicDocumentSleepTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.preparation = dict(sleep_id="night", scope=self.f.scope,
                                expected_generation=1, expected_parent=EMPTY_HEAD,
                                limits=self.f.limits)
        self.journal = Path(self.f.path).with_suffix(".calls.sqlite")
        self.request = self.f.prepare()

    def permission(self, request):
        return InvocationPermission(sha256_hex(request), "fictional-agent",
                                    True, True, 32768, 10)

    def invoke(self, stage="light", **kwargs):
        return invoke_stage(store=self.f.store, preparation=self.preparation,
                            stage=stage, journal_path=self.journal, **kwargs)

    @staticmethod
    def envelope(reply):
        return subprocess.CompletedProcess([], 0, canonical_json({
            "ok": True, "provider": "xiaomi", "model": "mimo-v2.6-pro",
            "attempts": [], "transport": "local",
            "outputs": [{"text": reply.decode("utf-8")}],
        }), b"")

    def test_two_stages_remain_unverified_and_exactly_observed(self):
        light = self.f.light_reply(self.request)
        deep_request = self.f.store.submit_light_result(
            sleep_id="night", expected_request_sha256=sha256_hex(self.request),
            result_bytes=light)
        deep = self.f.deep_reply(deep_request)
        with patch("agent_sleep_lab.public_document_model.subprocess.run",
                   side_effect=[self.envelope(light), self.envelope(deep)]) as cli:
            actual_light, _ = self.invoke(permission=self.permission(self.request))
            actual_deep, _ = self.invoke("deep", permission=self.permission(deep_request),
                                        light_result_bytes=actual_light)
        result = self.f.store.submit_deep_result(
            sleep_id="night", expected_request_sha256=sha256_hex(deep_request),
            result_bytes=actual_deep)
        self.assertEqual(result["state"], "unverified_proposals")
        counts = self.f.db_counts()
        self.assertEqual((counts["reviews"], counts["operations"]), (0, 0))
        receipts = inspect_journal(self.journal)
        for receipt in receipts:
            self.assertEqual(receipt["status"], "returned_valid_untrusted")
            self.assertIsNone(receipt["transport_receipt"]["cost"])
            self.assertEqual(receipt["transport_receipt"]["usage_state"], "not_observed")
        for call, request in zip(cli.call_args_list, (self.request, deep_request)):
            prompt = call.args[0][-1].encode("utf-8")
            observed = next(r for r in receipts if r["request_sha256"] == sha256_hex(request))
            self.assertEqual(observed["cli_prompt_sha256"], sha256_hex(prompt))
            self.assertIn(request, prompt)
            self.assertEqual(call.args[0][7], "xiaomi/mimo-v2.6-pro")

    def test_timeout_is_durable_and_new_sleep_id_cannot_redispatch(self):
        with patch("agent_sleep_lab.public_document_model.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("fake", 10)) as cli:
            with self.assertRaises(RuntimeError):
                self.invoke(permission=self.permission(self.request))
            self.preparation["sleep_id"] = "different"
            changed = self.f.store.prepare_sleep(**self.preparation)
            with self.assertRaisesRegex(ValueError, "already reserved"):
                self.invoke(permission=self.permission(changed))
        self.assertEqual(cli.call_count, 1)
        receipt = inspect_journal(self.journal)[0]
        self.assertEqual(receipt["status"], "outcome_unknown")
        self.assertIsNotNone(receipt["transport_receipt"]["transport_elapsed_ns"])

    def test_document_text_cannot_supply_permission(self):
        permission = replace(self.permission(self.request), allow_paid_call=False)
        with patch("agent_sleep_lab.public_document_model.subprocess.run") as cli:
            with self.assertRaisesRegex(ValueError, "permission required"):
                self.invoke(permission=permission)
        cli.assert_not_called()
        self.assertFalse(self.journal.exists())
