"""Explicit offline reader wiring. No initialization, plugins or dispatch path."""
from __future__ import annotations

from contextlib import ExitStack, closing
from itertools import combinations
import re

from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.oss_bridge import CollectOnlyBridge
from agent_sleep_lab import oss_cost_accounting as accounting
from agent_sleep_lab.oss_execution_journal import ExecutionJournal
from agent_sleep_lab.oss_fixture_cohort import CohortRegistry, MAX_TASKS
from agent_sleep_lab.oss_read_config import (
    CONFIG_KEYS, MAX_INPUT_BYTES, MAX_PATH_CHARS,
    _boundaries, _exact, _file, _id, _pairs, _read,
)
from agent_sleep_lab.strictjson import loads_strict_bytes

PROTOCOL = "agent-sleep-oss-cost-report-input/1"
MANIFEST_KEYS = {"protocol", "target", "store_config", "journal", "bridges"}
BRIDGE_KEYS = {"scope", "repository", "agent_commit"}


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
