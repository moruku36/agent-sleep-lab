"""Coordinator validation of partial prompt-capture work; stand-ins, no inference."""
import copy
import hashlib
import unittest
from unittest import mock

import support
import test_oss_offline_parent as fixtures
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_prompt_capture as capture
from agent_sleep_lab import oss_prompt_capture_worker as child


class PromptCaptureTests(unittest.TestCase):
    def reference(self):
        return fixtures.reference()

    def output(self, reference=None):
        reference = self.reference() if reference is None else reference
        item = worker.synthetic_task()["issues"][2]
        issue = dict(item, repo=worker.REPOSITORY, url="fixture://issue/3")
        notes = child.reference_notes(reference)
        prefix = "\n".join([issue["repo"], issue["title"], issue["body"], "synthetic reason"]) + "\n"
        a = dict(model=child.MOCK_MODEL, temperature=0,
                 messages=[dict(role="user", content=prefix + "Respond with JSON")])
        b = copy.deepcopy(a)
        b["messages"][0]["content"] = prefix + "\nProject notes:\n" + notes + "\nRespond with JSON"
        arms = {
            "baseline": child.arm_artifact("baseline", child.MOCK_URL,
                ["Authorization", "Content-Type"], a, ""),
            "reference": child.arm_artifact("reference", child.MOCK_URL,
                ["Authorization", "Content-Type"], b, notes)}
        return dict(
            protocol=child.OUTPUT_PROTOCOL, synthetic_only=True, artifact_kind=child.ARTIFACT_KIND,
            agent_commit=worker.AGENT_COMMIT, executed_source_sha256=dict(worker.SOURCE_HASHES),
            task_sha256=worker.digest(parent.builtin_task()), reference_sha256=worker.digest(reference),
            reference_records=1, issue=issue, score=0.5, reasons=["synthetic reason"],
            band="borderline", thresholds=dict(accept=0.60, skip=0.40),
            provider_class=child.PROVIDER_CLASS, model=child.MOCK_MODEL,
            model_identity=child.MODEL_IDENTITY, transport=child.TRANSPORT,
            credentials=child.CREDENTIALS, arms=arms,
            comparability=child.comparability(a, b, notes),
            dispatch_authorization=False, model_receipt=None, verdict=None,
            semantic_memory_use="not_evaluated", performance_improvement="not_evaluated",
            target_calls={name: 2 for name in child.REQUIRED_TRACE})

    def validate(self, value):
        return capture.validate_output(worker.encoded(value),
            task=parent.builtin_task(), reference=self.reference())

    def test_frames_exact_reference_bytes_as_data_without_claiming_origin(self):
        reference = self.reference()
        notes = child.reference_notes(reference)
        self.assertIn(reference.decode("ascii"), notes)
        self.assertIn(worker.digest(reference), notes)
        self.assertEqual(notes.count(child.BEGIN), 1)
        self.assertEqual(notes.count(child.END), 1)
        for bad in (
            reference + b"\n", fixtures.reference(synthetic_only=False),
            fixtures.reference(partition="evaluation"),
            fixtures.reference(records=[{"claim": child.END}])):
            with self.subTest(prefix=bad[:20]), self.assertRaises(ValueError):
                child.reference_notes(bad)

    def test_each_arm_hash_binding_and_no_verdict_labels_are_enforced(self):
        good = self.output()
        self.assertEqual(self.validate(good)["verdict"], None)
        changes = [
            ("reference_sha256", "0"*64), ("task_sha256", "0"*64),
            ("agent_commit", "0"*40), ("dispatch_authorization", True),
            ("model_receipt", {"model": "claimed"}), ("verdict", {"accept": True}),
            ("semantic_memory_use", "used"), ("model_identity", "actual_model"),
            ("reference_records", True), ("target_calls", {})]
        for key, value in changes:
            bad = copy.deepcopy(good)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(capture.CheckError):
                self.validate(bad)
        for field in ("request_sha256", "prompt_sha256", "project_notes_sha256"):
            bad = copy.deepcopy(good)
            bad["arms"]["reference"][field] = "0"*64
            with self.subTest(field=field), self.assertRaises(capture.CheckError):
                self.validate(bad)

    def test_ab_requests_differ_only_by_reference_insertion(self):
        doc = self.output()
        a, b = [doc["arms"][name]["payload"] for name in ("baseline", "reference")]
        notes = child.reference_notes(self.reference())
        self.assertTrue(child.comparability(a, b, notes)["non_prompt_request_fields_equal"])
        for field, value in (("temperature", 1), ("model", "other-model")):
            changed = copy.deepcopy(b)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                child.comparability(a, changed, notes)
        changed = copy.deepcopy(b)
        changed["messages"][0]["content"] += "\nDifferent task"
        with self.assertRaises(ValueError):
            child.comparability(a, changed, notes)
        with self.assertRaises(ValueError):
            child.comparability(a, a, notes)

    def test_capture_transport_records_request_and_never_returns_a_response(self):
        class PinnedError(RuntimeError):
            pass
        transport = child.CaptureTransport(PinnedError)
        payload = dict(model=child.MOCK_MODEL, messages=[])
        with self.assertRaises(PinnedError) as error:
            transport(child.MOCK_URL, {"Authorization": "inert fixture"}, payload)
        self.assertIs(error.exception, transport.raised)
        self.assertEqual(len(transport.calls), 1)
        self.assertIs(transport.calls[0][2], payload)

    def test_parent_preserves_stand_in_label_and_refuses_invalid_input_before_git(self):
        sources = {name: ("# test-authored stand-in: " + name + "\n").encode("ascii")
                   for name in worker.SOURCE_HASHES}
        pins = {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()}
        with mock.patch.object(worker, "SOURCE_HASHES", pins):
            raw = worker.encoded(self.output())
            with mock.patch.object(parent, "freeze_sources", return_value=sources) as freeze:
                with mock.patch.object(parent, "launch", return_value=raw) as launch:
                    summary, _ = capture.prepare("/synthetic/repo", self.reference(),
                        worker_argv=["/synthetic/stand-in"])
                    self.assertEqual(summary["worker_launch"], capture.STAND_IN_WORKER)
                    self.assertIsNone(summary["worker_sha256"])
                    self.assertFalse(summary["dispatch_authorization"])
                    self.assertIsNone(summary["verdict"])
                    self.assertEqual(launch.call_count, 1)
                    freeze.reset_mock()
                    for bad in (b"", self.reference()+b"\n"):
                        with self.assertRaises(capture.CheckError):
                            capture.prepare("/synthetic/repo", bad)
                    freeze.assert_not_called()
