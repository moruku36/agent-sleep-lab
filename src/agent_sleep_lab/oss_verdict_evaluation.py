"""Strict subset of the pinned OSS verdict contract and frozen fixture scoring.

No model-generated labels, authority, adoption or scientific performance claim.
This is NOT the target's permissive parse_verdict implementation: surrounding
prose, duplicate keys, extra fields and coerced rationales are refused.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

from agent_sleep_lab import strictjson
from agent_sleep_lab.strictjson import loads_strict_bytes
from agent_sleep_lab import oss_offline_worker as worker

PROTOCOL = "agent-sleep-oss-fixture-evaluation/1"
EVALUATOR = "strict-verdict-exact-decision/1"
PARSER = "oss-verdict-strict-subset/1"
MAX_REPLY_BYTES = 65536
MAX_RATIONALE_BYTES = 8192
ARMS = ("baseline", "reference")


class VerdictError(ValueError):
    """Sanitized parser failure with a finite code, never a raw model excerpt."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ParsedVerdict:
    accepted: bool
    rationale: str


def parse_verdict(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_REPLY_BYTES:
        raise VerdictError("reply_byte_bound")
    try:
        value = loads_strict_bytes(raw)
    except ValueError:
        raise VerdictError("invalid_json") from None
    if type(value) is not dict or set(value) != {"accept", "rationale"}:
        raise VerdictError("verdict_shape")
    if type(value["accept"]) is not bool:
        raise VerdictError("accept_not_boolean")
    rationale = value["rationale"]
    if type(rationale) is not str:
        raise VerdictError("rationale_not_text")
    rationale = rationale.strip()
    if not rationale or len(rationale.encode("utf-8")) > MAX_RATIONALE_BYTES:
        raise VerdictError("rationale_byte_bound")
    return ParsedVerdict(value["accept"], rationale)


def freeze_manifest(*, dataset_id, expected_accept, task_sha256, issue_number):
    """Caller-authored synthetic fixture label; never authenticates its truth."""
    if (type(dataset_id) is not str
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", dataset_id)):
        raise ValueError("bounded synthetic dataset ID required")
    if type(expected_accept) is not bool:
        raise ValueError("explicit boolean fixture decision required")
    if type(task_sha256) is not str or not re.fullmatch(r"[0-9a-f]{64}", task_sha256):
        raise ValueError("exact task SHA-256 required")
    if type(issue_number) is not int or issue_number not in range(1, 6):
        raise ValueError("explicit built-in issue number required")
    return dict(protocol=PROTOCOL, evaluator=EVALUATOR, parser=PARSER,
                implementation_sha256=IMPLEMENTATION_SHA256,
                strict_json_sha256=STRICT_JSON_SHA256,
                target_parser_source_sha256=worker.SOURCE_HASHES["src/collector/llm_triage.py"],
                dataset_id=dataset_id, partition="synthetic_fixture", task_sha256=task_sha256,
                issue_number=issue_number,
                expected_accept=expected_accept,
                criterion="valid_strict_verdict_and_exact_boolean_match",
                invalid_verdict_score=0, max_reply_bytes=MAX_REPLY_BYTES,
                max_rationale_bytes=MAX_RATIONALE_BYTES,
                label_origin="caller_declared_fixture_not_authenticated_truth")


def validate_manifest(manifest, task_sha256, issue_number):
    if type(manifest) is not dict:
        raise ValueError("evaluation manifest must be a dictionary")
    expected = freeze_manifest(dataset_id=manifest.get("dataset_id"),
                               expected_accept=manifest.get("expected_accept"),
                               task_sha256=task_sha256, issue_number=issue_number)
    if manifest != expected:
        raise ValueError("unsupported or mismatched frozen evaluation manifest")
    # Equality alone would accept bool as integer in limit/score fields.
    for key, value in expected.items():
        if type(manifest[key]) is not type(value):
            raise ValueError("manifest field type mismatch")
    return expected


def evaluate_pair(manifest, *, task_sha256, issue_number, arms, context_current, plan_status):
    """Score only currently disclosable saved replies, never invoke a provider.

    The journal owns/froze the manifest before intent. This standalone function
    is a pure calculation, not proof of that timing or an authenticated receipt.
    """
    result = dict(status="not_configured", evaluator=EVALUATOR,
                  manifest_sha256=None, arms={}, reference_minus_baseline=None,
                  total_arms=2, usage="unavailable", cost="unavailable",
                  scope="single_synthetic_fixture_not_effect_evidence")
    if manifest is None:
        return result
    result["manifest_sha256"] = worker.digest(worker.encoded(manifest))
    if context_current is not True:
        result["status"] = "withheld_context"
        return result
    try:
        frozen = validate_manifest(manifest, task_sha256, issue_number)
    except ValueError:
        result["status"] = "unavailable_evaluator_version_or_manifest"
        return result
    scores = []
    for arm in ARMS:
        row = arms[arm]
        item = dict(status="unresolved", execution_status=row["status"], score=None,
                    verdict=None, error_code=None, reply_sha256=row["reply_sha256"])
        if row["status"] == "completed" and type(row["reply_body"]) is str:
            raw = row["reply_body"].encode("utf-8")
            if worker.digest(raw) != row["reply_sha256"]:
                item.update(status="unresolved", error_code="reply_hash_mismatch")
            else:
                try:
                    parsed = parse_verdict(raw)
                except VerdictError as error:
                    item.update(status="invalid_verdict", score=0, error_code=error.code)
                else:
                    item.update(status="parsed",
                                score=int(parsed.accepted == frozen["expected_accept"]),
                                verdict=dict(accepted=parsed.accepted, rationale=parsed.rationale,
                                             rationale_role="untrusted_model_output"))
        result["arms"][arm] = item
        scores.append(item["score"])
    if plan_status != "complete" or any(score is None for score in scores):
        result["status"] = "incomplete"
    else:
        invalid = any(item["status"] == "invalid_verdict" for item in result["arms"].values())
        result["status"] = "complete_with_invalid_verdict" if invalid else "complete"
        result["reference_minus_baseline"] = scores[1] - scores[0]
    return result


# Freeze the complete parser/evaluator implementation, not just a mutable label.
# Saved manifests with another implementation hash are not silently rescored.
IMPLEMENTATION_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()
STRICT_JSON_SHA256 = sha256(Path(strictjson.__file__).read_bytes()).hexdigest()
