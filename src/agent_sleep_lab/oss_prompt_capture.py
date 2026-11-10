"""Parent side of offline A/B provider-request preparation (stdlib only).

Reuses the existing frozen-source preflight, payload schema and bounded
launcher of ``oss_offline_parent``; only the worker script and the output
contract are new. One fresh guarded process builds both arms, so the baseline
and reference requests come from the same loaded reviewed sources.

What a returned artifact is: the hash-bound request body that the pinned
``OpenAITriager.judge`` built for the built-in synthetic borderline issue, with
and without the untrusted reference frame.

What it is NOT: dispatch authorization, a model receipt, a verdict, semantic
memory use, performance evidence, an adopted memory or a verifier/evaluator
receipt. Nothing here contacts a provider, reads environment credentials or
authenticates where the reference bytes came from. A result obtained through
an injected worker argv is a stand-in, never target integration.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_offline_worker as worker
from agent_sleep_lab import oss_prompt_capture_worker as capture
from agent_sleep_lab.oss_bridge import CollectOnlyBridge

CHECK_PROTOCOL = "agent-sleep-oss-prompt-capture-check/1"
BUILTIN_WORKER = "builtin_pinned_prompt_capture_worker"
STAND_IN_WORKER = parent.STAND_IN_WORKER
ORIGIN_BYTES = "caller_supplied_bytes_store_origin_unauthenticated"
ORIGIN_BRIDGE = "explicit_bridge_current_policy_retrieval_store_unauthenticated"
CheckError = parent.CheckError


def builtin_worker_argv():
    argv = parent.builtin_worker_argv()
    return argv[:-1] + [str(Path(capture.__file__).resolve())]


def _issue(doc):
    for item in worker.synthetic_task()["issues"]:
        expected = dict(item, repo=worker.REPOSITORY,
                        url="fixture://issue/%d" % item["number"])
        if doc == expected:
            return expected
    raise ValueError("issue is not a built-in synthetic issue")


def validate_output(raw, *, task, reference):
    """Check the capture output and its source/task/reference/prompt bindings.

    Every arm hash and the A/B relation are recomputed here from the request
    bodies; worker-reported values are only compared, never trusted.
    """
    try:
        if type(raw) is not bytes or not 1 <= len(raw) <= parent.MAX_OUTPUT_BYTES:
            raise ValueError("bounded worker output required")
        doc = worker.strict_json(raw)
        if type(doc) is not dict or set(doc) != capture.OUTPUT_KEYS:
            raise ValueError("exact prompt capture output keys required")
        if worker.encoded(doc) != raw:
            raise ValueError("canonical worker output required")
        if task != parent.builtin_task():
            raise ValueError("only built-in synthetic task bytes accepted")
        notes = capture.reference_notes(reference)
        records = len(worker.validate_reference(reference)["records"])
        if (doc["protocol"] != capture.OUTPUT_PROTOCOL or doc["synthetic_only"] is not True
                or doc["artifact_kind"] != capture.ARTIFACT_KIND):
            raise ValueError("unexpected prompt capture protocol")
        if (doc["agent_commit"] != worker.AGENT_COMMIT
                or doc["executed_source_sha256"] != dict(worker.SOURCE_HASHES)):
            raise ValueError("source binding mismatch")
        if doc["task_sha256"] != worker.digest(task):
            raise ValueError("task binding mismatch")
        if (doc["reference_sha256"] != worker.digest(reference)
                or type(doc["reference_records"]) is not int
                or doc["reference_records"] != records):
            raise ValueError("reference binding mismatch")
        if (doc["dispatch_authorization"] is not False or doc["model_receipt"] is not None
                or doc["verdict"] is not None
                or doc["semantic_memory_use"] != "not_evaluated"
                or doc["performance_improvement"] != "not_evaluated"):
            raise ValueError("preparation artifact must not claim dispatch, verdict or use")
        if (doc["provider_class"] != capture.PROVIDER_CLASS
                or doc["model"] != capture.MOCK_MODEL
                or doc["model_identity"] != capture.MODEL_IDENTITY
                or doc["transport"] != capture.TRANSPORT
                or doc["credentials"] != capture.CREDENTIALS):
            raise ValueError("mock model/transport/credential labels required")
        issue = _issue(doc["issue"])
        score, reasons = doc["score"], doc["reasons"]
        if (doc["band"] != "borderline" or doc["thresholds"] != dict(accept=0.60, skip=0.40)
                or type(score) is not float or not 0.40 <= score < 0.60
                or type(reasons) is not list or not 1 <= len(reasons) <= 32
                or any(type(reason) is not str or not reason or len(reason) > 2048
                       for reason in reasons)):
            raise ValueError("borderline score/reasons contract mismatch")
        arms = doc["arms"]
        if type(arms) is not dict or set(arms) != {"baseline", "reference"}:
            raise ValueError("exactly baseline and reference arms required")
        capture.validate_arm(arms["baseline"], "baseline", "")
        capture.validate_arm(arms["reference"], "reference", notes)
        if arms["baseline"]["header_names"] != arms["reference"]["header_names"]:
            raise ValueError("arms differ in request headers")
        for arm in arms.values():
            prompt = capture.prompt_of(arm["payload"])
            # Same issue and rule reasons must be present in both requests.
            if any(text not in prompt for text in
                   [issue["repo"], issue["title"], issue["body"], *reasons]):
                raise ValueError("prompt does not carry the bound issue and reasons")
        if doc["comparability"] != capture.comparability(
                arms["baseline"]["payload"], arms["reference"]["payload"], notes):
            raise ValueError("A/B comparability mismatch")
        trace = doc["target_calls"]
        prefixes = tuple(name + ":" for name in worker.SOURCE_HASHES)
        if (type(trace) is not dict
                or any(type(key) is not str or not key.startswith(prefixes)
                       or type(count) is not int or count < 1
                       for key, count in trace.items())
                or any(trace.get(key, 0) < 2 for key in capture.REQUIRED_TRACE)):
            raise ValueError("output must trace judge and triage_prompt in reviewed sources")
    except CheckError:
        raise
    except (ValueError, RecursionError) as error:
        raise CheckError(str(error)) from None
    return doc


def prepare(repo, reference_bytes, *, git=None, worker_argv=None,
            timeout=parent.WORKER_TIMEOUT, reference_origin=ORIGIN_BYTES):
    """Preflight, launch once, validate; return (summary, capture document).

    ``reference_bytes`` is an explicit existing canonical bundle. Structural
    validity does not authenticate its store origin, and the summary says so.
    There is no retry: any failure raises and nothing is re-launched.
    """
    if reference_origin not in (ORIGIN_BYTES, ORIGIN_BRIDGE):
        raise CheckError("unknown reference origin label")
    if (type(timeout) not in (int, float) or not math.isfinite(timeout)
            or not 0 < timeout <= parent.WORKER_TIMEOUT):
        raise CheckError("worker timeout out of range")
    try:
        capture.reference_notes(reference_bytes)  # before any git or process call
    except ValueError as error:
        raise CheckError(str(error)) from None
    sources = parent.freeze_sources(repo, git=git)
    payload = parent.prepare_payload(sources, reference_bytes)
    task = parent.builtin_task()
    if worker_argv is None:
        argv, label = builtin_worker_argv(), BUILTIN_WORKER
        hashes = dict(capture=worker.digest(Path(argv[-1]).read_bytes()),
                      base=worker.digest(Path(worker.__file__).resolve().read_bytes()))
    else:
        argv, label, hashes = worker_argv, STAND_IN_WORKER, None
    raw = parent.launch(argv, payload, timeout=timeout)
    doc = validate_output(raw, task=task, reference=reference_bytes)
    arms = {name: {key: arm[key] for key in (
        "request_sha256", "prompt_sha256", "prompt_bytes", "project_notes_sha256")}
        for name, arm in doc["arms"].items()}
    summary = dict(
        protocol=CHECK_PROTOCOL, synthetic_only=True,
        artifact_kind=capture.ARTIFACT_KIND, agent_repository=parent.AGENT_REPOSITORY,
        repository_identity="local_origin_url_claim_unauthenticated",
        agent_commit=worker.AGENT_COMMIT, source_sha256=dict(worker.SOURCE_HASHES),
        worker_launch=label, worker_sha256=hashes,
        task_sha256=doc["task_sha256"], reference_sha256=doc["reference_sha256"],
        reference_records=doc["reference_records"], reference_origin=reference_origin,
        reference_role="untrusted_reference_data_not_operating_authority",
        issue_number=doc["issue"]["number"], score=doc["score"],
        reasons_sha256=worker.digest(worker.encoded(doc["reasons"])),
        provider_class=doc["provider_class"], model=doc["model"],
        model_identity=doc["model_identity"], transport=doc["transport"],
        credentials=doc["credentials"], arms=arms, comparability=doc["comparability"],
        worker_output_sha256=worker.digest(raw),
        dispatch_authorization=False, model_receipt=None, verdict=None,
        semantic_memory_use="not_evaluated", performance_improvement="not_evaluated",
        delivery_and_use_verified=False)
    return summary, doc


def prepare_from_bridge(bridge, repo, *, query, max_bytes, max_records=16,
                        git=None, worker_argv=None, timeout=parent.WORKER_TIMEOUT):
    """Retrieve through an explicit existing bridge, then ``prepare``.

    Uses the bridge's current-policy scoped retrieval with the worker's
    reference caps. The store behind the bridge stays caller-controlled and
    unauthenticated; no memory is created or adopted here.
    """
    if not isinstance(bridge, CollectOnlyBridge):
        raise TypeError("explicit CollectOnlyBridge required")
    task = worker.synthetic_task()
    if (bridge.repository != task["repository"]
            or bridge.agent_commit != task["agent_commit"]):
        raise CheckError("bridge repository/agent commit differ from the pinned task")
    if type(query) is not str or not query.strip() or len(query) > 1024:
        raise CheckError("explicit bounded retrieval query required")
    if type(max_bytes) is not int or not 1 <= max_bytes <= worker.MAX_REFERENCE_BYTES:
        raise CheckError("reference byte cap exceeds the offline worker cap")
    if type(max_records) is not int or not 1 <= max_records <= worker.MAX_REFERENCE_RECORDS:
        raise CheckError("reference record cap exceeds the offline worker cap")
    if not isinstance(repo, (str, Path)) or not os.path.isabs(str(repo)):
        raise CheckError("explicit absolute local repository path required")
    bundle = bridge.reference_context(query=query, max_bytes=max_bytes,
                                      max_records=max_records)
    reference = bundle.bundle_bytes
    if type(reference) is not bytes or len(reference) > max_bytes:
        raise CheckError("reference byte cap exceeded")
    return prepare(repo, reference, git=git, worker_argv=worker_argv, timeout=timeout,
                   reference_origin=ORIGIN_BRIDGE)
