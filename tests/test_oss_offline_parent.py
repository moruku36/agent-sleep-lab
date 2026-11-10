"""Parent checker preflight, process, output and consumer contracts.

Stand-ins only. Git is replaced by an in-test responder (no git process runs),
reviewed pins are replaced by test-authored sources, and the "worker" is a
trivial stand-in Python subprocess. The pinned target repository and the real
worker ``run()`` are NOT executed: actual target integration stays unverified.
"""
import hashlib
import os
import sys
import tempfile
import unittest
from unittest import mock

import support  # noqa: F401  (makes src importable)
from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_offline_worker as worker

SOURCES = {
    "src/__init__.py": b"# stand-in package\n",
    "src/tail.py": b"def f(): return 1\n",
}
ECHO = "import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write(bytes.fromhex(sys.argv[1]))"
PROBE = ("import json, os, sys; data = sys.stdin.buffer.read(); "
         "print(json.dumps(dict(cwd=os.getcwd(), env=dict(os.environ), size=len(data))))")


def reference(**overrides):
    doc = dict(
        schema_version="agent-sleep-reference-bundle/1", reference_data_only=True,
        synthetic_only=True, scope={"project": "p", "task_family": "t"},
        partition="experience", as_of="2026-11-10T00:00:00Z", snapshot_sha256="a" * 64,
        policy={"revision": 1}, exclusions={"version": 1},
        budget={"max_bytes": 32768}, counts={"returned": 1},
        records=[{"rank": 1, "claim": "synthetic reference"}])
    doc.update(overrides)
    return worker.encoded(doc)


class ParentCase(unittest.TestCase):
    def setUp(self):
        pins = {name: hashlib.sha256(data).hexdigest() for name, data in SOURCES.items()}
        patcher = mock.patch.object(worker, "SOURCE_HASHES", pins)
        patcher.start()
        self.addCleanup(patcher.stop)
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.repo = os.path.realpath(holder.name)
        self.top = self.repo + "\n"
        self.remote = b"https://github.com/moruku36/oss-contributor-agent.git\n"
        self.commit = (worker.AGENT_COMMIT + "\n").encode()
        self.blobs = dict(SOURCES)
        self.git_calls = []
        self.other_calls = []
        real = parent.bounded_run

        def responder(argv, **kwargs):
            if "-C" not in argv:
                self.other_calls.append(argv)
                return real(argv, **kwargs)
            self.git_calls.append((argv, kwargs))
            args = argv[argv.index("-C") + 2:]
            if args[:2] == ["rev-parse", "--show-toplevel"]:
                return 0, self.top.encode()
            if args[0] == "config":
                return 0, self.remote
            if args[0] == "rev-parse":
                return 0, self.commit
            name = args[-1].split(":", 1)[1]
            return (0, self.blobs[name]) if name in self.blobs else (128, b"")

        patcher = mock.patch.object(parent, "bounded_run", responder)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.reference = reference()
        self.task = parent.builtin_task()

    def freeze(self):
        return parent.freeze_sources(self.repo, git="/usr/bin/git")

    def output(self, **overrides):
        doc = dict(
            protocol="agent-sleep-oss-offline-output/1", synthetic_only=True,
            agent_commit=worker.AGENT_COMMIT,
            executed_source_sha256=dict(worker.SOURCE_HASHES),
            task_sha256=worker.digest(self.task),
            reference_sha256=worker.digest(self.reference),
            target_notes_sha256=worker.digest(self.reference), reference_records=1,
            reference_channel="Target.notes; unused by triage with llm=None",
            semantic_memory_use="not_evaluated", performance_improvement="not_evaluated",
            decisions=[{"number": n} for n in range(1, 6)],
            ledger_rows=[{"number": n} for n in range(1, 6)],
            client_calls=[dict(method="list_open_issues", repo="fixture/project"),
                          dict(method="find_existing_prs", repo="fixture/project", number=1)],
            still_pending_llm=0, candidate_pool=[],
            target_calls={"src/tail.py:f": 1}, digest="synthetic")
        doc.update(overrides)
        return worker.encoded(doc)

    def stand_in(self, raw):
        return [sys.executable, "-I", "-c", ECHO, raw.hex()]


class PreflightTests(ParentCase):
    def test_freezes_git_object_bytes_with_read_only_bounded_calls(self):
        with open(os.path.join(self.repo, "decoy.py"), "wb") as handle:
            handle.write(b"raise SystemExit('worktree file must never be read')\n")
        self.assertEqual(self.freeze(), SOURCES)
        self.assertEqual(os.listdir(self.repo), ["decoy.py"])  # nothing written
        subcommands = []
        for argv, kwargs in self.git_calls:
            index = argv.index("-C")
            self.assertEqual(argv[0], "/usr/bin/git")
            self.assertEqual(argv[index + 1], self.repo)
            for flag in ("--no-pager", "--no-replace-objects", "--no-optional-locks",
                         "protocol.allow=never"):
                self.assertIn(flag, argv[:index])
            subcommands.append(argv[index + 2])
            self.assertLessEqual(kwargs["timeout"], parent.GIT_TIMEOUT)
            self.assertLessEqual(kwargs["max_output"], worker.MAX_SOURCE_BYTES)
            self.assertNotEqual(os.path.realpath(kwargs["cwd"]), self.repo)
            self.assertEqual(kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
            self.assertEqual(kwargs["env"]["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(subcommands,
                         ["rev-parse", "config", "rev-parse"] + ["cat-file"] * len(SOURCES))
        blob_args = [argv[-1] for argv, _ in self.git_calls[3:]]
        self.assertEqual(blob_args,
                         [worker.AGENT_COMMIT + ":" + name for name in worker.SOURCE_HASHES])

    def test_rejects_wrong_identity_commit_or_bytes(self):
        cases = [
            ("top", "/somewhere/else\n"),
            ("remote", b"https://github.com/moruku36/oss-contributor-agent-fork.git\n"),
            ("remote", b"https://github.com/other/oss-contributor-agent.git\n"),
            ("remote", b"https://github.com/moruku36/oss-contributor-agent\nextra\n"),
            ("commit", b"e40b39c\n"),
            ("commit", ("0" * 40 + "\n").encode()),
            ("blobs", dict(SOURCES, **{"src/tail.py": b"def f(): return 2\n"})),
            ("blobs", {"src/__init__.py": SOURCES["src/__init__.py"]}),
        ]
        for attribute, value in cases:
            with self.subTest(attribute=attribute, value=value):
                original = getattr(self, attribute)
                setattr(self, attribute, value)
                try:
                    with self.assertRaises(parent.CheckError):
                        self.freeze()
                finally:
                    setattr(self, attribute, original)
        for bad in ("relative/repo", os.path.join(self.repo, "missing"), None):
            with self.subTest(repo=bad), self.assertRaises(parent.CheckError):
                parent.freeze_sources(bad, git="/usr/bin/git")
        with self.assertRaises(parent.CheckError):
            parent.freeze_sources(self.repo, git="git")

    def test_invalid_reference_or_sources_never_reach_a_launch(self):
        spaced = self.reference.replace(b'"records":', b'"records": ')
        bad_references = [
            spaced,  # valid bundle, not canonical bytes
            reference(synthetic_only=False), reference(partition="knowledge"),
            reference(counts={"returned": 2}), b"", b"x" * (worker.MAX_REFERENCE_BYTES + 1),
        ]
        argv = self.stand_in(self.output())
        for bad in bad_references:
            with self.subTest(reference=bad[:40]), self.assertRaises(parent.CheckError):
                parent.check(self.repo, bad, git="/usr/bin/git", worker_argv=argv)
        with self.assertRaises(parent.CheckError):
            parent.prepare_payload(dict(SOURCES, **{"src/tail.py": b"changed\n"}),
                                   self.reference)
        self.assertEqual(self.other_calls, [])
        payload = parent.prepare_payload(SOURCES, self.reference)
        _, task, frozen = worker.validate_payload(worker.strict_json(payload))
        self.assertEqual((task, frozen), (self.task, self.reference))


class ProcessTests(ParentCase):
    def test_stand_in_process_gets_temporary_cwd_and_sanitized_environment(self):
        with mock.patch.dict(os.environ, {"ASL_SECRET_PROBE": "leak", "PYTHONPATH": "/x"}):
            raw = parent.launch([sys.executable, "-I", "-c", PROBE], b"abc")
        seen = worker.strict_json(raw.strip())
        self.assertEqual(seen["size"], 3)
        self.assertNotIn("ASL_SECRET_PROBE", seen["env"])
        self.assertNotIn("PYTHONPATH", seen["env"])
        self.assertEqual(seen["env"]["HOME"], seen["cwd"])
        self.assertNotEqual(os.path.realpath(seen["cwd"]), os.path.realpath(os.getcwd()))
        self.assertFalse(os.path.exists(seen["cwd"]))  # removed after the run

    def test_timeout_output_cap_failure_and_argv_are_enforced(self):
        python = [sys.executable, "-I", "-c"]
        with self.assertRaises(parent.CheckError):
            parent.launch(python + ["import time; time.sleep(30)"], b"x", timeout=0.5)
        flood = "import sys; sys.stdout.write('x' * %d)" % (parent.MAX_OUTPUT_BYTES + 1)
        with self.assertRaises(parent.CheckError):
            parent.launch(python + [flood], b"x")
        with self.assertRaises(parent.CheckError):
            parent.launch(python + ["raise SystemExit(3)"], b"x")
        for bad in ("python -c pass", ["python", "-c", "pass"], []):
            with self.subTest(argv=bad), self.assertRaises(parent.CheckError):
                parent.launch(bad, b"x")
        with self.assertRaises(parent.CheckError):
            parent.launch(python + ["pass"], b"x" * (worker.MAX_INPUT_BYTES + 1))

    def test_builtin_worker_argv_is_isolated_python_on_the_worker_file(self):
        argv = parent.builtin_worker_argv()
        self.assertEqual(argv[:3], [sys.executable, "-I", "-B"])
        self.assertEqual(os.path.realpath(argv[3]), os.path.realpath(worker.__file__))
        self.assertEqual(len(argv), 4)


class OutputTests(ParentCase):
    def validate(self, raw):
        return parent.validate_output(raw, task=self.task, reference=self.reference)

    def test_accepts_bound_output_and_rejects_each_broken_binding(self):
        self.assertEqual(self.validate(self.output())["reference_records"], 1)
        other = "0" * 64
        broken = [
            dict(protocol="agent-sleep-oss-offline-output/2"), dict(synthetic_only=False),
            dict(agent_commit="0" * 40),
            dict(executed_source_sha256=dict(worker.SOURCE_HASHES, **{"src/tail.py": other})),
            dict(task_sha256=other), dict(reference_sha256=other),
            dict(target_notes_sha256=other), dict(reference_records=2),
            dict(reference_records=True), dict(reference_channel="prompt"),
            dict(semantic_memory_use="used"), dict(performance_improvement="improved"),
            dict(ledger_rows=[]), dict(decisions="none"),
            dict(client_calls=[]),
            dict(client_calls=[dict(method="create_pull_request", repo="fixture/project")]),
            dict(target_calls={}), dict(target_calls={"elsewhere.py:f": 1}),
            dict(extra=1),
        ]
        for change in broken:
            with self.subTest(change=change), self.assertRaises(parent.CheckError):
                self.validate(self.output(**change))
        good = self.output()
        for raw in (good + b"\n", good.replace(b'"digest":', b'"digest": '), b"[]", b"",
                    b"{" + b" " * parent.MAX_OUTPUT_BYTES + b"}"):
            with self.subTest(raw=raw[:30]), self.assertRaises(parent.CheckError):
                self.validate(raw)
        with self.assertRaises(parent.CheckError):
            parent.validate_output(good, task=self.task + b" ", reference=self.reference)

    def test_stand_in_check_is_never_labelled_target_integration(self):
        raw = self.output()
        summary, doc = parent.check(self.repo, self.reference, git="/usr/bin/git",
                                    worker_argv=self.stand_in(raw))
        self.assertEqual(summary["worker_launch"], parent.STAND_IN_WORKER)
        self.assertIsNone(summary["worker_sha256"])
        self.assertEqual(summary["worker_output_sha256"], worker.digest(raw))
        self.assertIs(summary["delivery_and_use_verified"], False)
        self.assertEqual(summary["semantic_memory_use"], "not_evaluated")
        self.assertEqual(doc["task_sha256"], worker.digest(self.task))
        self.assertEqual(len(self.other_calls), 1)
        tampered = self.stand_in(self.output(reference_sha256="0" * 64))
        with self.assertRaises(parent.CheckError):
            parent.check(self.repo, self.reference, git="/usr/bin/git", worker_argv=tampered)


class ConsumerTests(ParentCase):
    def test_receipt_matches_journal_contract_without_use_claims(self):
        consumer = parent.journal_consumer(self.repo, git="/usr/bin/git",
                                           worker_argv=self.stand_in(self.output()))
        receipt = consumer(use_id="use-1", task_bytes=self.task,
                           reference_bytes=self.reference)
        self.assertEqual(set(receipt),
                         {"use_id", "task_sha256", "reference_sha256", "output_bytes"})
        self.assertEqual(receipt["use_id"], "use-1")
        self.assertEqual(receipt["task_sha256"], hashlib.sha256(self.task).hexdigest())
        self.assertEqual(receipt["reference_sha256"],
                         hashlib.sha256(self.reference).hexdigest())
        self.assertLessEqual(len(receipt["output_bytes"]), parent.MAX_RECEIPT_BYTES)
        report = worker.strict_json(receipt["output_bytes"])
        self.assertEqual(report["protocol"], parent.CHECK_PROTOCOL)
        self.assertEqual(report["worker_launch"], parent.STAND_IN_WORKER)
        self.assertIs(report["delivery_and_use_verified"], False)
        self.assertEqual(report["semantic_memory_use"], "not_evaluated")
        self.assertEqual(report["repository_identity"],
                         "local_origin_url_claim_unauthenticated")

    def test_consumer_refuses_other_tasks_and_references_before_any_process(self):
        consumer = parent.journal_consumer(self.repo, git="/usr/bin/git",
                                           worker_argv=self.stand_in(self.output()))
        bad = [dict(task_bytes=b"real issue text"), dict(task_bytes=self.task + b"\n"),
               dict(reference_bytes=reference(synthetic_only=False)),
               dict(reference_bytes="text"), dict(use_id="")]
        for change in bad:
            arguments = dict(use_id="use-1", task_bytes=self.task,
                             reference_bytes=self.reference)
            arguments.update(change)
            with self.subTest(change=list(change)), self.assertRaises(parent.CheckError):
                consumer(**arguments)
        self.assertEqual(self.other_calls, [])


if __name__ == "__main__":
    unittest.main()
