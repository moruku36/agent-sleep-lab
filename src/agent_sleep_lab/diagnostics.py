"""Bounded, deterministic, ASCII-only diagnostics shared by all validation stages."""

from __future__ import annotations

from dataclasses import dataclass

ERROR = "error"
WARNING = "warning"
MAX_MESSAGE_CHARS = 200


def ascii_safe(text: object, limit: int = MAX_MESSAGE_CHARS) -> str:
    """Clip ``text`` and escape everything outside printable ASCII.

    Output never contains control characters (terminal escapes), bidi overrides, or
    non-ASCII text, so printing cannot fail on a narrow locale or spoof a terminal.
    """
    raw = str(text)
    out: list[str] = []
    for ch in raw[:limit]:
        code = ord(ch)
        if 0x20 <= code < 0x7F:
            out.append(ch)
        elif code <= 0xFF:
            out.append(f"\\x{code:02x}")
        elif code <= 0xFFFF:
            out.append(f"\\u{code:04x}")
        else:
            out.append(f"\\U{code:08x}")
    if len(raw) > limit:
        out.append("...")
    return "".join(out)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    severity: str = ERROR
    line: int | None = None  # 1-based physical line (JSONL, JSON syntax errors)
    column: int | None = None  # 1-based column when known
    record: int | None = None  # 1-based record ordinal (JSONL line / array element)
    pointer: str | None = None  # RFC 6901 pointer inside the record; "" = record root

    def __post_init__(self) -> None:
        object.__setattr__(self, "message", ascii_safe(self.message))

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        for name in ("line", "column", "record", "pointer"):
            value = getattr(self, name)
            if value is not None:
                data[name] = value
        return data

    def render(self) -> str:
        where = []
        if self.line is not None:
            where.append(f"line {self.line}")
        if self.column is not None:
            where.append(f"col {self.column}")
        if self.record is not None:
            where.append(f"record {self.record}")
        if self.pointer is not None:
            where.append(f"at {self.pointer or '(record root)'}")
        location = (" " + " ".join(where)) if where else ""
        return f"{self.severity}[{self.code}]{location}: {self.message}"


class Report:
    """Collects diagnostics, storing at most ``max_diagnostics`` but counting all."""

    def __init__(self, max_diagnostics: int = 50) -> None:
        self.max_diagnostics = max_diagnostics
        self.diagnostics: list[Diagnostic] = []
        self.error_count = 0
        self.warning_count = 0
        self.suppressed = 0

    def add(self, diagnostic: Diagnostic) -> None:
        if diagnostic.severity == ERROR:
            self.error_count += 1
        else:
            self.warning_count += 1
        if len(self.diagnostics) < self.max_diagnostics:
            self.diagnostics.append(diagnostic)
        else:
            self.suppressed += 1

    def error(self, code: str, message: str, **where: object) -> None:
        self.add(Diagnostic(code, message, ERROR, **where))  # type: ignore[arg-type]

    def warning(self, code: str, message: str, **where: object) -> None:
        self.add(Diagnostic(code, message, WARNING, **where))  # type: ignore[arg-type]
