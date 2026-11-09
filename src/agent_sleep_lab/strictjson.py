"""Strict, bounded JSON parsing for contract validation.

Stricter than ``json.loads`` defaults:

* duplicate object keys are rejected (the stdlib silently keeps the last one);
* ``NaN``, ``Infinity``, ``-Infinity`` and floats that overflow to infinity are rejected;
* a UTF-8 BOM, invalid UTF-8 and lone UTF-16 surrogates (``\\ud800`` escapes) are rejected;
* nesting depth and integer size are bounded, and parser failures such as
  ``RecursionError`` are converted into :class:`StrictJSONError`.

Nothing here touches the filesystem or the network.
"""

from __future__ import annotations

import json
import math
import re

MAX_DEPTH = 64

_SURROGATE = re.compile("[\ud800-\udfff]")


class StrictJSONError(ValueError):
    """Parse failure with a stable ``code`` and optional 1-based position."""

    def __init__(
        self,
        code: str,
        message: str,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.line = line
        self.column = column


def decode_utf8(data: bytes) -> str:
    """Strictly decode UTF-8; a leading BOM is an error, not silently skipped."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictJSONError(
            "json.invalid_utf8",
            f"input is not valid UTF-8 (byte offset {exc.start})",
            column=exc.start + 1,
        ) from None
    if text.startswith("﻿"):
        raise StrictJSONError("json.bom", "a UTF-8 byte order mark is not allowed", column=1)
    return text


def _reject_constant(name: str) -> object:
    raise StrictJSONError("json.non_finite_number", f"non-finite number {name} is not allowed")


def _parse_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise StrictJSONError(
            "json.non_finite_number", "number overflows to a non-finite value"
        )
    return value


def _object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError("json.duplicate_key", f"duplicate object key {key!r}")
        result[key] = value
    return result


def _check_tree(root: object) -> None:
    """Iteratively enforce depth and surrogate rules (no recursion on hostile input)."""
    stack: list[tuple[object, int]] = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        if isinstance(node, dict):
            if depth > MAX_DEPTH:
                raise StrictJSONError(
                    "json.too_deep", f"nesting deeper than {MAX_DEPTH} levels"
                )
            for key, value in node.items():
                if _SURROGATE.search(key):
                    raise StrictJSONError(
                        "json.lone_surrogate", "object key contains a lone surrogate"
                    )
                stack.append((value, depth + 1))
        elif isinstance(node, list):
            if depth > MAX_DEPTH:
                raise StrictJSONError(
                    "json.too_deep", f"nesting deeper than {MAX_DEPTH} levels"
                )
            for value in node:
                stack.append((value, depth + 1))
        elif isinstance(node, str) and _SURROGATE.search(node):
            raise StrictJSONError("json.lone_surrogate", "string contains a lone surrogate")


def loads_strict(text: str) -> object:
    """Parse one JSON document from ``text`` under the strict rules above."""
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
            parse_float=_parse_float,
        )
    except StrictJSONError:
        raise
    except json.JSONDecodeError as exc:
        raise StrictJSONError(
            "json.syntax", exc.msg, line=exc.lineno, column=exc.colno
        ) from None
    except RecursionError:
        raise StrictJSONError(
            "json.too_deep", f"nesting deeper than {MAX_DEPTH} levels"
        ) from None
    except ValueError:
        # e.g. integer literal exceeding the interpreter's digit limit
        raise StrictJSONError("json.number_too_large", "number literal is too large") from None
    _check_tree(value)
    return value


def loads_strict_bytes(data: bytes) -> object:
    """Decode strictly as UTF-8 (no BOM) and parse."""
    return loads_strict(decode_utf8(data))
