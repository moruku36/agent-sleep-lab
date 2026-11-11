"""Shared offline-reader input gates, extracted unchanged from oss-cost-report.

No accounting, execution journal, provider or adapter imports. The cost CLI
re-exports these validators so both readers use the same configuration gates.
"""
from __future__ import annotations

from pathlib import Path
import re

from agent_sleep_lab.provenance import CaptureBoundary
from agent_sleep_lab.runtime_artifacts import EvaluatorBoundary, VerifierBoundary

MAX_INPUT_BYTES = 32_768
MAX_PATH_CHARS = 4096
CONFIG_KEYS = {"path", "capture", "verifier", "evaluator", "evaluation_protocol"}


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
