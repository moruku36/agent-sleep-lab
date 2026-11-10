# Explicit selected-issue offline probes

[Current status](implementation-status.md) | [日本語の状況](implementation-status.ja.md)

## Selection and versions

The default `oss_prompt_capture.prepare*` call retains v1: the one built-in
borderline issue (#3). Opt in explicitly for any built-in issue, without an
issue importer or target configuration change:

```python
from agent_sleep_lab import oss_prompt_capture as capture

selection = capture.selected_issue_probe(2)
summary, document = capture.prepare_from_bridge(
    bridge, absolute_local_target_repo, query=query, max_bytes=32768,
    selected_issue_probe=selection)
```

`selection` has exactly `protocol`, `issue_number`, `issue_sha256` and
`task_sha256`. Its protocol is `agent-sleep-oss-selected-issue-probe/1`.
Only literal integers 1–5 are accepted; booleans, floats and strings fail.
The hash covers the complete canonical built-in issue, including its number,
labels, repository and fixture URL; the task hash covers the unchanged suite
and source pins. A changed number with an old hash fails, including #1 versus
#4/#5, whose prompt text happens to be identical. Caller and worker both validate
selection before source execution; the parent refuses invalid selection before
retrieval, Git reads or worker launch.

The explicit capture input wrapper, output and preparation summary use `/2`.
The base offline worker's input remains exact v1. There is no permissive union of
fields: v1 rejects probe fields, v2 requires selection and exact provenance.
`validate_output(..., selected_issue_probe=selection)` checks against the
caller's expected selection; leaving it out selects v1 validation. Downstream
consumers validate the explicit selection carried by the complete v2 artifact
and freeze it with that artifact's hash. Saved v1 documents need no migration.

## Actual scoring and forced judge path

Both routes load the same eleven pinned public source blobs. The worker uses
`Rules()` defaults, `score_issue_ref`, `verdict`, `OpenAITriager.judge` and
`triage_prompt`. It records the actual score, reasons and band. It never
substitutes a borderline score. Each arm makes one inert capture-transport
call, which raises the pinned `LLMTriageError` without returning a response.
No environment credential, network request, model reply or verdict is involved.

Every selected capture, including selected #3, carries exact `probe_provenance`:
`route=explicit_selected_issue_forced_judge_probe`,
`normal_automatic_triage=false`, default pinned scoring, and unchanged pinned
prompt provenance. Accept/skip-band issues reach the judge only because of this
explicit probe; this does not exercise the normal collection/automatic triage
route, duplicate checks or target task execution. The pinned prompt still says
“borderline band.” Those original bytes are preserved; the artifact's separate
score/band and provenance describe the actual route.

The validator recomputes hashes, selected issue identity, score/band consistency,
prompt field bindings and the two-arm relation. v2 additionally requires exactly
the pinned `Project notes` insertion, with no extra per-task instructions, and
traces of default scoring plus two judge/prompt calls. These are structural
integrity checks, not authentication or independent re-execution of scoring.
Caller-supplied worker/store labels remain unauthenticated; an injected worker
argv remains explicitly a stand-in.

## Journals and comparable cohorts

Adapters and journals retain selection, actual score/band and probe provenance.
Probe receipts bind them to the whole capture hash. Durable plans freeze a
distinct probe execution kind; they cannot replay as ordinary v1 execution.
The fake journal remains fake-only. No schema migration, dispatch permission,
retry, caller budget, current-policy or invalid-output rule changes.

Selected-probe cohorts use `agent-sleep-oss-fixture-cohort/2`, with exact
`selection_contract` and `probe_provenance` fields in both frozen documents and
reports. v1 cohort documents and comparison hashes retain their original rules.
Versions/routes cannot mix in one cohort. Selection is frozen in each member's
full binding before any member intent; membership and all answer manifests are
also frozen under the existing reservation.

Only issue identity, task prompt, actual task-specific score/reasons/band and
fixture answer may vary. Source pins, worker hashes, reference bytes/context,
retrieval, request settings, adapter/transport/limits and evaluator settings
must match. The validated identical pinned notes block supplies the v2 insertion
comparison hash, avoiding task-dependent prefix/suffix newline placement.
The full member binding still pins both exact requests and all omitted fields.
All registered tasks stay in the denominator; missing/unknown/withheld outcomes
prevent means, while invalid completed verdicts count as failures without retry.

## Regression sources and limits

[Selected-probe cases](../tests/test_oss_selected_probe.py) use the actual guarded
worker and [unaltered pinned public sources](../tests/fixtures/oss-pinned-sources.json),
with acquisition injected instead of Git reads. Source hashes are never patched.
The fixture retains the upstream MIT license. Adoption data and all replies are
test-authored; no capture, score, judge or prompt is substituted. Tests cover
selection rejection, v1/v2 boundaries, real five-issue capture, durable restart,
cohort freezing, invalid replies, unknown outcomes and policy withholding.

These fixtures are development inputs. #1/#4/#5 repeat the same issue text;
five distinct fixture identities are not five independent problems. No holdout,
semantic memory use, model quality, scientific performance or total cost is
established. Verification results belong only in the status pages above.
