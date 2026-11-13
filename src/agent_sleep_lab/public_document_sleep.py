"""Pure offline public-document Light/Deep handoff; never a transport or authority.

Requests contain exact source bytes as UTF-8 text, not summaries posing as evidence.
Saved replies are untrusted proposals. Hashes identify bytes, not model execution,
origin, truth, permission or independent review. No IO, clients or receipt issuance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from .provenance import canonical_json, sha256_hex
from .strictjson import loads_strict_bytes

VERSION = "agent-sleep-public-document-sleep/1"
MAX_BYTES = 512 * 1024
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_SHA = re.compile(r"[0-9a-f]{64}")
REJECTION_CODES = frozenset({
    "invalid_protocol", "protocol_fields", "invalid_json", "byte_limit", "item_limit",
    "binding_mismatch", "source_selection", "invalid_excerpt", "invalid_context",
    "authority_claim", "excerpt_source_mismatch", "quotation_bound",
    "quotation_not_exact", "duplicate_excerpt",
})


class PublicDocumentSleepError(ValueError):
    """Content-free protocol or bound failure."""

    def __init__(self, message, *, code="invalid_protocol"):
        super().__init__(message)
        self.code = code if code in REJECTION_CODES else "invalid_protocol"


@dataclass(frozen=True)
class SelectionContext:
    """Optional public development task/rubric DATA, never answers or authority."""

    task: str
    rubric: str
    max_bytes: int

    def __post_init__(self):
        if type(self.max_bytes) is not int or not 1 <= self.max_bytes <= 8192:
            raise PublicDocumentSleepError("bounded selection context required", code="invalid_context")
        data = _text_bytes(self.task) + _text_bytes(self.rubric)
        if not data or len(data) > self.max_bytes:
            raise PublicDocumentSleepError("selection context exceeds byte bound", code="invalid_context")


def _context(value):
    _fields(value, ("task", "rubric", "max_bytes", "untrusted", "authority"))
    if value["untrusted"] is not True or value["authority"] is not False:
        raise PublicDocumentSleepError("selection context cannot grant authority", code="invalid_context")
    return SelectionContext(value["task"], value["rubric"], value["max_bytes"])


@dataclass(frozen=True)
class SleepLimits:
    """All limits are explicit UTF-8/canonical-JSON byte or item counts, not tokens."""

    max_request_bytes: int
    max_reply_bytes: int
    max_source_units: int
    max_candidates: int
    max_quotation_bytes: int

    def __post_init__(self):
        for value, maximum in (
            (self.max_request_bytes, MAX_BYTES), (self.max_reply_bytes, MAX_BYTES),
            (self.max_source_units, 256), (self.max_candidates, 32),
            (self.max_quotation_bytes, 65536),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise PublicDocumentSleepError("explicit positive bounded limits required")


def _fields(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise PublicDocumentSleepError("unexpected protocol fields", code="protocol_fields")
    return value


def _identifier(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise PublicDocumentSleepError("invalid identifier")
    return value


def _hash(value):
    if type(value) is not str or not _SHA.fullmatch(value):
        raise PublicDocumentSleepError("SHA-256 required")
    return value


def _text_bytes(value):
    if type(value) is not str:
        raise PublicDocumentSleepError("UTF-8 text required")
    try:
        return value.encode("utf-8")
    except UnicodeEncodeError:
        raise PublicDocumentSleepError("valid UTF-8 text required") from None


def _parse(data, bound):
    if type(data) is not bytes or not 1 <= len(data) <= bound:
        raise PublicDocumentSleepError("saved bytes exceed explicit bound", code="byte_limit")
    try:
        return loads_strict_bytes(data)
    except ValueError:
        # Do not leak hostile keys, source text or raw replies through diagnostics.
        raise PublicDocumentSleepError("strict JSON required", code="invalid_json") from None


def _canonical(value, bound):
    data = canonical_json(value)
    if len(data) > bound:
        raise PublicDocumentSleepError("canonical artifact exceeds explicit bound", code="byte_limit")
    return data


def _digest(value):
    return sha256_hex(canonical_json(value))


def _units(source_text, limits):
    data = _text_bytes(source_text)
    if not 1 <= len(data) <= 65536:
        raise PublicDocumentSleepError("bounded nonempty admitted source required")
    # Deterministic complete lines, preserving separators and UTF-8 exactly.
    lines = source_text.splitlines(keepends=True)
    if len(lines) > limits.max_source_units:
        raise PublicDocumentSleepError("source unit limit exceeded; no silent truncation")
    units, offset = [], 0
    for index, text in enumerate(lines):
        raw = _text_bytes(text)
        units.append({"unit_id": "line-" + str(index + 1),
                      "start_byte": offset, "end_byte": offset + len(raw),
                      "source_unit_sha256": sha256_hex(raw), "text": text})
        offset += len(raw)
    return units


def build_light_request(*, sleep_id, artifact_sha256, source_sha256, generation,
                        scope, expected_parent, origin_task, source_text, limits,
                        selection_context=None):
    """Canonical whole-body request from already-admitted bytes; no authorization."""
    if type(limits) is not SleepLimits:
        raise PublicDocumentSleepError("explicit SleepLimits required")
    _fields(scope, ("project", "task_family"))
    for value in (sleep_id, origin_task, *scope.values()):
        _identifier(value)
    for value in (artifact_sha256, source_sha256, expected_parent):
        _hash(value)
    if type(generation) is not int or generation < 1:
        raise PublicDocumentSleepError("admitted generation required")
    if sha256_hex(_text_bytes(source_text)) != source_sha256:
        raise PublicDocumentSleepError("exact source hash mismatch")
    body = {
        "schema_version": VERSION, "stage": "light",
        "binding": {"sleep_id": sleep_id, "artifact_sha256": artifact_sha256,
                    "source_sha256": source_sha256, "generation": generation,
                    "scope": dict(scope), "expected_parent": expected_parent,
                    "origin_task": origin_task},
        "limits": asdict(limits), "source_units": _units(source_text, limits),
        "source_is_untrusted_data": True, "grants_execution_or_review_authority": False,
    }
    if selection_context is not None:
        if type(selection_context) is not SelectionContext:
            raise PublicDocumentSleepError("explicit SelectionContext required", code="invalid_context")
        body["selection_context"] = dict(asdict(selection_context), untrusted=True, authority=False)
    return _canonical(body, limits.max_request_bytes)


def _request(data, stage):
    body = _parse(data, MAX_BYTES)
    keys = ["schema_version", "stage", "binding", "limits", "source_units",
            "source_is_untrusted_data", "grants_execution_or_review_authority"]
    if stage == "light" and type(body) is dict and "selection_context" in body:
        keys += ["selection_context"]
        _context(body["selection_context"])
    if stage == "deep":
        keys += ["light_request_sha256", "light_reply_sha256", "source_selection_sha256"]
    _fields(body, keys)
    if (body["schema_version"] != VERSION or body["stage"] != stage
            or body["source_is_untrusted_data"] is not True
            or body["grants_execution_or_review_authority"] is not False):
        raise PublicDocumentSleepError("wrong stage or protocol")
    binding = _fields(body["binding"], (
        "sleep_id", "artifact_sha256", "source_sha256", "generation",
        "scope", "expected_parent", "origin_task"))
    _fields(binding["scope"], ("project", "task_family"))
    for value in (binding["sleep_id"], binding["origin_task"], *binding["scope"].values()):
        _identifier(value)
    for name in ("artifact_sha256", "source_sha256", "expected_parent"):
        _hash(binding[name])
    if type(binding["generation"]) is not int or binding["generation"] < 1:
        raise PublicDocumentSleepError("invalid generation")
    if type(body["limits"]) is not dict or set(body["limits"]) != set(SleepLimits.__dataclass_fields__):
        raise PublicDocumentSleepError("explicit limits required")
    limits = SleepLimits(**body["limits"])
    if len(data) > limits.max_request_bytes or canonical_json(body) != data:
        raise PublicDocumentSleepError("bounded canonical request required")
    units = body["source_units"]
    if type(units) is not list or not 1 <= len(units) <= limits.max_source_units:
        raise PublicDocumentSleepError("bounded nonempty source selection required")
    seen, previous_end = set(), 0
    for unit in units:
        _fields(unit, ("unit_id", "start_byte", "end_byte", "source_unit_sha256", "text"))
        _identifier(unit["unit_id"])
        raw = _text_bytes(unit["text"])
        if (unit["unit_id"] in seen or not raw
                or type(unit["start_byte"]) is not int or type(unit["end_byte"]) is not int
                or unit["start_byte"] < previous_end
                or unit["end_byte"] != unit["start_byte"] + len(raw)
                or unit["end_byte"] > 65536
                or unit["source_unit_sha256"] != sha256_hex(raw)):
            raise PublicDocumentSleepError("invalid exact source unit")
        seen.add(unit["unit_id"])
        previous_end = unit["end_byte"]
    if stage == "light":
        text = "".join(unit["text"] for unit in units)
        if (_units(text, limits) != units
                or sha256_hex(_text_bytes(text)) != binding["source_sha256"]):
            raise PublicDocumentSleepError("whole source binding mismatch")
    else:
        for name in ("light_request_sha256", "light_reply_sha256", "source_selection_sha256"):
            _hash(body[name])
        if len(units) > limits.max_candidates or body["source_selection_sha256"] != _digest(units):
            raise PublicDocumentSleepError("deep source selection mismatch")
    return body, limits


def parse_light_result(request_bytes, result_bytes):
    """Validate the entire reply, then return selected *original* units in source order.

    Reply: {schema_version, stage:'light', request_sha256,
            selected:[{unit_id, source_unit_sha256}]}.
    No generated rationale, quotations, permissions or additional evidence accepted.
    """
    request, limits = _request(request_bytes, "light")
    reply = _fields(_parse(result_bytes, limits.max_reply_bytes),
                    ("schema_version", "stage", "request_sha256", "selected"))
    if (reply["schema_version"] != VERSION or reply["stage"] != "light"
            or reply["request_sha256"] != sha256_hex(request_bytes)):
        raise PublicDocumentSleepError("light reply request binding mismatch", code="binding_mismatch")
    if type(reply["selected"]) is not list or len(reply["selected"]) > limits.max_candidates:
        raise PublicDocumentSleepError("selected candidate limit exceeded", code="item_limit")
    units = {unit["unit_id"]: unit for unit in request["source_units"]}
    selected = set()
    for item in reply["selected"]:
        _fields(item, ("unit_id", "source_unit_sha256"))
        name = _identifier(item["unit_id"])
        if (name in selected or name not in units
                or item["source_unit_sha256"] != units[name]["source_unit_sha256"]):
            raise PublicDocumentSleepError("unknown, duplicate or changed source selection", code="source_selection")
        selected.add(name)
    return [unit for unit in request["source_units"] if unit["unit_id"] in selected]


def build_deep_request(light_request_bytes, light_result_bytes):
    """Return selected-only canonical Deep input, or None for terminal no-change."""
    light, limits = _request(light_request_bytes, "light")
    selected = parse_light_result(light_request_bytes, light_result_bytes)
    if not selected:
        return None
    deep = dict(light, stage="deep", source_units=selected,
                light_request_sha256=sha256_hex(light_request_bytes),
                light_reply_sha256=sha256_hex(light_result_bytes),
                source_selection_sha256=_digest(selected))
    # Context guides Light selection only; Deep binds it through the Light hash.
    deep.pop("selection_context", None)
    return _canonical(deep, limits.max_request_bytes)


def parse_deep_result(request_bytes, result_bytes):
    """Validate ALL excerpts before returning any; never verification or adoption.

    Reply: {schema_version, stage:'deep', request_sha256, source_selection_sha256,
            proposals:[{unit_id, source_unit_sha256, quotation,
                        untrusted:true, authority:false}]}.
    Quotations must be nonempty exact substrings of a selected original unit.
    """
    request, limits = _request(request_bytes, "deep")
    reply = _fields(_parse(result_bytes, limits.max_reply_bytes), (
        "schema_version", "stage", "request_sha256", "source_selection_sha256", "proposals"))
    if (reply["schema_version"] != VERSION or reply["stage"] != "deep"
            or reply["request_sha256"] != sha256_hex(request_bytes)
            or reply["source_selection_sha256"] != request["source_selection_sha256"]):
        raise PublicDocumentSleepError("deep reply request or selection binding mismatch", code="binding_mismatch")
    if type(reply["proposals"]) is not list or len(reply["proposals"]) > limits.max_candidates:
        raise PublicDocumentSleepError("proposal count limit exceeded", code="item_limit")
    units = {unit["unit_id"]: unit for unit in request["source_units"]}
    excerpts, seen = [], set()
    for item in reply["proposals"]:
        _fields(item, ("unit_id", "source_unit_sha256", "quotation", "untrusted", "authority"))
        name = _identifier(item["unit_id"])
        quotation = item["quotation"]
        if item["untrusted"] is not True or item["authority"] is not False:
            raise PublicDocumentSleepError("excerpt cannot grant authority", code="authority_claim")
        if name not in units or item["source_unit_sha256"] != units[name]["source_unit_sha256"]:
            raise PublicDocumentSleepError("excerpt source mismatch", code="excerpt_source_mismatch")
        raw = _text_bytes(quotation)
        if not 1 <= len(raw) <= limits.max_quotation_bytes:
            raise PublicDocumentSleepError("quotation exceeds bound", code="quotation_bound")
        if quotation not in units[name]["text"]:
            raise PublicDocumentSleepError("quotation is not exact source text", code="quotation_not_exact")
        if quotation in seen:
            raise PublicDocumentSleepError("duplicate quotation", code="duplicate_excerpt")
        seen.add(quotation)
        excerpts.append(dict(item))
    return excerpts
