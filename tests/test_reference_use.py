"""Durable local dispatch accounting; synthetic fixtures, no network/model."""
from pathlib import Path

import support
from evidence_support import StoreCase
import test_adoption_store as fixtures
from runtime_support import make_control, policy_body
from agent_sleep_lab.oss_bridge import CollectOnlyBridge
from agent_sleep_lab.reference_use import ReferenceUseJournal
from agent_sleep_lab.provenance import sha256_hex


class ReferenceUseTests(StoreCase):
    open_adoption = fixtures.AdoptionTests.open_adoption
    setup_store = fixtures.AdoptionTests.setup_store

    def setup_use(self):
        store = self.setup_store()
        store.commit_adoption(**fixtures.AdoptionTests.proposal(self, store))
        bridge = CollectOnlyBridge(store, scope={"project": "p", "task_family": "t"},
                                   repository="fixture/project", agent_commit="a" * 40)
        path = str(Path(self.dir) / "reference-use.sqlite")
        journal = ReferenceUseJournal(path)
        self.addCleanup(journal.close)
        journal.prepare("use-1", bridge, task_bytes=b"synthetic task", query="thing",
                        max_bytes=32768, consumer_id="offline-fixture", consumer_version="1")
        return store, bridge, journal, path

    def dispatch(self, journal, bridge, consumer):
        return journal.dispatch("use-1", bridge, consumer,
                                consumer_id="offline-fixture", consumer_version="1")

    def receipt(self, **request):
        return dict(use_id=request["use_id"], task_sha256=sha256_hex(request["task_bytes"]),
                    reference_sha256=sha256_hex(request["reference_bytes"]),
                    output_bytes=b"synthetic output")

    def exclude(self, store):
        store.set_policy(make_control(), policy_body(memory_ids=("m-1",)), expected_revision=1)

    def test_exact_frozen_bytes_reopen_and_no_duplicate_dispatch(self):
        store, bridge, journal, path = self.setup_use()
        binding, _ = journal._row("use-1")
        seen = []
        def consumer(**request):
            seen.append(request)
            return self.receipt(**request)
        result = self.dispatch(journal, bridge, consumer)
        self.assertEqual(result["status"], "received_unreviewed")
        self.assertFalse(result["delivery_and_use_verified"])
        self.assertEqual(seen[0]["reference_bytes"].hex(), binding["reference_hex"])
        reopened = ReferenceUseJournal(path)
        self.addCleanup(reopened.close)
        self.assertEqual(self.dispatch(reopened, bridge, consumer), result)
        self.assertEqual(len(seen), 1)
        self.assertEqual(self.count("adoption_journal"), 1)

    def test_consumer_exception_reserves_unknown_after_reopen_no_retry(self):
        _, bridge, journal, path = self.setup_use()
        seen = []
        def consumer(**request):
            seen.append(request)
            raise RuntimeError("lost acknowledgment after side effect")
        result = self.dispatch(journal, bridge, consumer)
        self.assertEqual(result["status"], "dispatch_outcome_unknown")
        reopened = ReferenceUseJournal(path)
        self.addCleanup(reopened.close)
        self.assertEqual(self.dispatch(reopened, bridge, consumer)["dispatches"], 1)
        self.assertEqual(len(seen), 1)

    def test_stopped_worker_inflight_intent_is_never_replayed(self):
        _, bridge, journal, path = self.setup_use()
        _, before = journal._row("use-1")
        journal._cas("use-1", before, dict(before, status="dispatch_outcome_unknown",
                                         reason="consumer_outcome_unknown", dispatches=1))
        reopened = ReferenceUseJournal(path)
        self.addCleanup(reopened.close)
        def forbidden(**request):
            self.fail("unknown dispatch replayed")
        self.assertEqual(self.dispatch(reopened, bridge, forbidden)["status"], "dispatch_outcome_unknown")

    def test_policy_change_before_dispatch_blocks_consumer(self):
        store, bridge, journal, _ = self.setup_use()
        self.exclude(store)
        def forbidden(**request):
            self.fail("stale context dispatched")
        result = self.dispatch(journal, bridge, forbidden)
        self.assertEqual(result["status"], "invalidated")
        self.assertEqual(result["dispatches"], 0)

    def test_policy_change_during_dispatch_preserves_output_but_invalidates(self):
        store, bridge, journal, _ = self.setup_use()
        def consumer(**request):
            self.exclude(store)
            return self.receipt(**request)
        result = self.dispatch(journal, bridge, consumer)
        self.assertEqual(result["status"], "invalidated")
        self.assertEqual(result["output_sha256"], sha256_hex(b"synthetic output"))
        self.assertFalse(result["delivery_and_use_verified"])

    def test_wrong_receipt_not_accepted_and_no_second_dispatch(self):
        _, bridge, journal, _ = self.setup_use()
        calls = []
        def consumer(**request):
            calls.append(1)
            return dict(self.receipt(**request), reference_sha256="0" * 64)
        self.assertEqual(self.dispatch(journal, bridge, consumer)["status"], "invalid_receipt_unreviewed")
        self.dispatch(journal, bridge, consumer)
        self.assertEqual(len(calls), 1)

    def test_identity_conflicts_and_concurrent_dispatch_cannot_call_twice(self):
        _, bridge, journal, path = self.setup_use()
        with self.assertRaisesRegex(ValueError, "conflict"):
            journal.prepare("use-1", bridge, task_bytes=b"different task", query="thing",
                            max_bytes=32768, consumer_id="offline-fixture", consumer_version="1")
        with self.assertRaisesRegex(ValueError, "identity"):
            journal.dispatch("use-1", bridge, self.receipt, consumer_id="wrong", consumer_version="1")
        other = ReferenceUseJournal(path)
        self.addCleanup(other.close)
        def consumer(**request):
            inner = self.dispatch(other, bridge, lambda **unused: self.fail("double dispatch"))
            self.assertEqual(inner["status"], "dispatch_outcome_unknown")
            return self.receipt(**request)
        self.assertEqual(self.dispatch(journal, bridge, consumer)["status"], "received_unreviewed")

    def test_foreign_store_refused_without_mutation_and_binding_corruption_stops(self):
        store, bridge, journal, _ = self.setup_use()
        before = store._rows("SELECT name FROM sqlite_master ORDER BY name")
        with self.assertRaisesRegex(ValueError, "foreign database"):
            ReferenceUseJournal(self.path)
        self.assertEqual(store._rows("SELECT name FROM sqlite_master ORDER BY name"), before)
        journal.db.execute("UPDATE reference_uses SET binding_sha256=?", ("0" * 64,))
        with self.assertRaisesRegex(ValueError, "corrupt"):
            self.dispatch(journal, bridge, self.receipt)
