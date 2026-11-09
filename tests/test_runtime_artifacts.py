"""Gate 2B contract tests: strict artifact schemas and boundary stamping (synthetic only)."""

from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

import support
from runtime_support import (
    evaluation_claim,
    make_control,
    make_evaluator,
    make_verifier,
    policy_body,
)

from agent_sleep_lab import runtime_artifacts as ra
from agent_sleep_lab.provenance import BoundaryViolation, ContractViolation
from agent_sleep_lab.strictjson import loads_strict_bytes

NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)


def good_verification():
    claim = {
        "receipt_id": "vr-1",
        "memory_id": "m-1",
        "memory_sha256": "a" * 64,
        "scope": {"project": "p", "task_family": "t"},
        "evidence": [
            {"event_id": "e-1", "event_sha256": "1" * 64, "source_sha256": "2" * 64,
             "provenance_sha256": "3" * 64}
        ],
        "method": {"name": "manual-check", "version": "1"},
        "protocol_sha256": "b" * 64,
        "outcome": "confirmed",
        "expires_at": "2026-12-01T00:00:00Z",
        "limits": {"max_evidence": 8, "synthetic_only": True},
    }
    return make_verifier().stamp(claim, NOW)


def codes(kind, doc):
    return {p.code for p in ra.validate_artifact(kind, doc)}


class ArtifactContractTests(unittest.TestCase):
    def test_good_artifacts_validate(self):
        self.assertEqual(ra.validate_artifact("verification", good_verification()), [])
        evaluation = make_evaluator().stamp(evaluation_claim(), NOW)
        self.assertEqual(ra.validate_artifact("evaluation", evaluation), [])
        policy = make_control().build_policy(policy_body(), revision=1, now=NOW)
        self.assertEqual(ra.validate_artifact("policy", policy), [])

    def test_unknown_missing_and_wrongly_typed_fields_are_rejected(self):
        base = good_verification()
        extra = dict(base, surprise=1)
        self.assertIn("contract.schema", codes("verification", extra))
        for key in ("boundary", "outcome", "limits", "memory_sha256"):
            broken = copy.deepcopy(base)
            del broken[key]
            self.assertIn("contract.schema", codes("verification", broken), key)
        for path, value in (
            (("outcome",), "maybe"),
            (("limits", "synthetic_only"), False),
            (("limits", "max_evidence"), 0),
            (("schema_version",), "agent-sleep-verification-receipt/2"),
            (("memory_sha256",), "A" * 64),
        ):
            broken = copy.deepcopy(base)
            target = broken
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            self.assertIn("contract.schema", codes("verification", broken), path)
        self.assertEqual(codes("verification", []), {"contract.not_object"})

    def test_trailing_newline_forms_are_rejected_by_the_code_level_fullmatch(self):
        for key, value in (("receipt_id", "vr-1\n"), ("memory_sha256", "a" * 64 + "\n")):
            doc = good_verification()
            doc[key] = value
            self.assertIn("contract.bad_format", codes("verification", doc), key)
        doc = good_verification()
        doc["issued_at"] = "2026-11-10T00:00:00Z\n"  # rejected by maxLength or by fullmatch
        self.assertTrue(codes("verification", doc) & {"contract.schema", "contract.bad_format"})
        doc = good_verification()
        doc["boundary"]["boundary_id"] = "synthetic-verifier\n"
        self.assertIn("contract.bad_format", codes("verification", doc))

    def test_cross_field_rules(self):
        doc = good_verification()
        doc["evidence"].append(copy.deepcopy(doc["evidence"][0]))
        self.assertIn("contract.duplicate_evidence", codes("verification", doc))
        doc = good_verification()
        doc["limits"]["max_evidence"] = 1
        doc["evidence"].append(dict(doc["evidence"][0], event_id="e-2"))
        self.assertIn("contract.limit_exceeded", codes("verification", doc))
        doc = good_verification()
        doc["expires_at"] = "2026-11-10T00:00:00Z"  # equals issued_at
        self.assertIn("contract.expiry_order", codes("verification", doc))

        for claim, expected in (
            (evaluation_claim(completeness={"planned": 4, "completed": 3}), "contract.completeness"),
            (evaluation_claim(result="failed", completeness={"planned": 2, "completed": 3}),
             "contract.completeness"),
        ):
            evaluation = make_evaluator().stamp(claim, NOW)
            self.assertIn(expected, codes("evaluation", evaluation))
        incomplete = make_evaluator().stamp(
            evaluation_claim(result="incomplete", completeness={"planned": 4, "completed": 1}), NOW
        )
        self.assertEqual(ra.validate_artifact("evaluation", incomplete), [])

        policy = make_control().build_policy(
            policy_body(memory_ids=["m-1", "m-1"]), revision=1, now=NOW
        )
        self.assertIn("contract.duplicate_entry", codes("policy", policy))
        policy = make_control().build_policy(policy_body(), revision=1, now=NOW)
        policy["authorizations"].append({"ref": "auth-1", "revision": 2})
        self.assertIn("contract.duplicate_authorization", codes("policy", policy))

    def test_policy_purpose_and_partition_reject_trailing_newlines(self):
        for field in ("accepted_purposes", "accepted_partitions"):
            doc = make_control().build_policy(policy_body(), revision=1, now=NOW)
            doc[field][0] += "\n"
            with self.subTest(field):
                self.assertIn("contract.bad_format", codes("policy", doc))

    def test_strict_byte_parsing(self):
        data = ra.encode_artifact("verification", good_verification())
        self.assertEqual(ra.parse_artifact_bytes("verification", data)["receipt_id"], "vr-1")
        bad = {
            "duplicate key": b'{"schema_version":"x","schema_version":"y"}',
            "NaN": b'{"revision": NaN}',
            "not json": b"nope",
            "empty": b"",
            "too large": b" " * (ra.MAX_ARTIFACT_BYTES + 1),
        }
        for name, blob in bad.items():
            with self.subTest(name), self.assertRaises(ContractViolation):
                ra.parse_artifact_bytes("verification", blob)
        with self.assertRaises(ContractViolation):
            ra.parse_artifact_bytes("verification", "text, not bytes")
        with self.assertRaises(ContractViolation):
            ra.parse_artifact_bytes("nonsense", data)

    def test_encode_is_deterministic_and_refuses_invalid_documents(self):
        doc = good_verification()
        self.assertEqual(ra.encode_artifact("verification", doc), ra.encode_artifact("verification", doc))
        doc["outcome"] = "maybe"
        with self.assertRaises(ContractViolation):
            ra.encode_artifact("verification", doc)


class BoundaryStampingTests(unittest.TestCase):
    def test_boundary_identity_is_stamped_and_cannot_be_supplied(self):
        doc = good_verification()
        self.assertEqual(
            doc["boundary"], {"boundary_id": "synthetic-verifier", "boundary_version": "1.0.0"}
        )
        self.assertEqual(doc["issued_at"], "2026-11-10T00:00:00Z")
        claim = {k: v for k, v in doc.items() if k not in ("boundary", "schema_version", "issued_at")}
        for key, value in (
            ("boundary", {"boundary_id": "forged", "boundary_version": "9"}),
            ("schema_version", "agent-sleep-verification-receipt/1"),
            ("issued_at", "2000-01-01T00:00:00Z"),
        ):
            with self.subTest(key), self.assertRaises(ContractViolation) as cm:
                make_verifier().stamp(dict(claim, **{key: value}), NOW)
            self.assertEqual(cm.exception.code, "contract.boundary_field_in_claim")
        with self.assertRaises(ContractViolation):
            make_verifier().stamp(["not", "an", "object"], NOW)
        with self.assertRaises(ContractViolation):
            make_verifier().stamp(dict(claim, extra=float("nan")), NOW)

    def test_method_protocol_and_policy_fields_are_bounded_by_the_boundary(self):
        claim = {k: v for k, v in good_verification().items()
                 if k not in ("boundary", "schema_version", "issued_at")}
        claim["method"] = {"name": "other-method", "version": "1"}
        with self.assertRaises(BoundaryViolation) as cm:
            make_verifier().stamp(claim, NOW)
        self.assertEqual(cm.exception.code, "boundary.method_not_allowed")
        with self.assertRaises(BoundaryViolation) as cm:
            make_evaluator().stamp(evaluation_claim(protocol={"name": "x", "version": "1", "config_sha256": "d" * 64}), NOW)
        self.assertEqual(cm.exception.code, "boundary.protocol_not_allowed")
        for forbidden in ("revision", "set_by", "set_at", "schema_version"):
            with self.subTest(forbidden), self.assertRaises(ContractViolation):
                make_control().build_policy(dict(policy_body(), **{forbidden: 1}), revision=1, now=NOW)

    def test_unhashable_method_and_protocol_values_are_boundary_errors(self):
        for field in ("name", "version"):
            for value in ([], {}, None, 1):
                method = {"name": "manual-check", "version": "1"}
                method[field] = value
                with self.subTest(field=field, value=value):
                    with self.assertRaises(BoundaryViolation):
                        make_verifier().stamp({"method": method}, NOW)
                    protocol = {"name": "fixture-protocol", "version": "1",
                                "config_sha256": "d" * 64}
                    protocol[field] = value
                    with self.assertRaises(BoundaryViolation):
                        make_evaluator().stamp(evaluation_claim(protocol=protocol), NOW)

    def test_boundary_construction_is_validated_and_input_is_not_mutated(self):
        for kwargs in ({"boundary_id": "Bad Id"}, {"boundary_version": ""}, {"methods": frozenset()},
                       {"methods": frozenset({("ok", "BAD VERSION")})}):
            with self.subTest(kwargs), self.assertRaises(ValueError):
                make_verifier(**kwargs)
        with self.assertRaises(ValueError):
            make_evaluator(protocols=frozenset())
        with self.assertRaises(ValueError):
            make_control(boundary_id="")
        claim = evaluation_claim()
        before = copy.deepcopy(claim)
        make_evaluator().stamp(claim, NOW)
        self.assertEqual(claim, before)
        with self.assertRaises(ValueError):
            make_verifier().stamp({"method": {"name": "manual-check", "version": "1"}},
                                  datetime(2026, 11, 10))  # naive time


class PackagedSchemaTests(unittest.TestCase):
    def test_copies_match_and_versions_agree_with_code(self):
        for kind, (version, filename) in ra.ARTIFACT_KINDS.items():
            packaged = support.SRC / "agent_sleep_lab" / "schemas" / filename
            repository = support.ROOT / "schemas" / filename
            self.assertTrue(packaged.is_file(), filename)
            self.assertTrue(repository.is_file(), filename)
            self.assertEqual(repository.read_bytes(), packaged.read_bytes(), filename)
            schema = loads_strict_bytes(packaged.read_bytes())
            self.assertEqual(schema["properties"]["schema_version"]["const"], version)
            self.assertIs(schema["additionalProperties"], False)
            self.assertNotIn("$ref", packaged.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
