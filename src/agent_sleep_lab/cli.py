"""Read-only command line interface (Gate 1).

    agent-sleep-lab validate {events,memory,promotion} PATH [--format text|json]
    agent-sleep-lab schemas

Exit codes: 0 valid (warnings allowed), 1 content invalid, 2 usage or input could
not be read. The CLI only reads the named file; it writes nothing, resolves no
references, and makes no network calls. Output is ASCII-only and bounded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Sequence, TextIO

from agent_sleep_lab import __version__
from agent_sleep_lab.diagnostics import ascii_safe
from agent_sleep_lab.validation import (
    CONTRACTS,
    InputError,
    SchemaLoadError,
    schema_bytes,
    validate_file,
)

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_ERROR = 2


def _bounded_int(text: str) -> int:
    value = int(text)
    if not 1 <= value <= 1000:
        raise argparse.ArgumentTypeError("must be between 1 and 1000")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-sleep-lab",
        description="Read-only offline contract validation for Agent Sleep Lab (Gate 1).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate one input file against a contract")
    validate.add_argument("kind", choices=sorted(CONTRACTS), help="contract to validate against")
    validate.add_argument("path", help="file to read (never modified)")
    validate.add_argument("--format", choices=("text", "json"), default="text")
    validate.add_argument(
        "--max-diagnostics",
        type=_bounded_int,
        default=50,
        help="maximum diagnostics printed (all are still counted); default 50",
    )

    sub.add_parser("schemas", help="list the packaged local schemas")
    return parser


def _cmd_validate(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    try:
        result = validate_file(args.kind, args.path, args.max_diagnostics)
    except InputError as exc:
        print(f"error[{exc.code}]: {ascii_safe(exc.message)}", file=err)
        return EXIT_ERROR
    except SchemaLoadError as exc:
        print(f"error[schema.load]: {ascii_safe(exc)}", file=err)
        return EXIT_ERROR

    report = result.report
    if args.format == "json":
        payload = {
            "kind": result.kind,
            "path": ascii_safe(args.path),
            "records": result.records,
            "valid": result.valid,
            "errors": report.error_count,
            "warnings": report.warning_count,
            "suppressed": report.suppressed,
            "diagnostics": [d.to_dict() for d in report.diagnostics],
        }
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True), file=out)
    else:
        for diagnostic in report.diagnostics:
            print(diagnostic.render(), file=out)
        if report.suppressed:
            print(f"... {report.suppressed} further diagnostic(s) not shown", file=out)
        verdict = "valid" if result.valid else "invalid"
        print(
            f"{args.kind}: {result.records} record(s), {report.error_count} error(s), "
            f"{report.warning_count} warning(s): {verdict} "
            "(schema and input-local checks only; evidence, authorization and adoption "
            "are not checked)",
            file=out,
        )
    return EXIT_OK if result.valid else EXIT_INVALID


def _cmd_schemas(out: TextIO, err: TextIO) -> int:
    try:
        for kind in sorted(CONTRACTS):
            contract = CONTRACTS[kind]
            digest = hashlib.sha256(schema_bytes(contract.schema_file)).hexdigest()
            print(f"{kind}\t{contract.schema_file}\tsha256:{digest}", file=out)
    except SchemaLoadError as exc:
        print(f"error[schema.load]: {ascii_safe(exc)}", file=err)
        return EXIT_ERROR
    return EXIT_OK


def main(
    argv: Sequence[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse exits 0 for --help/--version, 2 for usage errors
        return int(exc.code) if isinstance(exc.code, int) else EXIT_ERROR
    if args.command == "validate":
        return _cmd_validate(args, out, err)
    return _cmd_schemas(out, err)


def console_main() -> None:
    sys.exit(main())
