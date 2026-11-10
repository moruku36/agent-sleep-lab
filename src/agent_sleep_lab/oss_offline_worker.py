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


def validate_payload(payload):
    if type(payload) is not dict or set(payload) != {"sources", "task_hex", "reference_hex"}:
        raise ValueError("exact offline worker payload required")
    if type(payload["sources"]) is not dict or set(payload["sources"]) != set(SOURCE_HASHES):
        raise ValueError("exact reviewed source set required")
    sources = {name: bytes.fromhex(value) for name, value in payload["sources"].items()}
    if any(digest(data) != SOURCE_HASHES[name] for name, data in sources.items()):
        raise ValueError("reviewed source hash mismatch")
    task = bytes.fromhex(payload["task_hex"])
    reference = bytes.fromhex(payload["reference_hex"])
    if task != encoded(synthetic_task()):
        raise ValueError("only built-in synthetic task bytes accepted")
    if not 1 <= len(reference) <= 32768:
        raise ValueError("reference byte cap exceeded")
    doc = json.loads(reference)
    if (doc.get("schema_version") != "agent-sleep-reference-bundle/1"
            or doc.get("synthetic_only") is not True
            or doc.get("reference_data_only") is not True
            or doc.get("partition") != "experience"):
        raise ValueError("synthetic experience reference data required")
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


def load_sources(sources):
    # Config imports yaml, but this path never parses operational configuration.
    # An inert import shim avoids installing PyYAML; every YAML operation fails.
    yaml = types.ModuleType("yaml")
    def denied(*args, **kwargs):
        raise PermissionError("operational YAML loading is disabled")
    yaml.safe_load = denied
    yaml.YAMLError = ValueError
    sys.modules["yaml"] = yaml
    modules = {}
    for name, data in sources.items():
        package = name.endswith("/__init__.py")
        module_name = name[:-12].replace("/", ".") if package else name[:-3].replace("/", ".")
        spec = importlib.util.spec_from_loader(module_name, loader=None, is_package=package)
        module = importlib.util.module_from_spec(spec)
        module.__file__ = f"oss-pinned:{AGENT_COMMIT}/{name}"
        sys.modules[module_name] = module
        if "." in module_name:
            parent, attr = module_name.rsplit(".", 1)
            setattr(sys.modules[parent], attr, module)
        exec(compile(data, module.__file__, "exec"), module.__dict__)
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
    # JSON sorts mappings; use reviewed dependency order, never payload order.
    modules = load_sources({name: sources[name] for name in SOURCE_HASHES})
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
        reference_records=len(json.loads(reference)["records"]),
        reference_channel="Target.notes; unused by triage with llm=None",
        semantic_memory_use="not_evaluated", performance_improvement="not_evaluated",
        decisions=decisions, ledger_rows=rows, client_calls=calls,
        still_pending_llm=summary.still_pending_llm,
        candidate_pool=[asdict(entry) for entry in summary.candidate_pool],
        target_calls=trace, digest=rendered,
    )


if __name__ == "__main__":
    raw = sys.stdin.buffer.read(524289)
    if len(raw) > 524288:
        raise ValueError("offline worker input cap exceeded")
    sys.stdout.buffer.write(encoded(run(json.loads(raw))))
