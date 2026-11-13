"""Explicit public-document staging, NOT admission to a synthetic adoption store.

Pure bytes-in/bytes-out boundary: no fetching, file IO, provider calls, receipt
registration or permission discovery. Caller-supplied approvals are local trust
configuration, not authentication or an automatic secrets/publication check.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from urllib.parse import urlsplit

from agent_sleep_lab.provenance import canonical_json, parse_timestamp, sha256_hex

VERSION = "agent-sleep-public-source-intake/1"
MAX_SOURCE_BYTES = 65536
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_SHA = re.compile(r"[0-9a-f]{64}")
PURPOSE = "public_document_consolidation"
DELETION = "delete_staging_bundle_and_all_derivatives"


def _identifier(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise ValueError("invalid intake identifier")
    return value


def _stamp(value):
    if type(value) is not str or len(value) > 64:
        raise ValueError("explicit timestamp required")
    try:
        return parse_timestamp(value)
    except (ValueError, OverflowError):
        raise ValueError("timezone-aware timestamp required") from None


def _public_uri(value):
    # This is a locator check, not SSRF protection: this module never fetches.
    if (type(value) is not str or not 1 <= len(value) <= 2048
            or not value.isascii() or not value.isprintable()
            or any(char.isspace() for char in value) or "\\" in value):
        raise ValueError("public HTTPS source locator required")
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == "https" and parts.hostname and not parts.username
                 and not parts.password and not parts.query and not parts.fragment
                 and parts.port in (None, 443))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("public HTTPS locator must not contain credentials, query or fragment")
    return value


@dataclass(frozen=True)
class PublicDocumentApproval:
    """One exact-byte, exact-scope approval supplied outside source content.

    Setting these fields is an explicit caller assertion, not proof of public
    origin, copyright permission, secrets removal or identity. Never construct
    this object from document text or from a model-generated approval.
    """

    ref: str
    revision: int
    source_uri: str
    source_sha256: str
    project: str
    task_family: str
    approved_at: str
    expires_at: str
    public_release_reviewed: bool
    secrets_reviewed: bool
    purpose: str = PURPOSE
    deletion: str = DELETION

    def __post_init__(self):
        for value in (self.ref, self.project, self.task_family):
            _identifier(value)
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("positive approval revision required")
        _public_uri(self.source_uri)
        if type(self.source_sha256) is not str or not _SHA.fullmatch(self.source_sha256):
            raise ValueError("exact source SHA-256 required")
        if _stamp(self.approved_at) >= _stamp(self.expires_at):
            raise ValueError("approval must expire after approval time")
        if self.public_release_reviewed is not True or self.secrets_reviewed is not True:
            raise ValueError("explicit public-release and secrets review required")
        if self.purpose != PURPOSE or self.deletion != DELETION:
            raise ValueError("unsupported intake purpose or deletion contract")


def prepare_public_document(*, source_bytes, source_uri, scope, event_id,
                            observed_at, captured_at, approval, now):
    """Return a non-synthetic private staging artifact for exactly one document.

    Caller must supply the CURRENT approval each time; missing/revoked approval,
    changed bytes/scope/URI, not-yet-approved or expired data are refused.
    Source bytes are preserved exactly as UTF-8 text, with no normalization.
    A successful check does not authorize adoption, a model request or publication.
    """
    if type(approval) is not PublicDocumentApproval:
        raise ValueError("current separate public-document approval required")
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware current time required")
    if (type(source_bytes) is not bytes or not source_bytes
            or len(source_bytes) > MAX_SOURCE_BYTES):
        raise ValueError("source must be 1..65536 bytes")
    try:
        text = source_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("public document must be UTF-8 text") from None
    if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        raise ValueError("public document contains unsupported control characters")
    _identifier(event_id)
    _public_uri(source_uri)
    if (type(scope) is not dict or set(scope) != {"project", "task_family"}
            or any(type(v) is not str for v in scope.values())
            or scope != {"project": approval.project, "task_family": approval.task_family}):
        raise ValueError("source scope is not approved")
    if source_uri != approval.source_uri or sha256_hex(source_bytes) != approval.source_sha256:
        raise ValueError("source does not match exact reviewed URI and bytes")
    observed, captured = _stamp(observed_at), _stamp(captured_at)
    approved, expires = _stamp(approval.approved_at), _stamp(approval.expires_at)
    if not observed <= captured <= now or not approved <= captured <= now < expires:
        raise ValueError("source time or current approval is not valid")
    document = {
        "schema_version": VERSION, "synthetic": False, "origin": "external_document",
        "event_id": event_id, "scope": dict(scope),
        "observed_at": observed_at, "captured_at": captured_at,
        "source": {"uri": source_uri, "sha256": approval.source_sha256,
                   "byte_length": len(source_bytes), "text": text},
        "approval": {"ref": approval.ref, "revision": approval.revision,
                     "approved_at": approval.approved_at, "expires_at": approval.expires_at,
                     "purpose": approval.purpose, "retention": "until_expiry",
                     "deletion": approval.deletion},
        "state": "staged_not_admitted",
        "requires_current_approval_recheck": True,
        "grants_model_or_adoption_permission": False,
    }
    return canonical_json(document)


def recheck_public_document(artifact, *, approval, now):
    """Revalidate all staged fields against CURRENT caller approval before use."""
    intake_summary(artifact)  # bounded parsing/integrity; not authorization
    from agent_sleep_lab.strictjson import loads_strict_bytes
    doc = loads_strict_bytes(artifact)
    try:
        expected = prepare_public_document(
            source_bytes=doc["source"]["text"].encode("utf-8"),
            source_uri=doc["source"]["uri"], scope=doc["scope"],
            event_id=doc["event_id"], observed_at=doc["observed_at"],
            captured_at=doc["captured_at"], approval=approval, now=now)
    except (KeyError, TypeError):
        raise ValueError("invalid staged fields") from None
    if artifact != expected:
        raise ValueError("staging artifact differs from current approved preparation")
    return intake_summary(artifact)


def intake_summary(artifact):
    """Allowlisted content-free summary; never return source text/URI or ref."""
    from agent_sleep_lab.strictjson import loads_strict_bytes

    if type(artifact) is not bytes or not 1 <= len(artifact) <= 6 * MAX_SOURCE_BYTES + 8192:
        raise ValueError("invalid intake artifact size")
    doc = loads_strict_bytes(artifact)
    if (type(doc) is not dict or doc.get("schema_version") != VERSION
            or doc.get("synthetic") is not False or doc.get("state") != "staged_not_admitted"):
        raise ValueError("not a public-source staging artifact")
    source = doc.get("source")
    if type(source) is not dict or type(source.get("text")) is not str:
        raise ValueError("invalid staged source")
    data = source["text"].encode("utf-8")
    if (not 1 <= len(data) <= MAX_SOURCE_BYTES or source.get("byte_length") != len(data)
            or source.get("sha256") != sha256_hex(data)):
        raise ValueError("staged source integrity mismatch")
    # Summary is an observation, never a replay validator or authorization check.
    return {"schema_version": VERSION, "synthetic": False, "state": "staged_not_admitted",
            "artifact_sha256": sha256_hex(artifact), "source_sha256": sha256_hex(data),
            "source_bytes": len(data), "admitted_to_store": False,
            "model_calls": 0, "adoption": False}
