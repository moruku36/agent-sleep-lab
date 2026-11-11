"""Strict offline read-only adopted-reference -> pinned request preparation.

Only the built-in v1 synthetic task and pinned prompt-capture worker are wired
here. No initialization, writes, journals, plugins or provider dispatch imports.
Preparation is called once, after a nonempty current-policy retrieval. A second
read transaction rechecks the context before any artifact is returned.
"""
from __future__ import annotations

from contextlib import closing
from pathlib import Path

from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.oss_bridge import CollectOnlyBridge
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_prompt_capture as capture
from agent_sleep_lab.oss_read_config import (
    MAX_INPUT_BYTES, MAX_PATH_CHARS, _boundaries, _exact, _file, _id, _read,
)
from agent_sleep_lab.provenance import canonical_json, sha256_hex
from agent_sleep_lab.strictjson import loads_strict_bytes

PROTOCOL = "agent-sleep-oss-prepare-input/1"
OUTPUT_PROTOCOL = "agent-sleep-oss-prepare-output/1"
MANIFEST_KEYS = {"protocol", "target_repo", "bridge", "retrieval"}
RETRIEVAL_KEYS = {"query", "max_bytes", "max_records"}


def _manifest(doc):
    _exact(doc, MANIFEST_KEYS)
    if doc["protocol"] != PROTOCOL:
        raise ValueError("unsupported preparation input protocol")
    bridge = doc["bridge"]
    _exact(bridge, {"scope", "repository", "agent_commit"})
    _exact(bridge["scope"], {"project", "task_family"})
    for value in bridge["scope"].values():
        _id(value)
    if (bridge["repository"] != worker.REPOSITORY
            or bridge["agent_commit"] != worker.AGENT_COMMIT):
        raise ValueError("bridge must match the pinned synthetic task")
    retrieval = doc["retrieval"]
    _exact(retrieval, RETRIEVAL_KEYS)
    query = retrieval["query"]
    if (type(query) is not str or not query.strip() or len(query) > 1024
            or not query.isprintable()):
        raise ValueError("explicit bounded printable retrieval query required")
    for key, limit in (("max_bytes", worker.MAX_REFERENCE_BYTES),
                       ("max_records", worker.MAX_REFERENCE_RECORDS)):
        if type(retrieval[key]) is not int or not 1 <= retrieval[key] <= limit:
            raise ValueError("retrieval cap out of range")
    repo = doc["target_repo"]
    if (type(repo) is not str or not 1 <= len(repo) <= MAX_PATH_CHARS
            or "\x00" in repo or not Path(repo).is_absolute()):
        raise ValueError("explicit absolute target repository required")
    repo = Path(repo).resolve(strict=True)
    if not repo.is_dir():
        raise ValueError("existing target repository directory required")
    return repo


def _context_hash(bundle):
    # Match the existing reference-context convention: only the read timestamp
    # may advance. Retrieval itself still checks expiry against the CURRENT time.
    value = dict(bundle.document)
    value.pop("as_of")
    return sha256_hex(canonical_json(value))


def execute(manifest_path, *, store_config_path):
    """Return hash-bound request artifacts, or raise without emitting anything.

    Configuration gates are the unchanged oss-cost-report validators. The local
    store and Git origin are caller-controlled, not authenticated identities.
    No injected executable, preparation callable or dispatch option is accepted.
    """
    doc = loads_strict_bytes(_read(_file(manifest_path), MAX_INPUT_BYTES))
    repo = _manifest(doc)
    config = loads_strict_bytes(_read(_file(store_config_path), MAX_INPUT_BYTES))
    boundaries = _boundaries(config)
    path = _file(config["path"])
    with closing(AdoptionStore(path, **boundaries, read_only=True)) as store:
        bridge = CollectOnlyBridge(store, **doc["bridge"])
        bundle = bridge.reference_context(**doc["retrieval"])
        if not bundle.document["records"]:
            raise ValueError("at least one eligible returned experience record required")
        context = _context_hash(bundle)
        # Pass the exact frozen bytes. prepare_from_bridge would retrieve again
        # between the nonempty check and launch. prepare launches once for BOTH
        # arms and retains all existing repository/commit/blob and output checks.
        summary, artifact = capture.prepare(
            repo, bundle.bundle_bytes, reference_origin=capture.ORIGIN_BRIDGE)
        current = bridge.reference_context(**doc["retrieval"])
        if _context_hash(current) != context:
            raise ValueError("reference context changed during preparation")
        return dict(protocol=OUTPUT_PROTOCOL, synthetic_only=True,
                    context_sha256=context, summary=summary, capture=artifact)
