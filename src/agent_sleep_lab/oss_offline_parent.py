"""Parent checker/consumer for the private offline worker (stdlib only).

Reviewed bytes are frozen from Git *objects* of an explicit local repository
with read-only git calls; worktree files are never read, imported or executed,
and nothing is checked out or written to the target repository. Everything is
validated before a fresh isolated worker process is launched without a shell.

Limits that callers must not overstate:
- The origin URL is a local, mutable claim, not authenticated repository
  identity. The binding that matters is the pinned commit plus the SHA-256 of
  each of the reviewed blobs.
- A result produced through an injected worker argv is labelled as a stand-in
  and is never an actual target integration.
- No result here is verified delivery, semantic memory use, adoption or a
  verifier/evaluator receipt.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

from agent_sleep_lab import oss_offline_worker as worker

AGENT_REPOSITORY = "moruku36/oss-contributor-agent"
CONSUMER_ID = "oss-offline-parent"
CONSUMER_VERSION = "1"
CHECK_PROTOCOL = "agent-sleep-oss-offline-check/1"
OUTPUT_PROTOCOL = "agent-sleep-oss-offline-output/1"
REFERENCE_CHANNEL = "Target.notes; unused by triage with llm=None"
BUILTIN_WORKER = "builtin_pinned_worker"
STAND_IN_WORKER = "injected_stand_in_not_target_integration"
GIT_TIMEOUT = 10.0
WORKER_TIMEOUT = 30.0
MAX_GIT_TEXT_BYTES = 4096
MAX_OUTPUT_BYTES = 262144
MAX_RECEIPT_BYTES = 65536  # ReferenceUseJournal output cap
OUTPUT_KEYS = frozenset({
    "protocol", "synthetic_only", "agent_commit", "executed_source_sha256",
    "task_sha256", "reference_sha256", "target_notes_sha256", "reference_records",
    "reference_channel", "semantic_memory_use", "performance_improvement",
    "decisions", "ledger_rows", "client_calls", "still_pending_llm",
    "candidate_pool", "target_calls", "digest"})
_REMOTE = re.compile(
    r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    + re.escape(AGENT_REPOSITORY) + r"(?:\.git)?")


class CheckError(ValueError):
    """A preflight, process or output contract was not met; nothing is trusted."""


def bounded_run(argv, *, cwd, env, timeout, max_output, input_bytes=b""):
    """Run one absolute-path argv without a shell; bound wall time and stdout.

    stderr is discarded. Returns (exit code, stdout bytes). The process group
    is killed on timeout or when stdout exceeds ``max_output``.
    """
    if (type(argv) is not list or not argv or any(type(a) is not str for a in argv)
            or not os.path.isabs(argv[0])):
        raise CheckError("explicit absolute argv required")
    if type(input_bytes) is not bytes or type(env) is not dict:
        raise CheckError("explicit input bytes and environment required")
    deadline = time.monotonic() + timeout
    proc = subprocess.Popen(
        argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        cwd=cwd, env=env, shell=False, close_fds=True, start_new_session=True)
    box = {}

    def feed():
        try:
            proc.stdin.write(input_bytes)
        except (OSError, ValueError):
            pass
        finally:
            try:
                proc.stdin.close()
            except (OSError, ValueError):
                pass

    def drain():
        try:
            box["out"] = proc.stdout.read(max_output + 1)
        except (OSError, ValueError):
            pass

    threads = [threading.Thread(target=feed, daemon=True),
               threading.Thread(target=drain, daemon=True)]
    try:
        for thread in threads:
            thread.start()
        threads[1].join(max(0.0, deadline - time.monotonic()))
        if threads[1].is_alive():
            raise CheckError("process timeout")
        if "out" not in box:
            raise CheckError("process output unreadable")
        if len(box["out"]) > max_output:
            raise CheckError("process output cap exceeded")
        try:
            code = proc.wait(max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise CheckError("process timeout") from None
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (OSError, AttributeError):
                proc.kill()
        proc.wait()
        for thread in threads:
            thread.join(1.0)
        if not threads[1].is_alive():
            proc.stdout.close()
    return code, box["out"]


def _git_argv(git, repo, *args):
    # Read-only plumbing only. No pager, replace refs, optional locks, fsmonitor
    # helper or transport (a partial clone must not lazily fetch).
    return [git, "--no-pager", "--no-replace-objects", "--no-optional-locks",
            "-c", "core.fsmonitor=false", "-c", "protocol.allow=never",
            "-C", repo, *args]


def freeze_sources(repo, *, git=None):
    """Return reviewed source bytes read from Git objects at the pinned commit.

    Calls made: ``rev-parse --show-toplevel``, ``config --local --get
    remote.origin.url``, ``rev-parse --verify <commit>^{commit}`` and one
    ``cat-file blob <commit>:<path>`` per reviewed path. The worktree and HEAD
    are irrelevant and never read.
    """
    if not isinstance(repo, (str, Path)) or not os.path.isabs(str(repo)):
        raise CheckError("explicit absolute local repository path required")
    repo = os.path.realpath(str(repo))
    if not os.path.isdir(repo):
        raise CheckError("local repository directory required")
    git = shutil.which("git") if git is None else git
    if type(git) is not str or not os.path.isabs(git):
        raise CheckError("absolute git executable required")
    commit = worker.AGENT_COMMIT
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise CheckError("full pinned commit required")
    with tempfile.TemporaryDirectory(prefix="asl-git-home-") as home:
        env = {
            "PATH": os.defpath, "HOME": home, "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull, "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_CEILING_DIRECTORIES": os.path.dirname(repo),
        }

        def call(cap, *args):
            code, out = bounded_run(_git_argv(git, repo, *args), cwd=home, env=env,
                                    timeout=GIT_TIMEOUT, max_output=cap)
            if code != 0:
                raise CheckError("read-only git call failed: " + args[0])
            return out

        def line(*args):
            out = call(MAX_GIT_TEXT_BYTES, *args)
            try:
                text = out.decode("utf-8")
            except UnicodeDecodeError:
                raise CheckError("git text output must be UTF-8") from None
            if not text.endswith("\n") or "\n" in text[:-1]:
                raise CheckError("single git output line required")
            return text[:-1]

        # No upward discovery: the explicit path itself must be the repository root.
        if line("rev-parse", "--show-toplevel") != repo:
            raise CheckError("explicit path is not the repository root")
        if not _REMOTE.fullmatch(line("config", "--local", "--get", "remote.origin.url")):
            raise CheckError("origin is not " + AGENT_REPOSITORY)
        if line("rev-parse", "--verify", "--quiet", "--end-of-options",
                commit + "^{commit}") != commit:
            raise CheckError("pinned commit object not present")
        sources = {}
        for name in worker.SOURCE_HASHES:
            data = call(worker.MAX_SOURCE_BYTES, "cat-file", "blob", commit + ":" + name)
            if worker.digest(data) != worker.SOURCE_HASHES[name]:
                raise CheckError("reviewed source hash mismatch: " + name)
            sources[name] = data
    try:
        worker.check_sources(sources)
    except ValueError as error:
        raise CheckError(str(error)) from None
    return sources


def builtin_task():
    return worker.encoded(worker.synthetic_task())


def prepare_payload(sources, reference_bytes):
    """Build and fully validate worker stdin bytes; nothing is launched here."""
    try:
        worker.check_sources(sources)
        doc = worker.validate_reference(reference_bytes)
        if worker.canonical_reference(doc) != reference_bytes:
            raise ValueError("canonical reference bundle bytes required")
        payload = worker.encoded(dict(
            sources={name: sources[name].hex() for name in worker.SOURCE_HASHES},
            task_hex=builtin_task().hex(), reference_hex=reference_bytes.hex()))
        if len(payload) > worker.MAX_INPUT_BYTES:
            raise ValueError("offline worker input cap exceeded")
        # Same validator the worker applies, run here before any launch.
        worker.validate_payload(worker.strict_json(payload))
    except CheckError:
        raise
    except (ValueError, RecursionError) as error:
        raise CheckError(str(error)) from None
    return payload


def builtin_worker_argv():
    if not sys.executable or not os.path.isabs(sys.executable):
        raise CheckError("absolute Python executable required")
    # -I: isolated (no PYTHON* variables, user site or script directory on
    # sys.path); -B: no bytecode writes.
    return [sys.executable, "-I", "-B", str(Path(worker.__file__).resolve())]


def launch(argv, payload, *, timeout=WORKER_TIMEOUT):
    """One fresh process: temporary cwd, sanitized environment, bounded I/O."""
    if type(payload) is not bytes or not 1 <= len(payload) <= worker.MAX_INPUT_BYTES:
        raise CheckError("bounded worker input required")
    with tempfile.TemporaryDirectory(prefix="asl-oss-offline-") as directory:
        directory = os.path.realpath(directory)
        env = {"LC_ALL": "C", "TZ": "UTC", "HOME": directory, "TMPDIR": directory}
        code, out = bounded_run(argv, cwd=directory, env=env, timeout=timeout,
                                max_output=MAX_OUTPUT_BYTES, input_bytes=payload)
    if code != 0:
        raise CheckError("offline worker failed")
    return out


def _objects(value, low, high):
    return (type(value) is list and low <= len(value) <= high
            and all(type(item) is dict for item in value))


def validate_output(raw, *, task, reference):
    """Check the worker output protocol and its source/task/reference/notes bindings.

    This establishes that the output is well formed and names the frozen
    inputs. It does not establish that the reference influenced any decision.
    """
    try:
        if type(raw) is not bytes or not 1 <= len(raw) <= MAX_OUTPUT_BYTES:
            raise ValueError("bounded worker output required")
        doc = worker.strict_json(raw)
        if type(doc) is not dict or set(doc) != OUTPUT_KEYS:
            raise ValueError("exact worker output keys required")
        if worker.encoded(doc) != raw:
            raise ValueError("canonical worker output required")
        records = len(worker.validate_reference(reference)["records"])
    except (ValueError, RecursionError) as error:
        raise CheckError(str(error)) from None
    if task != builtin_task():
        raise CheckError("only built-in synthetic task bytes accepted")
    if doc["protocol"] != OUTPUT_PROTOCOL or doc["synthetic_only"] is not True:
        raise CheckError("unexpected worker output protocol")
    if (doc["agent_commit"] != worker.AGENT_COMMIT
            or doc["executed_source_sha256"] != dict(worker.SOURCE_HASHES)):
        raise CheckError("worker output source binding mismatch")
    if doc["task_sha256"] != worker.digest(task):
        raise CheckError("worker output task binding mismatch")
    # Target.notes is the reference decoded as UTF-8, so its bytes are identical.
    if (doc["reference_sha256"] != worker.digest(reference)
            or doc["target_notes_sha256"] != worker.digest(reference)
            or type(doc["reference_records"]) is not int
            or doc["reference_records"] != records
            or doc["reference_channel"] != REFERENCE_CHANNEL):
        raise CheckError("worker output reference/notes binding mismatch")
    if (doc["semantic_memory_use"] != "not_evaluated"
            or doc["performance_improvement"] != "not_evaluated"):
        raise CheckError("worker output must not claim memory use or improvement")
    issues = len(worker.synthetic_task()["issues"])
    calls = doc["client_calls"]
    if (not _objects(doc["decisions"], 0, 64) or not _objects(doc["ledger_rows"], issues, issues)
            or not _objects(doc["candidate_pool"], 0, 64) or type(doc["digest"]) is not str):
        raise CheckError("worker output collection shape mismatch")
    if (not _objects(calls, 1, 4)
            or calls[0] != dict(method="list_open_issues", repo=worker.REPOSITORY)
            or any(set(call) != {"method", "repo", "number"}
                   or call["method"] != "find_existing_prs"
                   or call["repo"] != worker.REPOSITORY or type(call["number"]) is not int
                   for call in calls[1:])):
        raise CheckError("worker output client calls mismatch")
    trace = doc["target_calls"]
    prefixes = tuple(name + ":" for name in worker.SOURCE_HASHES)
    if (type(trace) is not dict or not trace
            or any(not key.startswith(prefixes) or type(count) is not int or count < 1
                   for key, count in trace.items())):
        raise CheckError("worker output must trace calls into reviewed sources")
    return doc


def check(repo, reference_bytes, *, git=None, worker_argv=None, timeout=WORKER_TIMEOUT):
    """Preflight, launch once, validate; return (summary, worker output document).

    ``worker_argv`` exists for stand-in process tests. Any injected argv is
    recorded as a stand-in; only the default launches the pinned worker.
    """
    sources = freeze_sources(repo, git=git)
    payload = prepare_payload(sources, reference_bytes)
    task = builtin_task()
    if worker_argv is None:
        argv, label = builtin_worker_argv(), BUILTIN_WORKER
        worker_sha256 = worker.digest(Path(argv[-1]).read_bytes())
    else:
        argv, label, worker_sha256 = worker_argv, STAND_IN_WORKER, None
    raw = launch(argv, payload, timeout=timeout)
    doc = validate_output(raw, task=task, reference=reference_bytes)
    summary = dict(
        protocol=CHECK_PROTOCOL, synthetic_only=True,
        agent_repository=AGENT_REPOSITORY,
        repository_identity="local_origin_url_claim_unauthenticated",
        agent_commit=worker.AGENT_COMMIT, source_sha256=dict(worker.SOURCE_HASHES),
        worker_launch=label, worker_sha256=worker_sha256,
        task_sha256=doc["task_sha256"], reference_sha256=doc["reference_sha256"],
        target_notes_sha256=doc["target_notes_sha256"],
        reference_records=doc["reference_records"], reference_channel=REFERENCE_CHANNEL,
        worker_output_sha256=worker.digest(raw), decisions=len(doc["decisions"]),
        semantic_memory_use="not_evaluated", performance_improvement="not_evaluated",
        delivery_and_use_verified=False)
    return summary, doc


def journal_consumer(repo, *, git=None, worker_argv=None, timeout=WORKER_TIMEOUT):
    """Local consumer with the ReferenceUseJournal.dispatch signature.

    The receipt is this process's own unreviewed report. It is not verified
    delivery, semantic memory use, adoption or a verifier/evaluator receipt.
    Any rejected input raises before a worker is launched, which the journal
    records as an unknown outcome and never retries.
    """
    def consumer(*, use_id, task_bytes, reference_bytes):
        if type(use_id) is not str or not use_id:
            raise CheckError("reference use identity required")
        if type(task_bytes) is not bytes or task_bytes != builtin_task():
            raise CheckError("only built-in synthetic task bytes accepted")
        if type(reference_bytes) is not bytes:
            raise CheckError("reference bytes required")
        summary, _ = check(repo, reference_bytes, git=git, worker_argv=worker_argv,
                           timeout=timeout)
        output = worker.encoded(summary)
        if len(output) > MAX_RECEIPT_BYTES:
            raise CheckError("consumer receipt output cap exceeded")
        return dict(use_id=use_id, task_sha256=worker.digest(task_bytes),
                    reference_sha256=worker.digest(reference_bytes), output_bytes=output)
    return consumer
