"""Offline paired-outcome journal over captured OSS prompt artifacts.

Temporary adoption store and temporary private journal only. Every
verifier/evaluator receipt and adoption is a TEST-AUTHORED fixture. The capture
worker is a mocked, labelled stand-in for the pinned worker; no target source
runs. Replies come from ``FakeReplyProvider`` and are test-authored synthetic
bytes: not model receipts, verdicts, usage, cost or performance evidence.
"""
import copy
import hashlib
import os
import sqlite3
from unittest import mock

import support  # noqa: F401  (test path setup)
import test_adoption_store as store_fixtures
import test_retrieval as retrieval_fixtures
from evidence_support import StoreCase
from runtime_support import make_control, policy_body
from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_paired_outcome as paired
from agent_sleep_lab import oss_prompt_capture as capture
from agent_sleep_lab import oss_prompt_capture_worker as child
from agent_sleep_lab.oss_bridge import CollectOnlyBridge

SCOPE = {"project": "p", "task_family": "t"}
OTHER = {"project": "q", "task_family": "u"}
CLAIM = "重複確認を先に行う café duplicate checks"
QUERY = "重複 duplicate"
REPLIES = {"baseline": "合成返答A synthetic test-authored".encode("utf-8"),
           "reference": "合成返答B synthetic test-authored".encode("utf-8")}


class PairedOutcomeJournalTests(StoreCase):
    # Borrow fixture helper functions only; the owning classes' cases are not collected here.
    open_adoption = store_fixtures.AdoptionTests.open_adoption
    setup_store = store_fixtures.AdoptionTests.setup_store
    adopt = retrieval_fixtures.RetrievalTests.adopt

    def setUp(self):
        super().setUp()
        self.store = self.setup_store()  # policy revision 1, e-1 captured
        self.adopt(self.store, "m-1", "e-1", claim=CLAIM)
        self.sources = {name: ("# test-authored stand-in: " + name + "\n").encode("ascii")
                        for name in worker.SOURCE_HASHES}
        pins = {name: hashlib.sha256(data).hexdigest() for name, data in self.sources.items()}
        self.delivered, self.calls = [], []
        for patch in (mock.patch.object(worker, "SOURCE_HASHES", pins),
                      mock.patch.object(parent, "freeze_sources", return_value=self.sources),
                      mock.patch.object(parent, "launch", side_effect=self.stand_in)):
            patch.start()
            self.addCleanup(patch.stop)
        self.bridge = self.make_bridge()
        self.summary, self.doc = capture.prepare_from_bridge(
            self.bridge, self.dir, query=QUERY, max_bytes=worker.MAX_REFERENCE_BYTES,
            worker_argv=["/synthetic/stand-in"])
        self.reference = self.delivered[-1]
        self.journal_path = os.path.join(self.dir, "paired-outcome.sqlite3")
        self.journal = self.open_journal()

    def make_bridge(self, scope=SCOPE):
        return CollectOnlyBridge(self.store, scope=scope, repository=worker.REPOSITORY,
                                 agent_commit=worker.AGENT_COMMIT)

    def open_journal(self):
        journal = paired.PairedOutcomeJournal(self.journal_path)
        self.addCleanup(journal.close)
        return journal

    def stand_in(self, argv, payload, timeout=None):
        """Mocked stand-in for the pinned capture worker: frames bytes, no verdict."""
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

    def provider(self, fail=None, before_reply=None, replies=REPLIES):
        """Fake seam recording every dispatch; replies are test-authored bytes."""
        def reply(arm, request):
            self.calls.append((arm, request))
            if before_reply is not None:
                before_reply(arm)
            if fail is not None and arm in fail:
                raise fail[arm]
            return replies[arm]
        return paired.FakeReplyProvider(reply)

    def register(self, plan_id="plan-1", journal=None, **changes):
        options = dict(summary=self.summary, capture_doc=self.doc, reference=self.reference,
                       bridge=self.bridge, query=QUERY, max_bytes=worker.MAX_REFERENCE_BYTES,
                       max_request_bytes=paired.MAX_REQUEST_BYTES, max_reply_bytes=4096)
        options.update(changes)
        return (journal or self.journal).register(plan_id, **options)

    def exclude_memory(self):
        self.store.set_policy(make_control(), policy_body(memory_ids=("m-1",)),
                              expected_revision=1)

    def arms(self, report):
        return [report["arms"][name]["status"] for name in paired.ARMS]

    def test_captured_unicode_requests_are_frozen_and_dispatched_byte_exact_with_labels(self):
        self.assertFalse(self.reference.isascii())
        self.assertIn(CLAIM.encode("utf-8"), self.reference)
        report = self.register()
        self.assertEqual((report["plan_status"], self.arms(report)),
                         ("open", ["not_started", "not_started"]))
        frozen = self.journal.frozen("plan-1", self.bridge)
        self.assertEqual(frozen["reference"], self.reference)  # original bytes, not re-encoded
        for name in paired.ARMS:
            arm = self.doc["arms"][name]
            request = worker.encoded(dict(url=arm["url"], header_names=arm["header_names"],
                                          payload=arm["payload"]))
            self.assertEqual(frozen["requests"][name], request)
            self.assertEqual(report["arms"][name]["request_sha256"], arm["request_sha256"])
        report = self.journal.run("plan-1", self.bridge, self.provider())
        # The fake seam received the actual captured request bodies, not substitutes.
        self.assertEqual(self.calls, [(n, frozen["requests"][n]) for n in paired.ARMS])
        baseline, reference = [child.prompt_of(worker.strict_json(body)["payload"])
                               for _, body in self.calls]
        self.assertEqual(reference.count(self.reference.decode("utf-8")), 1)
        self.assertIn(CLAIM, reference)
        self.assertNotIn(CLAIM, baseline)
        self.assertEqual((report["plan_status"], report["pair_outcome"]),
                         ("complete", "both_arms_completed_synthetic_replies"))
        self.assertEqual(report["arm_statuses"],
                         {"baseline": "completed", "reference": "completed"})
        for name in paired.ARMS:
            arm = report["arms"][name]
            self.assertEqual(arm["reply_body"], REPLIES[name].decode("utf-8"))
            self.assertEqual(arm["reply_sha256"], worker.digest(REPLIES[name]))
            self.assertEqual((arm["reply_kind"], arm["usage"], arm["cost"], arm["model_receipt"],
                              arm["verdict"], arm["fake_dispatches"]),
                             (paired.REPLY_KIND, paired.UNAVAILABLE, paired.UNAVAILABLE,
                              None, None, 1))
        # Provenance: exact capture hash, pins, honest stand-in and unauthenticated labels.
        self.assertEqual(report["capture_document_sha256"], self.summary["worker_output_sha256"])
        self.assertEqual(report["capture_document_sha256"],
                         worker.digest(worker.encoded(self.doc)))
        self.assertEqual(report["source"]["agent_commit"], worker.AGENT_COMMIT)
        self.assertEqual(report["source"]["source_sha256"], dict(worker.SOURCE_HASHES))
        self.assertEqual(report["source"]["task_sha256"], worker.digest(parent.builtin_task()))
        self.assertEqual(report["worker"], dict(
            launch=capture.STAND_IN_WORKER, sha256=None,
            target_integration="stand_in_worker_not_target_integration",
            label_origin=paired.SUMMARY_ORIGIN))
        self.assertEqual(report["reference"]["sha256"], worker.digest(self.reference))
        self.assertEqual(report["reference"]["store_origin"], paired.STORE_ORIGIN)
        self.assertEqual(report["retrieval"]["query"], QUERY)
        self.assertEqual(report["bridge"]["scope"], SCOPE)
        self.assertEqual(report["bounds"], dict(
            max_request_bytes_per_arm=paired.MAX_REQUEST_BYTES, max_reply_bytes_per_arm=4096,
            max_calls_per_arm=1, kind=paired.BOUND_KIND))
        self.assertEqual(
            (report["usage"], report["cost"], report["savings"], report["model_receipt"],
             report["verdict"], report["evaluator"], report["adoption"],
             report["performance_improvement"], report["semantic_memory_use"],
             report["live_provider_support"], report["delivery_and_use_verified"]),
            (paired.UNAVAILABLE, paired.UNAVAILABLE, "not_measured", None, None, "not_run",
             "none", "not_evaluated", "not_evaluated", False, False))
        self.assertNotIn(0, (report["usage"], report["cost"]))  # unavailable, never zero

    def test_close_and_reopen_continues_with_one_dispatch_per_arm_and_replays_saved_replies(self):
        self.register()
        report = self.journal.run("plan-1", self.bridge, self.provider(), limit=1)
        self.assertEqual((report["plan_status"], self.arms(report)),
                         ("open", ["completed", "not_started"]))
        self.journal.close()

        reopened = self.open_journal()
        # The first reply was durable before the second arm was ever dispatched.
        saved = reopened.report("plan-1", self.bridge)
        self.assertEqual(saved["arms"]["baseline"]["reply_body"], REPLIES["baseline"].decode())
        self.assertEqual(self.register(journal=reopened)["plan_status"], "open")  # same binding
        report = reopened.run("plan-1", self.bridge, self.provider(), limit=1)
        self.assertEqual((report["plan_status"], self.arms(report)),
                         ("complete", ["completed", "completed"]))
        self.assertEqual([arm for arm, _ in self.calls], ["baseline", "reference"])
        reopened.close()

        again = self.open_journal()
        other = {name: b"a different reply must never replace the saved one" for name in REPLIES}
        replay = again.run("plan-1", self.bridge, self.provider(replies=other))
        self.assertEqual(len(self.calls), 2)  # replay only: no redispatch
        self.assertEqual(replay["arms"], report["arms"])
        self.assertEqual(replay["arms"]["reference"]["fake_dispatches"], 1)

    def test_unknown_outcome_stops_forever_keeps_first_reply_and_is_never_redispatched(self):
        self.register()
        report = self.journal.run("plan-1", self.bridge,
                                  self.provider(fail={"reference": RuntimeError("boom")}))
        self.assertEqual((report["plan_status"], report["stop_reason"], self.arms(report)),
                         ("stopped", "unknown_outcome_reference", ["completed", "unknown"]))
        self.assertEqual(report["pair_outcome"], "incomplete_stopped_no_retry")
        self.assertEqual(report["arms"]["baseline"]["reply_body"], REPLIES["baseline"].decode())
        self.assertIsNone(report["arms"]["reference"]["reply_sha256"])
        self.assertEqual(report["arms"]["reference"]["usage"], paired.UNAVAILABLE)
        self.journal.close()
        reopened = self.open_journal()
        for _ in range(2):  # a healthy provider is still never called again
            later = reopened.run("plan-1", self.bridge, self.provider())
            self.assertEqual(later["arms"], report["arms"])
        self.assertEqual([arm for arm, _ in self.calls], ["baseline", "reference"])

        # Interruption during the first arm: the second arm can never start.
        self.register("plan-2", journal=reopened)
        with self.assertRaises(KeyboardInterrupt):
            reopened.run("plan-2", self.bridge,
                         self.provider(fail={"baseline": KeyboardInterrupt()}))
        later = reopened.run("plan-2", self.bridge, self.provider())
        self.assertEqual((later["plan_status"], later["stop_reason"], self.arms(later)),
                         ("stopped", "unknown_outcome_baseline", ["unknown", "missing"]))
        self.assertEqual(len(self.calls), 3)  # plan-2 baseline only; nothing afterwards

        # Intent committed but no outcome recorded (process died): unknown, no dispatch.
        self.register("plan-3", journal=reopened)
        reopened._db.execute(
            "INSERT INTO arms (plan_id, arm, state, request_sha256) VALUES (?, ?, 'intent', ?)",
            ("plan-3", "baseline", self.doc["arms"]["baseline"]["request_sha256"]))
        seen = reopened.report("plan-3", self.bridge)  # read-only view already says unknown
        self.assertEqual((seen["plan_status"], self.arms(seen)),
                         ("stopped", ["unknown", "missing"]))
        later = reopened.run("plan-3", self.bridge, self.provider())
        self.assertEqual((later["stop_reason"], self.arms(later)),
                         ("interrupted_baseline", ["unknown", "missing"]))
        self.assertEqual(len(self.calls), 3)

    def test_invalidation_between_arms_stops_second_arm_and_withholds_stale_reply_body(self):
        self.register()
        report = self.journal.run("plan-1", self.bridge, self.provider(), limit=1)
        self.assertEqual(report["arms"]["baseline"]["reply_body"], REPLIES["baseline"].decode())
        self.exclude_memory()  # current policy now excludes the adopted memory

        stale = self.journal.report("plan-1", self.bridge)  # recheck on report, before any run
        self.assertEqual(stale["context"], "changed_or_unverifiable")
        self.assertIsNone(stale["arms"]["baseline"]["reply_body"])
        report = self.journal.run("plan-1", self.bridge, self.provider())
        self.assertEqual([arm for arm, _ in self.calls], ["baseline"])  # reference never sent
        self.assertEqual((report["plan_status"], report["stop_reason"], self.arms(report)),
                         ("stopped", "context_changed_before_reference",
                          ["completed", "missing"]))
        baseline = report["arms"]["baseline"]
        self.assertEqual((baseline["reply_body"], baseline["reply_export"]),
                         (None, "withheld_context_changed_hash_and_status_only"))
        self.assertEqual(baseline["reply_sha256"], worker.digest(REPLIES["baseline"]))
        self.assertNotIn(REPLIES["baseline"].decode(), repr(report))
        # The frozen artifact is not authority: a new plan from it is refused, no calls.
        with self.assertRaises(paired.JournalError):
            self.register("plan-2")
        with self.assertRaises(paired.JournalError):
            self.journal.report("plan-2", self.bridge)
        self.assertEqual(len(self.calls), 1)

    def test_context_revoked_while_reply_returns_is_invalidated_without_storing_the_body(self):
        self.register()
        report = self.journal.run(
            "plan-1", self.bridge, self.provider(before_reply=lambda arm: self.exclude_memory()))
        self.assertEqual([arm for arm, _ in self.calls], ["baseline"])
        self.assertEqual((report["plan_status"], report["stop_reason"], self.arms(report)),
                         ("stopped", "context_changed_after_baseline",
                          ["invalidated", "missing"]))
        baseline = report["arms"]["baseline"]
        self.assertEqual((baseline["reply_body"], baseline["reply_sha256"], baseline["detail"]),
                         (None, worker.digest(REPLIES["baseline"]),
                          "context_changed_after_reply"))
        stored = self.journal._db.execute("SELECT reply FROM arms").fetchall()
        self.assertEqual(stored, [(None,)])  # hash/status only; body was never persisted
        self.journal.run("plan-1", self.bridge, self.provider())
        self.assertEqual(len(self.calls), 1)

    def test_unavailable_context_stops_remaining_dispatches_permanently(self):
        self.register()
        self.journal.run("plan-1", self.bridge, self.provider(), limit=1)
        with mock.patch.object(self.bridge, "reference_context", side_effect=RuntimeError("unavailable")):
            report = self.journal.run("plan-1", self.bridge, self.provider())
            self.assertEqual(report["stop_reason"], "context_changed_before_reference")
            self.assertIsNone(report["arms"]["baseline"]["reply_body"])
        report = self.journal.run("plan-1", self.bridge, self.provider())
        self.assertEqual(report["plan_status"], "stopped")
        self.assertEqual([arm for arm, _ in self.calls], ["baseline"])

    def test_database_identity_durability_and_saved_reply_integrity(self):
        foreign_path = os.path.join(self.dir, "foreign.sqlite")
        with sqlite3.connect(foreign_path) as db:
            db.execute("PRAGMA application_id=1234")
        with self.assertRaises(paired.JournalError):
            paired.PairedOutcomeJournal(foreign_path)
        with sqlite3.connect(foreign_path) as db:
            self.assertEqual(db.execute("PRAGMA application_id").fetchone()[0], 1234)
            self.assertEqual(db.execute("SELECT name FROM sqlite_master").fetchall(), [])
        self.assertEqual(self.journal._db.execute("PRAGMA synchronous").fetchone()[0], 2)
        self.assertEqual(self.journal._db.execute("PRAGMA fullfsync").fetchone()[0], 1)
        self.register()
        self.journal.run("plan-1", self.bridge, self.provider(), limit=1)
        self.journal._db.execute(
            "UPDATE arms SET reply=? WHERE plan_id=? AND arm=?",
            (b"corrupted", "plan-1", "baseline"))
        with self.assertRaisesRegex(paired.JournalError, "reply integrity"):
            self.journal.report("plan-1", self.bridge)
        with self.assertRaisesRegex(paired.JournalError, "reply integrity"):
            self.journal.run("plan-1", self.bridge, self.provider())
        self.assertEqual([arm for arm, _ in self.calls], ["baseline"])

    def test_changed_bindings_oversize_and_non_fake_providers_fail_before_any_dispatch(self):
        self.register()
        tampered = copy.deepcopy(self.doc)
        tampered["arms"]["reference"]["payload"]["messages"][0]["content"] += " extra"
        verdict = dict(self.summary, verdict="accept")
        builtin = dict(self.summary, worker_launch=capture.BUILTIN_WORKER)  # unsupported label
        refused = {
            "changed_reply_bound": (paired.PlanConflict, dict(max_reply_bytes=4097)),
            "changed_query": (paired.PlanConflict, dict(query="duplicate")),
            "changed_record_cap": (paired.PlanConflict, dict(max_records=8)),
            "other_scope_bridge": (paired.PlanConflict, dict(bridge=self.make_bridge(OTHER))),
            "tampered_capture": (capture.CheckError, dict(capture_doc=tampered)),
            "capture_hash_mismatch": (capture.CheckError, dict(
                summary=dict(self.summary, worker_output_sha256="0" * 64))),
            "summary_claims_verdict": (capture.CheckError, dict(summary=verdict)),
            "relabelled_builtin_worker": (capture.CheckError, dict(summary=builtin)),
            "other_reference_bytes": (capture.CheckError, dict(reference=self.reference + b" ")),
            "oversize_request": (paired.JournalError, dict(plan_id="plan-big",
                                                           max_request_bytes=64)),
            "reply_bound_over_module_cap": (paired.JournalError, dict(
                plan_id="plan-big", max_reply_bytes=paired.MAX_REPLY_BYTES + 1)),
        }
        for label, (error, changes) in refused.items():
            with self.subTest(case=label):
                with self.assertRaises(error):
                    self.register(**changes)
        with self.assertRaises(paired.JournalError):  # refused plans were never stored
            self.journal.report("plan-big", self.bridge)
        with self.assertRaises(paired.PlanConflict):
            self.journal.run("plan-1", self.make_bridge(OTHER), self.provider())

        class Subclass(paired.FakeReplyProvider):
            pass

        for live in (lambda arm, request: b"x", mock.Mock(), Subclass(lambda a, r: b"x")):
            with self.assertRaises(TypeError):
                self.journal.run("plan-1", self.bridge, live)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.arms(self.journal.report("plan-1", self.bridge)),
                         ["not_started", "not_started"])

        # Post-output byte cap: an oversized reply is invalid, hash-only, and final.
        self.register("plan-small", max_reply_bytes=16)
        big = dict(REPLIES, baseline=b"x" * 17)
        report = self.journal.run("plan-small", self.bridge, self.provider(replies=big))
        self.assertEqual((report["plan_status"], report["stop_reason"], self.arms(report)),
                         ("stopped", "invalid_reply_baseline", ["invalid", "missing"]))
        baseline = report["arms"]["baseline"]
        self.assertEqual((baseline["reply_body"], baseline["reply_bytes"], baseline["detail"]),
                         (None, 17, "reply_outside_post_output_byte_cap"))
        self.assertEqual(report["bounds"]["kind"], paired.BOUND_KIND)
        self.journal.run("plan-small", self.bridge, self.provider())
        self.assertEqual([arm for arm, _ in self.calls], ["baseline"])
