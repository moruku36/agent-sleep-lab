"""Byte-identical public OSS pin for offline tests; no replacement target code."""
from pathlib import Path

from agent_sleep_lab import oss_offline_worker as worker


def pinned_sources():
    document = worker.strict_json(
        (Path(__file__).parent / "fixtures/oss-pinned-sources.json").read_bytes())
    if (document["commit"] != worker.AGENT_COMMIT
            or document["repository"] != "moruku36/oss-contributor-agent"):
        raise ValueError("test source fixture pin mismatch")
    sources = {name: text.encode("utf-8") for name, text in document["sources"].items()}
    worker.check_sources(sources)  # no pin substitution, before any compilation
    return sources
