"""Thin daily-use command namespace for ONE persistent public-document store.

``agent-sleep-lab public-document <action>`` drives the existing
``PublicDocumentStore`` lifecycle. It adds NO model, network, provider, dispatch or
automatic-adoption path. It never invents owner approval or a semantic judgment:
``approve`` registers the host-supplied approval file, and ``verify``/``evaluate``
register the library's MECHANICAL receipts (exact-quotation fidelity, snapshot
check) for the one explicitly named role identity.

* ``stage`` prepares an artifact from explicitly supplied bytes and existing approval,
  without opening a store. Preview writes no artifact; output is new-only.
* Only ``init`` creates a store (and its parent directories). All remaining actions
  open an EXISTING store and refuse a missing one.
* ``status`` and ``cleanup-preview`` use the library's read-only metadata seam (one
  consistent read snapshot) and never construct the mutating store, sweep, purge or
  read content. Explicit mutating actions are different: content-accessing actions,
  ``cleanup`` and ``withdraw`` run the library's eligibility/integrity guard and, on
  failure, exclude and purge managed content before refusing.
* Role-bearing actions take ONE explicit ``--identity``/``--identity-version`` pair.
  The library compares it with the persisted configuration; these strings are
  checked configuration, NOT authentication or proof of different humans.
* ``cleanup`` is the explicit expiry/integrity sweep (it may exclude and purge, and it
  completes a pending purge). ``withdraw`` requires an explicit ``--purge`` or
  ``--exclude-only`` choice and confirms ITS OWN exclusion (``withdraw(purge=False)``)
  before any separate purge. A competing or stale withdrawal is a refusal (exit 2);
  this call never claims a transition it did not confirm. Operations, content-free
  no-retry tombstones and external exports are never touched.
* Exit codes: 0 completed or nothing due; 1 an incomplete, failed or unconfirmed
  attempt (including a late purge error whose readback observes deletion) (``purge_pending_incomplete``: exclusion committed, inspect ``status`` before choosing ``cleanup``;
  ``failed_state_unchanged``: an error before exclusion, inspect with ``status``); 2
  refused or failed. Stage may leave a partial artifact or confirm a completed
  artifact with failed summary delivery: inspect its diagnostic before retrying.
  For store actions, read fresh ``status`` after a nonzero code before repeating.
* Metrics are OFF by default and NEW-ONLY. ``--metrics-out PATH`` is created
  exclusively (``O_CREAT|O_EXCL|O_NOFOLLOW``, mode 0600) BEFORE any store action, and
  that same held descriptor receives ONE bounded allowlisted, content-free JSON line
  afterwards. A pathname is never reopened, appended to, truncated or unlinked and no
  directory is created. EVERY existing destination (the store, a SQLite sidecar or
  journal, an export, a hardlink, a symlink, a directory) and a missing parent are
  refused with exit 2 before the action. The parent directory is trusted not to be
  swapped concurrently; if another creator wins the name this call is refused. The
  reserved file remains, possibly empty, even if the action or the write fails. A
  metrics-write failure after the action never changes the exit code and the action
  must NOT be repeated to obtain metrics. Cost is never measured here and is
  reported as unavailable, never zero.
* Errors are reported by fixed category only; no path, text or hash is echoed.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from agent_sleep_lab.provenance import canonical_json, sha256_hex
from agent_sleep_lab.public_document_runtime import (
    MAX_CONTENT_BYTES, Authority, Consumer, PublicDocumentError, PublicDocumentStore,
)
from agent_sleep_lab.public_source_intake import (
    MAX_SOURCE_BYTES, PublicDocumentApproval, PublicSourceLocatorError,
    intake_summary, prepare_public_document,
)
from agent_sleep_lab.strictjson import loads_strict_bytes

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_ERROR = 2
METRICS_SCHEMA = "agent-sleep-public-document-metrics/1"
ROLE_KEYS = ("control", "verifier", "evaluator", "semantic_reviewer", "consumer")
_CODE = re.compile(r"[a-z][a-z_]{0,47}")


def _utcnow():
    return datetime.now(timezone.utc)


def _read(path, limit=MAX_CONTENT_BYTES):
    """Exact bytes of one explicitly named regular file; no normalization."""
    target = Path(path)
    if not target.is_file():
        raise ValueError("input file required")
    with target.open("rb") as handle:
        data = handle.read(limit + 1)
    if not 1 <= len(data) <= limit:
        raise ValueError("input file size out of bounds")
    return data


def _object(data):
    value = loads_strict_bytes(data)
    if type(value) is not dict:
        raise ValueError("JSON object required")
    return value


def _authority(value):
    if type(value) is not dict or set(value) != {"identity", "version"}:
        raise ValueError("exact authority configuration required")
    return Authority(**value)


def _flag_authority(args):
    # One explicit role per action; never inferred from the store configuration.
    return Authority(args.identity, args.identity_version)


def _existing(args, clock):
    return PublicDocumentStore(Path(args.store), clock=clock)


def _status_view(args, clock):
    return PublicDocumentStore.metadata_status(Path(args.store), clock=clock)


class _MetricsRefused(ValueError):
    """The opt-in metrics destination could not be reserved; no action ran."""


def _classify(exc):
    if isinstance(exc, PublicDocumentError):
        code = getattr(exc, "code", "")
        return code if type(code) is str and _CODE.fullmatch(code) else "lifecycle_rejected"
    if isinstance(exc, PublicSourceLocatorError):
        return "source_locator_refused"
    if isinstance(exc, _ArtifactDestinationRefused):
        return "artifact_destination_refused"
    if isinstance(exc, _ArtifactWriteFailed):
        return "artifact_write_incomplete"
    if isinstance(exc, _MetricsRefused):
        return "metrics_destination_refused"
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return "invalid_input"
    if isinstance(exc, FileExistsError):
        return "store_exists"
    if isinstance(exc, OSError):
        return "io_error"
    if isinstance(exc, sqlite3.Error):
        return "store_error"
    return "internal_error"


# ---------------------------------------------------------------- actions

class _ArtifactDestinationRefused(ValueError):
    """No artifact created; destination must be new with an existing parent."""


class _ArtifactWriteFailed(OSError):
    """Reserved file may be partial; never overwrite or retry automatically."""


def _stage(args, clock):
    approval = PublicDocumentApproval(**_object(_read(args.approval)))
    artifact = prepare_public_document(
        source_bytes=_read(args.source_file, MAX_SOURCE_BYTES),
        source_uri=approval.source_uri,
        scope={"project": approval.project, "task_family": approval.task_family},
        event_id=args.event_id, observed_at=args.observed_at,
        captured_at=args.captured_at, approval=approval, now=clock())
    result = dict(intake_summary(artifact), action="stage", preview_only=bool(args.preview),
                  artifact_written=False)
    if args.preview:
        return result, EXIT_OK
    # Only after validation: NEW-ONLY, no symlink following, no truncation, no mkdir.
    # Parent-directory stability is a caller trust assumption, as for metrics.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(args.artifact_out, flags, 0o600)
    except (OSError, ValueError):
        raise _ArtifactDestinationRefused() from None
    try:
        try:
            remaining = memoryview(artifact)
            while remaining:
                count = os.write(fd, remaining)
                if count <= 0:
                    raise OSError()
                remaining = remaining[count:]
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        raise _ArtifactWriteFailed() from None
    return dict(result, artifact_written=True), EXIT_OK


def _receipt(args, kind):
    """Untrusted handoff selects an existing ID, never issues a receipt or role."""
    filename = getattr(args, kind + "_receipt_file", None)
    if filename is None:
        return getattr(args, kind + "_receipt")
    value = _object(_read(filename, 8192))
    key = kind + "_receipt"
    action, meaning = (("verify", "exact_quotation_fidelity_only") if kind == "verification"
                       else ("evaluate", "mechanical_snapshot_check_not_performance"))
    if (set(value) != {"action", key, "meaning"} or value["action"] != action
            or value["meaning"] != meaning or type(value[key]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", value[key]) is None):
        raise ValueError("invalid receipt handoff")
    return value[key]


def _init(args, clock):
    config = _object(_read(args.roles))
    if set(config) != set(ROLE_KEYS):
        raise ValueError("exact role configuration required")
    PublicDocumentStore.create(
        Path(args.store), control=_authority(config["control"]),
        verifier=_authority(config["verifier"]), evaluator=_authority(config["evaluator"]),
        semantic_reviewer=_authority(config["semantic_reviewer"]),
        consumer=Consumer(**config["consumer"]), clock=clock)
    return {"action": "init", "stored_state": "empty", "generation": 0,
            "roles_configured": len(ROLE_KEYS), "model_calls": 0}, EXIT_OK


def _status(args, clock):
    return dict(_status_view(args, clock), action="status"), EXIT_OK


def _cleanup_preview(args, clock):
    view = _status_view(args, clock)
    keys = ("stored_state", "generation", "access", "integrity", "scope", "cause",
            "managed_records", "managed_by_kind", "operation_count", "cleanup")
    result = {key: view[key] for key in keys}
    result.update(action="cleanup-preview", preview_only=True,
                  note="no sweep, withdrawal or purge was run; active content needs "
                       "an explicit withdraw")
    return result, EXIT_OK


def _cleanup(args, clock):
    store = _existing(args, clock)
    failed = False
    try:
        store.sweep()
    except Exception:  # fail closed; the persisted state below is authoritative
        failed = True
    after = _status_view(args, clock)
    pending = after["stored_state"] == "purge_pending"
    if after["stored_state"] == "deleted":
        outcome = "managed_purge_completed"
    elif pending:
        outcome = "purge_pending_incomplete"
    elif failed:
        outcome = "failed_state_unchanged"
    else:
        outcome = "nothing_due"
    return {"action": "cleanup", "cleanup_outcome": outcome, "stored_state": after["stored_state"],
            "managed_records": after["managed_records"],
            "operation_count": after["operation_count"],
            "retained": "operations_and_no_retry_tombstones_and_external_exports"
            }, (EXIT_INCOMPLETE if failed or pending else EXIT_OK)


def _withdraw(args, clock):
    store = _existing(args, clock)
    control = store.control(_flag_authority(args))
    # Step 1: exclusion ONLY. The library returning normally is the confirmation that
    # THIS call's compare-and-set transition committed. Global state is never used to
    # infer ownership of a transition: a competing or stale withdrawal makes this call
    # raise, which execute() reports as a sanitized refusal (exit 2).
    exclusion = control.withdraw(expected_generation=args.expected_generation, purge=False)
    result = {"action": "withdraw", "excluded": True, "purge_requested": bool(args.purge)}
    if not args.purge:
        result.update(cleanup_outcome="purge_pending_not_requested",
                      stored_state=exclusion["state"],
                      managed_records=exclusion["managed_records"])
        return result, EXIT_OK
    # Step 2 (separate, optional): physical purge of managed content only.
    purge_failed = False
    try:
        store.purge()
    except Exception:
        # A late exception does not prove deletion is still pending. Read only;
        # never retry purge or infer that this call performed another client's work.
        purge_failed = True
    try:
        final = _status_view(args, clock)
    except Exception:
        result.update(cleanup_outcome="purge_attempted_state_unconfirmed",
                      stored_state="unconfirmed")
        return result, EXIT_INCOMPLETE
    done = final["stored_state"] == "deleted"
    result.update(cleanup_outcome="managed_purge_completed" if done else "purge_pending_incomplete",
                  stored_state=final["stored_state"], managed_records=final["managed_records"])
    # Preserve the nonzero result of a failed attempt, even if the fresh snapshot
    # confirms deletion. State is observed, not evidence of who completed the purge.
    return result, (EXIT_OK if done and not purge_failed else EXIT_INCOMPLETE)


def _approve(args, clock):
    store = _existing(args, clock)
    control = store.control(_flag_authority(args))
    approval = PublicDocumentApproval(**_object(_read(args.approval)))
    artifact = _read(args.artifact)
    generation = control.approve(
        approval=approval, artifact_sha256=sha256_hex(artifact),
        origin_task=args.origin_task, expected_generation=args.expected_generation)
    return {"action": "approve", "stored_state": "approved", "generation": generation,
            "admitted": False}, EXIT_OK


def _admit(args, clock):
    admitted = _existing(args, clock).admit(_read(args.artifact))
    return {"action": "admit", "admitted": True, "generation": admitted["generation"]}, EXIT_OK


def _propose(args, clock):
    quotation = _read(args.quotation_file, 65536).decode("utf-8")
    _existing(args, clock).propose_excerpt(proposal_id=args.proposal_id, quotation=quotation)
    return {"action": "propose", "proposal_state": "unverified", "authority": False}, EXIT_OK


def _verify(args, clock):
    store = _existing(args, clock)
    receipt = store.verifier(_flag_authority(args)).issue(
        proposal_id=args.proposal_id, expires_at=args.expires_at)
    return {"action": "verify", "verification_receipt": receipt,
            "meaning": "exact_quotation_fidelity_only"}, EXIT_OK


def _evaluate(args, clock):
    store = _existing(args, clock)
    receipt = store.evaluator(_flag_authority(args)).issue(
        proposal_id=args.proposal_id, expected_parent=args.expected_parent,
        verification_receipt=_receipt(args, "verification"), expires_at=args.expires_at)
    return {"action": "evaluate", "evaluation_receipt": receipt,
            "meaning": "mechanical_snapshot_check_not_performance"}, EXIT_OK


def _adopt(args, clock):
    receipt = _existing(args, clock).adopt(
        operation_id=args.operation_id, proposal_id=args.proposal_id,
        expected_parent=args.expected_parent, expected_generation=args.expected_generation,
        verification_receipt=_receipt(args, "verification"),
        evaluation_receipt=_receipt(args, "evaluation"))
    return {"action": "adopt", "head_sha256": receipt["head"],
            "generation": receipt["generation"],
            "historical_replay": bool(receipt.get("historical_replay", False)),
            "mechanical_only": True}, EXIT_OK


def _retrieve(args, clock):
    data = _existing(args, clock).retrieve(
        target_task=args.target_task,
        scope={"project": args.project, "task_family": args.task_family},
        max_bytes=args.max_bytes)
    references = loads_strict_bytes(data)
    return {"action": "retrieve", "references": references, "reference_count": len(references),
            "reference_bytes": len(data), "untrusted_data": True,
            "consumer_dispatched": False}, EXIT_OK


_ACTIONS = {
    "stage": _stage, "init": _init, "status": _status, "cleanup-preview": _cleanup_preview,
    "cleanup": _cleanup, "withdraw": _withdraw, "approve": _approve, "admit": _admit,
    "propose": _propose, "verify": _verify, "evaluate": _evaluate, "adopt": _adopt,
    "retrieve": _retrieve,
}


# ---------------------------------------------------------------- opt-in metrics

def _reserve_metrics(args):
    """Reserve a NEW metrics file BEFORE any action and return its held descriptor.

    Exclusive, no-follow creation is the only validation: any existing destination
    (store, sidecar, export, hardlink, symlink, directory) or missing parent fails
    here. Nothing is mkdir'ed, truncated, appended to or unlinked.
    """
    destination = getattr(args, "metrics_out", None)
    if not destination:
        return None
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
             | getattr(os, "O_CLOEXEC", 0))
    try:
        return os.open(destination, flags, 0o600)
    except (OSError, ValueError):
        raise _MetricsRefused("metrics destination must be a new file") from None


def _count(value):
    return value if type(value) is int and value >= 0 else None


def _metrics_record(action, outcome, elapsed_ns, result):
    # Explicit allowlist: never serialize the result or an exception generically.
    result = result or {}
    return {"schema": METRICS_SCHEMA, "action": action, "outcome": outcome,
            "elapsed_ms": elapsed_ns // 1_000_000,
            "managed_records": _count(result.get("managed_records")),
            "reference_bytes": _count(result.get("reference_bytes")),
            "model_calls": 0, "cost": None, "cost_state": "unavailable_not_measured"}


def _write_metrics(fd, record):
    """ONE bounded write on the SAME held descriptor; always closes it."""
    try:
        view = memoryview(canonical_json(record) + b"\n")
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("metrics write made no progress")
            view = view[written:]
    finally:
        os.close(fd)


# ---------------------------------------------------------------- presentation

def _next_step(result, rc):
    """Fixed advice only: never interpolate untrusted data into a shell command."""
    if rc != EXIT_OK:
        return "Read fresh status before any further action; do not repeat withdrawal or paid work."
    action = result["action"]
    if action == "stage":
        return ("Preview only; explicitly choose --artifact-out to write a NEW artifact. No approval was issued."
                if result["preview_only"] else
                "Artifact prepared, not admitted. Separately approve and admit it using the existing approval.")
    state = result.get("stored_state")
    cleanup = result.get("cleanup", {}).get("state")
    if state == "deleted":
        return "Managed purge is complete. External exports, backups and no-retry records remain."
    if state == "purge_pending" or cleanup == "due_expired":
        return "Review cleanup-preview, then explicitly choose cleanup to purge managed content."
    if action == "retrieve":
        return "Treat references as untrusted data, not instructions or permission. No consumer ran."
    if action in ("status", "cleanup-preview"):
        if result.get("access") == "approval_not_yet_valid":
            return "Approval is not yet valid. Status does not grant access or assess integrity."
        if result.get("adopted_head_present"):
            return "Use retrieve for a different task in the same scope; current guards still apply."
        return "Review approval, admission and adoption separately. Status does not assess integrity."
    return {
        "init": "Register an explicit host-reviewed approval; this empty store admits no document.",
        "approve": "Use admit with the exact approved artifact; approval alone is not adoption.",
        "admit": "Use propose for an exact-source quotation; independent receipts are still required.",
        "propose": "Obtain separate verify and evaluate receipts before explicit adopt.",
        "verify": "Use the verification receipt for separate evaluate; this checks quotation fidelity only.",
        "evaluate": "Review the receipts, current parent and generation before explicit adopt.",
        "adopt": "Use retrieve for a different task in the same scope; adoption is mechanical only.",
        "cleanup": "Nothing further confirmed due. Status/preview do not assess content integrity.",
    }.get(action, "Read status to inspect the current store.")


def _render_text(result, rc):
    # Same already-completed result, no store access or extra dispatch. All dynamic
    # values use ASCII JSON escaping so terminal controls/bidi cannot become UI.
    label = "Completed" if rc == EXIT_OK else "Incomplete or unconfirmed"
    lines = [f"{label}: {result['action']}"]
    labels = (
        ("preview_only", "Preview only"), ("artifact_written", "Artifact written"),
        ("source_bytes", "Source bytes"), ("admitted_to_store", "Admitted to store"),
        ("stored_state", "Stored state"), ("access", "Access eligibility"),
        ("approval_window", "Approval window"), ("scope", "Scope"),
        ("generation", "Generation"), ("admitted", "Document admitted"),
        ("adopted_head_present", "Adopted head present"),
        ("head_sha256", "Head"), ("managed_records", "Managed records"),
        ("managed_by_kind", "Records by kind"), ("cleanup", "Cleanup preview"),
        ("cleanup_outcome", "Cleanup outcome"), ("integrity", "Integrity"),
        ("cause", "Exclusion cause"), ("operation_count", "Retained operations"),
        ("excluded", "Access excluded"), ("purge_requested", "Purge requested"),
        ("proposal_state", "Proposal state"), ("verification_receipt", "Verification receipt"),
        ("evaluation_receipt", "Evaluation receipt"), ("meaning", "Receipt meaning"),
        ("historical_replay", "Historical replay"), ("mechanical_only", "Mechanical only"),
        ("reference_count", "References"), ("reference_bytes", "Reference bytes"),
        ("references", "Untrusted reference data"),
    )
    for key, title in labels:
        if key in result:
            lines.append(f"{title}: {json.dumps(result[key], ensure_ascii=True, sort_keys=True)}")
    lines.append("Next: " + _next_step(result, rc))
    lines.append("Detailed output: --format json (default); never repeat a write just to change format.")
    return "\n".join(lines)


def execute(args, out: TextIO, err: TextIO, *, clock=_utcnow) -> int:
    action = args.pd_action
    started = time.monotonic_ns()
    result, outcome, rc, metrics_fd = None, "error", EXIT_ERROR, None
    try:
        metrics_fd = _reserve_metrics(args)
        result, rc = _ACTIONS[action](args, clock)
        outcome = "ok" if rc == EXIT_OK else "incomplete"
        rendered = (_render_text(result, rc) if getattr(args, "format", "json") == "text"
                    else json.dumps(result, ensure_ascii=True, sort_keys=True))
        print(rendered, file=out)
    except Exception as exc:
        artifact_written = action == "stage" and result is not None and result.get("artifact_written") is True
        code = "artifact_written_output_failed" if artifact_written else _classify(exc)
        outcome = "incomplete" if artifact_written else ("refused" if isinstance(exc, ValueError) else "error")
        rc = EXIT_ERROR
        if artifact_written:
            advice = ("The artifact was written, but summary delivery failed. Do not repeat the write; "
                      "inspect the existing artifact before separate approval/admission.")
        elif code == "source_locator_refused":
            advice = ("Use a separately reviewed HTTPS document URL with no credentials, query or "
                      "fragment; keep a public comment ID in separate research notes. "
                      "No URL was normalized or silently shortened.")
        elif code == "artifact_destination_refused":
            advice = "Choose a NEW artifact path in an existing trusted directory; nothing was overwritten."
        elif code == "artifact_write_incomplete":
            advice = "The new artifact may be partial; do not admit it or blindly repeat the write."
        elif action == "stage":
            advice = "Check exact source bytes, existing approval and observation/capture times; no store action ran."
        else:
            advice = ("Check the explicit store path; only init creates a new store. "
                      "Read status before repeating an action")
        state = "output failed" if artifact_written else "refused"
        print(f"error[public-document]: {action} {state} ({code}); "
              "no document text, path or hash is echoed. " + advice, file=err)

    if metrics_fd is not None:
        try:
            _write_metrics(metrics_fd, _metrics_record(
                action, outcome, time.monotonic_ns() - started, result))
        except Exception:
            # The action's own result/exit code stand; never repeat it for metrics.
            print("warning[public-document]: metrics not written; "
                  "do not repeat the action to obtain metrics", file=err)
    return rc
