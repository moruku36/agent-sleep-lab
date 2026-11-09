import os
import tempfile
import unittest
from unittest import mock

import support
from support import codes, dumps, good_event, good_memory, good_promotion, jsonl

from agent_sleep_lab import validation
from agent_sleep_lab.validation import (
    InputError,
    SchemaLoadError,
    assert_self_contained,
    build_validator,
    make_registry,
    read_input,
    validate_bytes,
)


def render_all(result):
    return "\n".join(d.render() for d in result.report.diagnostics)


class EventTests(unittest.TestCase):
    def test_valid_events_pass(self):
        result = validate_bytes("events", jsonl(good_event(), good_event(event_id="e-2")))
        self.assertTrue(result.valid, render_all(result))
        self.assertEqual(result.records, 2)
        self.assertEqual(result.report.warning_count, 0)

    def test_missing_trailing_newline_is_fine(self):
        result = validate_bytes("events", dumps(good_event()))
        self.assertTrue(result.valid)
        self.assertEqual(result.records, 1)

    def test_extra_field_rejected_with_location(self):
        result = validate_bytes("events", jsonl(good_event(), good_event(event_id="e-2", extra=1)))
        self.assertFalse(result.valid)
        diag = result.report.diagnostics[0]
        self.assertEqual(diag.code, "schema.additionalProperties")
        self.assertEqual((diag.line, diag.record, diag.pointer), (2, 2, ""))
        self.assertIn("extra", diag.message)

    def test_nested_extra_field_pointer(self):
        scope = {"project": "p", "task_family": "t", "owner": "x"}
        result = validate_bytes("events", jsonl(good_event(scope=scope)))
        self.assertEqual(codes(result), ["schema.additionalProperties"])
        self.assertEqual(result.report.diagnostics[0].pointer, "/scope")

    def test_malformed_date_times_rejected(self):
        for bad in (
            "2026-13-01T00:00:00Z",
            "2026-11-08T00:00:00",  # no offset
            "2026-11-08T25:00:00Z",
            "yesterday",
            "2026-11-08",
            "",
        ):
            with self.subTest(value=bad):
                result = validate_bytes("events", jsonl(good_event(occurred_at=bad)))
                self.assertFalse(result.valid)
                self.assertEqual(result.report.diagnostics[0].pointer, "/occurred_at")

    def test_valid_date_time_offsets_accepted(self):
        for ok in ("2026-11-08T09:00:00+09:00", "2026-11-08T00:00:00.123Z"):
            with self.subTest(value=ok):
                self.assertTrue(validate_bytes("events", jsonl(good_event(occurred_at=ok))).valid)

    def test_unknown_versions_rejected_once(self):
        for version in ("0.2", "1", "", None, 0.1, ["0.1"]):
            with self.subTest(version=version):
                result = validate_bytes("events", jsonl(good_event(schema_version=version)))
                self.assertEqual(codes(result), ["record.unknown_version"])
                self.assertEqual(result.report.diagnostics[0].pointer, "/schema_version")

    def test_missing_version_reported_as_required(self):
        record = good_event()
        del record["schema_version"]
        result = validate_bytes("events", jsonl(record))
        self.assertEqual(codes(result), ["schema.required"])

    def test_non_object_records(self):
        result = validate_bytes("events", b'[]\n"x"\n3\nnull\n')
        self.assertEqual(codes(result), ["record.not_object"] * 4)

    def test_blank_lines_are_errors(self):
        result = validate_bytes("events", dumps(good_event()) + b"\n\n" + dumps(good_event(event_id="e-2")))
        self.assertEqual(codes(result), ["jsonl.blank_line"])
        self.assertEqual(result.report.diagnostics[0].line, 2)

    def test_syntax_error_does_not_stop_later_lines(self):
        data = dumps(good_event()) + b"\nnot json\n" + dumps(good_event(event_id="e-3", extra=1)) + b"\n"
        result = validate_bytes("events", data)
        self.assertEqual(codes(result), ["json.syntax", "schema.additionalProperties"])
        self.assertEqual([d.line for d in result.report.diagnostics], [2, 3])
        self.assertEqual(result.records, 3)

    def test_duplicate_key_nan_and_infinity_in_line(self):
        data = (
            b'{"schema_version":"0.1","schema_version":"0.1"}\n'
            b'{"synthetic": NaN}\n'
            b'{"synthetic": Infinity}\n'
            b'{"synthetic": 1e999}\n'
        )
        result = validate_bytes("events", data)
        self.assertEqual(
            codes(result),
            ["json.duplicate_key"] + ["json.non_finite_number"] * 3,
        )

    def test_invalid_utf8_and_bom(self):
        result = validate_bytes("events", b'{"a": "\xff"}\n')
        self.assertEqual(codes(result), ["json.invalid_utf8"])
        result = validate_bytes("events", b"\xef\xbb\xbf" + dumps(good_event()))
        self.assertEqual(codes(result), ["json.bom"])

    def test_corrects_self_flagged(self):
        result = validate_bytes("events", jsonl(good_event(kind="correction", corrects_event_id="e-1")))
        self.assertEqual(codes(result), ["event.corrects_self"])

    def test_duplicate_event_ids(self):
        same = validate_bytes("events", jsonl(good_event(), good_event()))
        self.assertTrue(same.valid)
        self.assertEqual(codes(same), ["id.duplicate_identical"])
        conflict = validate_bytes("events", jsonl(good_event(), good_event(summary="other")))
        self.assertFalse(conflict.valid)
        self.assertEqual(codes(conflict), ["id.duplicate_conflict"])

    def test_empty_input_is_warning_only(self):
        result = validate_bytes("events", b"")
        self.assertTrue(result.valid)
        self.assertEqual(codes(result), ["input.no_records"])


class MemoryTests(unittest.TestCase):
    def test_object_and_array_accepted(self):
        self.assertTrue(validate_bytes("memory", dumps(good_memory())).valid)
        result = validate_bytes("memory", dumps([good_memory(), good_memory(memory_id="m-2")]))
        self.assertTrue(result.valid, render_all(result))
        self.assertEqual(result.records, 2)

    def test_empty_array_is_warning(self):
        result = validate_bytes("memory", b"[]")
        self.assertTrue(result.valid)
        self.assertEqual(codes(result), ["input.no_records"])

    def test_scalar_document_rejected(self):
        self.assertEqual(codes(validate_bytes("memory", b'"x"')), ["document.not_object_or_array"])

    def test_array_element_locations_use_record_ordinal(self):
        result = validate_bytes("memory", dumps([good_memory(), good_memory(memory_id="m-2", bogus=1), 7]))
        self.assertEqual(codes(result), ["schema.additionalProperties", "record.not_object"])
        self.assertEqual([d.record for d in result.report.diagnostics], [2, 3])

    def test_valid_until_formats(self):
        self.assertTrue(validate_bytes("memory", dumps(good_memory(valid_until="2027-01-01T00:00:00Z"))).valid)
        bad = validate_bytes("memory", dumps(good_memory(valid_until="soon")))
        self.assertEqual(bad.report.diagnostics[0].pointer, "/valid_until")

    def test_schema_constraints(self):
        cases = {
            "schema.minItems": good_memory(evidence=[]),
            "schema.uniqueItems": good_memory(supersedes=["a", "a"]),
            "schema.enum": good_memory(status="active"),
            "schema.type": good_memory(tags="x"),
        }
        for expected, record in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(codes(validate_bytes("memory", dumps(record))), [expected])

    def test_unknown_version(self):
        result = validate_bytes("memory", dumps(good_memory(schema_version="0.2")))
        self.assertEqual(codes(result), ["record.unknown_version"])

    def test_verified_needs_confirmation_and_verifier(self):
        pending = good_memory(status="verified")
        self.assertEqual(codes(validate_bytes("memory", dumps(pending))), ["memory.verified_unconfirmed"])
        no_verifier = good_memory(
            status="verified",
            verification={"method": "m", "verifier": "", "result": "confirmed"},
        )
        self.assertEqual(codes(validate_bytes("memory", dumps(no_verifier))), ["memory.verified_unconfirmed"])
        ok = good_memory(
            status="verified",
            verification={"method": "m", "verifier": "reviewer", "result": "confirmed"},
        )
        self.assertTrue(validate_bytes("memory", dumps(ok)).valid)

    def test_hypothesis_cannot_be_verified(self):
        record = good_memory(
            kind="hypothesis",
            status="verified",
            verification={"method": "m", "verifier": "reviewer", "result": "confirmed"},
        )
        self.assertEqual(codes(validate_bytes("memory", dumps(record))), ["memory.hypothesis_verified"])

    def test_supersedes_self(self):
        result = validate_bytes("memory", dumps(good_memory(supersedes=["m-1"])))
        self.assertEqual(codes(result), ["memory.supersedes_self"])

    def test_semantic_checks_only_run_on_schema_valid_records(self):
        record = good_memory(status="verified", extra=1)
        self.assertEqual(codes(validate_bytes("memory", dumps(record))), ["schema.additionalProperties"])

    def test_duplicate_memory_ids_in_array(self):
        result = validate_bytes("memory", dumps([good_memory(), good_memory(claim="different")]))
        self.assertEqual(codes(result), ["id.duplicate_conflict"])

    def test_duplicate_object_key_rejected(self):
        data = dumps(good_memory())[:-1] + b', "tags": []}'
        self.assertEqual(codes(validate_bytes("memory", data)), ["json.duplicate_key"])


class PromotionTests(unittest.TestCase):
    def test_valid_request(self):
        result = validate_bytes("promotion", dumps(good_promotion()))
        self.assertTrue(result.valid, render_all(result))

    def test_parent_hash_forms(self):
        self.assertTrue(validate_bytes("promotion", dumps(good_promotion(expected_parent_sha256="a" * 64))).valid)
        for bad in ("A" * 64, "a" * 63, "g" * 64, 5):
            with self.subTest(value=bad):
                result = validate_bytes("promotion", dumps(good_promotion(expected_parent_sha256=bad)))
                self.assertEqual(codes(result), ["schema.anyOf"])

    def test_nested_hash_pointer(self):
        request = good_promotion(candidate_snapshot={"id": "x", "sha256": "xyz"})
        result = validate_bytes("promotion", dumps(request))
        self.assertEqual(codes(result), ["schema.pattern"])
        self.assertEqual(result.report.diagnostics[0].pointer, "/candidate_snapshot/sha256")

    def test_revisions_must_be_non_negative_integers(self):
        for field in ("authorization_revision", "exclusion_revision"):
            for bad in (-1, "0", True):
                with self.subTest(field=field, value=bad):
                    result = validate_bytes("promotion", dumps(good_promotion(**{field: bad})))
                    self.assertFalse(result.valid)

    def test_extra_fields_and_types(self):
        self.assertEqual(
            codes(validate_bytes("promotion", dumps(good_promotion(active=True)))),
            ["schema.additionalProperties"],
        )
        self.assertEqual(
            codes(validate_bytes("promotion", dumps(good_promotion(proposal_only="yes")))),
            ["schema.type"],
        )

    def test_unknown_version(self):
        for version in ("sleep-promotion/2", "0.1"):
            with self.subTest(version=version):
                result = validate_bytes("promotion", dumps(good_promotion(schema_version=version)))
                self.assertEqual(codes(result), ["record.unknown_version"])

    def test_array_rejected(self):
        result = validate_bytes("promotion", dumps([good_promotion()]))
        self.assertEqual(codes(result), ["document.not_object"])

    def test_event_record_is_not_a_promotion(self):
        self.assertFalse(validate_bytes("promotion", dumps(good_event())).valid)


class DiagnosticsTests(unittest.TestCase):
    def test_diagnostics_bounded_but_all_counted(self):
        data = b"not json\n" * 5
        result = validate_bytes("events", data, max_diagnostics=2)
        self.assertEqual(len(result.report.diagnostics), 2)
        self.assertEqual(result.report.error_count, 5)
        self.assertEqual(result.report.suppressed, 3)

    def test_per_record_schema_errors_capped(self):
        result = validate_bytes("events", b"{}\n")
        self.assertLessEqual(len(result.report.diagnostics), validation.MAX_ERRORS_PER_RECORD + 1)
        self.assertGreaterEqual(result.report.error_count, 9)

    def test_instance_values_are_not_echoed(self):
        secret = "SECRET-TOKEN-VALUE"
        data = jsonl(good_event(kind=secret, occurred_at=secret, event_id=[secret], synthetic=secret))
        result = validate_bytes("events", data)
        self.assertFalse(result.valid)
        self.assertNotIn(secret, render_all(result))

    def test_output_is_ascii_even_for_hostile_keys(self):
        hostile = "k‮\x1b[31mé\U0001f600" + "z" * 500
        result = validate_bytes("events", jsonl(good_event(**{hostile: 1})))
        text = render_all(result)
        self.assertTrue(text.isascii())
        self.assertNotIn("\x1b", text)
        self.assertLess(max(len(d.message) for d in result.report.diagnostics), 300)


class LimitTests(unittest.TestCase):
    def test_input_too_large(self):
        with mock.patch.object(validation, "MAX_FILE_BYTES", 10):
            result = validate_bytes("events", b"x" * 11)
        self.assertEqual(codes(result), ["input.too_large"])

    def test_line_too_long(self):
        with mock.patch.object(validation, "MAX_LINE_BYTES", 50):
            result = validate_bytes("events", jsonl(good_event()))
        self.assertEqual(codes(result), ["jsonl.line_too_long"])

    def test_too_many_records(self):
        with mock.patch.object(validation, "MAX_RECORDS", 2):
            result = validate_bytes("events", jsonl(*[good_event(event_id=f"e-{i}") for i in range(4)]))
        self.assertEqual(codes(result), ["input.too_many_records"])
        self.assertEqual(result.records, 2)

    def test_unknown_kind(self):
        with self.assertRaises(ValueError):
            validate_bytes("nope", b"")


class SchemaIsolationTests(unittest.TestCase):
    def test_external_references_rejected_before_use(self):
        for ref in ("http://example.invalid/s.json", "file:///etc/passwd", "other.json#/a", "//host/x"):
            with self.subTest(ref=ref):
                with self.assertRaises(SchemaLoadError):
                    assert_self_contained({"properties": {"a": {"$ref": ref}}})
        assert_self_contained({"definitions": {"x": {}}, "properties": {"a": {"$ref": "#/definitions/x"}}})

    def test_build_validator_rejects_external_ref_and_wrong_dialect(self):
        from jsonschema import Draft7Validator

        with self.assertRaises(SchemaLoadError):
            build_validator(
                {"$schema": "http://json-schema.org/draft-07/schema#", "$ref": "http://example.invalid/x"},
                Draft7Validator,
            )
        with self.assertRaises(SchemaLoadError):
            build_validator({"$schema": "https://json-schema.org/draft/2020-12/schema"}, Draft7Validator)

    def test_registry_refuses_retrieval_and_nothing_hits_the_network(self):
        from jsonschema import Draft7Validator
        from referencing.exceptions import Unretrievable

        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network used")) as urlopen:
            with self.assertRaises(Unretrievable):
                make_registry().get_or_retrieve("http://example.invalid/s.json")
            validator = Draft7Validator({"$ref": "http://example.invalid/s.json"}, registry=make_registry())
            with self.assertRaises(Exception):
                list(validator.iter_errors({}))
            urlopen.assert_not_called()

    def test_packaged_schemas_are_self_contained_and_loadable(self):
        for kind, contract in validation.CONTRACTS.items():
            with self.subTest(kind=kind):
                validator, version = validation._validator_for(kind)
                self.assertTrue(version)
                assert_self_contained(validator.schema)

    def test_date_time_checking_is_active(self):
        validator, _ = validation._validator_for("events")
        self.assertIn("date-time", validator.format_checker.checkers)


class ReadInputTests(unittest.TestCase):
    def test_reads_regular_file_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "in.jsonl")
            with open(path, "wb") as fh:
                fh.write(jsonl(good_event()))
            before = os.stat(path)
            data = read_input(path)
            after = os.stat(path)
            self.assertEqual(data, jsonl(good_event()))
            self.assertEqual((before.st_size, before.st_mtime_ns), (after.st_size, after.st_mtime_ns))
            self.assertEqual(os.listdir(tmp), ["in.jsonl"])

    def test_missing_directory_and_oversize(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(InputError) as ctx:
                read_input(os.path.join(tmp, "missing"))
            self.assertEqual(ctx.exception.code, "io.not_found")
            with self.assertRaises(InputError) as ctx:
                read_input(tmp)
            self.assertEqual(ctx.exception.code, "io.not_regular_file")
            path = os.path.join(tmp, "big")
            with open(path, "wb") as fh:
                fh.write(b"x" * 20)
            with self.assertRaises(InputError) as ctx:
                read_input(path, max_bytes=10)
            self.assertEqual(ctx.exception.code, "io.too_large")


if __name__ == "__main__":
    unittest.main()
