"""Explicit offline reader wiring. No initialization, plugins or dispatch path."""
from __future__ import annotations

from contextlib import ExitStack, closing
from itertools import combinations
from pathlib import Path
import re

from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.oss_bridge import CollectOnlyBridge
from agent_sleep_lab import oss_cost_accounting as accounting
from agent_sleep_lab.oss_execution_journal import ExecutionJournal
from agent_sleep_lab.oss_fixture_cohort import CohortRegistry, MAX_TASKS
from agent_sleep_lab.provenance import CaptureBoundary
from agent_sleep_lab.runtime_artifacts import EvaluatorBoundary, VerifierBoundary
from agent_sleep_lab.strictjson import loads_strict_bytes

PROTOCOL = "agent-sleep-oss-cost-report-input/1"
MAX_INPUT_BYTES = 32_768
MAX_PATH_CHARS = 4096
MANIFEST_KEYS = {"protocol", "target", "store_config", "journal", "bridges"}
CONFIG_KEYS = {"path", "capture", "verifier", "evaluator", "evaluation_protocol"}
BRIDGE_KEYS = {"scope", "repository", "agent_commit"}


def _exact(value, keys):
    if type(value) is not dict or set(value) != keys:
        raise ValueError("exact input fields required")


def _id(value):
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value):
        raise ValueError("bounded ID required")


def _file(value):
    if (type(value) is not str or not 1 <= len(value) <= MAX_PATH_CHARS
            or "\x00" in value or value.startswith("file:") or value == ":memory:"):
        raise ValueError("explicit local file path required")
    path = Path(value).resolve(strict=True)
    if not path.is_file():
        raise ValueError("existing regular file required")
    return path


def _read(path, limit):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if not 1 <= len(raw) <= limit:
        raise ValueError("input byte bound exceeded or empty input")
    return raw


def _pairs(value):
    if (type(value) is not list or not 1 <= len(value) <= 64
            or any(type(row) is not list or len(row) != 2
                   or any(type(item) is not str or not 1 <= len(item) <= 128 for item in row)
                   for row in value)):
        raise ValueError("bounded explicit pairs required")
    pairs = frozenset(tuple(row) for row in value)
    if len(pairs) != len(value):
        raise ValueError("duplicate configuration pair")
    return pairs


def _boundaries(config):
    # The existing local simulation identities are configuration, not caller authentication.
    _exact(config, CONFIG_KEYS)
    capture = dict(config["capture"]) if type(config["capture"]) is dict else None
    _exact(capture, {"adapter_id", "adapter_version", "allowed_origins", "authorizations",
                     "allowed_scopes"})
    origins, auth = capture["allowed_origins"], capture["authorizations"]
    if (type(origins) is not list or not 1 <= len(origins) <= 64
            or any(type(item) is not str for item in origins) or len(set(origins)) != len(origins)
            or type(auth) is not dict or not 1 <= len(auth) <= 64):
        raise ValueError("bounded capture configuration required")
    capture["allowed_origins"] = frozenset(origins)
    capture["allowed_scopes"] = _pairs(capture["allowed_scopes"])
    verifier, evaluator = config["verifier"], config["evaluator"]
    _exact(verifier, {"boundary_id", "boundary_version", "methods"})
    _exact(evaluator, {"boundary_id", "boundary_version", "protocols"})
    protocol = config["evaluation_protocol"]
    if (type(protocol) is not list or len(protocol) != 3
            or any(type(item) is not str for item in protocol)):
        raise ValueError("explicit evaluation protocol required")
    return dict(boundary=CaptureBoundary(**capture),
                verifier=VerifierBoundary(**(verifier | {"methods": _pairs(verifier["methods"])})),
                evaluator=EvaluatorBoundary(**(evaluator | {"protocols": _pairs(evaluator["protocols"])})),
                evaluation_protocol=tuple(protocol))


def _manifest(doc):
    if type(doc) is not dict:
        raise ValueError("input manifest required")
    target = doc.get("target")
    _exact(target, {"kind", "id"})
    if type(target["kind"]) is not str or target["kind"] not in {"pair", "cohort"}:
        raise ValueError("pair or cohort target required")
    _id(target["id"])
    _exact(doc, MANIFEST_KEYS | ({"cohort_registry"} if target["kind"] == "cohort" else set()))
    if doc["protocol"] != PROTOCOL:
        raise ValueError("unsupported report input protocol")
    bridges = doc["bridges"]
    if type(bridges) is not dict or len(bridges) > MAX_TASKS:
        raise ValueError("bounded explicit bridge mapping required")
    if target["kind"] == "pair" and set(bridges) != {target["id"]}:
        raise ValueError("pair requires exactly its own bridge")
    for plan_id, bridge in bridges.items():
        _id(plan_id)
        _exact(bridge, BRIDGE_KEYS)
        _exact(bridge["scope"], {"project", "task_family"})
        for item in bridge["scope"].values():
            _id(item)
        if (type(bridge["repository"]) is not str or len(bridge["repository"]) > 256
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", bridge["repository"])
                or type(bridge["agent_commit"]) is not str
                or not re.fullmatch(r"[0-9a-f]{40}", bridge["agent_commit"])):
            raise ValueError("explicit repository and immutable commit required")
    return target


def execute(manifest_path, *, observations_path=None):
    """Return only the accounting allowlist, passing observation bytes unchanged."""
    doc = loads_strict_bytes(_read(_file(manifest_path), MAX_INPUT_BYTES))
    target = _manifest(doc)
    config = loads_strict_bytes(_read(_file(doc["store_config"]), MAX_INPUT_BYTES))
    boundaries = _boundaries(config)
    paths = {"store": _file(config["path"]), "journal": _file(doc["journal"])}
    if target["kind"] == "cohort":
        paths["registry"] = _file(doc["cohort_registry"])
    # Resolve symbolic links AND compare inodes (hard links). Do this before any
    # store constructor, including the historical default writer constructors.
    for first, second in combinations(paths.values(), 2):
        if first == second or first.samefile(second):
            raise ValueError("evidence, execution and registry databases must be separate")
    artifact = (None if observations_path is None else
                _read(_file(observations_path), accounting.MAX_ARTIFACT_BYTES))
    with ExitStack() as stack:
        store = stack.enter_context(closing(AdoptionStore(paths["store"], **boundaries, read_only=True)))
        journal = stack.enter_context(closing(ExecutionJournal(paths["journal"], read_only=True)))
        bridges = {plan_id: CollectOnlyBridge(store, **identity)
                   for plan_id, identity in doc["bridges"].items()}
        if target["kind"] == "pair":
            return accounting.pair_report(journal, target["id"], bridges[target["id"]], artifact=artifact)
        registry = stack.enter_context(closing(CohortRegistry(paths["registry"], read_only=True)))
        return accounting.cohort_report(registry, target["id"], journal=journal,
                                        bridges=bridges, artifact=artifact)
