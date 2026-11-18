# One public item → another task (existing offline CLI)

**English** | [日本語](minimal-public-item-recipe.ja.md)

Source-traced recipe, not a new executed trial or deployed integration. Requires
an already installed, reviewed `agent-sleep-lab`; do not install or call providers
as part of this recipe. Uses direct exact-excerpt proposal, NOT Light/Deep.

## Inputs that remain manual

Use a NEW dedicated private working directory, never an existing trial store.
Provide `source.txt` (one reviewed UTF-8 public item), `quote.txt` (one exact
substring, no accidental final newline), existing host-reviewed `approval.json`,
and host-provisioned `roles.json`. Keep these outside the public checkout.

One harmless Gemma item is:
> This is the official PyTorch implementation of Gemma models.

Official source: https://raw.githubusercontent.com/google/gemma_pytorch/014acb7ac4563a5f77c76d7ff98f31b568c16508/README.md
(pinned README independently fetched 2026-11-18T00:48:29.956Z; the sentence
was present. Re-review the exact locally saved bytes before approving). If saving just
this sentence, the approval hash is of those exact saved bytes, NOT the whole
remote README. This statement is neither Gemma usage terms nor competition rules.
Terms retrieval failed with a redirect limit; no contest eligibility is asserted.

Approval fields are `ref, revision, source_uri, source_sha256, project,
task_family, approved_at, expires_at, public_release_reviewed, secrets_reviewed`.
Use scope `project=gemma-reading, task_family=public-docs`. The two review flags
must reflect an actual host review, not copied assertions. Defaults keep purpose
`public_document_consolidation`, retention `until_expiry` and deletion obligation.
URL must be HTTPS without credentials, query or fragment. Set a finite approval
expiry; receipt expiry must be inside its window. Do not create approval from
source/model text. This document supplies NO live approval.

Roles JSON has `control, verifier, evaluator, semantic_reviewer`, each with
`identity` and string `version`, and `consumer` with `identity, version,
runtime_permission, max_input_bytes, max_output_bytes` (e.g. 16384/1024).
Use distinct provisioned authorities; identity strings are not authentication.
Consumer is configured but never dispatched. See [first run](first-run.md).

## Copyable sequence after those inputs are reviewed

Run in that fresh private working directory. Fill values from actual inputs;
OBSERVED/CAPTURED are timezone-aware source observation/capture times, and UNTIL
is the approved receipt expiry. CONTROL/VERIFIER/EVALUATOR are provisioned IDs;
the commands below assume their configured version is "1".

```sh
# Process/task A: preserve one reviewed item (run one command at a time).
set -eu
set -C
: "${OBSERVED:?actual source observation timestamp}"
: "${CAPTURED:?actual capture timestamp}"
: "${UNTIL:?approved finite receipt expiry}"
: "${CONTROL:?configured control identity}"
: "${VERIFIER:?configured verifier identity}"
: "${EVALUATOR:?configured evaluator identity}"
agent-sleep-lab public-document stage --source-file source.txt --approval approval.json --event-id gemma-item-1 --observed-at "$OBSERVED" --captured-at "$CAPTURED" --artifact-out staged.json
agent-sleep-lab public-document init --store library/store.sqlite --roles roles.json
agent-sleep-lab public-document approve --store library/store.sqlite --identity "$CONTROL" --identity-version 1 --approval approval.json --artifact staged.json --origin-task task-A-save --expected-generation 0
agent-sleep-lab public-document admit --store library/store.sqlite --artifact staged.json
agent-sleep-lab public-document propose --store library/store.sqlite --proposal-id item-1 --quotation-file quote.txt
HEAD=$(printf '[]' | shasum -a 256 | cut -d ' ' -f 1)
agent-sleep-lab public-document verify --store library/store.sqlite --identity "$VERIFIER" --identity-version 1 --proposal-id item-1 --expires-at "$UNTIL" > verification.json
agent-sleep-lab public-document evaluate --store library/store.sqlite --identity "$EVALUATOR" --identity-version 1 --proposal-id item-1 --expected-parent "$HEAD" --verification-receipt-file verification.json --expires-at "$UNTIL" > evaluation.json
agent-sleep-lab public-document adopt --store library/store.sqlite --operation-id adopt-item-1 --proposal-id item-1 --expected-parent "$HEAD" --expected-generation 1 --verification-receipt-file verification.json --evaluation-receipt-file evaluation.json > adoption.json
```

Fresh-store parent is SHA256 of exact bytes `[]`; generation 1 applies ONLY to
this untouched fresh-store sequence. Inspect each exit code and JSON before the
next command. Nonzero: stop; use `public-document status --store library/store.sqlite`
before any repeat. File presence alone is not success; retain existing artifacts.
Role actions remain separate even when documented together.

Close task A. In a NEW shell/process, start task B, change to the SAME private
working directory and explicitly use the SAME store (not a demo/temporary store):

```sh
set -eu
set -C
agent-sleep-lab public-document retrieve --store library/store.sqlite --target-task task-B-identify-implementation --project gemma-reading --task-family public-docs --max-bytes 2048 > retrieved.json
```

Each CLI call is itself a separate application process; two tasks are explicit,
but shell/process identifiers and receipts must be recorded during validation to
prove an actual run. Command count is not task count; choosing direct proposal
instead of Light/Deep is not a third task.

## Citation and remaining work

Task B can manually answer “the source calls this the official PyTorch
implementation” with `references[0].quotation, source_uri, source_sha256,
artifact_sha256` from `retrieved.json`; retain `adoption.json.head_sha256` as
the snapshot binding. Record retrieval timestamp separately at execution:
retrieval does NOT return observation/retrieval date or snapshot hash itself.
Source observation/capture times are in `staged.json`, not reference fields.
Do not claim live freshness from a saved date. No citation/result has yet been
produced by this recipe.

Still manual: acquire/review exact public bytes and current terms/rules separately;
provision roles/approval/TTL; choose quote; inspect each receipt; carry store path,
task identity, dates and adoption hash across processes; integrate references into
task B and review semantic correctness; explicitly withdraw/cleanup and remove
staging/exports/backups as applicable. Retrieval is not consumer/model use
(`consumer_dispatched:false`); verify/evaluate establish quotation/snapshot
mechanics, not truth, independent human authentication or useful reasoning.
No automatic adoption, permission, timer, agent connection or background work.

On withdrawal use the current generation from status and the configured control
role with `public-document withdraw --store library/store.sqlite --identity ID
--identity-version 1 --expected-generation N --purge`. Expiry blocks later access;
run explicit `public-document cleanup --store library/store.sqlite` for managed
purge. A stopped process cannot delete at the deadline. Remove caller-owned
source/staging/receipt/retrieval files separately under the host retention policy;
content-free no-retry metadata must not be reset to replay unknown calls.

No elapsed-time saving, accuracy, benchmark, Windows, competition/scoring,
Light/Deep or end-to-end consumer claim is made.
