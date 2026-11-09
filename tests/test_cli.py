import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest

import support
from support import dumps, good_event, good_memory, good_promotion, jsonl

from agent_sleep_lab import __version__
from agent_sleep_lab.cli import EXIT_ERROR, EXIT_INVALID, EXIT_OK, main


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(io.StringIO()) as argparse_err:
        code = main(list(argv), stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue() + argparse_err.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name

    def write(self, name, data):
        path = os.path.join(self.dir, name)
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def test_valid_inputs_exit_zero(self):
        cases = [
            ("events", self.write("e.jsonl", jsonl(good_event()))),
            ("memory", self.write("m.json", dumps([good_memory()]))),
            ("promotion", self.write("p.json", dumps(good_promotion()))),
        ]
        for kind, path in cases:
            with self.subTest(kind=kind):
                code, out, err = run("validate", kind, path)
                self.assertEqual(code, EXIT_OK, out + err)
                self.assertIn(": valid", out)
                self.assertEqual(err, "")

    def test_invalid_input_exits_one_with_located_diagnostic(self):
        path = self.write("e.jsonl", jsonl(good_event(), good_event(event_id="e-2", extra=1)))
        code, out, _ = run("validate", "events", path)
        self.assertEqual(code, EXIT_INVALID)
        self.assertIn("error[schema.additionalProperties] line 2 record 2", out)
        self.assertIn(": invalid", out)

    def test_wrong_kind_for_content_is_invalid(self):
        path = self.write("p.json", dumps(good_promotion()))
        code, _, _ = run("validate", "memory", path)
        self.assertEqual(code, EXIT_INVALID)

    def test_unreadable_input_exits_two_on_stderr(self):
        code, out, err = run("validate", "events", os.path.join(self.dir, "missing.jsonl"))
        self.assertEqual(code, EXIT_ERROR)
        self.assertEqual(out, "")
        self.assertIn("io.not_found", err)
        code, _, err = run("validate", "events", self.dir)
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("io.not_regular_file", err)

    def test_usage_errors_exit_two(self):
        for argv in ([], ["validate"], ["validate", "bogus", "x"], ["nope"]):
            with self.subTest(argv=argv):
                self.assertEqual(run(*argv)[0], EXIT_ERROR)
        path = self.write("e.jsonl", jsonl(good_event()))
        for bad in ("0", "-1", "1001", "x"):
            with self.subTest(max_diagnostics=bad):
                self.assertEqual(run("validate", "events", path, "--max-diagnostics", bad)[0], EXIT_ERROR)

    def test_version_and_help_exit_zero(self):
        code, _, _ = run("--help")
        self.assertEqual(code, 0)
        code, _, _ = run("--version")
        self.assertEqual(code, 0)

    def test_json_format(self):
        path = self.write("e.jsonl", b"not json\n" * 3)
        code, out, _ = run("validate", "events", path, "--format", "json", "--max-diagnostics", "2")
        self.assertEqual(code, EXIT_INVALID)
        payload = json.loads(out)
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["errors"], 3)
        self.assertEqual(payload["suppressed"], 1)
        self.assertEqual(len(payload["diagnostics"]), 2)
        self.assertEqual(payload["diagnostics"][0]["code"], "json.syntax")
        self.assertEqual(payload["diagnostics"][0]["line"], 1)
        self.assertEqual(payload["records"], 3)

    def test_text_output_reports_suppression(self):
        path = self.write("e.jsonl", b"not json\n" * 4)
        _, out, _ = run("validate", "events", path, "--max-diagnostics", "1")
        self.assertIn("3 further diagnostic(s) not shown", out)

    def test_output_is_ascii_for_hostile_path_and_content(self):
        path = self.write("café-‮.jsonl", jsonl(good_event(**{"k‮é": 1})))
        for fmt in ("text", "json"):
            with self.subTest(format=fmt):
                _, out, err = run("validate", "events", path, "--format", fmt)
                self.assertTrue(out.isascii() and err.isascii())

    def test_validate_never_modifies_input_or_directory(self):
        path = self.write("e.jsonl", jsonl(good_event(extra=1)))
        before = (open(path, "rb").read(), os.stat(path).st_mtime_ns, sorted(os.listdir(self.dir)))
        run("validate", "events", path)
        after = (open(path, "rb").read(), os.stat(path).st_mtime_ns, sorted(os.listdir(self.dir)))
        self.assertEqual(before, after)

    def test_schemas_command_lists_packaged_schemas_with_hashes(self):
        code, out, _ = run("schemas")
        self.assertEqual(code, EXIT_OK)
        rows = [line.split("\t") for line in out.strip().splitlines()]
        self.assertEqual([r[0] for r in rows], ["events", "memory", "promotion"])
        for kind, filename, digest in rows:
            packaged = support.SRC / "agent_sleep_lab" / "schemas" / filename
            self.assertEqual(digest, "sha256:" + hashlib.sha256(packaged.read_bytes()).hexdigest())

    def test_version_string_matches_package(self):
        self.assertEqual(__version__, "0.1.0.dev0")


if __name__ == "__main__":
    unittest.main()
