"""Five offline Gate 4E cases: manual research-notes handoff journal.

Fictional drafts only. No agent, network, target-repository access or file output.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import support  # noqa: F401
from evidence_support import StoreCase
from runtime_support import make_control, policy_body
import test_raw_baseline as raw_fixtures
import paper_fixture
from agent_sleep_lab import research_handoff
from agent_sleep_lab.ab_comparison import FakeTaskProvider
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.research_handoff import HandoffInvalidated, ResearchHandoffJournal

Fixture = raw_fixtures.RawBaselineTests
EN = """[English](glass-owls.md) | [日本語](glass-owls.ja.md)

# Fictional note: an invented preprint

## Overview

- **What it is:** an invented preprint used only as a test fixture.
- **What it says:** an invented statement with no real source.
- **Caveat:** nothing in this draft describes a real paper.

## Record fields

- Source: fictional

## Practical reading (required for future notes)

- Reported: invented line one.
- Reported: invented line two.
- Proposed: invented line three.
- Proposed: invented line four.
- Alignment: invented line five.
- Limits: invented line six.
"""
JA = """[English](glass-owls.md) | [日本語](glass-owls.ja.md)

# 架空のノート：実在しないプレプリント

## 概要

- **何についてのものか：** テスト用の架空プレプリント。
- **何を述べているか：** 実在の出典がない架空の記述。
- **留意点：** この下書きは実在の論文を説明していません。

## 記録項目

- 出典：架空

## 実務向けの読み解き（今後の必須項目）

- 報告：架空の一行目。
- 報告：架空の二行目。
- 提案：架空の三行目。
- 提案：架空の四行目。
- 整合：架空の五行目。
- 限界：架空の六行目。
"""


class ResearchHandoffTests(StoreCase):
    open_adoption = Fixture.open_adoption
    setup_store = Fixture.setup_store
    adopt = Fixture.adopt
    evidence_store = Fixture.evidence_store
    adopt_fixture = Fixture.adopt_fixture
    paper_store = Fixture.paper_store
    comparisons = Fixture.comparisons
    adapter = Fixture.adapter
    plan = Fixture.plan

    def journal(self, adapter):
        journal = ResearchHandoffJournal(Path(self.dir) / "handoff.sqlite", adapter)
        self.addCleanup(journal.close)
        return journal

    def ready(self):
        store = self.paper_store()
        adapter = self.adapter(store)
        self.plan(adapter)
        return store, adapter, self.journal(adapter)

    def prepare(self, journal, handoff_id="h-1", **override):
        params = dict(handoff_id=handoff_id, plan_id="raw-1", task_index=0, arm="B",
                      topic="fictional-topic", slug="glass-owls")
        params.update(override)
        return journal.prepare(**params)

    def response(self, status, **override):
        paths = status["output_paths"]
        document = dict(protocol=research_handoff.PROTOCOL, kind="result",
                        handoff_id=status["handoff_id"], request_sha256=status["request_sha256"],
                        plan_id=status["plan_id"], task_index=status["task_index"],
                        arm=status["arm"], outputs={paths["en"]: EN, paths["ja"]: JA})
        document.update(override)
        return json.dumps(document, ensure_ascii=False).encode("utf-8")

    def test_envelope_binds_frozen_arm_target_and_paths_without_answers(self):
        _, adapter, journal = self.ready()
        for field in ("topic", "slug"):
            for bad in ("../escape", "/absolute", "a\\b", "Upper", "a/b", "a--b", "", "a b",
                        "a\x00b", "ａｂｃ", "template" if field == "slug" else "x.y"):
                with self.assertRaises(ValueError):
                    self.prepare(journal, "h-bad", **{field: bad})
        for bad in (dict(arm="C"), dict(task_index=9), dict(task_index=True),
                    dict(plan_id="unknown-plan"), dict(handoff_id="../h")):
            with self.assertRaises(ValueError):
                self.prepare(journal, **dict(dict(handoff_id="h-bad"), **bad))
        with self.assertRaises(ValueError):
            journal.status("h-bad")  # nothing was journaled
        status = self.prepare(journal)
        packet = journal.claim("h-1")
        self.assertEqual(sha256_hex(packet), status["request_sha256"])
        self.assertLessEqual(len(packet), research_handoff.MAX_ENVELOPE_BYTES)
        envelope = json.loads(packet)
        audit = adapter.audit("raw-1")
        entry = next(a for a in audit["arms"] if (a["task_index"], a["arm"]) == (0, "B"))
        frozen = adapter.frozen("raw-1")
        packed = adapter.comparisons._plan("raw-1")[0]["tasks"][0]["B"]["request"]
        self.assertEqual(envelope["packed_request"], packed)  # exact frozen bytes, not caller text
        self.assertEqual(envelope["packed_request_sha256"], entry["request_sha256"])
        self.assertEqual(sha256_hex(packed.encode("ascii")), entry["request_sha256"])
        self.assertEqual((envelope["plan_sha256"], envelope["context_sha256"]),
                         (audit["plan_sha256"], audit["context_sha256"]))
        self.assertEqual((envelope["scope"], envelope["policy_sha256"], envelope["snapshot_sha256"]),
                         (frozen["scope"], frozen["policy_sha256"], frozen["snapshot_sha256"]))
        self.assertEqual(envelope["target"], {
            "repository": "moruku36/independent-tech-research-notes",
            "commit": "b6ba067024c908cc931fc582c9904cb4596877da"})
        self.assertEqual(envelope["output_paths"], {
            "en": "surveys/fictional-topic/glass-owls.md",
            "ja": "surveys/fictional-topic/glass-owls.ja.md"})
        self.assertEqual((envelope["protocol"], envelope["kind"], envelope["draft_only"],
                          envelope["references_untrusted"], envelope["grants_permissions"]),
                         (research_handoff.PROTOCOL, "request", True, True, False))
        for secret in (list(paper_fixture.EVALUATOR_KEY.values())
                       + [b"raw-baseline-fixture-score", b"fake-model-1"]):
            self.assertNotIn(secret, packet)

    def test_prepare_is_stable_across_reopen_and_rejects_changed_binding(self):
        _, adapter, journal = self.ready()
        self.plan(adapter, plan_id="raw-2")
        first = self.prepare(journal)
        self.assertEqual((first["status"], first["packet_claimable"]), ("prepared", True))
        self.assertEqual(self.prepare(journal), first)
        journal.close()
        reopened = self.journal(adapter)
        self.assertEqual(self.prepare(reopened), first)  # saved binding, same request hash
        for change in (dict(arm="A"), dict(task_index=1), dict(slug="other-slug"),
                       dict(topic="other-topic"), dict(plan_id="raw-2")):
            with self.assertRaisesRegex(ValueError, "handoff binding conflict"):
                self.prepare(reopened, **change)
        original = research_handoff.PROTOCOL
        research_handoff.PROTOCOL = "agent-sleep-research-handoff/2"
        self.addCleanup(setattr, research_handoff, "PROTOCOL", original)
        with self.assertRaisesRegex(ValueError, "handoff binding conflict"):
            self.prepare(reopened)
        research_handoff.PROTOCOL = original
        self.assertEqual(reopened.status("h-1"), first)
        provider = FakeTaskProvider(default=raw_fixtures.fake_reply)
        adapter.run("raw-2", provider, raw_fixtures.EVALUATOR, limit=1)  # executes task 0, arm A
        with self.assertRaisesRegex(HandoffInvalidated, "comparison_arm_executed"):
            self.prepare(reopened, "h-2", plan_id="raw-2", arm="A")
        with self.assertRaises(ValueError):
            reopened.status("h-2")
        other = self.prepare(reopened, "h-3", plan_id="raw-2", task_index=1, arm="A")
        self.assertEqual(other["status"], "prepared")
        self.assertNotEqual(other["request_sha256"], first["request_sha256"])

    def test_claim_is_one_shot_and_leaves_durable_unknown_outcome(self):
        _, adapter, journal = self.ready()
        prepared = self.prepare(journal)
        packet = journal.claim("h-1")
        status = journal.status("h-1")
        self.assertEqual((status["status"], status["packet_claimable"],
                          status["delivery_confirmed"], status["requires_human_review"],
                          status["result_sha256"]),
                         ("export_intent_outcome_unknown", False, None, True, None))
        self.assertEqual(status["request_sha256"], sha256_hex(packet))  # kept for reconciliation
        self.assertNotIn("packed_request\"", json.dumps(status))  # status never re-exposes it
        self.assertNotIn(json.loads(packet)["packed_request"], json.dumps(status))
        with self.assertRaisesRegex(ValueError, "not claimable"):
            journal.claim("h-1")
        with self.assertRaisesRegex(ValueError, "already bound"):
            self.prepare(journal, "h-duplicate")  # a new ID cannot resend the same arm
        with self.assertRaises(ValueError):
            journal.status("h-duplicate")
        journal.close()
        reopened = self.journal(adapter)
        with self.assertRaisesRegex(ValueError, "not claimable"):
            reopened.claim("h-1")  # no automatic resend after reopen
        self.assertEqual(reopened.status("h-1"), status)
        again = self.prepare(reopened)  # identical prepare does not reset the claim
        self.assertEqual((again["status"], again["request_sha256"]),
                         ("export_intent_outcome_unknown", prepared["request_sha256"]))
        with self.assertRaises(ValueError):
            reopened.unreviewed_result("h-1")  # a missing result stays unknown
        entry = next(a for a in adapter.audit("raw-1")["arms"]
                     if (a["task_index"], a["arm"]) == (0, "B"))
        self.assertEqual(entry["status"], "planned_not_dispatched")  # no fake dispatch was made

    def test_result_import_is_strict_bound_idempotent_and_unreviewed(self):
        _, adapter, journal = self.ready()
        self.prepare(journal)
        with self.assertRaisesRegex(ValueError, "no claimed request"):
            journal.import_result("h-1", self.response(journal.status("h-1")))
        journal.claim("h-1")
        status = journal.status("h-1")
        good = self.response(status)
        paths = status["output_paths"]
        both = {paths["en"]: EN, paths["ja"]: JA}
        big = "x" * (research_handoff.MAX_OUTPUT_BYTES + 1)
        rejected = [
            self.response(status, extra="key"),
            self.response(status, request_sha256="0" * 64),
            self.response(status, handoff_id="h-2"),
            self.response(status, arm="A"),
            self.response(status, task_index=1),
            self.response(status, plan_id="raw-2"),
            self.response(status, kind="request"),
            self.response(status, outputs=dict(both, **{"../evil.md": "x"})),
            self.response(status, outputs={paths["en"]: EN}),
            self.response(status, outputs={paths["en"]: EN, "surveys/other/glass-owls.ja.md": JA}),
            self.response(status, outputs=dict(both, **{paths["ja"]: "  "})),
            self.response(status, outputs=dict(both, **{paths["ja"]: big})),
            self.response(status, outputs=dict(both, **{paths["ja"]: 7})),
            good[:-1] + b',"arm":"B"}',           # duplicate JSON key
            good + b" " * research_handoff.MAX_RESPONSE_BYTES,  # total size bound
            b"\xff" + good, b"", good.decode("utf-8"),
        ]
        for data in rejected:
            with self.assertRaises(ValueError):
                journal.import_result("h-1", data)
        self.assertEqual(journal.status("h-1"), status)  # no rejection mutated the journal
        received = journal.import_result("h-1", good)
        self.assertEqual((received["status"], received["result_sha256"], received["result_bytes"]),
                         ("received_unreviewed", sha256_hex(good), len(good)))
        self.assertEqual((received["adopted"], received["verified"],
                          received["requires_human_review"], received["delivery_confirmed"],
                          received["agent_execution_confirmed"]),
                         (False, False, True, None, None))
        for language in ("en", "ja"):
            self.assertEqual(received["structure"][language], {
                "headings_in_order": True, "overview_labels": True, "language_link": True,
                "practical_lines": 6, "practical_lines_in_range": True})
        self.assertIn("not a semantic", received["structure"]["limits"])
        self.assertEqual(journal.import_result("h-1", good), received)  # idempotent
        self.assertEqual(journal.unreviewed_result("h-1"), good)
        with self.assertRaisesRegex(ValueError, "handoff result conflict"):
            journal.import_result("h-1", self.response(status, outputs=dict(
                both, **{paths["en"]: EN + "\nedited\n"})))
        self.assertEqual(journal.status("h-1"), received)
        journal.db.execute("UPDATE research_handoffs SET result=? WHERE handoff_id=?",
                           (b"{}", "h-1"))
        with self.assertRaisesRegex(ValueError, "corrupt handoff result"):
            journal.status("h-1")
        journal.db.execute("UPDATE research_handoffs SET result=? WHERE handoff_id=?",
                           (good, "h-1"))
        self.assertEqual(journal.status("h-1"), received)
        audit = adapter.audit("raw-1")  # no comparison reply, score or status was manufactured
        self.assertEqual({a["status"] for a in audit["arms"]}, {"planned_not_dispatched"})
        self.assertEqual(adapter.comparisons.inspect("raw-1")["arms"], [])

    def test_policy_or_evidence_change_invalidates_before_export_and_import(self):
        store, adapter, journal = self.ready()
        self.prepare(journal, "h-1", arm="A")
        self.prepare(journal, "h-2", arm="B")
        journal.claim("h-2")
        claimed = journal.status("h-2")
        self.prepare(journal, "h-reviewed", task_index=1, arm="A")
        journal.claim("h-reviewed")
        reviewed = journal.status("h-reviewed")
        received = journal.import_result("h-reviewed", self.response(reviewed))
        real_get = store.get

        def corrupt(event_id):
            stored = real_get(event_id)
            if event_id == "e-2":
                stored = dataclasses.replace(stored, source_bytes=b"altered fictional note")
            return stored

        store.get = corrupt  # frozen evidence no longer matches
        with self.assertRaises(HandoffInvalidated):
            journal.claim("h-1")
        store.get = real_get  # restoring the bytes does not revive the handoff
        stopped = journal.status("h-1")
        self.assertEqual((stopped["status"], stopped["packet_claimable"]), ("invalidated", False))
        with self.assertRaisesRegex(ValueError, "not claimable"):
            journal.claim("h-1")
        store.set_policy(make_control(), policy_body(event_ids=("e-1",)), expected_revision=1)
        with self.assertRaises(HandoffInvalidated):
            journal.import_result("h-2", self.response(claimed))
        with self.assertRaises(HandoffInvalidated):
            journal.unreviewed_result("h-reviewed")  # later revocation blocks stored draft release
        withheld = journal.status("h-reviewed")
        self.assertEqual((withheld["status"], withheld["result_sha256"], withheld["structure"]),
                         ("invalidated", received["result_sha256"], None))
        with self.assertRaises(ValueError):
            journal.import_result("h-reviewed", self.response(reviewed))
        late = journal.status("h-2")
        self.assertEqual((late["status"], late["result_sha256"], late["structure"]),
                         ("invalidated", None, None))
        with self.assertRaises(ValueError):
            journal.import_result("h-2", self.response(claimed))  # stays stopped
        with self.assertRaises(HandoffInvalidated):
            self.prepare(journal, "h-3", task_index=1)  # no silent refresh of the frozen plan
        with self.assertRaises(ValueError):
            journal.status("h-3")
        self.assertEqual(self.prepare(journal, "h-1", arm="A")["status"], "invalidated")
