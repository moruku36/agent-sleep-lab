"""Validation and explicit runtime command line interface.

validate/schemas are offline read-only operations. Runtime commands may write
private journals and adoption state; only explicit --provider mimo calls a paid
registered model. The input-free demo uses built-in synthetic fixtures and
disposable temporary stores, including local fixture receipt registration.
Exit codes: 0 completed/inspected, 1 invalid or incomplete run,
2 usage/input/runtime error. JSON output is ASCII-escaped.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr
import hashlib
import io
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
        description="Agent Sleep Lab contract validation and explicit runtime operations.",
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
    demo = sub.add_parser("demo", allow_abbrev=False,
                          help="run the built-in synthetic offline chain in temporary state")
    demo.add_argument("--format", choices=("json", "text"), default="json")
    report = sub.add_parser("oss-cost-report", allow_abbrev=False,
                            help="offline read-only accounting over existing OSS pairs/cohorts")
    report.add_argument("--manifest", required=True, help="strict bounded report input JSON")
    report.add_argument("--observations", help="exact canonical bounded cost-observations file")
    prepare = sub.add_parser("oss-prepare", allow_abbrev=False,
                             help="offline read-only pinned synthetic request preparation")
    prepare.add_argument("--manifest", required=True, help="strict bounded preparation JSON")
    prepare.add_argument("--store-config", required=True, help="explicit existing store configuration JSON")
    comparison_prepare = sub.add_parser(
        "compare-prepare", allow_abbrev=False,
        help="offline freeze and inspect an independent-raw comparison; no execution")
    comparison_prepare.add_argument("--manifest", required=True, help="existing bounded compare manifest JSON")
    comparison_prepare.add_argument("--store-config", required=True, help="explicit existing store configuration JSON")
    comparison_prepare.add_argument("--journal", required=True, help="separate private comparison SQLite journal")
    comparison_prepare.add_argument("--model", required=True,
                                    choices=("xiaomi/mimo-v2.6-pro", "fake-model-1"))
    comparison_inspect = sub.add_parser(
        "compare-inspect", allow_abbrev=False,
        help="read-only saved comparison progress; no execution or state changes")
    comparison_inspect.add_argument("--store-config", required=True,
                                    help="explicit existing store configuration JSON")
    comparison_inspect.add_argument("--journal", required=True,
                                    help="existing separate private comparison SQLite journal")
    comparison_inspect.add_argument("--plan-id", required=True, help="existing comparison plan ID")
    comparison_inspect.add_argument("--measurements", action="store_true",
                                    help="include saved byte/process-time observations; no raw receipts")
    for name in ("sleep", "adopt", "retrieve", "compare", "sleep-status"):
        cmd = sub.add_parser(name, help="explicit runtime " + name)
        if name != "sleep-status":
            cmd.add_argument("--store-config", required=True, help="local boundary configuration JSON")
            cmd.add_argument("--manifest", required=True, help="bounded operation JSON")
        if name in ("sleep", "compare", "sleep-status"):
            cmd.add_argument("--journal", required=True, help="separate private SQLite journal")
        if name in ("sleep", "compare"):
            cmd.add_argument("--provider", choices=("script", "mimo"), required=True)
            cmd.add_argument("--agent", help="registered OpenClaw account for explicit paid MiMo inference")
        if name == "sleep":
            cmd.add_argument("--replies", help="script provider JSON (offline only)")
        if name == "compare":
            cmd.add_argument("--rubric", required=True, help="local evaluator key, never sent to provider")
        if name == "sleep-status":
            cmd.add_argument("--run-id", required=True)
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
    arguments = list(sys.argv[1:] if argv is None else argv)
    private_command = arguments[0] if arguments[:1] in (
        ["oss-prepare"], ["compare-prepare"], ["compare-inspect"]) else None
    try:
        # argparse otherwise echoes unknown options/values from untrusted input.
        if private_command:
            with redirect_stderr(io.StringIO()):
                args = parser.parse_args(arguments)
        else:
            args = parser.parse_args(arguments)
    except SystemExit as exc:  # argparse exits 0 for --help/--version, 2 for usage errors
        if private_command and exc.code != 0:
            print(f"error[{private_command}]: invalid command arguments", file=err)
        return int(exc.code) if isinstance(exc.code, int) else EXIT_ERROR
    if args.command == "validate":
        return _cmd_validate(args, out, err)
    if args.command == "schemas":
        return _cmd_schemas(out, err)
    if args.command == "compare-inspect":
        try:
            from agent_sleep_lab.comparison_inspect import execute as inspect_comparison
            result = inspect_comparison(store_config_path=args.store_config,
                                        journal_path=args.journal, plan_id=args.plan_id,
                                        measurements=args.measurements)
            print(json.dumps(result, ensure_ascii=True, sort_keys=True), file=out)
            return EXIT_OK
        except Exception:
            print("error[compare-inspect]: inspection refused; check strict inputs, existing "
                  "distinct databases and saved comparison integrity", file=err)
            return EXIT_ERROR
    if args.command == "compare-prepare":
        try:
            from agent_sleep_lab.comparison_prepare import execute as prepare_comparison
            result = prepare_comparison(args.manifest, store_config_path=args.store_config,
                                        journal_path=args.journal, model=args.model)
            print(json.dumps(result, ensure_ascii=True, sort_keys=True), file=out)
            return EXIT_OK
        except Exception:
            print("error[compare-prepare]: preparation refused; check strict inputs, distinct "
                  "databases, frozen bindings, budgets and current eligible memory", file=err)
            return EXIT_ERROR
    if args.command == "oss-prepare":
        try:
            from agent_sleep_lab.oss_prepare_cli import execute as prepare
            result = prepare(args.manifest, store_config_path=args.store_config)
            print(json.dumps(result, ensure_ascii=True, sort_keys=True), file=out)
            return EXIT_OK
        except Exception:
            print("error[oss-prepare]: preparation refused; check strict inputs, existing "
                  "store, pinned repository and nonempty current-policy context", file=err)
            return EXIT_ERROR
    if args.command == "oss-cost-report":
        try:
            from agent_sleep_lab.oss_cost_report_cli import execute as report
            result = report(args.manifest, observations_path=args.observations)
            print(json.dumps(result, ensure_ascii=True, sort_keys=True), file=out)
            return EXIT_OK
        except Exception:
            # Untrusted JSON/database diagnostics can contain private field/body
            # excerpts. Never copy them into this command's output.
            print("error[oss-cost-report]: report refused; check input contract, existing "
                  "distinct databases, integrity, current policy and exact observations", file=err)
            return EXIT_ERROR
    try:
        if getattr(args, "provider", None) == "mimo" and not args.agent:
            raise ValueError("--agent is required for MiMo")
        if args.command == "sleep" and args.provider == "script" and not args.replies:
            raise ValueError("--replies is required for script provider")
        if args.command == "demo":
            from agent_sleep_lab.offline_demo import run_demo
            result = run_demo()
        else:
            from agent_sleep_lab.runtime_cli import execute
            result = execute(args)
        if args.command == "demo" and args.format == "text":
            from agent_sleep_lab.demo_text import format_demo_text
            print(format_demo_text(result), file=out)
        else:
            print(json.dumps(result, ensure_ascii=True, sort_keys=True), file=out)
        if args.command in ("sleep", "compare") and result.get("status") in ("failed", "incomplete", "invalidated"):
            return EXIT_INVALID
        return EXIT_OK
    except Exception as exc:
        print("error[runtime]: " + ascii_safe(str(exc))[:512], file=err)
        return EXIT_ERROR


def console_main() -> None:
    sys.exit(main())
