"""Adopted SYNTHETIC memory -> current-policy retrieval -> offline paired prompt preparation.

Temporary adoption-store fixtures only. Every verifier/evaluator receipt and
adoption here is TEST-AUTHORED fixture data, never a production memory or
receipt. The worker is a labelled stand-in that only frames the delivered
reference bytes: no target source, provider, model verdict or performance
claim, and no store-origin authentication or semantic memory use.
"""
import copy
import hashlib
from unittest import mock

import support  # noqa: F401  (test path setup)
import test_adoption_store as store_fixtures
import test_retrieval as retrieval_fixtures
from evidence_support import StoreCase, make_item
from runtime_support import make_control, policy_body
from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_prompt_capture as capture
from agent_sleep_lab import oss_prompt_capture_worker as child
from agent_sleep_lab.oss_bridge import CollectOnlyBridge

SCOPE = {"project": "p", "task_family": "t"}
OTHER = {"project": "q", "task_family": "u"}
CLAIM = "重複確認を先に行う café duplicate checks"
OTHER_CLAIM = "別scopeの重複確認 duplicate checks"
TABLES = ("evidence", "receipts", "adoption_journal", "adoption_memories")


class AdoptedReferencePreparationTests(StoreCase):
    # Borrow fixture helpers only; the owning classes' cases are not collected here.
    open_adoption = store_fixtures.AdoptionTests.open_adoption
    setup_store = store_fixtures.AdoptionTests.setup_store
    adopt = retrieval_fixtures.RetrievalTests.adopt

    def setUp(self):
        super().setUp()
        self.store = self.setup_store()  # policy revision 1, e-1 captured
        self.sources = {name: ("# test-authored stand-in: " + name + "\n").encode("ascii")
                        for name in worker.SOURCE_HASHES}
        self.pins = {name: hashlib.sha256(data).hexdigest()
                     for name, data in self.sources.items()}
        self.delivered = []

    def bridge(self, scope=SCOPE):
        return CollectOnlyBridge(self.store, scope=scope, repository=worker.REPOSITORY,
                                 agent_commit=worker.AGENT_COMMIT)

    def stand_in(self, argv, payload, timeout=None):
        """Labelled stand-in worker: frames the delivered bytes, returns no verdict."""
        reference = bytes.fromhex(worker.strict_json(payload)["reference_hex"])
        self.delivered.append(reference)
        item = worker.synthetic_task()["issues"][2]
        issue = dict(item, repo=worker.REPOSITORY, url="fixture://issue/3")
        notes = child.reference_notes(reference)
        prefix = "\n".join([issue["repo"], issue["title"], issue["body"], "synthetic reason"]) + "\n"
        a = dict(model=child.MOCK_MODEL, temperature=0,
                 messages=[dict(role="user", content=prefix + "Respond with JSON")])
        b = copy.deepcopy(a)
        b["messages"][0]["content"] = prefix + "\nProject notes:\n" + notes + "\nRespond with JSON"
        names = ["Authorization", "Content-Type"]
        return worker.encoded(dict(
            protocol=child.OUTPUT_PROTOCOL, synthetic_only=True, artifact_kind=child.ARTIFACT_KIND,
            agent_commit=worker.AGENT_COMMIT, executed_source_sha256=dict(worker.SOURCE_HASHES),
            task_sha256=worker.digest(parent.builtin_task()),
            reference_sha256=worker.digest(reference),
            reference_records=len(worker.validate_reference(reference)["records"]),
            issue=issue, score=0.5, reasons=["synthetic reason"], band="borderline",
            thresholds=dict(accept=0.60, skip=0.40), provider_class=child.PROVIDER_CLASS,
            model=child.MOCK_MODEL, model_identity=child.MODEL_IDENTITY,
            transport=child.TRANSPORT, credentials=child.CREDENTIALS,
            arms={"baseline": child.arm_artifact("baseline", child.MOCK_URL, names, a, ""),
                  "reference": child.arm_artifact("reference", child.MOCK_URL, names, b, notes)},
            comparability=child.comparability(a, b, notes),
            dispatch_authorization=False, model_receipt=None, verdict=None,
            semantic_memory_use="not_evaluated", performance_improvement="not_evaluated",
            target_calls={name: 2 for name in child.REQUIRED_TRACE}))

    def state(self):
        return ([self.count(table) for table in TABLES],
                self.store.current_policy().revision,
                self.store.current_snapshot(SCOPE), self.store.current_snapshot(OTHER),
                self.store._db().total_changes)

    def patched(self):
        stack = mock.patch.object(worker, "SOURCE_HASHES", self.pins)
        freeze = mock.patch.object(parent, "freeze_sources", return_value=self.sources)
        launch = mock.patch.object(parent, "launch", side_effect=self.stand_in)
        return stack, freeze, launch

    def prepare(self, bridge, query="重複 duplicate"):
        """prepare_from_bridge with a stand-in worker; asserts the store is not mutated."""
        pins, freeze, launch = self.patched()
        with pins, freeze, launch as launched:
            before = self.state()
            summary, doc = capture.prepare_from_bridge(
                bridge, self.dir, query=query, max_bytes=worker.MAX_REFERENCE_BYTES,
                worker_argv=["/synthetic/stand-in"])
            self.assertEqual(self.state(), before)  # preparation writes nothing
            self.assertEqual(launched.call_count, 1)
            raw = worker.encoded(doc)
        self.assertTrue(raw.isascii())  # worker protocol output stays canonical ASCII
        self.assertEqual(summary["worker_output_sha256"], worker.digest(raw))
        self.assertEqual(summary["worker_launch"], capture.STAND_IN_WORKER)
        self.assertEqual(summary["reference_origin"], capture.ORIGIN_BRIDGE)
        self.assertEqual((summary["dispatch_authorization"], summary["verdict"],
                          summary["model_receipt"], summary["semantic_memory_use"],
                          summary["performance_improvement"], summary["delivery_and_use_verified"]),
                         (False, None, None, "not_evaluated", "not_evaluated", False))
        return summary, doc

    def prompts(self, doc):
        return [child.prompt_of(doc["arms"][name]["payload"])
                for name in ("baseline", "reference")]

    def test_nonempty_unicode_adopted_reference_is_framed_byte_exact_in_reference_arm_only(self):
        self.adopt(self.store, "m-1", "e-1", claim=CLAIM)
        expected = self.bridge().reference_context(
            query="重複 duplicate", max_bytes=worker.MAX_REFERENCE_BYTES)
        self.assertEqual([r["memory_id"] for r in expected.document["records"]], ["m-1"])
        self.assertEqual(expected.document["records"][0]["eligibility"], "verified")
        self.assertFalse(expected.bundle_bytes.isascii())
        self.assertIn(CLAIM.encode("utf-8"), expected.bundle_bytes)  # raw UTF-8, not escaped
        self.assertNotEqual(worker.encoded(expected.document), expected.bundle_bytes)

        summary, doc = self.prepare(self.bridge())
        # Exact retrieval bytes reach the worker payload; the hash is of those bytes.
        self.assertEqual(self.delivered, [expected.bundle_bytes])
        self.assertEqual(summary["reference_sha256"], expected.bundle_sha256)
        self.assertEqual(summary["reference_records"], 1)
        notes = child.reference_notes(expected.bundle_bytes)
        baseline, reference = self.prompts(doc)
        self.assertEqual(reference.count(expected.bundle_bytes.decode("utf-8")), 1)
        self.assertIn(expected.bundle_sha256, reference)
        self.assertNotIn(CLAIM, baseline)
        self.assertNotIn(child.BEGIN, baseline)
        # Comparability: one contiguous insertion holding the notes, same other fields.
        arms, relation = summary["arms"], summary["comparability"]
        self.assertEqual(relation, child.comparability(
            doc["arms"]["baseline"]["payload"], doc["arms"]["reference"]["payload"], notes))
        self.assertEqual(relation["relation"], child.RELATION)
        self.assertTrue(relation["non_prompt_request_fields_equal"])
        self.assertGreaterEqual(relation["inserted_bytes"], len(notes.encode("utf-8")))
        self.assertEqual(arms["reference"]["prompt_bytes"] - arms["baseline"]["prompt_bytes"],
                         relation["inserted_bytes"])  # UTF-8 bytes, not characters
        self.assertEqual(arms["reference"]["project_notes_sha256"],
                         worker.digest(notes.encode("utf-8")))
        self.assertEqual(arms["baseline"]["project_notes_sha256"], worker.digest(b""))

    def test_current_exclusion_and_other_scope_never_reach_the_prompt(self):
        self.put(self.store, make_item("e-9", scope=("q", "u")))
        self.adopt(self.store, "m-1", "e-1", claim=CLAIM)
        self.adopt(self.store, "m-9", "e-9", scope=OTHER, claim=OTHER_CLAIM)

        summary, doc = self.prepare(self.bridge())  # scope p/t sees only its own memory
        self.assertEqual(summary["reference_records"], 1)
        reference = self.prompts(doc)[1]
        self.assertIn(CLAIM, reference)
        self.assertNotIn(OTHER_CLAIM, reference)
        self.assertNotIn("m-9", reference)

        summary, doc = self.prepare(self.bridge(OTHER))
        self.assertEqual(summary["reference_records"], 1)
        reference = self.prompts(doc)[1]
        self.assertIn(OTHER_CLAIM, reference)
        self.assertNotIn(CLAIM, reference)

        # Current policy excludes m-1: the historical head is not permission.
        self.store.set_policy(make_control(), policy_body(memory_ids=("m-1",)),
                              expected_revision=1)
        summary, doc = self.prepare(self.bridge())
        self.assertEqual(summary["reference_records"], 0)
        bundle = worker.validate_reference(self.delivered[-1])
        self.assertEqual(bundle["counts"],
                         {"active_members": 1, "eligible": 0, "returned": 0, "dropped": 0})
        self.assertEqual(bundle["policy"]["revision"], 2)
        for prompt in self.prompts(doc):
            self.assertNotIn(CLAIM, prompt)
            self.assertNotIn("m-1", prompt)
        self.assertNotEqual(*self.prompts(doc))  # the empty bundle is still framed

    def test_noncanonical_or_malformed_unicode_reference_fails_closed_before_git_or_launch(self):
        self.adopt(self.store, "m-1", "e-1", claim=CLAIM)
        good = self.bridge().reference_context(
            query="重複", max_bytes=worker.MAX_REFERENCE_BYTES).bundle_bytes
        doc = worker.strict_json(good)
        self.assertEqual(worker.canonical_reference(doc), good)
        first = "重".encode("utf-8")
        marked, astral, big = copy.deepcopy(doc), copy.deepcopy(doc), copy.deepcopy(doc)
        marked["records"][0]["memory"]["claim"] = "重複 " + child.END
        astral["records"][0]["memory"]["claim"] = "重複 🧪"
        big["records"][0]["memory"]["claim"] = "重" * worker.MAX_REFERENCE_BYTES
        # Non-BMP text is accepted in the one canonical form and framed unescaped.
        self.assertIn("🧪", child.reference_notes(worker.canonical_reference(astral)))
        bad = {
            "ascii_escaped": worker.encoded(doc),
            "astral_escaped": worker.encoded(astral),
            "respaced": good.replace(b'","', b'", "', 1),
            "trailing_newline": good + b"\n",
            "bom": b"\xef\xbb\xbf" + good,
            "invalid_utf8": good.replace(first, first[:2], 1),
            "lone_surrogate": good.replace(first, b"\\ud800", 1),
            "duplicate_key": good[:-1] + b',"synthetic_only":true}',
            "frame_marker": worker.canonical_reference(marked),
            "oversize": worker.canonical_reference(big),
            "empty": b"",
        }
        self.assertGreater(len(bad["oversize"]), worker.MAX_REFERENCE_BYTES)
        pins, freeze, launch = self.patched()
        with pins, freeze as frozen, launch as launched:
            for label, data in bad.items():
                self.assertNotEqual(data, good)
                with self.subTest(case=label):
                    with self.assertRaises(ValueError):
                        child.reference_notes(data)
                    with self.assertRaises(capture.CheckError):
                        capture.prepare(self.dir, data, worker_argv=["/synthetic/stand-in"])
                    if label not in ("empty", "frame_marker"):  # framing is prompt-specific
                        with self.assertRaises(capture.CheckError):
                            parent.prepare_payload(self.sources, data)
            frozen.assert_not_called()
            launched.assert_not_called()
            # Output validation is bound to the exact reference bytes it is given.
            raw = self.stand_in([], parent.prepare_payload(self.sources, good))
            capture.validate_output(raw, task=parent.builtin_task(), reference=good)
            with self.assertRaises(capture.CheckError):
                capture.validate_output(raw, task=parent.builtin_task(),
                                        reference=worker.canonical_reference(astral))
