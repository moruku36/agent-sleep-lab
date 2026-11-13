"""Offline accounting contracts; injected transport is never live evidence."""
from __future__ import annotations

import json
import unittest

import support  # noqa: F401
import test_ab_comparison as ab
import test_runtime_review as runtime
from evidence_support import StoreCase
from agent_sleep_lab.ab_comparison import ComparisonStore
from agent_sleep_lab.mimo_provider import OpenClawMimoProvider, MODEL
from agent_sleep_lab.provider_usage import accounting_fields, usage_observation
from agent_sleep_lab.sleep_coordinator import SleepCoordinator


def provider(result, calls=1):
    return OpenClawMimoProvider(agent="kurotchi-work", max_calls=calls,
                                transport=lambda *args, **kwargs: result)


class UsageTests(unittest.TestCase):
    def test_observed_counts_billed_cost_last_call_and_privacy(self):
        usage = dict(input=17, output=4, total=21, cacheRead=3, cacheWrite=2,
                     cacheWrite1h=1, cacheWrite5m=1, reasoningTokens=2,
                     usageReport=dict(state="available", account="PRIVATE"),
                     cost=dict(total=0.25, totalOrigin="provider-billed", account="PRIVATE"),
                     account="PRIVATE", contextUsage=dict(account="PRIVATE"))
        p = provider(runtime.envelope("ok", usage=usage, transport="gateway",
                                     lastCallUsage=dict(input=7, output=2, total=9),
                                     account="PRIVATE"))
        self.assertEqual(p.reply(b"task", 100), b"ok")
        receipt = p.receipts[0]
        self.assertEqual(receipt["usage"]["input"], 17)
        self.assertEqual(receipt["usage"]["reasoningTokens"], 2)
        self.assertEqual(receipt["last_call_usage"], dict(input=7, output=2, total=9))
        self.assertEqual(receipt["cost"], dict(label="provider_billed", value=0.25, currency=None))
        self.assertEqual(receipt["usage"]["usageReport"], dict(state="available"))
        self.assertNotIn("PRIVATE", json.dumps(receipt))
        self.assertEqual(receipt["transport_source"], "injected_transport_not_live_verified")
        self.assertEqual(receipt["envelope_transport"], "gateway")

    def test_absent_default_zero_explicit_zero_and_unavailable(self):
        for raw in (None, {}, dict(input=0, output=0, total=0, cost=dict(total=0)),
                    dict(account="PRIVATE")):
            self.assertEqual(usage_observation(raw), (None, "absent"))
        explicit = dict(input=0, output=0, total=0, usageReport=dict(state="available"))
        self.assertEqual(usage_observation(explicit), (explicit, "observed"))
        unavailable = dict(input=17, usageReport=dict(state="unavailable"),
                           cost=dict(total=12, totalOrigin="provider-billed"))
        p = provider(runtime.envelope("ok", usage=unavailable))
        p.reply(b"task", 100)
        self.assertEqual(p.receipts[0]["usage"], dict(usageReport=dict(state="unavailable")))
        self.assertEqual(p.receipts[0]["usage_state"], "unavailable")
        self.assertIsNone(p.receipts[0]["cost"])

    def test_malformed_metrics_are_not_coerced_or_persisted(self):
        for raw in ([], "PRIVATE", dict(input=True), dict(total=-1), dict(output=1.5),
                    dict(input="17"), dict(total=2**53), dict(usageReport=[]),
                    dict(usageReport=dict(state="PRIVATE")), dict(costStatus="PRIVATE"),
                    dict(cost=[]), dict(cost=dict(total=True)), dict(cost=dict(total=-1)),
                    dict(cost=dict(total=float("nan"))), dict(cost=dict(total=float("inf"))),
                    dict(cost=dict(total=10**400))):
            with self.subTest(raw=repr(raw)[:80]):
                self.assertEqual(usage_observation(raw), (None, "invalid"))
        p = provider(runtime.envelope("ok", usage=dict(input=True, account="PRIVATE")))
        self.assertEqual(p.reply(b"task", 100), b"ok")
        self.assertEqual(p.receipts[0]["usage_state"], "invalid")
        self.assertNotIn("PRIVATE", json.dumps(p.receipts))

    def test_cost_provenance_no_currency_guess_no_last_call_substitution(self):
        fields = accounting_fields(dict(usage=dict(input=5, cost=dict(total=0.4))))
        self.assertEqual(fields["cost"], dict(label="recorded_unverified_billing", value=0.4, currency=None))
        self.assertNotIn("total", fields["usage"])  # no computed token totals
        for cost, expected in ((dict(total=0), None),
                               (dict(total=0, totalOrigin="provider-billed"), "provider_billed"),
                               (dict(total=0, input=0.1), "recorded_unverified_billing")):
            observed = accounting_fields(dict(usage=dict(cost=cost)))
            self.assertEqual(observed["cost"]["label"] if observed["cost"] else None, expected)
        fields = accounting_fields(dict(
            usage=dict(total=0, costStatus="complete", cost=dict(total=0))))
        self.assertEqual(fields["cost"]["label"], "recorded_unverified_billing")
        fields = accounting_fields(dict(
            usage=dict(total=48, costStatus="unavailable", cost=dict(total=0.4)),
            lastCallUsage=dict(input=7, cost=dict(total=0.2, totalOrigin="provider-billed"))))
        self.assertIsNone(fields["cost"])
        self.assertEqual(fields["usage"], dict(total=48, costStatus="unavailable"))
        fields = accounting_fields(dict(lastCallUsage=dict(input=7, output=2)))
        self.assertIsNone(fields["usage"])
        self.assertIsNone(fields["cost"])
        self.assertEqual(fields["last_call_usage"], dict(input=7, output=2))

    def test_failed_output_keeps_observations_but_wrong_model_and_timeout_do_not(self):
        p = provider(runtime.envelope("too long", usage=dict(input=4, cost=dict(total=0.2))))
        with self.assertRaisesRegex(ValueError, "post-generation"):
            p.reply(b"task", 2)
        self.assertEqual(p.receipts[0]["usage"]["input"], 4)
        self.assertEqual(p.receipts[0]["cost"]["value"], 0.2)
        with self.assertRaisesRegex(ValueError, "call budget"):
            p.reply(b"task", 100)
        p = provider(runtime.envelope("ok", provider="other", usage=dict(input=4)))
        with self.assertRaisesRegex(ValueError, "unverified model"):
            p.reply(b"task", 100)
        self.assertIsNone(p.receipts[0]["usage"])
        self.assertEqual(p.receipts[0]["usage_state"], "not_observed")
        def timeout(*args, **kwargs):
            raise TimeoutError("PRIVATE")
        p = OpenClawMimoProvider(agent="kurotchi-work", max_calls=1, transport=timeout)
        with self.assertRaisesRegex(RuntimeError, "unknown") as error:
            p.reply(b"task", 100)
        self.assertNotIn("PRIVATE", str(error.exception))
        self.assertEqual((p.calls, p.receipts[0]["usage_state"]), (1, "not_observed"))


class JournalUsageTests(unittest.TestCase):
    setUp = ab.ComparisonTests.setUp
    store = ab.ComparisonTests.store
    params = ab.ComparisonTests.params
    observe = ab.ComparisonTests.observe

    def test_comparison_reopen_retains_usage_without_total_cost_or_redispatch(self):
        store = self.store()
        store.plan(**self.params(model=MODEL, tasks=ab.tasks(1)))
        p = provider(runtime.envelope("used-memo", usage=dict(
            input=17, output=4, total=21, cost=dict(total=0.25, totalOrigin="provider-billed"))), calls=2)
        store.run("plan-1", p, ab.evaluator, self.observe)
        saved = store.report("plan-1", self.observe)
        self.assertEqual(len(saved["provider_receipts"]), 2)
        self.assertEqual(saved["provider_receipts"][0]["receipt"]["usage"]["total"], 21)
        self.assertEqual(saved["cost"]["A"]["total"]["label"], "unavailable")
        self.assertIsNone(saved["measured_savings"])
        store.close()
        reopened = self.store()
        self.assertEqual(reopened.report("plan-1", self.observe)["provider_receipts"],
                         saved["provider_receipts"])
        stopped = provider(runtime.envelope("must not run"), calls=2)
        reopened.run("plan-1", stopped, ab.evaluator, self.observe)
        self.assertEqual(stopped.calls, 0)
        # A post-generation failure still durably records usage, leaving intent
        # unknown and never replaying the request.
        reopened.plan(**self.params(plan_id="failed", model=MODEL, tasks=ab.tasks(1)))
        failed = provider(runtime.envelope("x" * 65, usage=dict(input=31)))
        with self.assertRaises(ValueError):
            reopened.run("failed", failed, ab.evaluator, self.observe)
        reopened.close()
        journal = self.store()
        report = journal.report("failed", self.observe)
        self.assertEqual(report["provider_receipts"][0]["receipt"]["usage"]["input"], 31)
        self.assertEqual(report["outcomes"]["A"]["unknown"], 1)
        journal.run("failed", stopped, ab.evaluator, self.observe)
        self.assertEqual(stopped.calls, 0)


class SleepUsageTests(StoreCase):
    open_adoption = runtime.BodyBoundSleepTests.open_adoption
    setup_store = runtime.BodyBoundSleepTests.setup_store
    prepare_run = runtime.BodyBoundSleepTests.prepare_run

    def test_light_deep_checkpoints_preserve_each_usage_without_adoption(self):
        store, coordinator, current = self.prepare_run()
        light = provider(runtime.envelope('{"event_ids":["e-1"]}', usage=dict(input=11)))
        self.assertEqual(coordinator.advance("body-1", light, current=current)["status"], "deep")
        coordinator.close()
        coordinator = SleepCoordinator(self.dir + "/body-sleep.sqlite")
        self.addCleanup(coordinator.close)
        deep = provider(runtime.envelope('{"operations":[{"op":"add","memory_id":"m-1",'
                                         '"event_ids":["e-1"],"claim":"Check source before reuse"}]}',
                                         usage=dict(input=13, output=7)))
        state = coordinator.advance("body-1", deep, current=current)
        self.assertEqual(state["status"], "ready")
        self.assertEqual([r["usage"]["input"] for r in state["provider_receipts"]], [11, 13])
        self.assertIsNone(store.current_snapshot(ab.SCOPE))
        coordinator.close()
        reopened = SleepCoordinator(self.dir + "/body-sleep.sqlite")
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.inspect("body-1")["provider_receipts"], state["provider_receipts"])
        self.assertEqual((light.calls, deep.calls), (1, 1))
