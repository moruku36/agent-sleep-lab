"""Private stdlib-only worker for the reviewed OSS collect-only source pin.

No source is imported from the target checkout. The parent sends verified frozen
bytes; this worker verifies them again before compiling them in a fresh process.
This is a guard for reviewed code, not a sandbox for arbitrary hostile Python.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import types

AGENT_COMMIT = "e40b39c6258ac5a4446c38246bdfd7f5dc5dbf7b"
REPOSITORY = "fixture/project"
SOURCE_HASHES = {
    "src/__init__.py": "382556a10a66b2bccba0cb34b90753d4741d701f8992c5550f7b09108caed02d",
    "src/collector/__init__.py": "c4bc1c75e9b97f3276b318abeb126d2731f450f09e2a754d5e6935e6c4d22174",
    "src/agent/__init__.py": "98e3de8f5f23fa40661c36e9ca1319a178436e833140c748df7783b7248288e2",
    "src/collector/triager.py": "cadb1d9556cf29817e0f91198871eebda51e42e4d21a37745336b74accb9f273",
    "src/collector/github_client.py": "be751d1d73d0ead735c8fcacb9ea3153b0ea191df83ea1785974a1548670eba8",
    "src/config.py": "a291b0503a8dac97bb4145f4824bcf07f2ac12a4f74dd232678df80fd6719e7a",
    "src/collector/ledger.py": "43218ad7a5680a39e4d9de7f461f934e0caffa994e60f8e61792179f24030c25",
    "src/collector/digest.py": "02234fb0975e471b2c46da36b801dab0e53305d6ccddaa3924cb79ec4fb1ddec",
    "src/agent/prompts.py": "edb6cc1f898dc654e1044c85591a5b321c1c079b547cbdbde7b68fb85fe07ff0",
    "src/collector/llm_triage.py": "1cd465f12558d2d785267c8f5c9f5335ae82de8993b3a1e01c4a7c627fb84ba3",
    "src/collector/pipeline.py": "bc9d47371b2d23766413b56a2d71abbf75d20e6fee18bf3bc715ce25efe1e0bc",
}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def synthetic_task():
    # Built-in inputs only: there is deliberately no issue/log file importer.
    accepted = dict(title="Synthetic docs broken link", body="Synthetic tests.",
                    labels=["documentation", "good first issue"])
    return dict(
        protocol="agent-sleep-oss-offline/1", synthetic_only=True,
        agent_commit=AGENT_COMMIT, source_sha256=SOURCE_HASHES,
        repository=REPOSITORY, mode="collect-only", llm=None,
        issues=[dict(accepted, number=1),
                dict(number=2, title="Synthetic discussion", body="Synthetic.", labels=[]),
                dict(number=3, title="Synthetic docs", body="Synthetic tests.",
                     labels=["help wanted"]),
                dict(accepted, number=4), dict(accepted, number=5)],
    )


MAX_INPUT_BYTES = 524288
MAX_SOURCE_BYTES = 131072
MAX_TASK_BYTES = 8192
MAX_REFERENCE_BYTES = 32768
MAX_REFERENCE_RECORDS = 256
REFERENCE_SCHEMA = "agent-sleep-reference-bundle/1"
# Exact top-level keys emitted by agent_sleep_lab.retrieval; kept as a local
# copy because this worker must stay importable with the stdlib alone.
REFERENCE_KEYS = frozenset({
    "schema_version", "reference_data_only", "synthetic_only", "scope", "partition",
    "as_of", "snapshot_sha256", "policy", "exclusions", "budget", "counts", "records"})
_HEX = frozenset("0123456789abcdef")


def strict_json(data):
    """Parse bytes as one strict JSON value; every failure is a ValueError."""
    if type(data) is not bytes:
        raise ValueError("JSON input must be bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("JSON input must be valid UTF-8") from None
    if text.startswith("﻿"):
        raise ValueError("JSON byte order mark is not allowed")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def constant(name):
        raise ValueError("non-finite JSON number")

    def number(literal):
        value = float(literal)
        if value in (float("inf"), float("-inf")):
            raise ValueError("non-finite JSON number")
        return value

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant,
                          parse_float=number)
    except RecursionError:
        raise ValueError("JSON nesting too deep") from None


def from_hex(value, cap, label):
    """Decode bounded lowercase hex; bytes.fromhex alone tolerates whitespace/case."""
    if (type(value) is not str or len(value) % 2 or len(value) > 2 * cap
            or not _HEX.issuperset(value)):
        raise ValueError(f"{label}: bounded lowercase hex string required")
    return bytes.fromhex(value)


def validate_reference(reference):
    """Check the synthetic experience reference-bundle contract; return the document.

    This is a structural contract check on data. It does not verify that the
    bundle came from the adoption store or that any consumer used it.
    """
    if type(reference) is not bytes or not 1 <= len(reference) <= MAX_REFERENCE_BYTES:
        raise ValueError("reference byte cap exceeded")
    doc = strict_json(reference)
    if type(doc) is not dict or set(doc) != REFERENCE_KEYS:
        raise ValueError("exact reference bundle keys required")
    if (doc["schema_version"] != REFERENCE_SCHEMA
            or doc["synthetic_only"] is not True
            or doc["reference_data_only"] is not True
            or doc["partition"] != "experience"):
        raise ValueError("synthetic experience reference data required")
    records, counts, snapshot = doc["records"], doc["counts"], doc["snapshot_sha256"]
    if (type(records) is not list or len(records) > MAX_REFERENCE_RECORDS
            or any(type(record) is not dict for record in records)):
        raise ValueError("reference records must be a bounded list of objects")
    if (type(counts) is not dict or type(counts.get("returned")) is not int
            or counts["returned"] != len(records)):
        raise ValueError("reference record count mismatch")
    if snapshot is None:
        if records:
            raise ValueError("reference records require a snapshot")
    elif type(snapshot) is not str or len(snapshot) != 64 or not _HEX.issuperset(snapshot):
        raise ValueError("reference snapshot sha256 required")
    return doc


def check_sources(sources):
    """Require exactly the reviewed byte strings; nothing is compiled here."""
    if type(sources) is not dict or set(sources) != set(SOURCE_HASHES):
        raise ValueError("exact reviewed source set required")
    for name, data in sources.items():
        if type(data) is not bytes or len(data) > MAX_SOURCE_BYTES:
            raise ValueError("reviewed source byte cap exceeded")
        if digest(data) != SOURCE_HASHES[name]:
            raise ValueError("reviewed source hash mismatch")


def validate_payload(payload):
    """Validate without compiling or importing anything from the payload."""
    if type(payload) is not dict or set(payload) != {"sources", "task_hex", "reference_hex"}:
        raise ValueError("exact offline worker payload required")
    if type(payload["sources"]) is not dict or set(payload["sources"]) != set(SOURCE_HASHES):
        raise ValueError("exact reviewed source set required")
    sources = {name: from_hex(payload["sources"][name], MAX_SOURCE_BYTES, "source")
               for name in SOURCE_HASHES}
    check_sources(sources)
    task = from_hex(payload["task_hex"], MAX_TASK_BYTES, "task")
    if task != encoded(synthetic_task()):
        raise ValueError("only built-in synthetic task bytes accepted")
    reference = from_hex(payload["reference_hex"], MAX_REFERENCE_BYTES, "reference")
    validate_reference(reference)
    return sources, task, reference


def install_guards(directory):
    """Deny network/process actions and writes outside this worker's temp cwd."""
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    def audit(event, args):
        if (event.startswith(("socket.", "subprocess.", "ctypes.", "os.exec", "os.spawn"))
                or event in {"os.system", "os.fork", "os.forkpty", "os.posix_spawn",
                             "os.chdir", "os.putenv", "os.unsetenv"}):
            raise PermissionError("offline worker action denied")
        if event == "open":
            path, mode, flags = args
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
            if writing and (not isinstance(path, (str, bytes, os.PathLike))
                            or not Path(os.fsdecode(path)).resolve().is_relative_to(directory)):
                raise PermissionError("offline worker write outside temporary directory")
        if event == "sqlite3.connect":
            if Path(args[0]).resolve() != directory / "ledger.sqlite3":
                raise PermissionError("only temporary offline ledger allowed")

    sys.addaudithook(audit)


def module_plan():
    """Reviewed load order as (module name, source path, is_package) tuples.

    Order comes only from SOURCE_HASHES, never from payload/mapping order, and
    every parent package must precede its children.
    """
    plan = []
    for name in SOURCE_HASHES:
        package = name.endswith("/__init__.py")
        stem = name[:-12] if package else name[:-3]
        parts = stem.split("/")
        if (not name.endswith(".py") or parts[0] != "src"
                or not all(part.isidentifier() for part in parts)):
            raise ValueError("reviewed source path must be a src/ Python module")
        plan.append((".".join(parts), name, package))
    seen = set()
    for module_name, _, _ in plan:
        if module_name in seen:
            raise ValueError("duplicate reviewed module name")
        if "." in module_name and module_name.rsplit(".", 1)[0] not in seen:
            raise ValueError("reviewed load order must define parent packages first")
        seen.add(module_name)
    return plan


def load_sources(sources):
    """Execute exactly the reviewed bytes, in reviewed order, in a fresh process.

    Hashes are rechecked here so a direct caller cannot reach compile/exec with
    unreviewed bytes. All sources compile before any executes.
    """
    check_sources(sources)
    plan = module_plan()
    if any(module_name in sys.modules for module_name, _, _ in plan):
        raise RuntimeError("fresh process required: reviewed module name already loaded")
    # dont_inherit: this file's __future__ flags must not alter the pinned code.
    code = {name: compile(sources[name], f"oss-pinned:{AGENT_COMMIT}/{name}", "exec",
                          dont_inherit=True)
            for _, name, _ in plan}
    # Config imports yaml, but this path never parses operational configuration.
    # An inert import shim avoids installing PyYAML; every YAML operation fails.
    yaml = types.ModuleType("yaml")
    def denied(*args, **kwargs):
        raise PermissionError("operational YAML loading is disabled")
    yaml.safe_load = denied
    yaml.YAMLError = ValueError
    sys.modules["yaml"] = yaml
    modules = {}
    for module_name, name, package in plan:
        spec = importlib.util.spec_from_loader(module_name, loader=None, is_package=package)
        module = importlib.util.module_from_spec(spec)
        module.__file__ = f"oss-pinned:{AGENT_COMMIT}/{name}"
        sys.modules[module_name] = module
        if "." in module_name:
            parent, attr = module_name.rsplit(".", 1)
            setattr(sys.modules[parent], attr, module)
        exec(code[name], module.__dict__)
        modules[module_name] = module
    return modules


def run(payload):
    # Preload stdlib dependencies before the write/network guards and target code.
    import sqlite3  # noqa: F401
    import urllib.request  # noqa: F401
    from dataclasses import asdict
    from datetime import datetime, timezone

    sources, task, reference = validate_payload(payload)
    directory = Path.cwd().resolve()
    install_guards(directory)
    # load_sources uses the reviewed dependency order, never payload order.
    modules = load_sources(sources)
    config = modules["src.config"]
    github = modules["src.collector.github_client"]
    ledger_mod = modules["src.collector.ledger"]
    pipeline = modules["src.collector.pipeline"]
    digest_mod = modules["src.collector.digest"]
    target = config.Target(repo=REPOSITORY, enabled=True, mode="collect-only",
                           notes=reference.decode("utf-8"))
    # No patch/PR action is called, including the target's attempt entrypoints.
    if not target.collect_only:
        raise ValueError("collect-only gate required")
    rules = config.Rules()  # actual defaults; no production YAML or env lookup
    if (rules.triage_accept_threshold, rules.triage_skip_threshold) != (0.60, 0.40):
        raise ValueError("unexpected target thresholds")
    calls = []

    class OfflineClient:
        def list_open_issues(self, repo, labels):
            if calls or repo != REPOSITORY or labels != []:
                raise ValueError("unexpected collection call")
            calls.append(dict(method="list_open_issues", repo=repo))
            return [github.IssueRef(repo=repo, url=f"fixture://issue/{item['number']}", **item)
                    for item in synthetic_task()["issues"]]

        def find_existing_prs(self, repo, number):
            expected = [1, 4, 5]
            seen = [c["number"] for c in calls if "number" in c]
            if repo != REPOSITORY or len(seen) >= 3 or number != expected[len(seen)]:
                raise ValueError("unexpected duplicate-check call")
            calls.append(dict(method="find_existing_prs", repo=repo, number=number))
            if number == 5:
                raise github.GitHubAPIError("synthetic offline duplicate-check failure")
            return [dict(number=44, url="fixture://pull/44")] if number == 4 else []

    trace = {}
    def profile(frame, event, arg):
        if event == "call" and frame.f_code.co_filename.startswith("oss-pinned:"):
            key = frame.f_code.co_filename.split("/", 1)[1] + ":" + frame.f_code.co_qualname
            trace[key] = trace.get(key, 0) + 1

    with ledger_mod.Ledger(directory / "ledger.sqlite3") as ledger:
        sys.setprofile(profile)
        try:
            summary = pipeline.run_collection_pass(
                targets=[target], rules=rules, client=OfflineClient(), store=ledger,
                llm=None, now=datetime(2026, 11, 10, tzinfo=timezone.utc))
            rendered = digest_mod.render_digest(summary)
        finally:
            sys.setprofile(None)
        decisions = [asdict(d) for d in summary.decisions]
        rows = [asdict(ledger.get(REPOSITORY, n)) for n in range(1, 6)]
    return dict(
        protocol="agent-sleep-oss-offline-output/1", synthetic_only=True,
        agent_commit=AGENT_COMMIT, executed_source_sha256=SOURCE_HASHES,
        task_sha256=digest(task), reference_sha256=digest(reference),
        target_notes_sha256=digest(target.notes.encode("utf-8")),
        reference_records=len(validate_reference(reference)["records"]),
        reference_channel="Target.notes; unused by triage with llm=None",
        semantic_memory_use="not_evaluated", performance_improvement="not_evaluated",
        decisions=decisions, ledger_rows=rows, client_calls=calls,
        still_pending_llm=summary.still_pending_llm,
        candidate_pool=[asdict(entry) for entry in summary.candidate_pool],
        target_calls=trace, digest=rendered,
    )


if __name__ == "__main__":
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("offline worker input cap exceeded")
    sys.stdout.buffer.write(encoded(run(strict_json(raw))))
