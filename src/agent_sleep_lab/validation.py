"""Offline validation of event JSONL, memory documents and promotion requests.

Scope (Gate 1): strict JSON parsing, JSON Schema validation against the packaged
local schemas, and a few input-local consistency checks. Nothing here resolves
references, authenticates evidence, authorizes or adopts anything, or touches the
network. A valid result means "well-formed against the design contract" only.
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any, Callable

from jsonschema import Draft7Validator, Draft202012Validator, FormatChecker
from referencing import Registry

from agent_sleep_lab.diagnostics import Report, ascii_safe
from agent_sleep_lab.strictjson import (
    StrictJSONError,
    decode_utf8,
    loads_strict,
    loads_strict_bytes,
)

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_RECORDS = 10_000
MAX_ERRORS_PER_RECORD = 10

_EXTERNAL_REF_KEYS = ("$ref", "$dynamicRef", "$recursiveRef")


class SchemaLoadError(RuntimeError):
    """A packaged schema is missing, malformed, or not self-contained."""


class InputError(Exception):
    """The input file could not be read (not a validation failure of its content)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Contract:
    kind: str  # CLI name
    schema_file: str
    validator_cls: type
    shape: str  # "jsonl" | "object_or_array" | "object"


CONTRACTS: dict[str, Contract] = {
    "events": Contract("events", "event.schema.json", Draft7Validator, "jsonl"),
    "memory": Contract("memory", "memory.schema.json", Draft7Validator, "object_or_array"),
    "promotion": Contract(
        "promotion", "promotion-request.schema.json", Draft202012Validator, "object"
    ),
}

_DIALECT_URIS = {
    Draft7Validator: "http://json-schema.org/draft-07/schema#",
    Draft202012Validator: "https://json-schema.org/draft/2020-12/schema",
}


# --------------------------------------------------------------------------- schemas


def schema_bytes(schema_file: str) -> bytes:
    """Raw bytes of a packaged schema (read from package data, never from a URL)."""
    try:
        return resources.files("agent_sleep_lab").joinpath("schemas", schema_file).read_bytes()
    except OSError as exc:
        raise SchemaLoadError(f"packaged schema {schema_file} is unavailable") from exc


def _deny_retrieve(uri: str) -> Any:
    raise LookupError(f"external schema resolution is disabled (requested {ascii_safe(uri)})")


def make_registry() -> Registry:
    """Empty registry whose retrieval hook always refuses (no file/network lookups)."""
    return Registry(retrieve=_deny_retrieve)  # type: ignore[arg-type]


def assert_self_contained(schema: object) -> None:
    """Reject any reference that is not a same-document ``#...`` fragment."""
    stack = [schema]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                if key in _EXTERNAL_REF_KEYS:
                    if not (isinstance(value, str) and value.startswith("#")):
                        raise SchemaLoadError(
                            f"external schema reference is not allowed ({key}: "
                            f"{ascii_safe(value, 80)})"
                        )
                stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)


def build_validator(schema: dict[str, Any], validator_cls: type) -> Any:
    """Validator with date-time checking enforced and external resolution disabled."""
    assert_self_contained(schema)
    expected = _DIALECT_URIS[validator_cls]
    if schema.get("$schema") != expected:
        raise SchemaLoadError("schema declares an unexpected $schema dialect")
    validator_cls.check_schema(schema)
    checker = FormatChecker()
    if "date-time" not in checker.checkers:
        # jsonschema silently ignores unknown formats; refuse that for date-time.
        raise SchemaLoadError("date-time format checking unavailable (rfc3339-validator)")
    return validator_cls(schema, format_checker=checker, registry=make_registry())


@lru_cache(maxsize=None)
def _validator_for(kind: str) -> tuple[Any, str]:
    contract = CONTRACTS[kind]
    try:
        schema = loads_strict_bytes(schema_bytes(contract.schema_file))
    except StrictJSONError as exc:
        raise SchemaLoadError(f"packaged schema {contract.schema_file} is malformed") from exc
    if not isinstance(schema, dict):
        raise SchemaLoadError("packaged schema is not an object")
    version = schema["properties"]["schema_version"]["const"]
    return build_validator(schema, contract.validator_cls), version


# --------------------------------------------------------------------------- diagnostics


def _pointer(path: Any) -> str:
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in path)


def _describe(error: Any) -> tuple[str, str]:
    """Static, bounded description: never echoes the offending instance value."""
    kw = error.validator
    code = f"schema.{kw}"
    if kw == "required":
        return code, error.message  # names a missing field from the schema only
    if kw == "additionalProperties":
        props = error.schema.get("properties", {})
        extras = sorted(str(k) for k in error.instance if k not in props)
        shown = ", ".join(repr(ascii_safe(k, 40)) for k in extras[:5])
        more = f" (+{len(extras) - 5} more)" if len(extras) > 5 else ""
        return code, f"unexpected field(s): {shown}{more}"
    if kw == "format":
        return code, f"value is not a valid {ascii_safe(error.validator_value, 40)}"
    if kw == "type":
        wanted = error.validator_value
        wanted = ", ".join(wanted) if isinstance(wanted, list) else wanted
        return code, f"value has the wrong type (expected {ascii_safe(wanted, 60)})"
    if kw in ("const", "enum"):
        return code, "value is not one of the allowed values"
    if kw in ("anyOf", "oneOf"):
        return code, "value does not match any allowed form"
    return code, f"value violates schema keyword '{ascii_safe(kw, 40)}'"


def _validate_record(
    kind: str,
    record: object,
    report: Report,
    ordinal: int,
    line: int | None,
) -> bool:
    """Schema-validate one record. Returns True iff it is schema-valid."""
    validator, version = _validator_for(kind)
    where: dict[str, Any] = {"record": ordinal}
    if line is not None:
        where["line"] = line
    if not isinstance(record, dict):
        report.error("record.not_object", "record must be a JSON object", pointer="", **where)
        return False
    if "schema_version" in record:
        found = record["schema_version"]
        if not (type(found) is str and found == version):
            shown = ascii_safe(found, 40) if isinstance(found, str) else type(found).__name__
            report.error(
                "record.unknown_version",
                f"unsupported schema_version ({shown}); expected {version!r}",
                pointer="/schema_version",
                **where,
            )
            return False
    errors = sorted(validator.iter_errors(record), key=lambda e: (list(map(str, e.path)), e.validator))
    for error in errors[:MAX_ERRORS_PER_RECORD]:
        code, message = _describe(error)
        report.error(code, message, pointer=_pointer(error.absolute_path), **where)
    if len(errors) > MAX_ERRORS_PER_RECORD:
        report.error(
            "schema.more_errors",
            f"{len(errors) - MAX_ERRORS_PER_RECORD} further schema error(s) in this record not shown",
            pointer="",
            **where,
        )
    return not errors


# --------------------------------------------------------------------------- semantic


def _semantic_event(record: dict[str, Any], report: Report, where: dict[str, Any]) -> None:
    if record.get("corrects_event_id") is not None and record["corrects_event_id"] == record["event_id"]:
        report.error(
            "event.corrects_self", "event corrects itself", pointer="/corrects_event_id", **where
        )


def _semantic_memory(record: dict[str, Any], report: Report, where: dict[str, Any]) -> None:
    verification = record["verification"]
    if record["status"] == "verified":
        verifier = verification["verifier"]
        if verification["result"] != "confirmed" or not (isinstance(verifier, str) and verifier):
            report.error(
                "memory.verified_unconfirmed",
                "status 'verified' needs verification.result 'confirmed' and a non-empty verifier",
                pointer="/status",
                **where,
            )
        if record["kind"] == "hypothesis":
            report.error(
                "memory.hypothesis_verified",
                "a hypothesis must stay 'candidate' until confirmed as a fact or procedure",
                pointer="/status",
                **where,
            )
    if record["memory_id"] in record["supersedes"]:
        report.error(
            "memory.supersedes_self", "memory supersedes itself", pointer="/supersedes", **where
        )


_ID_FIELD = {"events": "event_id", "memory": "memory_id"}
_SEMANTIC: dict[str, Callable[[dict[str, Any], Report, dict[str, Any]], None]] = {
    "events": _semantic_event,
    "memory": _semantic_memory,
}


class _RecordChecker:
    """Validates records of one kind, tracking duplicate IDs within the input."""

    def __init__(self, kind: str, report: Report) -> None:
        self.kind = kind
        self.report = report
        self.seen: dict[str, tuple[int, str]] = {}
        self.count = 0

    def check(self, record: object, ordinal: int, line: int | None = None) -> None:
        self.count += 1
        if not _validate_record(self.kind, record, self.report, ordinal, line):
            return
        assert isinstance(record, dict)
        where: dict[str, Any] = {"record": ordinal}
        if line is not None:
            where["line"] = line
        semantic = _SEMANTIC.get(self.kind)
        if semantic is not None:
            semantic(record, self.report, where)
        id_field = _ID_FIELD.get(self.kind)
        if id_field is None:
            return
        identity = record[id_field]
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
        previous = self.seen.get(identity)
        if previous is None:
            self.seen[identity] = (ordinal, canonical)
        elif previous[1] == canonical:
            self.report.warning(
                "id.duplicate_identical",
                f"{id_field} repeats record {previous[0]} with identical content",
                pointer=f"/{id_field}",
                **where,
            )
        else:
            self.report.error(
                "id.duplicate_conflict",
                f"{id_field} repeats record {previous[0]} with different content",
                pointer=f"/{id_field}",
                **where,
            )


# --------------------------------------------------------------------------- documents


def _syntax_error(report: Report, exc: StrictJSONError, **where: Any) -> None:
    if exc.line is not None:
        where.setdefault("line", exc.line)
    if exc.column is not None:
        where.setdefault("column", exc.column)
    report.error(exc.code, exc.message, **where)


def _validate_jsonl(kind: str, data: bytes, report: Report) -> int:
    checker = _RecordChecker(kind, report)
    lines = data.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    for index, raw in enumerate(lines, start=1):
        if not raw.strip(b" \t\r"):
            report.error("jsonl.blank_line", "blank lines are not allowed", line=index)
            continue
        if checker.count >= MAX_RECORDS:
            report.error("input.too_many_records", f"more than {MAX_RECORDS} records", line=index)
            break
        if len(raw) > MAX_LINE_BYTES:
            checker.count += 1
            report.error(
                "jsonl.line_too_long",
                f"line exceeds {MAX_LINE_BYTES} bytes",
                line=index,
                record=checker.count,
            )
            continue
        try:
            record = loads_strict(decode_utf8(raw))
        except StrictJSONError as exc:
            checker.count += 1
            _syntax_error(report, exc, line=index, record=checker.count)
            continue
        checker.check(record, checker.count + 1, line=index)
    if checker.count == 0 and report.error_count == 0:
        report.warning("input.no_records", "input contains no records")
    return checker.count


def _validate_memory(data: bytes, report: Report) -> int:
    try:
        document = loads_strict_bytes(data)
    except StrictJSONError as exc:
        _syntax_error(report, exc)
        return 0
    checker = _RecordChecker("memory", report)
    if isinstance(document, list):
        if len(document) > MAX_RECORDS:
            report.error("input.too_many_records", f"more than {MAX_RECORDS} records")
            return 0
        for ordinal, item in enumerate(document, start=1):
            checker.check(item, ordinal)
        if not document:
            report.warning("input.no_records", "array contains no memory objects")
    elif isinstance(document, dict):
        checker.check(document, 1)
    else:
        report.error(
            "document.not_object_or_array", "memory input must be an object or an array", pointer=""
        )
    return checker.count


def _validate_promotion(data: bytes, report: Report) -> int:
    try:
        document = loads_strict_bytes(data)
    except StrictJSONError as exc:
        _syntax_error(report, exc)
        return 0
    if isinstance(document, list):
        report.error(
            "document.not_object", "a promotion request must be a single object", pointer=""
        )
        return 0
    checker = _RecordChecker("promotion", report)
    checker.check(document, 1)
    return checker.count


@dataclass(frozen=True)
class ValidationResult:
    kind: str
    records: int
    report: Report

    @property
    def valid(self) -> bool:
        return self.report.error_count == 0


def validate_bytes(kind: str, data: bytes, max_diagnostics: int = 50) -> ValidationResult:
    """Validate raw bytes as ``kind`` (one of :data:`CONTRACTS`). Pure; no I/O."""
    if kind not in CONTRACTS:
        raise ValueError(f"unknown kind {kind!r}")
    report = Report(max_diagnostics=max_diagnostics)
    if len(data) > MAX_FILE_BYTES:
        report.error("input.too_large", f"input exceeds {MAX_FILE_BYTES} bytes")
        return ValidationResult(kind, 0, report)
    if kind == "events":
        count = _validate_jsonl(kind, data, report)
    elif kind == "memory":
        count = _validate_memory(data, report)
    else:
        count = _validate_promotion(data, report)
    return ValidationResult(kind, count, report)


def read_input(path: str, max_bytes: int = MAX_FILE_BYTES) -> bytes:
    """Read a regular file read-only, bounded; never blocks on FIFOs/devices."""
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        raise InputError("io.not_found", "input file not found") from None
    except PermissionError:
        raise InputError("io.permission_denied", "input file is not readable") from None
    except OSError as exc:
        raise InputError("io.open_failed", f"cannot open input ({exc.strerror or 'error'})") from None
    try:
        is_regular = stat.S_ISREG(os.fstat(fd).st_mode)
    except OSError:
        os.close(fd)
        raise InputError("io.read_failed", "cannot inspect input") from None
    if not is_regular:
        os.close(fd)
        raise InputError("io.not_regular_file", "input is not a regular file")
    try:
        with os.fdopen(fd, "rb") as handle:  # takes ownership of fd
            data = handle.read(max_bytes + 1)
    except OSError as exc:
        raise InputError("io.read_failed", f"cannot read input ({exc.strerror or 'error'})") from None
    if len(data) > max_bytes:
        raise InputError("io.too_large", f"input exceeds {max_bytes} bytes")
    return data


def validate_file(kind: str, path: str, max_diagnostics: int = 50) -> ValidationResult:
    return validate_bytes(kind, read_input(path), max_diagnostics)
