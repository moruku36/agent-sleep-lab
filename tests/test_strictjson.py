import unittest

import support  # noqa: F401  (adds src to sys.path)
from agent_sleep_lab.strictjson import (
    MAX_DEPTH,
    StrictJSONError,
    decode_utf8,
    loads_strict,
    loads_strict_bytes,
)


class StrictJsonTests(unittest.TestCase):
    def assertRejected(self, text, code):
        with self.assertRaises(StrictJSONError) as ctx:
            loads_strict(text)
        self.assertEqual(ctx.exception.code, code)
        return ctx.exception

    def test_accepts_ordinary_document(self):
        self.assertEqual(
            loads_strict('{"a": [1, 2.5, "x", null, true], "b": {"c": -0.0}}'),
            {"a": [1, 2.5, "x", None, True], "b": {"c": -0.0}},
        )

    def test_rejects_duplicate_keys_top_level_and_nested(self):
        self.assertRejected('{"a": 1, "a": 2}', "json.duplicate_key")
        self.assertRejected('{"x": {"a": 1, "b": 2, "a": 3}}', "json.duplicate_key")
        self.assertRejected('[{"k": 1, "k": 1}]', "json.duplicate_key")

    def test_rejects_duplicate_keys_that_differ_only_by_escape(self):
        self.assertRejected('{"a": 1, "\\u0061": 2}', "json.duplicate_key")

    def test_rejects_non_finite_numbers(self):
        for text in ("NaN", "Infinity", "-Infinity", '{"x": NaN}', "[Infinity]"):
            with self.subTest(text=text):
                self.assertRejected(text, "json.non_finite_number")

    def test_rejects_float_overflow_to_infinity(self):
        self.assertRejected("1e999", "json.non_finite_number")
        self.assertRejected("-1e999", "json.non_finite_number")

    def test_rejects_oversized_integer_literal(self):
        self.assertRejected("1" * 5000, "json.number_too_large")

    def test_syntax_error_has_position(self):
        exc = self.assertRejected('{"a": 1,\n  "b": }', "json.syntax")
        self.assertEqual(exc.line, 2)
        self.assertIsNotNone(exc.column)

    def test_trailing_garbage_and_empty_are_syntax_errors(self):
        self.assertRejected("{} {}", "json.syntax")
        self.assertRejected("", "json.syntax")
        self.assertRejected("   ", "json.syntax")

    def test_depth_limit(self):
        ok = "[" * MAX_DEPTH + "]" * MAX_DEPTH
        loads_strict(ok)
        too_deep = "[" * (MAX_DEPTH + 1) + "]" * (MAX_DEPTH + 1)
        self.assertRejected(too_deep, "json.too_deep")

    def test_extreme_nesting_does_not_crash(self):
        self.assertRejected("[" * 200000, "json.too_deep")

    def test_lone_surrogates_rejected_but_valid_pair_allowed(self):
        self.assertRejected('"\\ud800"', "json.lone_surrogate")
        self.assertRejected('{"\\udc00": 1}', "json.lone_surrogate")
        self.assertEqual(loads_strict('"\\ud83d\\ude00"'), "\U0001f600")

    def test_bytes_decoding(self):
        self.assertEqual(loads_strict_bytes('{"k": "é"}'.encode("utf-8")), {"k": "é"})
        with self.assertRaises(StrictJSONError) as ctx:
            decode_utf8(b'{"k": "\xff"}')
        self.assertEqual(ctx.exception.code, "json.invalid_utf8")
        with self.assertRaises(StrictJSONError) as ctx:
            loads_strict_bytes(b"\xef\xbb\xbf{}")
        self.assertEqual(ctx.exception.code, "json.bom")

    def test_python_literals_are_not_json(self):
        for text in ("{'a': 1}", "None", "True", "[1,]"):
            with self.subTest(text=text):
                self.assertRejected(text, "json.syntax")


if __name__ == "__main__":
    unittest.main()
