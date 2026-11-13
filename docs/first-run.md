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

## If you want a real public-document trial

This is a **separate library/store path**, not a demo option or a new automatic CLI.
Read [lifecycle](public-document-lifecycle.md) and
[model connection](public-document-model.md) before writing a host integration.

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
