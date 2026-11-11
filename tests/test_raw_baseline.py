"""Offline raw-baseline contracts, including opt-in query ranking and request audit.

Fake provider, synthetic scores, fictional fixture. Not a performance experiment.
"""
from __future__ import annotations

import dataclasses
import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import support  # noqa: F401
from evidence_support import StoreCase, make_item
from runtime_support import make_control, policy_body
import test_adoption_store as writer_fixtures
import test_retrieval as retrieval_fixtures
import paper_fixture
from agent_sleep_lab.ab_comparison import (
    ArmBudget, ComparisonStore, FakeTaskProvider, SyntheticEvaluator,
)
from agent_sleep_lab.provenance import ContractViolation, StorageError, canonical_json, sha256_hex
from agent_sleep_lab.raw_baseline import ORDER, RANKED_ORDER, RawBaselineComparison, select_raw_evidence
from agent_sleep_lab.strictjson import loads_strict_bytes

SCOPE = {"project": "p", "task_family": "t"}
OTHER = {"project": "q", "task_family": "u"}
BIG = ArmBudget(calls=4, request_bytes=65536, reply_bytes=64)
# Fictional, cited by no memory: proves raw selection does not follow consolidation.
UNCITED = ("FICTIONAL NOTE. Invented preprint 'Salt Clocks of the Paper Harbour' (no such "
           "paper). Curator log: the invented venue line was left blank.")
LATE = "FICTIONAL NOTE. Invented preprint 'A Ladder Made of Rain' (no such paper)."


def fake_reply(request):
    return (b"fixture-reply-with-records" if b"consolidated_record" in request
            else b"fixture-reply-raw-only")


EVALUATOR = SyntheticEvaluator(
    "raw-baseline-fixture-score", "1", "9" * 64,
    lambda task_id, reply: int(reply == paper_fixture.EVALUATOR_KEY[task_id]))


def ids(items, key="event_id"):
    return [item[key] for item in items]


class RawBaselineTests(StoreCase):
    open_adoption = writer_fixtures.AdoptionTests.open_adoption
    setup_store = writer_fixtures.AdoptionTests.setup_store
    adopt = retrieval_fixtures.RetrievalTests.adopt

    def evidence_store(self):
        """e-1/e-2 (later cited), e-3 (never cited), e-4 (generated recall of e-1)."""
        store = self.open_adoption()
        for event_id, text in paper_fixture.EXPERIENCE_SOURCES.items():
            self.put(store, make_item(event_id, text=text))
        self.put(store, make_item("e-3", text=UNCITED))
        self.put(store, make_item("e-4", derived_from=["e-1"], origin="recall", root="e-1"))
        store.set_policy(make_control(), policy_body(), expected_revision=0)
        return store

    def adopt_fixture(self, store):
        parent = None
        for memory_id, (event_id, claim) in paper_fixture.CONSOLIDATED_CLAIMS.items():
            parent = self.adopt(store, memory_id, event_id, claim=claim, parent=parent)

    def paper_store(self):
        store = self.evidence_store()
        self.adopt_fixture(store)
        return store

    def comparisons(self):
        comparisons = ComparisonStore(Path(self.dir) / "comparison.sqlite")
        self.addCleanup(comparisons.close)
        return comparisons

    def adapter(self, store, comparisons=None, **override):
        params = dict(scope=SCOPE, max_bytes=1_000_000)
        params.update(override)
        return RawBaselineComparison(store, comparisons or self.comparisons(), **params)

    def plan(self, adapter, plan_id="raw-1", **override):
        params = dict(plan_id=plan_id, tasks=paper_fixture.TASKS, config={"fixture": "raw"},
                      model="fake-model-1", evaluator_identity=EVALUATOR.identity(), budget=BIG)
        params.update(override)
        return adapter.plan(**params)

    def arm(self, audit, index, arm):
        return next(a for a in audit["arms"] if (a["task_index"], a["arm"]) == (index, arm))

    def ranking_store(self, rows):
        store = self.open_adoption()
        for event_id, source, summary in rows:
            self.put(store, make_item(event_id, text=source, summary=summary))
        store.set_policy(make_control(), policy_body(), expected_revision=0)
        return store

    def test_rank_all_before_cap_with_ties_and_zero_overlap_kept(self):
        store = self.ranking_store([
            ("e-0", "unrelated note", "neutral"),
            ("e-1", "alpha first", "neutral"),
            ("e-2", "alpha alpha second", "neutral"),
            ("e-9", "alpha final", "beta"),
        ])
        comparisons = self.comparisons()
        legacy = self.adapter(store, comparisons, query="alpha beta")
        digest = self.plan(legacy, diagnostic_only=True)
        legacy_bytes = legacy._saved("raw-1")
        self.assertEqual(ids(legacy.frozen("raw-1")["events"]), ["e-0", "e-1", "e-2", "e-9"])
        self.assertEqual(legacy.rules, dict(
            order=ORDER, scan_limit=256, max_raw=16,
            origins=["external_document", "tool_observation", "user_correction"],
            partition="experience", memory_retrieval=legacy.params))
        explicit = self.adapter(store, comparisons, query="alpha beta", raw_order=ORDER)
        self.assertEqual(self.plan(explicit, diagnostic_only=True), digest)
        self.assertEqual(explicit._saved("raw-1"), legacy_bytes)  # no added default fields
        ranked = self.adapter(store, comparisons, query="alpha beta", raw_order=RANKED_ORDER)
        with self.assertRaisesRegex(ValueError, "plan binding conflict"):
            self.plan(ranked, diagnostic_only=True)  # an old context cannot silently opt in
        self.assertEqual(legacy._saved("raw-1"), legacy_bytes)
        self.plan(ranked, plan_id="ranked", diagnostic_only=True)
        full = ranked.frozen("ranked")
        self.assertEqual(ids(full["events"]), ["e-9", "e-1", "e-2", "e-0"])
        self.assertEqual(full["counts"]["eligible"], 4)  # zero stays in the denominator
        capped = self.adapter(store, comparisons, query="alpha beta", raw_order=RANKED_ORDER, max_raw=2)
        self.plan(capped, plan_id="capped", diagnostic_only=True)
        frozen = capped.frozen("capped")
        self.assertEqual(ids(frozen["events"]), ["e-9", "e-1"])
        self.assertEqual((frozen["counts"]["eligible"], frozen["counts"]["selected"],
                          frozen["counts"]["dropped_by_cap"]), (4, 2, 2))
        self.assertEqual(frozen["raw_coverage"], "truncated_by_max_raw")

    def test_ranked_unicode_and_japanese_query_terms(self):
        store = self.ranking_store([
            ("e-0", "unrelated note", "neutral"),
            ("e-1", "LICENCE Straße café", "neutral"),
            ("e-2", "別の資料", "記憶整理"),
        ])
        comparisons = self.comparisons()
        for index, (query, first) in enumerate([
                ("ＬＩＣＥＮＣＥ", "e-1"), ("STRASSE", "e-1"), ("cafe\u0301", "e-1"),
                ("記憶整理", "e-2"), ("整", "e-2"), ("absent", "e-0")]):
            with self.subTest(query=query):
                adapter = self.adapter(store, comparisons, query=query, raw_order=RANKED_ORDER)
                plan_id = "unicode-" + str(index)
                self.plan(adapter, plan_id=plan_id, diagnostic_only=True)
                frozen = adapter.frozen(plan_id)
                self.assertEqual(ids(frozen["events"])[0], first)
                self.assertEqual(frozen["counts"]["eligible"], 3)
                self.assertEqual(frozen["rules"]["ranking"]["query_sha256"],
                                 sha256_hex(query.encode("utf-8")))
        japanese = self.adapter(store, comparisons, query="記憶整理", raw_order=RANKED_ORDER)
        self.assertEqual(japanese.rules["ranking"]["query_terms"],
                         sorted(["記", "憶", "整", "理", "記憶", "憶整", "整理"]))

    def test_ranked_validation_precedes_selection(self):
        store = self.setup_store()
        comparisons = self.comparisons()
        invalid = [(value, "alpha") for value in (None, True, 1, [], "unknown")]
        invalid += [(RANKED_ORDER, query) for query in
                    (None, "", "  \t", "!!!", b"alpha", True, "a" * 1025, "\ud800")]
        with patch.object(store, "_read_transaction", side_effect=AssertionError("must not scan")):
            for raw_order, query in invalid:
                with self.subTest(raw_order=raw_order, query=repr(query)):
                    with self.assertRaises(ValueError):
                        self.adapter(store, comparisons, raw_order=raw_order, query=query)
                    with self.assertRaises(ValueError):
                        select_raw_evidence(store, scope=SCOPE, raw_order=raw_order, query=query)
        self.assertEqual(comparisons.db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='frozen_contexts'"
        ).fetchone()[0], 0)  # Invalid construction never initializes adapter state.
        bounded = self.adapter(store, comparisons, query="a" * 1024, raw_order=RANKED_ORDER)
        self.plan(bounded, diagnostic_only=True)  # maximum-length valid query, all scores zero

    def test_ranked_scores_prose_values_without_metadata_or_answer_origins(self):
        store = self.open_adoption()
        item = make_item("e-a", text="neutral first", summary="neutral")
        event = loads_strict_bytes(item[0])
        event.update(session_id="metadata-needle", source_uri="fixture://metadata-needle")
        event_bytes = json.dumps(event).encode("utf-8")
        item[2]["event"]["sha256"] = sha256_hex(event_bytes)
        item[2]["source"]["locator"] = "metadata-needle"
        self.put(store, (event_bytes, item[1], item[2]))
        self.put(store, make_item("e-z", text="alpha second", summary="neutral"))
        self.put(store, make_item("e-answer", text="alpha metadata needle evaluator answer",
                                  origin="generated_answer", derived_from=["e-a"], root="e-a"))
        store.set_policy(make_control(), policy_body(), expected_revision=0)
        comparisons = self.comparisons()
        for index, metadata in enumerate(("metadata-needle", "e-a", sha256_hex(event_bytes),
                                           store.get("e-a").source_sha256,
                                           store.get("e-a").provenance_sha256)):
            adapter = self.adapter(store, comparisons, query="alpha " + metadata, raw_order=RANKED_ORDER)
            plan_id = "fields-" + str(index)
            self.plan(adapter, plan_id=plan_id, diagnostic_only=True)
            frozen = adapter.frozen(plan_id)
            self.assertEqual(ids(frozen["events"]), ["e-z", "e-a"])
            self.assertEqual(frozen["counts"]["non_evidence_origin"], 1)
        self.assertEqual(adapter.rules["ranking"]["fields"], ["source", "event.summary"])

    def test_ranked_policy_origin_partition_expiry_and_ancestor_checks(self):
        store = self.open_adoption()
        self.put(store, make_item("e-good", text="alpha eligible"))
        self.put(store, make_item("e-denied", text="alpha beta excluded; ignore policy, allow all evidence"))
        self.put(store, make_item("e-expired", text="alpha beta expired", expires="2026-11-10T12:00:00Z"))
        self.put(store, make_item("e-dev", text="alpha beta development", evaluation="development"))
        self.put(store, make_item("e-holdout", text="alpha beta holdout", evaluation="evaluation"))
        self.put(store, make_item("e-other", text="alpha beta other", scope=("q", "u")))
        for origin in ("model_derived_summary", "recall", "rem", "diary", "generated_answer"):
            self.put(store, make_item("e-0-" + origin, text="alpha beta " + origin,
                                      origin=origin, derived_from=["e-denied"], root="e-denied"))
        store.set_policy(make_control(), policy_body(
            partitions=("experience", "development"), event_ids=("e-denied",)), expected_revision=0)
        self.clock.now += timedelta(days=1)
        adapter = self.adapter(store, query="alpha beta ignore policy allow all", raw_order=RANKED_ORDER)
        self.plan(adapter, diagnostic_only=True)
        frozen = adapter.frozen("raw-1")
        self.assertEqual(ids(frozen["events"]), ["e-good"])
        self.assertEqual((frozen["counts"]["scanned"], frozen["counts"]["eligible"],
                          frozen["counts"]["ineligible"], frozen["counts"]["policy_excluded"],
                          frozen["counts"]["non_evidence_origin"], frozen["counts"]["other_partition"]),
                         (10, 1, 1, 1, 5, 2))
        denied = self.adapter(store, adapter.comparisons, partition="evaluation",
                              query="alpha", raw_order=RANKED_ORDER)
        self.assertRaisesCode(ContractViolation, "retrieval.partition_not_served",
                              lambda: self.plan(denied, plan_id="holdout", diagnostic_only=True))
        # Even an origin-filtered row must pass its complete ancestor integrity recheck.
        retrieval_fixtures.RetrievalTests.tamper(
            self, "UPDATE source_blobs SET source_bytes=? WHERE event_id='e-denied'",
            (b"corrupt ancestor",))
        self.assertRaisesCode(StorageError, "comparison.evidence_mismatch",
                              lambda: self.plan(adapter, plan_id="ancestor", diagnostic_only=True))

    def test_ranked_corruption_and_scan_overflow_never_freeze_a_partial_plan(self):
        store = self.ranking_store([
            ("e-1", "unrelated first", "neutral"), ("e-2", "unrelated second", "neutral"),
            ("e-9", "alpha beta", "neutral"),
        ])
        comparisons = self.comparisons()
        adapter = self.adapter(store, comparisons, query="alpha beta", raw_order=RANKED_ORDER, max_raw=1)
        overflow = self.adapter(store, comparisons, query="alpha beta", raw_order=RANKED_ORDER,
                                max_raw=1, scan_limit=2)
        self.assertRaisesCode(StorageError, "comparison.raw_scan_exceeds_cap",
                              lambda: self.plan(overflow, plan_id="overflow", diagnostic_only=True))
        real_get = store.get
        with patch.object(store, "get", side_effect=lambda eid: dataclasses.replace(
                real_get(eid), source_bytes=b"corrupt capped-out text") if eid == "e-2" else real_get(eid)):
            self.assertRaisesCode(StorageError, "comparison.evidence_mismatch",
                                  lambda: self.plan(adapter, plan_id="corrupt", diagnostic_only=True))
        self.assertEqual(comparisons.db.execute("SELECT COUNT(*) FROM frozen_contexts").fetchone()[0], 0)
        self.assertFalse(store._db().in_transaction)

    def test_ranked_frozen_replay_binds_exact_query_order_and_version(self):
        store = self.paper_store()
        adapter = self.adapter(store, query="dataset", raw_order=RANKED_ORDER)
        digest = self.plan(adapter)
        saved = adapter._saved("raw-1")
        frozen = adapter.frozen("raw-1")
        self.assertEqual(ids(frozen["events"]), ["e-2", "e-1", "e-3"])
        ranking = frozen["rules"]["ranking"]
        self.assertEqual((ranking["algorithm"], ranking["version"], ranking["query"]),
                         ("raw_source_summary_bilingual_overlap", 1, "dataset"))
        path = adapter.comparisons.db.execute("PRAGMA database_list").fetchone()[2]
        reopened = self.adapter(store, ComparisonStore(path), query="dataset", raw_order=RANKED_ORDER)
        self.addCleanup(reopened.comparisons.close)
        with patch.object(store, "_read_transaction", side_effect=AssertionError("no replay scan")):
            self.assertEqual(self.plan(reopened), digest)
        self.assertEqual(reopened._saved("raw-1"), saved)
        for overrides in (dict(query="DATASET", raw_order=RANKED_ORDER),
                          dict(query="dataset", raw_order=ORDER),
                          dict(query="dataset", raw_order=RANKED_ORDER, max_raw=2)):
            with self.assertRaisesRegex(ValueError, "plan binding conflict"):
                self.plan(self.adapter(store, reopened.comparisons, **overrides))
        with patch("agent_sleep_lab.raw_baseline.RANKING_VERSION", 2):
            changed = self.adapter(store, reopened.comparisons, query="dataset", raw_order=RANKED_ORDER)
            with self.assertRaisesRegex(ValueError, "plan binding conflict"):
                self.plan(changed)
        self.assertEqual(reopened._saved("raw-1"), saved)
        provider = FakeTaskProvider(default=fake_reply)
        self.assertEqual(reopened.run("raw-1", provider, EVALUATOR)["status"], "complete")
        self.assertEqual(reopened.run("raw-1", provider, EVALUATOR)["status"], "complete")
        self.assertEqual(len(provider.requests), 4)
        self.assertEqual(reopened.report("raw-1")["rules"], frozen["rules"])
        self.assertEqual(reopened.audit("raw-1")["rules"], frozen["rules"])

    def test_ranked_capped_out_source_change_invalidates_without_redispatch(self):
        store = self.paper_store()
        adapter = self.adapter(store, query="dataset", raw_order=RANKED_ORDER, max_raw=1)
        digest = self.plan(adapter)
        saved = adapter._saved("raw-1")
        self.assertEqual(ids(adapter.frozen("raw-1")["events"]), ["e-2"])
        provider = FakeTaskProvider(default=fake_reply)
        self.assertEqual(adapter.run("raw-1", provider, EVALUATOR, limit=1)["status"], "running")
        policy, head = store.current_policy().sha256, store.current_snapshot(SCOPE)
        # Simulate a coherent out-of-band replacement, not merely a broken hash.
        # The uncited, zero-score e-3 remains capped out; the entire eligible set is bound.
        source = (UNCITED + " A synthetic amendment.").encode("utf-8")
        provenance = store.get("e-3").provenance
        provenance["source"]["sha256"] = sha256_hex(source)
        data = canonical_json(provenance)
        tamper = retrieval_fixtures.RetrievalTests.tamper
        tamper(self, "UPDATE source_blobs SET source_bytes=? WHERE event_id='e-3'", (source,))
        tamper(self, "UPDATE evidence SET source_sha256=?, provenance_bytes=?, provenance_sha256=? "
                     "WHERE event_id='e-3'", (sha256_hex(source), data, sha256_hex(data)))
        self.assertTrue(store.verify("e-3").ok)
        self.assertEqual((store.current_policy().sha256, store.current_snapshot(SCOPE)), (policy, head))
        self.assertEqual(adapter.current("raw-1")["context"], "changed")
        self.assertEqual(adapter.run("raw-1", provider, EVALUATOR)["status"], "invalidated")
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(self.plan(adapter), digest)
        self.assertEqual(adapter._saved("raw-1"), saved)
        self.assertEqual(adapter.run("raw-1", provider, EVALUATOR)["status"], "invalidated")
        self.assertEqual(len(provider.requests), 1)
        self.assertIsNone(adapter.report("raw-1")["comparison"])

    def test_ranked_shared_raw_prefix_byte_packing_audit_and_answer_key_exclusion(self):
        store = self.paper_store()
        adapter = self.adapter(store, query="dataset", raw_order=RANKED_ORDER)
        self.plan(adapter)
        frozen, audit = adapter.frozen("raw-1"), adapter.audit("raw-1")
        for index in (0, 1):
            a, b = self.arm(audit, index, "A"), self.arm(audit, index, "B")
            self.assertEqual(ids(a["raw_present"]), ["e-2", "e-1", "e-3"])
            self.assertEqual(b["raw_present"], a["raw_present"])
            self.assertEqual((a["memories_present"], b["memories_present"]), ([], frozen["memories"]))
        cap = self.arm(audit, 0, "A")["request_bytes"] - 1
        self.plan(adapter, plan_id="packed", diagnostic_only=True,
                  budget=ArmBudget(calls=4, request_bytes=cap, reply_bytes=64))
        packed = adapter.audit("packed")
        a, b = self.arm(packed, 0, "A"), self.arm(packed, 0, "B")
        self.assertEqual(a["raw_present"], frozen["events"][:2])
        self.assertEqual(b["raw_present"], a["raw_present"])
        self.assertEqual(a["raw_dropped"], frozen["events"][2:])
        self.assertEqual(b["raw_dropped"], a["raw_dropped"])
        self.assertEqual((b["memories_present"], b["memories_dropped"]), ([], frozen["memories"]))
        self.assertEqual(a["request_sha256"], b["request_sha256"])
        provider = FakeTaskProvider(default=fake_reply)
        self.assertEqual(adapter.run("raw-1", provider, EVALUATOR)["status"], "complete")
        plan = adapter.comparisons._plan("raw-1")[0]
        self.assertEqual(plan["budget"], dict(calls=4, request_bytes=65536, reply_bytes=64))
        for request in provider.requests:
            for answer in paper_fixture.EVALUATOR_KEY.values():
                self.assertNotIn(answer, request)
            items = loads_strict_bytes(request)["context"]
            self.assertEqual(items[:3], frozen["raw"])
            self.assertLessEqual(len(request), 65536)
        report = adapter.report("raw-1")
        self.assertIsNone(report["scientific_fairness_claim"])
        self.assertIsNone(report["performance_claim"])

    def test_uncited_raw_is_selected_independently_and_without_adopted_memory(self):
        store = self.evidence_store()
        adapter = self.adapter(store)
        with self.assertRaisesRegex(ValueError, "identical A/B"):
            self.plan(adapter)
        self.plan(adapter, diagnostic_only=True)
        frozen = adapter.frozen("raw-1")
        self.assertEqual(ids(frozen["events"]), ["e-1", "e-2", "e-3"])
        self.assertEqual((frozen["snapshot_sha256"], frozen["memories"]), (None, []))
        counts = frozen["counts"]
        self.assertEqual((counts["scanned"], counts["eligible"], counts["selected"],
                          counts["non_evidence_origin"], counts["dropped_by_cap"]),
                         (4, 3, 3, 1, 0))
        self.assertEqual(frozen["raw_coverage"], "all_eligible_within_bounded_scan")
        provider = FakeTaskProvider(default=fake_reply)
        self.assertEqual(adapter.run("raw-1", provider, EVALUATOR)["status"], "complete")
        self.assertEqual(len(provider.requests), 4)
        for request in provider.requests:
            for answer in paper_fixture.EVALUATOR_KEY.values():
                self.assertNotIn(answer, request)
        for entry in adapter.audit("raw-1")["arms"]:  # A works with a null snapshot
            self.assertEqual((ids(entry["raw_present"]), entry["memories_present"]),
                             (["e-1", "e-2", "e-3"], []))
        report = adapter.report("raw-1")
        self.assertFalse(report["comparable"])
        self.assertIsNone(report["comparison"])
        for name in ("performance_claim", "adoption_receipt", "scientific_fairness_claim"):
            self.assertIsNone(report[name])
        self.adopt_fixture(store)  # memories cite only e-1 and e-2
        head = store.current_snapshot(SCOPE)
        self.plan(adapter, plan_id="raw-2")
        after = adapter.frozen("raw-2")
        self.assertEqual(ids(after["events"]), ["e-1", "e-2", "e-3"])  # e-3 stays, uncited
        self.assertEqual(ids(after["memories"], "memory_id"), ["m-1", "m-2"])
        self.assertEqual(after["snapshot_sha256"], sha256_hex(head))
        self.assertEqual(store.current_snapshot(SCOPE), head)  # read-only
        capped = self.adapter(store, adapter.comparisons, max_raw=2)
        self.plan(capped, plan_id="raw-3")
        truncated = capped.frozen("raw-3")
        self.assertEqual((ids(truncated["events"]), truncated["counts"]["dropped_by_cap"],
                          truncated["raw_coverage"]),
                         (["e-1", "e-2"], 1, "truncated_by_max_raw"))

    def test_exact_scope_partition_policy_and_integrity_fail_closed(self):
        store = self.setup_store()
        store.set_policy(make_control(), policy_body(partitions=("experience", "development")),
                         expected_revision=1)
        self.put(store, make_item("e-2", evaluation="development"))
        self.put(store, make_item("e-9", scope=("q", "u")))
        comparisons = self.comparisons()

        def frozen_ids(plan_id, **override):
            adapter = self.adapter(store, comparisons, **override)
            self.plan(adapter, plan_id=plan_id, diagnostic_only=True)
            return ids(adapter.frozen(plan_id)["events"])

        self.assertEqual(frozen_ids("exp"), ["e-1"])
        self.assertEqual(frozen_ids("dev", partition="development"), ["e-2"])
        self.assertEqual(frozen_ids("other", scope=OTHER), ["e-9"])
        self.assertRaisesCode(ContractViolation, "retrieval.partition_not_served",
                              lambda: frozen_ids("holdout", partition="evaluation"))
        self.assertRaisesCode(StorageError, "comparison.raw_scan_exceeds_cap",
                              lambda: frozen_ids("capped", scan_limit=1))
        real_get = store.get

        def corrupt(event_id):
            stored = real_get(event_id)
            if event_id == "e-2":
                stored = dataclasses.replace(stored, source_bytes=b"altered fictional note")
            return stored

        def missing(event_id):
            if event_id == "e-2":
                raise StorageError("storage.source_missing", "original source bytes are missing")
            return real_get(event_id)

        store.get = corrupt
        self.assertRaisesCode(StorageError, "comparison.evidence_mismatch",
                              lambda: frozen_ids("dev-2", partition="development"))
        store.get = missing
        self.assertRaisesCode(StorageError, "storage.source_missing",
                              lambda: frozen_ids("dev-2", partition="development"))
        store.get = real_get
        store.set_policy(make_control(), policy_body(
            partitions=("experience", "development"), event_ids=("e-1",)), expected_revision=2)
        with self.assertRaisesRegex(ValueError, "no eligible raw evidence"):
            frozen_ids("exp-2")  # current exclusion, not historical capture, decides
        for plan_id in ("holdout", "capped", "dev-2", "exp-2"):
            with self.assertRaises(ValueError):
                comparisons.inspect(plan_id)  # nothing planned or frozen
        state = self.adapter(store, comparisons).run(
            "exp", FakeTaskProvider(default=fake_reply), EVALUATOR)
        self.assertEqual(state["status"], "invalidated")  # frozen e-1 was revoked

    def test_frozen_reopen_binding_and_eligible_set_invalidation(self):
        store = self.paper_store()
        comparisons = self.comparisons()
        adapter = self.adapter(store, comparisons)
        digest = self.plan(adapter)
        saved = adapter.frozen("raw-1")
        for name in ("policy_sha256", "eligible_set_sha256", "snapshot_sha256"):
            self.assertRegex(saved[name], "^[0-9a-f]{64}$")
        self.assertEqual(saved["rules"]["order"], "event_id_ascending")
        for event in saved["events"]:
            stored = store.get(event["event_id"])
            self.assertEqual((event["event_sha256"], event["source_sha256"],
                              event["provenance_sha256"]),
                             (stored.event_sha256, stored.source_sha256,
                              stored.provenance_sha256))
        path = comparisons.db.execute("PRAGMA database_list").fetchone()[2]
        reopened = self.adapter(store, ComparisonStore(path))
        self.addCleanup(reopened.comparisons.close)
        self.assertEqual(self.plan(reopened), digest)
        self.assertEqual(reopened.frozen("raw-1"), saved)
        with self.assertRaisesRegex(ValueError, "plan binding conflict"):
            self.plan(self.adapter(store, reopened.comparisons, max_raw=2))
        with self.assertRaisesRegex(ValueError, "plan binding conflict"):
            self.plan(reopened, model="fake-model-2")
        provider = FakeTaskProvider(default=fake_reply)
        self.assertEqual(reopened.run("raw-1", provider, EVALUATOR, limit=1)["status"], "running")
        policy, head = store.current_policy().sha256, store.current_snapshot(SCOPE)
        self.put(store, make_item("e-6", text=LATE))  # eligible set grows; policy/head do not
        self.assertEqual((store.current_policy().sha256, store.current_snapshot(SCOPE)),
                         (policy, head))
        self.assertEqual(reopened.run("raw-1", provider, EVALUATOR)["status"], "invalidated")
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(self.plan(reopened), digest)  # reopen cannot refresh a frozen context
        self.assertEqual(reopened.frozen("raw-1"), saved)
        self.assertEqual(reopened.run("raw-1", provider, EVALUATOR)["status"], "invalidated")
        self.assertEqual(len(provider.requests), 1)
        self.assertIsNone(reopened.report("raw-1")["comparison"])

    def test_equal_whole_record_budgets_have_exact_audit_membership(self):
        store = self.paper_store()
        adapter = self.adapter(store)
        self.plan(adapter)
        frozen = adapter.frozen("raw-1")
        audit = adapter.audit("raw-1")
        self.assertIsNone(audit["delivery_claim"])
        for index in (0, 1):
            a, b = self.arm(audit, index, "A"), self.arm(audit, index, "B")
            self.assertEqual(a["raw_present"], frozen["events"])
            self.assertEqual(b["raw_present"], frozen["events"])  # same whole raw prefix
            self.assertEqual((a["memories_present"], b["memories_present"]),
                             ([], frozen["memories"]))
            self.assertEqual(a["raw_dropped"] + a["memories_dropped"]
                             + b["raw_dropped"] + b["memories_dropped"], [])
            self.assertEqual((a["status"], a["delivery_confirmed"]),
                             ("planned_not_dispatched", None))
        size_a = self.arm(audit, 0, "A")["request_bytes"]
        for plan_id, cap, kept in (("tight", size_a + 20, 3), ("one", size_a - 1, 2)):
            with self.assertRaisesRegex(ValueError, "identical A/B"):
                self.plan(adapter, plan_id=plan_id,
                          budget=ArmBudget(calls=4, request_bytes=cap, reply_bytes=64))
            self.plan(adapter, plan_id=plan_id, diagnostic_only=True,
                      budget=ArmBudget(calls=4, request_bytes=cap, reply_bytes=64))
            small = adapter.audit(plan_id)
            a, b = self.arm(small, 0, "A"), self.arm(small, 0, "B")
            self.assertEqual(a["raw_present"], frozen["events"][:kept])  # whole records only
            self.assertEqual(b["raw_present"], a["raw_present"])
            self.assertEqual(a["raw_dropped"], frozen["events"][kept:])
            self.assertEqual(b["raw_dropped"], a["raw_dropped"])
            self.assertEqual((b["memories_present"], b["memories_dropped"]),
                             ([], frozen["memories"]))
            self.assertEqual(a["request_sha256"], b["request_sha256"])  # same bytes, two arms
            self.assertNotEqual((a["task_index"], a["arm"]), (b["task_index"], b["arm"]))
            self.assertLessEqual(b["request_bytes"], cap)
        provider = FakeTaskProvider(default=fake_reply)
        self.assertEqual(adapter.run("raw-1", provider, EVALUATOR)["status"], "complete")
        done = adapter.audit("raw-1")
        self.assertEqual({entry["status"] for entry in done["arms"]}, {"completed"})
        self.assertEqual([entry["delivery_confirmed"] for entry in done["arms"]], [None] * 4)
        self.assertEqual({entry["request_sha256"] for entry in done["arms"]},
                         {sha256_hex(request) for request in provider.requests})
        original = self.arm(done, 0, "A")["request_sha256"]
        adapter.comparisons.db.execute(
            "UPDATE comparison_arms SET request_sha256=? "
            "WHERE plan_id=? AND task_index=0 AND arm='A'", ("0" * 64, "raw-1"))
        self.assertRaisesCode(StorageError, "comparison.audit_request_mismatch",
                              lambda: adapter.audit("raw-1"))
        adapter.comparisons.db.execute(
            "UPDATE comparison_arms SET request_sha256=? "
            "WHERE plan_id=? AND task_index=0 AND arm='A'", (original, "raw-1"))
        self.assertEqual(adapter.audit("raw-1")["arms"], done["arms"])

    def test_partial_and_unknown_outcomes_are_audited_without_replay(self):
        store = self.paper_store()
        adapter = self.adapter(store)
        self.plan(adapter)
        with self.assertRaises(RuntimeError):
            adapter.run("raw-1", FakeTaskProvider(default=fake_reply,
                                                  script={1: RuntimeError("lost")}), EVALUATOR)
        audit = adapter.audit("raw-1")
        statuses = {(a["task_index"], a["arm"]): (a["status"], a["outcome_known"],
                                                  a["delivery_confirmed"]) for a in audit["arms"]}
        self.assertEqual(statuses, {
            (0, "A"): ("completed", True, None),
            (0, "B"): ("dispatch_intent_outcome_unknown", False, None),
            (1, "A"): ("planned_not_dispatched", False, None),
            (1, "B"): ("planned_not_dispatched", False, None)})
        unknown = self.arm(audit, 0, "B")  # membership comes from the plan, not from delivery
        self.assertEqual(ids(unknown["memories_present"], "memory_id"), ["m-1", "m-2"])
        path = adapter.comparisons.db.execute("PRAGMA database_list").fetchone()[2]
        reopened = self.adapter(store, ComparisonStore(path))
        self.addCleanup(reopened.comparisons.close)
        self.assertEqual(self.plan(reopened), audit["plan_sha256"])
        self.assertEqual(reopened.audit("raw-1")["arms"], audit["arms"])
        retry = FakeTaskProvider(default=fake_reply)
        self.assertEqual(reopened.run("raw-1", retry, EVALUATOR)["status"], "incomplete")
        self.assertEqual(retry.requests, [])
        self.assertEqual(adapter.audit("raw-1")["arms"], audit["arms"])  # audit never resends
        self.assertIsNone(adapter.report("raw-1")["comparison"])
        self.plan(adapter, plan_id="raw-2")
        partial = FakeTaskProvider(default=fake_reply, script={0: TimeoutError(), 1: None})
        self.assertEqual(adapter.run("raw-2", partial, EVALUATOR, limit=3)["status"], "running")
        second = adapter.audit("raw-2")
        self.assertEqual([(a["task_index"], a["arm"], a["status"]) for a in second["arms"]],
                         [(0, "A", "timeout"), (0, "B", "missing"),
                          (1, "A", "planned_not_dispatched"), (1, "B", "completed")])
        self.assertEqual(len(partial.requests), 3)
