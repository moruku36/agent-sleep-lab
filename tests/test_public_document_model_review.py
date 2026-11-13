"""Two distinct independent-review checks; mocked fictional bytes only."""
from dataclasses import replace
import unittest
from unittest.mock import patch
import test_public_document_model as fixtures
from agent_sleep_lab.public_document_model import inspect_journal

class PublicDocumentModelReviewTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.PublicDocumentModelTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_host_hash_mismatch_never_reserves_or_dispatches(self):
        permission = replace(self.f.permission(self.f.request), request_sha256="0" * 64)
        with patch("agent_sleep_lab.public_document_model.subprocess.run") as cli:
            with self.assertRaisesRegex(ValueError, "permission or prompt bound mismatch"):
                self.f.invoke(permission=permission)
        cli.assert_not_called()
        self.assertFalse(self.f.journal.exists())

    def test_returned_invalid_protocol_remains_reserved(self):
        with patch("agent_sleep_lab.public_document_model.subprocess.run",
                   return_value=self.f.envelope(b"{}")) as cli:
            with self.assertRaises(ValueError):
                self.f.invoke(permission=self.f.permission(self.f.request))
            with self.assertRaisesRegex(ValueError, "already reserved"):
                self.f.invoke(permission=self.f.permission(self.f.request))
        self.assertEqual(cli.call_count, 1)
        receipt, = inspect_journal(self.f.journal)
        self.assertEqual(receipt["status"], "returned_invalid")
        self.assertEqual(receipt["transport_receipt"]["status"], "returned")
        self.assertEqual(receipt["transport_receipt"]["output_bytes"], 2)
