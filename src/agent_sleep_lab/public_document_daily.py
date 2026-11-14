"""Thin daily-use command namespace for ONE persistent public-document store.

``agent-sleep-lab public-document <action>`` drives the existing
``PublicDocumentStore`` lifecycle. It adds NO model, network, provider, dispatch or
automatic-adoption path. It never invents owner approval or a semantic judgment:
``approve`` registers the host-supplied approval file, and ``verify``/``evaluate``
register the library's MECHANICAL receipts (exact-quotation fidelity, snapshot
check) for the one explicitly named role identity.

* Only ``init`` creates a store (and its parent directories). Every other action
  opens an EXISTING store and refuses a missing one.
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
* Exit codes: 0 completed or nothing due; 1 the action was attempted but cleanup is
  incomplete (``purge_pending_incomplete``: exclusion committed, run ``cleanup`` again;
  ``failed_state_unchanged``: an error before exclusion, inspect with ``status``); 2
  refused or failed, with no completed effect confirmed by THIS call. After a nonzero
  code, read the persisted state with ``status`` before repeating anything.
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
from agent_sleep_lab.public_source_intake import PublicDocumentApproval
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
    try:
        store.purge()
    except Exception:  # exclusion above is already committed; purge stays pending
        result.update(cleanup_outcome="purge_pending_incomplete", stored_state="purge_pending")
        return result, EXIT_INCOMPLETE
    try:
        final = store.audit()
    except Exception:  # purge returned, but its final state could not be read back
        result.update(cleanup_outcome="purge_attempted_state_unconfirmed",
                      stored_state="unconfirmed")
        return result, EXIT_INCOMPLETE
    done = final["state"] == "deleted"
    result.update(cleanup_outcome="managed_purge_completed" if done else "purge_pending_incomplete",
                  stored_state=final["state"], managed_records=final["managed_records"])
    return result, (EXIT_OK if done else EXIT_INCOMPLETE)


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
        verification_receipt=args.verification_receipt, expires_at=args.expires_at)
    return {"action": "evaluate", "evaluation_receipt": receipt,
            "meaning": "mechanical_snapshot_check_not_performance"}, EXIT_OK


def _adopt(args, clock):
    receipt = _existing(args, clock).adopt(
        operation_id=args.operation_id, proposal_id=args.proposal_id,
        expected_parent=args.expected_parent, expected_generation=args.expected_generation,
        verification_receipt=args.verification_receipt,
        evaluation_receipt=args.evaluation_receipt)
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
    "init": _init, "status": _status, "cleanup-preview": _cleanup_preview,
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


def execute(args, out: TextIO, err: TextIO, *, clock=_utcnow) -> int:
    action = args.pd_action
    started = time.monotonic_ns()
    result, outcome, rc, metrics_fd = None, "error", EXIT_ERROR, None
    try:
        metrics_fd = _reserve_metrics(args)
        result, rc = _ACTIONS[action](args, clock)
        outcome = "ok" if rc == EXIT_OK else "incomplete"
        print(json.dumps(result, ensure_ascii=True, sort_keys=True), file=out)
    except Exception as exc:
        code = _classify(exc)
        outcome = "refused" if isinstance(exc, ValueError) else "error"
        rc = EXIT_ERROR
        print(f"error[public-document]: {action} refused ({code}); "
              "no document text, path or hash is echoed", file=err)
    if metrics_fd is not None:
        try:
            _write_metrics(metrics_fd, _metrics_record(
                action, outcome, time.monotonic_ns() - started, result))
        except Exception:
            # The action's own result/exit code stand; never repeat it for metrics.
            print("warning[public-document]: metrics not written; "
                  "do not repeat the action to obtain metrics", file=err)
    return rc
