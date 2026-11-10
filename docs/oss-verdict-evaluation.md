# Strict verdict parsing and frozen fixture evaluation

[Current status](implementation-status.md) | [日本語の状況](implementation-status.ja.md)

## Deliberate strict subset

[Parser / evaluator](../src/agent_sleep_lab/oss_verdict_evaluation.py) accepts one
whole UTF-8 JSON object with exactly `accept` (boolean) and `rationale`
(nonempty string after stripping). Replies are capped at 65,536 bytes; stripped
rationales at 8,192 bytes. Duplicate keys, BOM, nonfinite numbers, lone surrogates,
extra fields, code fences, surrounding prose and coerced rationale values fail
with finite error codes, not excerpts of untrusted model text.

The pinned OSS parser extracts the first-to-last braces and coerces rationale
values to text. This implementation is **stricter, not an identical port**.
It returns a typed decision and untrusted rationale, not authority, a verifier
receipt, a memory adoption or an independently established fact.
The target source and its permissive retry policy are not changed.

## Freeze before any intent

Call `freeze_manifest(dataset_id=..., expected_accept=True or False,
task_sha256=..., issue_number=...)` to declare one synthetic fixture's expected
decision. Pass its result as `evaluation_manifest=...` to
[ExecutionJournal.register](../src/agent_sleep_lab/oss_execution_journal.py).
The manifest is validated and included in the immutable plan binding **before
registration completes or any arm intent can start**. It pins:

- fixed evaluator/parser identifiers and complete implementation-file hash;
- strict JSON dependency hash and pinned target-parser source hash;
- whole task hash **and the actual issue number**, not a label for another issue;
- explicit boolean fixture label, bounded dataset ID and `synthetic_fixture` partition;
- exact-match criterion, invalid-output score zero and parser byte limits.

A manifest cannot be changed or attached later to an existing unscored plan.
There is no DB migration; older bindings omit the optional field and stay
unscored. Caller-supplied labels are **declared test fixtures, not authenticated
truth or a blinded/held-out scientific oracle**. No model generates the label.
The manifest/answer is never inserted into captured prompts or transport requests.

## Reporting, failure and disclosure

The journal saves the original reply/receipt independently of parser success.
At report time, after current-context and saved-reply integrity checks, optional
`verdict_evaluation` contains:

| Status | Meaning |
| --- | --- |
| `not_configured` | No frozen manifest; no score |
| `incomplete` | A stopped/missing/unknown arm prevents a paired score |
| `complete` | Both transport outcomes resolved and strict verdicts parsed |
| `complete_with_invalid_verdict` | Invalid verdicts are scored zero, not excluded |
| `withheld_context` | Context changed/unavailable; no parsed text or scores disclosed |
| `unavailable_evaluator_version_or_manifest` | Frozen code/dependency/criterion unavailable; never silently re-score |

For a parsed verdict, score is one only if its decision matches the frozen
boolean. A valid decision can score zero. Rationale presence is validated, but
its truth/quality is **not scored**. Invalid completed replies score zero without
retry. Unknown/missing outcomes keep the pair incomplete; they are not silently
dropped or converted into successful decisions. The denominator remains two arms.
Only complete pairs get `reference_minus_baseline`; this is a single-fixture
difference, **not effect or performance evidence**.

The top-level execution verdict remains null. Usage/cost stay unavailable,
semantic memory use/performance stay unevaluated, and nothing is adopted.
A later code/dependency mismatch withholds scoring rather than replacing the
frozen criterion. Direct use of the calculation helper does not prove pre-call
freezing; the journal provides that lifecycle. Context/store writes are still
not a cross-store atomic transaction, and withholding is not physical deletion.

## Verification scope

[Eight new cases](../tests/test_oss_verdict_evaluation.py) use injected process
envelopes and test-authored capture/adoption labels. A separate local offline
acceptance verified all pinned source blobs, executed only the reviewed target
parser definitions on three synthetic samples (one match and two deliberate
strict-subset refusals), then ran actual captured OSS prompts through two mocked
replies, restart/replay, scoring and policy revocation. The authored fixture
difference is not a model result. No live model/effect measurement was run.

Remaining: live verification under applicable spending controls, a meaningful
independently justified evaluation dataset, broader multi-task aggregation,
rationale quality verification and paired usage/cost accounting.
