"""Bounded synthetic process-crash/CAS acceptance; no production test hooks."""
from __future__ import annotations

from contextlib import contextmanager
import multiprocessing
import signal

from evidence_support import Clock, StoreCase, make_boundary
from runtime_support import make_evaluator, make_verifier
from test_adoption_store import AdoptionTests, SCOPE
from agent_sleep_lab.adoption_candidates import parse_canonical
from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.provenance import ConflictError

TIMEOUT = 15


def open_store(path):
    return AdoptionStore(
        path, make_boundary(), verifier=make_verifier(), evaluator=make_evaluator(),
        evaluation_protocol=("fixture-protocol", "1", "d" * 64), clock=Clock(),
    )


def crash_writer(path, payload, point, pipe):
    with open_store(path) as store:
        if point == "before_commit":
            def trace(sql):
                # Trace runs before SQLite executes COMMIT, after all writer DML.
                if sql.strip().upper() == "COMMIT":
                    pipe.send(("before_commit", store._db().in_transaction))
                    pipe.recv()  # Parent kills this process; no transaction cleanup.
            store._db().set_trace_callback(trace)
        elif point == "after_commit":
            original = store._immediate

            @contextmanager
            def pause_after_commit():
                with original():
                    yield
                pipe.send(("after_commit", store._db().in_transaction))
                pipe.recv()  # Durable COMMIT, but commit_adoption has not returned.
            store._immediate = pause_after_commit
        else:
            raise ValueError(point)
        store.commit_adoption(**payload)
        pipe.send(("unexpected_ack", None))


def contender(path, payload, pipe):
    with open_store(path) as store:
        pipe.send(("ready", None))
        if pipe.recv() != "go":
            raise RuntimeError("bad start signal")
        try:
            result = store.commit_adoption(**payload)
            pipe.send(("created", result.receipt_bytes))
        except ConflictError as exc:
            pipe.send(("conflict", exc.code))


class AdoptionProcessTests(StoreCase):
    # Reuse fixture construction only, without inheriting seven historical tests.
    open_adoption = AdoptionTests.open_adoption
    setup_store = AdoptionTests.setup_store
    proposal = AdoptionTests.proposal

    def start(self, target, *args):
        ctx = multiprocessing.get_context("spawn")
        parent, child = ctx.Pipe()
        process = ctx.Process(target=target, args=(*args, child))

        def cleanup():
            if process.pid is not None:
                if process.is_alive():
                    process.kill()
                process.join(TIMEOUT)
                if not process.is_alive():
                    process.close()
            parent.close()
            child.close()

        self.addCleanup(cleanup)
        process.start()
        child.close()
        return process, parent

    def receive(self, pipe):
        self.assertTrue(pipe.poll(TIMEOUT), "worker did not reach expected boundary")
        return pipe.recv()

    def kill_at_boundary(self, payload, point):
        process, pipe = self.start(crash_writer, self.path, payload, point)
        self.assertEqual(self.receive(pipe), (point, point == "before_commit"))
        process.kill()
        process.join(TIMEOUT)
        self.assertFalse(process.is_alive(), "worker did not stop")
        self.assertEqual(process.exitcode, -signal.SIGKILL)

    def counts(self):
        return tuple(self.count(t) for t in (
            "adoption_memories", "adoption_snapshots", "adoption_journal", "adoption_heads",
        ))

    def test_kill_before_commit_rolls_back_all_adoption_rows(self):
        store = self.setup_store()
        payload = self.proposal(store)
        store.close()
        self.kill_at_boundary(payload, "before_commit")
        reopened = self.open_adoption()
        self.assertEqual(self.counts(), (0, 0, 0, 0))
        self.assertIsNone(reopened.resolve_operation("op-1"))
        self.assertIsNone(reopened.current_snapshot(SCOPE))
        self.assertEqual(reopened.current_policy().revision, 1)
        self.assertEqual(reopened.get("e-1").event_id, "e-1")
        self.assertEqual(reopened.commit_adoption(**payload).status, "created")
        self.assertEqual(self.counts(), (1, 1, 1, 1))

    def test_kill_after_commit_reconciles_lost_ack_without_reapplying(self):
        store = self.setup_store()
        payload = self.proposal(store)
        store.close()
        self.kill_at_boundary(payload, "after_commit")
        reopened = self.open_adoption()
        original = reopened.resolve_operation("op-1")
        self.assertIsNotNone(original)
        self.assertEqual(original.status, "replayed")
        snapshot = reopened.current_snapshot(SCOPE)
        receipt = parse_canonical("committed_receipt", original.receipt_bytes)
        request = parse_canonical("adoption_request", payload["request_bytes"])
        self.assertEqual(receipt["snapshot_sha256"], request["candidate_snapshot_sha256"])
        self.assertEqual(self.counts(), (1, 1, 1, 1))
        replay = reopened.commit_adoption(**payload)
        self.assertEqual(replay, original)
        self.assertEqual(reopened.current_snapshot(SCOPE), snapshot)
        self.assertEqual(self.counts(), (1, 1, 1, 1))

    def test_two_spawned_contenders_have_exactly_one_winner(self):
        store = self.setup_store()
        payloads = [self.proposal(store, "race-1", "m-1"),
                    self.proposal(store, "race-2", "m-2")]
        store.close()
        workers = [self.start(contender, self.path, payload) for payload in payloads]
        for _, pipe in workers:
            self.assertEqual(self.receive(pipe), ("ready", None))
        for _, pipe in workers:
            pipe.send("go")
        results = [self.receive(pipe) for _, pipe in workers]
        for process, _ in workers:
            process.join(TIMEOUT)
            self.assertFalse(process.is_alive())
            self.assertEqual(process.exitcode, 0)
        self.assertEqual(sorted(r[0] for r in results), ["conflict", "created"])
        winner = next(i for i, r in enumerate(results) if r[0] == "created")
        loser = 1 - winner
        self.assertEqual(results[loser][1], "adoption.parent_conflict")
        reopened = self.open_adoption()
        winner_id = "race-" + str(winner + 1)
        loser_id = "race-" + str(loser + 1)
        self.assertEqual(reopened.resolve_operation(winner_id).receipt_bytes, results[winner][1])
        self.assertIsNone(reopened.resolve_operation(loser_id))
        self.assertEqual(self.counts(), (1, 1, 1, 1))
        snapshot = parse_canonical("candidate_snapshot", reopened.current_snapshot(SCOPE))
        self.assertEqual([m["memory_id"] for m in snapshot["members"]], ["m-" + str(winner + 1)])
