"""Review regressions: no paid calls, test receipts explicitly simulated."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

import support
from evidence_support import StoreCase
import test_adoption_store as fixtures
from runtime_support import make_control, policy_body
from agent_sleep_lab.sleep_coordinator import SleepCoordinator, FakeProvider, _encode
from agent_sleep_lab.sleep_evidence import bind_from_store, current_store
from agent_sleep_lab.sleep_candidates import candidate_memories
from agent_sleep_lab.mimo_provider import OpenClawMimoProvider, MODEL
from agent_sleep_lab.strictjson import loads_strict_bytes
from agent_sleep_lab.ab_comparison import ComparisonStore, ArmBudget, FakeTaskProvider
import test_ab_comparison as ab
from agent_sleep_lab.runtime_cli import open_store


def envelope(text, **changes):
    doc = dict(ok=True, provider="xiaomi", model="mimo-v2.6-pro", attempts=[],
               outputs=[{"text": text, "mediaUrl": None}])
    doc.update(changes)
    return SimpleNamespace(returncode=0, stdout=_encode(doc), stderr=b"")


class TransportTests(unittest.TestCase):
    def test_registered_model_argv_and_receipt_no_shell_or_key(self):
        calls = []
        def transport(argv, **kwargs):
            calls.append((argv, kwargs))
            return envelope('{"event_ids":["e-1"]}')
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=1, transport=transport)
        self.assertEqual(json.loads(p.propose("light", b'{"source":"evidence body"}', 100)),
                         {"event_ids": ["e-1"]})
        self.assertIn(MODEL, calls[0][0])
        self.assertIn("evidence body", calls[0][0][-1])
        self.assertNotIn("shell", calls[0][1])
        self.assertEqual(p.receipts[0]["status"], "returned")
        self.assertIsNone(p.receipts[0]["generation_token_cap"])
        with self.assertRaisesRegex(ValueError, "call budget"):
            p.reply(b"again", 100)
        self.assertEqual(len(calls), 1)

    def test_wrong_model_fallback_and_nontext_are_rejected(self):
        for changes in ({"model": "other"}, {"attempts": ["fallback"]},
                        {"provider": "other"}, {"outputs": [{"text": "ok", "mediaUrl": "https://example.com"}]}):
            p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=1,
                                    transport=lambda *a, **k: envelope("ok", **changes))
            with self.assertRaises(ValueError):
                p.reply(b"task", 100)
            self.assertEqual(p.calls, 1)

    def test_unknown_timeout_not_retried_and_output_cap_is_post_generation(self):
        def timeout(*a, **k):
            raise TimeoutError()
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=1, transport=timeout)
        with self.assertRaisesRegex(RuntimeError, "unknown"):
            p.reply(b"task", 100)
        self.assertEqual(p.receipts[0]["status"], "outcome_unknown")
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=1,
                                transport=lambda *a, **k: envelope("x" * 101))
        with self.assertRaisesRegex(ValueError, "post-generation"):
            p.reply(b"task", 100)
        self.assertEqual(p.receipts[0]["output_bytes"], 101)


class BodyBoundSleepTests(StoreCase):
    open_adoption = fixtures.AdoptionTests.open_adoption
    setup_store = fixtures.AdoptionTests.setup_store

    def prepare_run(self):
        store = self.setup_store()
        c = SleepCoordinator(Path(self.dir) / "body-sleep.sqlite")
        self.addCleanup(c.close)
        bind_from_store(c, store, run_id="body-1", scope=ab.SCOPE, event_ids=["e-1"], config={})
        current = current_store(store, scope=ab.SCOPE, event_ids=["e-1"])
        return store, c, current

    def generated(self, claim="Do a grounded task"):
        return FakeProvider(_encode({"event_ids": ["e-1"]}), _encode({"operations": [
            {"op": "add", "memory_id": "m-1", "event_ids": ["e-1"], "claim": claim}]}))

    def test_body_reaches_provider_and_generated_prose_becomes_unverified_candidate(self):
        store, c, current = self.prepare_run()
        requests = []
        def transport(argv, **kwargs):
            requests.append(argv[-1])
            return envelope('{"event_ids":["e-1"]}' if len(requests) == 1 else
                            '{"operations":[{"op":"add","memory_id":"m-1","event_ids":["e-1"],"claim":"Check source before reuse"}]}')
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=2, transport=transport)
        c.advance("body-1", p, current=current)
        # A fresh process/provider resumes Deep without losing the Light receipt.
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=2, transport=transport)
        state = c.advance("body-1", p, current=current)
        self.assertEqual(state["status"], "ready")
        self.assertIn(store.get("e-1").source_bytes.decode(), requests[0])
        binding = loads_strict_bytes(c._read("body-1")[0])
        memories = candidate_memories(binding, state["deep"], observed_at="2026-11-10T00:00:00Z")
        memory = loads_strict_bytes(memories["m-1"])
        self.assertEqual(memory["claim"], "Check source before reuse")
        self.assertEqual(memory["verification"]["result"], "pending")
        self.assertIsNone(store.current_snapshot(ab.SCOPE))
        self.assertEqual(len(state["provider_receipts"]), 2)

    def test_revocation_stops_before_provider_call(self):
        store, c, current = self.prepare_run()
        store.set_policy(make_control(), policy_body(event_ids=("e-1",)), expected_revision=1)
        p = self.generated()
        self.assertEqual(c.advance("body-1", p, current=current)["status"], "invalidated")
        self.assertEqual(p.calls, [])

    def test_policy_change_during_inference_invalidates_returned_proposal(self):
        store, c, current = self.prepare_run()
        def transport(*a, **k):
            store.set_policy(make_control(), policy_body(event_ids=("e-1",)), expected_revision=1)
            return envelope('{"event_ids":["e-1"]}')
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=2, transport=transport)
        self.assertEqual(c.advance("body-1", p, current=current)["status"], "invalidated")
        self.assertEqual(c.advance("body-1", p, current=current)["status"], "invalidated")
        self.assertEqual(p.calls, 1)

    def test_live_provider_cannot_use_historical_bodyless_binding(self):
        store = self.setup_store()
        c = SleepCoordinator(Path(self.dir) / "bodyless.sqlite")
        self.addCleanup(c.close)
        c.bind(run_id="old", scope=ab.SCOPE, events=[{"event_id": "e-1", "event_sha256": store.get("e-1").event_sha256}], config={})
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=1)
        with self.assertRaisesRegex(ValueError, "body-bound"):
            c.advance("old", p)
        self.assertEqual(p.calls, 0)

    def test_preparer_cannot_substitute_generated_memory_prose(self):
        store, c, current = self.prepare_run()
        p = self.generated("Specific generated prose, not fixture-written")
        c.advance("body-1", p, current=current)
        c.advance("body-1", p, current=current)
        def preparer(op, run, binding, deep):
            return fixtures.AdoptionTests.proposal(self, store, operation_id=op, run_id=run)
        with self.assertRaisesRegex(ValueError, "substituted"):
            c.prepare("body-1", preparer)
        self.assertIsNone(store.current_snapshot(ab.SCOPE))

    def test_crashed_preparation_has_explicit_unknown_recovery_no_replay(self):
        store, c, current = self.prepare_run()
        p = self.generated()
        c.advance("body-1", p, current=current)
        c.advance("body-1", p, current=current)
        def crash(*args):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            c.prepare("body-1", crash)
        self.assertEqual(c.inspect("body-1")["status"], "preparing")
        state = c.recover_stopped_preparation("body-1")
        self.assertEqual((state["status"], state["reason"]), ("incomplete", "preparation_outcome_unknown"))
        self.assertEqual(c.prepare("body-1", crash), state)


class IdenticalPlanTests(unittest.TestCase):
    setUp = ab.ComparisonTests.setUp
    store = ab.ComparisonTests.store
    params = ab.ComparisonTests.params
    observe = ab.ComparisonTests.observe
    def test_mimo_comparison_adapter_persists_receipts_and_never_calls_cost_zero(self):
        store = self.store()
        store.plan(**self.params(model=MODEL, tasks=ab.tasks(1)))
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=2,
                                transport=lambda *a, **k: envelope("used-memo"))
        store.run("plan-1", p, ab.evaluator, self.observe)
        self.assertEqual(p.calls, 2)
        report = store.report("plan-1", self.observe)
        self.assertFalse(report["fake_provider"])
        self.assertEqual(len(report["provider_receipts"]), 2)
        self.assertEqual(report["cost"]["A"]["total"]["label"], "unavailable")
        self.assertIsNone(report["cost_unit"])
        store.close()
        reopened = self.store()
        self.assertEqual(reopened.report("plan-1", self.observe)["provider_receipts"],
                         report["provider_receipts"])

    def test_oversized_raw_rejects_before_registration_and_diagnostics_never_compare(self):
        store = self.store()
        params = self.params(raw_references=["x" * 9000])
        with self.assertRaisesRegex(ValueError, "identical A/B"):
            store.plan(**params)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM comparison_plans").fetchone()[0], 0)
        store.plan(**params, diagnostic_only=True)
        store.run("plan-1", FakeTaskProvider(), ab.evaluator, self.observe)
        report = store.report("plan-1", self.observe)
        self.assertFalse(report["comparable"])
        self.assertIsNone(report["comparison"])
