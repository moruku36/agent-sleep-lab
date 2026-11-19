# First run: understand the offline demo

**English** | [日本語](first-run.ja.md) | [Home](../README.md)

This is a walkthrough, not a second status page. For verified capabilities and
open gaps, use [implementation status](implementation-status.md).

## Install and run

Use Python **3.11 or newer**, from a local checkout:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/agent-sleep-lab demo --format text
```

Installation may download build tools and dependencies; it is not guaranteed
offline. Once installed with its dependencies, the demo runtime needs no network,
credentials or live model. No OpenClaw account is needed for this demo.
If installation fails, check Python version and package availability; do not
switch to a paid provider to repair installation.

For the full machine-readable report, JSON remains the default:

```sh
.venv/bin/agent-sleep-lab demo
.venv/bin/agent-sleep-lab demo --format json
```

Text is an opt-in presentation of the same scripted walkthrough, not another
execution mode. No caller data, existing store, provider or output-file options
are accepted. See [the complete demo contract](runtime-guide.md#built-in-offline-demo).

## Read the result

Follow capture → scripted Light/Deep → pending candidate → separate local fixture
verification/evaluation → atomic adoption → retrieval → paired comparison.
The fixture contains two events, one candidate/adopted memory and two task pairs.
Scripted calls are **not live-model calls**; exact-match scores verify wiring,
not semantic usefulness or general improvement.

In JSON, inspect `status`, `synthetic_only`, `calls`, `adoption`,
`retrieval` and `comparison`. The live-provider/integration/performance flags
remain false. Text summarizes the same boundaries; retain JSON when you need
hashes, frozen membership and detailed per-arm evidence.
`temporary_state_removed:true` is emitted only after connections close and the
three disposable SQLite stores are removed. Success does not leave a reusable
memory or connect an existing agent. Normal success/failure paths clean up;
forced termination or host failure is not a cleanup guarantee.
Errors exit 2 without a success report. Read the diagnostic; do not reinterpret
partial output as adoption or retry an unknown live operation.

The demo bounds calls and UTF-8 bytes; these are not generated-token or currency
caps. Synthetic-zero/unavailable labels are not measured savings.

## Trace withdrawal offline before a real trial

Read the [minimum synthetic adoption → use → withdrawal trace](offline-lifecycle-trace.md).
It reuses an existing one-case fixture, with exact operations and checks including
purge failure/recovery. Temporary demo cleanup is not authorization withdrawal.
The documented trace is not automatically executed and consumes its own test allocation.

## Read advice before resuming

Use `resume-advice` with an existing local adoption store and a
[strict runtime store config](../configs/runtime-store.example.json).

```sh
agent-sleep-lab resume-advice --store-config private/store.json \
  --project p --task-family t --environment lab:local --candidate resume:1
```

To opt in, include the exact tag `resume-advice:<environment>/<candidate>` in the
memory's `tags` through the normal verification and adoption process. The example
uses `resume-advice:lab:local/resume:1`. IDs are case-sensitive and limited to
128 characters. They start with an ASCII letter or digit and may also contain
`.`, `_`, `:`, or `-` after it. The `/` separates the environment from the candidate.
The adopted memory's hash covers the tag. Retrieval requires the exact project,
task family and full tag.

The command reads one snapshot under the current eligibility policy. It shows up
to three eligible experience memories in memory ID order, subject to a 32,768-byte
limit on the underlying bundle. An empty result exits successfully. The text shows
the claim, memory expiry and verified evidence IDs and hashes. A displayed locator
comes from the adopted memory and is labeled as recorded. Locators containing
path separators and source URIs are withheld. Keep private paths and credentials
out of claims and locators.

The command is offline and read-only. Advice is reference only and never authorizes
execution or retry.

## If you want a real public-document trial

This is a **separate persistent store path**, not a demo option. It has an explicit
offline command namespace, `agent-sleep-lab public-document`, described below; it has
no automatic chain, model call, network access, schedule or agent connection. Model
use stays the separate library adapter: read [lifecycle](public-document-lifecycle.md)
and [model connection](public-document-model.md) before writing a host integration.

| Order | Explicit host responsibility |
|---|---|
| 1. Prepare | Review exact public bytes, scope, approval and expiry; admit one document into a fresh dedicated library; preserve its no-retry sidecar |
| 2. Light / Deep | Authorize each bounded stage separately; an empty Light selection ends the path; replies create unverified proposals only |
| 3. Independent review | Check exact source/candidate bindings; separately register verifier and snapshot-evaluator receipts |
| 4. Adopt | Use the guarded atomic writer with current parent, policy, scope and expiry checks; never self-certify provider output |
| 5. Different-task use | Retrieve eligible adopted references; separately authorize consumer dispatch and review semantic use |
| 6. Withdraw / expire / delete | Revoke access and purge managed content/derivatives explicitly; keep content-free no-retry tombstones; remote copies/backups are outside this guarantee |

Source, task context and generated text remain untrusted data, never permission.
Do not put held-out answers/rubrics in Light context. Rejected-response retention
is disabled by default; optional quarantine is bounded managed content, not a log
of rejected responses or authority to retry.

### Daily use of one persistent store (offline commands)

Except for `stage`, every action below names its store with `--store`. Only `init` creates a store (and
its parent directories); all others open an **existing** store and refuse a missing
one. Nothing here calls a model, uses the network, or retries anything.

#### Prepare bytes without writing Python

First obtain an **existing host-reviewed approval JSON** matching the exact public
source bytes, HTTPS document URL, scope and finite expiry. `stage` does not create
or infer approval, fetch a URL, initialize a store, issue receipts or adopt anything.
It preserves the source file's UTF-8 bytes (up to 65,536), including newlines.

```sh
agent-sleep-lab public-document stage --source-file source.txt --approval approval.json \
  --event-id source-1 --observed-at OBSERVED_AT --captured-at CAPTURED_AT --preview --format text
agent-sleep-lab public-document stage --source-file source.txt --approval approval.json \
  --event-id source-1 --observed-at OBSERVED_AT --captured-at CAPTURED_AT --artifact-out staged.json
```

Replace timestamps with the actual timezone-aware observation/capture times, not
invented freshness. Preview only validates and prints a content-free summary; it
writes no artifact. Optional `--metrics-out` still explicitly creates a metrics file.
Artifact output requires a NEW path with an existing trusted parent. It refuses
existing files, links and directories, and never overwrites, appends, creates parents
or deletes anything. Successful writes use mode 0600. A failed write can leave a
partial file: do not admit it, replay blindly, or confuse file existence with success.
If the artifact completes but summary output fails, `artifact_written_output_failed`
means the file exists: inspect it, do not repeat the write just to get output.
Caller-managed staging files contain the source and must be included in later cleanup;
store purge does not remove them. Parent-directory stability is a trust assumption.

**A `#` URL is deliberately refused.** Credentials, query strings and fragments can
carry secrets. The existing locator restriction is unchanged, and nothing is silently
stripped or normalized. Use a *separately reviewed* document URL without those parts
in the approval, and keep a public comment/section identifier in separate research
notes. That identifier is not automatically stored or returned by retrieval. Do not
move private tokens into another field. Source syntax is not a secrets scan.

```sh
agent-sleep-lab public-document init --store lib/store.sqlite --roles roles.json
agent-sleep-lab public-document approve --store lib/store.sqlite \
  --identity CONTROL_ID --identity-version 1 --approval approval.json \
  --artifact staged.json --origin-task ORIGIN --expected-generation 0
agent-sleep-lab public-document admit --store lib/store.sqlite --artifact staged.json
agent-sleep-lab public-document propose --store lib/store.sqlite \
  --proposal-id p1 --quotation-file quote.txt
agent-sleep-lab public-document verify --store lib/store.sqlite \
  --identity VERIFIER_ID --identity-version 1 --proposal-id p1 --expires-at WHEN
agent-sleep-lab public-document evaluate --store lib/store.sqlite \
  --identity EVALUATOR_ID --identity-version 1 --proposal-id p1 \
  --expected-parent HEAD --verification-receipt V --expires-at WHEN
agent-sleep-lab public-document adopt --store lib/store.sqlite --operation-id op1 \
  --proposal-id p1 --expected-parent HEAD --expected-generation N \
  --verification-receipt V --evaluation-receipt E
agent-sleep-lab public-document retrieve --store lib/store.sqlite --target-task OTHER \
  --project P --task-family F --max-bytes 2048
```

- **Roles are host-provisioned.** `roles.json` holds four distinct authorities
  (control, verifier, evaluator, semantic reviewer) and one consumer
  configuration (never dispatched here). Each role-bearing action takes exactly one
  `--identity`/`--identity-version` pair. The library compares it with the stored
  configuration; these strings are **not authentication**, a secret or proof of
  different people. Nothing selects a role for you.
- **Approval is a separate step.** `approval.json` must be the host-reviewed
  approval for the exact staged artifact (see [public-source staging](public-source-intake.md));
  `approve` only registers the file you supply and never invents, reviews or infers an
  owner approval. A schema-valid file is not evidence that the owner approved those bytes.
- **Receipts are mechanical.** `verify` and `evaluate` register the library's own
  mechanical receipts for the one role identity you name; they never judge meaning.
  `verify` checks exact quotation fidelity;
  `evaluate` checks the candidate snapshot mechanically; `adopt` needs both plus the
  current parent (`head_sha256` from `status`; a new store starts at the hash of `[]`)
  and generation. Passing them is **not factual truth, semantic usefulness or
  performance**. Provider output never issues them.
- **Retrieval is not use.** It returns whole untrusted references for a *different*
  task in the same approved scope within `--max-bytes`. It calls no consumer and shows
  no demonstrated use. The file passed to `propose` is used byte for byte; avoid an
  added trailing newline.

#### Hand off receipt JSON without copying IDs

Keep verification, evaluation and adoption as separate explicit steps. Save JSON
stdout from `verify` and `evaluate`, then pass those files to the next command:

```sh
set -C  # shell refuses an existing redirection target before running the command
agent-sleep-lab public-document verify --store lib/store.sqlite \
  --identity VERIFIER_ID --identity-version 1 --proposal-id p1 --expires-at WHEN \
  --format json > verification.json
agent-sleep-lab public-document evaluate --store lib/store.sqlite \
  --identity EVALUATOR_ID --identity-version 1 --proposal-id p1 \
  --expected-parent HEAD --verification-receipt-file verification.json --expires-at WHEN \
  --format json > evaluation.json
agent-sleep-lab public-document adopt --store lib/store.sqlite --operation-id op1 \
  --proposal-id p1 --expected-parent HEAD --expected-generation N \
  --verification-receipt-file verification.json --evaluation-receipt-file evaluation.json
```

Inspect each exit code/result before the next command. A failed command may leave
an empty output file; file presence is not a receipt. Files must contain the exact
bounded JSON result shape (not `--format text`). The original `--verification-receipt`
and `--evaluation-receipt` ID options remain available, but cannot be combined with
the corresponding file option. A file only supplies an untrusted receipt ID: the
store still checks issuance, proposal, parent, generation and expiry. No role,
receipt, adoption or consumer execution is created merely by reading a file.

#### Readable output and safe next steps

Every daily action accepts `--format text` for labeled state, counts, receipts or
retrieved references plus a suggested next step. The default and explicit
`--format json` keep the existing machine-readable result. Text is rendered from
the same completed action, with no extra dispatch or store access. Dynamic values
are JSON-escaped, including terminal control characters. Labels are English.

```sh
agent-sleep-lab public-document status --store lib/store.sqlite --format text
agent-sleep-lab public-document cleanup-preview --store lib/store.sqlite --format text
```

`Stored state` is persisted lifecycle state, `Access eligibility` is the time
window, and `Adopted head present` distinguishes adoption from admission. Inspect
`Approval window`, `Scope` and `Managed records` before choosing a later action.
For retrieval, add `--format text` to the explicit different-task command above;
it includes untrusted quotations and sources. Nothing is automatically adopted,
retrieved or deleted. Keep the explicit store path yourself: it is not echoed or
remembered by the tool. Never rerun a write merely to change its output format.

#### Status, preview and cleanup

`status` and `cleanup-preview` open the store read-only inside ONE read transaction, so
one output is a single consistent snapshot even if another client withdraws meanwhile.
They change nothing (not even by expiry) and print no document text, URI, reference or
role name. They keep three things
apart: the stored state (`empty`, `approved`, `purge_pending`, `deleted`), the effective
`access` (`approval_not_yet_valid`, `approval_expired`, `approved_not_admitted`,
`admitted_in_window`, `suppressed_purge_pending`, `suppressed_deleted`) and the cleanup
state. At the exact expiry instant access is `approval_expired` while the stored state
may still read `approved`. `integrity` is always `not_assessed`: the preview is
metadata-only, does not check the admitted bytes or derivatives, and so cannot predict
every action `cleanup` may take, and `admitted_in_window` does not promise a later
retrieval. After exclusion the cause is `unknown`: the store
does not record why. `deleted` means this library's managed purge finished, not file or
forensic erasure.

For store operations, only `status` and `cleanup-preview` are guaranteed side-effect
free (without opt-in metrics). Separately, `stage --preview` without metrics creates
no artifact or store. `cleanup` is the
explicit expiry/integrity sweep and also finishes a pending purge. It checks whether the
approval is currently valid and the managed bytes are intact; valid, intact in-window
data stays, but data that fails those checks is excluded and purged. `withdraw` is the
explicit way to remove still-valid content and requires `--purge` or `--exclude-only`.
Other mutating actions that read managed content (such as `verify`, `evaluate`, `adopt`
and `retrieve`) run the same guard and, when it fails, also exclude and purge before they
refuse. `withdraw` first confirms its own exclusion against `--expected-generation`, and
only then (with `--purge`) attempts the separate purge. If another client withdrew first,
the stale compare-and-set is a refusal (exit 2); the command never reports an exclusion it
did not itself confirm. Operation records, content-free no-retry tombstones
and any external export or backup are kept and are outside this guarantee.

**Exit codes.** `0`: completed or nothing due. `1`: attempted but incomplete.
`purge_pending_incomplete` means exclusion is committed and the physical purge did not
finish (inspect `status` first, then choose `cleanup` on the same store); `failed_state_unchanged` means an error
before any exclusion; `purge_attempted_state_unconfirmed` means the final state could
not be read back. `2`: refused or failed. In particular, staging may leave a partial artifact or a
completed artifact with failed summary delivery; inspect its diagnostic before retrying.
For store actions, after any nonzero code read the persisted state with `status`
before repeating anything. Status cannot inspect staging artifacts.
After a purge exception, withdrawal now reads a fresh metadata snapshot: it reports
`deleted` only if observed, or `unconfirmed` if readback fails. A late exception
keeps exit 1 even when `managed_purge_completed` is observed; this is not proof
that this call, rather than another client, completed deletion. Do not repeat withdrawal.

#### Optional minimal metrics

Off by default. `--metrics-out FILE` is **new-only**. Before any store action the tool
creates FILE exclusively (no-follow, mode 0600) in an already existing directory and
keeps that same file handle for one bounded write afterwards. Any existing path (the
store, a SQLite sidecar or journal, an export, a hardlink or symlink, a directory) or a
missing parent is refused with exit 2 before the action; nothing is appended, truncated,
unlinked or created. The parent directory is trusted not to be swapped concurrently, and
if another process creates the name first you are refused. The one line has only: action,
outcome, elapsed milliseconds, managed-record or
reference byte counts, `model_calls: 0` and `cost: null` with
`cost_state: unavailable_not_measured`. The reserved file stays (possibly empty) even if
the action or the write fails. A metrics-write failure after the action prints a warning
but never changes the action's result or exit code; **do not repeat the action to obtain
metrics**. Unknown cost is not zero and nothing here
measures savings. The file is never rotated or deleted by the tool; remove it yourself.
Metrics describe local wiring only, not usefulness or performance.

### Cost before any live call

The adapter reserves a call before dispatch and bounds prompt/input/reply bytes
and transport time. **Output bytes are checked after generation**: no pre-generation
max-token or hard monetary cap is implemented here. Use separately established
account controls where required; adding hard caps needs separate implementation,
not a documentation switch.

Usage/cost observations are retained only when the actual selected adapter and
returned envelope supply them. Missing usage/cost is unknown, **not zero**.
Recorded estimates/unverified billing are not invoices; full pipeline costs also
include review, adoption, retrieval, task use and maintenance. Failed, rejected,
timed-out and UNKNOWN calls can still be billable. Never automatically retry an
unknown outcome or reset its reservation.

Real-model work is not “never tested”: see the
[dated 2026-11-12 trial](public-source-trial-2026-11-12.md) and current status's
bounded README-library observation. Neither proves general improvement, PR56 live
acceptance, full-cost savings or a deployed agent loop.
