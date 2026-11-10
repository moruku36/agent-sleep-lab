"""Five offline Gate 4A cases, not a live-model or performance experiment."""
from __future__ import annotations

import json
from pathlib import Path

import support
from evidence_support import StoreCase
from test_adoption_store import AdoptionTests
from agent_sleep_lab.sleep_coordinator import FakeProvider, Limits, SleepCoordinator
from agent_sleep_lab.provenance import sha256_hex
from agent_sleep_lab.retrieval import retrieve_reference_bundle

SCOPE = {"project": "p", "task_family": "t"}


def proposal(**fields):
    return json.dumps(fields).encode()


def provider():
    return FakeProvider(proposal(event_ids=["e-1"]),
                        proposal(operations=[{"op": "add", "memory_id": "m-1",
                                              "event_ids": ["e-1"]}]))


class SleepTests(StoreCase):
    open_adoption = AdoptionTests.open_adoption
    setup_store = AdoptionTests.setup_store

    def coordinator(self):
        coordinator = SleepCoordinator(Path(self.path).with_name("sleep.sqlite"))
        self.addCleanup(coordinator.close)
        return coordinator

    def binding(self, store, **override):
        params = dict(run_id="sleep-1", scope=SCOPE,
                      events=[{"event_id": "e-1",
                               "event_sha256": store.get("e-1").event_sha256}],
                      config={"fixture": "1"})
        params.update(override)
        return params

    def test_synthetic_roundtrip_reconciles_lost_adoption_ack(self):
        store = self.setup_store()
        c = self.coordinator()
        c.bind(**self.binding(store))
        p = provider()
        self.assertEqual(c.advance("sleep-1", p)["status"], "deep")
        self.assertEqual(c.advance("sleep-1", p)["status"], "ready")

        def trusted_prepare(operation_id, run_id, binding, deep):
            # This is an independent synthetic test boundary, not provider self-certification.
            self.assertEqual(deep["operations"][0]["event_ids"], ["e-1"])
            return AdoptionTests.proposal(self, store, operation_id=operation_id,
                                          mid=deep["operations"][0]["memory_id"], run_id=run_id)

        self.assertEqual(c.prepare("sleep-1", trusted_prepare)["status"], "handoff")
        commit = store.commit_adoption

        def lost_ack(**payload):
            commit(**payload)
            raise OSError("simulated lost ACK after durable adoption")

        store.commit_adoption = lost_ack
        with self.assertRaises(OSError):
            c.adopt("sleep-1", store)
        self.assertEqual(c.inspect("sleep-1")["status"], "handoff")
        store.commit_adoption = commit
        c.close()
        c = self.coordinator()
        self.assertEqual(c.adopt("sleep-1", store)["status"], "adopted")
        self.assertEqual(self.count("adoption_journal"), 1)
        bundle = retrieve_reference_bundle(store, scope=SCOPE, max_bytes=32768)
        self.assertEqual([r["memory_id"] for r in bundle.document["records"]], ["m-1"])
        self.assertEqual(bundle.document["records"][0]["evidence"][0]["event_id"], "e-1")
        self.assertEqual(bundle.document["snapshot_sha256"],
                         sha256_hex(store.current_snapshot(SCOPE)))
        self.assertEqual(p.calls, ["light", "deep"])
        self.assertEqual(c.inspect("sleep-1")["calls"], 2)

    def test_reopen_resumes_deep_without_repeating_light(self):
        store = self.setup_store()
        c = self.coordinator()
        args = self.binding(store)
        c.bind(**args)
        p = provider()
        c.advance("sleep-1", p)
        c.close()
        reopened = self.coordinator()
        reopened.bind(**args)
        self.assertEqual(reopened.advance("sleep-1", p)["status"], "ready")
        self.assertEqual(reopened.advance("sleep-1", p)["status"], "ready")
        self.assertEqual(p.calls, ["light", "deep"])
        self.assertIsNone(store.current_snapshot(SCOPE))

    def test_changed_run_binding_rejects_without_mutation(self):
        store = self.setup_store()
        c = self.coordinator()
        args = self.binding(store)
        c.bind(**args)
        before = c.inspect("sleep-1")
        with self.assertRaisesRegex(ValueError, "binding conflict"):
            c.bind(**dict(args, config={"fixture": "changed"}))
        self.assertEqual(c.inspect("sleep-1"), before)
        self.assertIsNone(store.current_snapshot(SCOPE))

    def test_budget_stops_before_deep_and_retains_consumed_usage(self):
        store = self.setup_store()
        c = self.coordinator()
        c.bind(**self.binding(store, limits=Limits(calls=1)))
        p = provider()
        first = c.advance("sleep-1", p)
        self.assertEqual(first["status"], "deep")
        final = c.advance("sleep-1", p)
        self.assertEqual((final["status"], final["reason"]),
                         ("incomplete", "provider_budget_exhausted"))
        self.assertEqual(p.calls, ["light"])
        self.assertEqual((final["calls"], final["output_reserved"]), (1, 16384))
        self.assertGreater(final["output_actual"], 0)
        self.assertEqual(final["input_bytes"], first["input_bytes"])
        self.assertIsNone(store.current_snapshot(SCOPE))

    def test_provider_verification_claim_cannot_promote_memory(self):
        store = self.setup_store()
        c = self.coordinator()
        c.bind(**self.binding(store))
        p = provider()
        c.advance("sleep-1", p)
        p.responses["deep"] = proposal(
            operations=[{"op": "add", "memory_id": "m-1", "event_ids": ["e-1"],
                         "verified": True, "receipt_id": "provider-self-certified"}])
        final = c.advance("sleep-1", p)
        self.assertEqual((final["status"], final["reason"]),
                         ("failed", "invalid_provider_output"))
        self.assertEqual(final["calls"], 2)
        self.assertEqual(c.advance("sleep-1", p), final)
        self.assertEqual(p.calls, ["light", "deep"])
        self.assertIsNone(store.current_snapshot(SCOPE))
        self.assertEqual(self.count("adoption_journal"), 0)
