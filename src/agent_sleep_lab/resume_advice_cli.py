"""Read and render opt-in adopted experience for a human before resuming."""
from __future__ import annotations

from contextlib import closing
import json

from agent_sleep_lab.adoption_store import AdoptionStore
from agent_sleep_lab.oss_read_config import MAX_INPUT_BYTES, _boundaries, _file, _id, _read
from agent_sleep_lab.retrieval import retrieve_reference_bundle
from agent_sleep_lab.strictjson import loads_strict_bytes

MAX_RECORDS = 3
MAX_BUNDLE_BYTES = 32_768


def _quote(value: str) -> str:
    """Quote untrusted text without terminal control or bidi characters."""
    return json.dumps(value, ensure_ascii=True)


def _render(bundle, environment: str, candidate: str) -> str:
    scope = bundle["scope"]
    snapshot = bundle["snapshot_sha256"]
    lines = [
        "Reference only. This advice never authorizes execution or retry.",
        f"Scope: project={_quote(scope['project'])} task_family={_quote(scope['task_family'])}",
        f"Match: environment={_quote(environment)} candidate={_quote(candidate)}",
        f"As of: {_quote(bundle['as_of'])}",
        f"Snapshot SHA-256: {_quote(snapshot) if snapshot is not None else 'none'}",
        f"Policy revision: {bundle['policy']['revision']}",
    ]
    if not bundle["records"]:
        if bundle["counts"]["eligible"]:
            lines.append("No matching advice fits the reference byte limit.")
        else:
            lines.append("No matching advice.")

    for record in bundle["records"]:
        memory = record["memory"]
        expiry = memory["valid_until"]
        lines.extend((
            "",
            f"Memory ID: {_quote(record['memory_id'])}",
            f"Claim: {_quote(memory['claim'])}",
            f"Observed at: {_quote(memory['observed_at'])}",
            f"Memory valid until: {_quote(expiry) if expiry is not None else 'no expiry recorded'}",
        ))
        locators = {item["event_id"]: item["locator"] for item in memory["evidence"]}
        for evidence in record["evidence"]:
            event_id = evidence["event_id"]
            locator = locators[event_id]
            # Free-text locators can carry paths or URIs. Withhold locators with
            # path separators and leave out the separate source_uri field.
            locator_text = (
                "withheld (path or URI)" if "/" in locator or "\\" in locator else _quote(locator)
            )
            lines.extend((
                f"  Verified event: {_quote(event_id)} (SHA-256 {_quote(evidence['event_sha256'])})",
                f"  Source SHA-256: {_quote(evidence['source_sha256'])}",
                f"  Recorded locator (not independently verified): {locator_text}",
            ))
    return "\n".join(lines)


def execute(*, store_config_path: str, project: str, task_family: str,
            environment: str, candidate: str) -> str:
    for value in (project, task_family, environment, candidate):
        _id(value)
    # IDs may contain colons, but neither can contain the pair delimiter '/'.
    tag = f"resume-advice:{environment}/{candidate}"
    config = loads_strict_bytes(_read(_file(store_config_path), MAX_INPUT_BYTES))
    boundaries = _boundaries(config)
    with closing(AdoptionStore(_file(config["path"]), **boundaries, read_only=True)) as store:
        bundle = retrieve_reference_bundle(
            store, scope={"project": project, "task_family": task_family}, partition="experience",
            required_tag=tag, max_records=MAX_RECORDS, max_bytes=MAX_BUNDLE_BYTES,
        )
    return _render(bundle.document, environment, candidate)
