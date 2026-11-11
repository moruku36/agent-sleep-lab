# Offline OSS cost accounting

[Current status](implementation-status.md) | [日本語の状況](implementation-status.ja.md)

The [accounting API](../src/agent_sleep_lab/oss_cost_accounting.py) reads a
[durable execution pair](oss-durable-execution.md) or a
[frozen fixture cohort](oss-fixture-cohort.md). It returns a JSON-compatible
`agent-sleep-oss-cost-accounting/1` report. The caller can retain a separate
canonical JSON observation artifact and replay it against the same report
snapshot. Reads use the existing journal integrity and current-policy checks.

```python
from hashlib import sha256
from agent_sleep_lab.oss_cost_accounting import (
    cohort_report, freeze_observations, pair_report,
)

# Existing synthetic fixture journal and bridge, with a saved plan.
snapshot = pair_report(journal, "synthetic-plan", bridge)
artifact = freeze_observations(snapshot["target"], currency="USD", observations=[{
    "plan_id": "synthetic-plan", "arm": "baseline", "stage": "task_execution",
    "cost": "0.0031", "input_tokens": None, "output_tokens": None,
    "evidence_sha256": sha256(b"synthetic accounting record").hexdigest(),
}])
report = pair_report(journal, "synthetic-plan", bridge, artifact=artifact)
assert report["totals"]["cost"] is None  # One of fourteen cost slots is known.

# Use this reader both to obtain a cohort target and to replay its own artifact.
snapshot = cohort_report(registry, "synthetic-cohort", journal=journal, bridges=bridges)
```

## Identity and trust

- The artifact protocol is `agent-sleep-oss-cost-observations/1`. Its exact
  fields are `protocol`, `observation_trust`, `target`, `currency`, and
  `observations`. `target` carries `kind`, `id`, `frozen_sha256`, and
  `report_sha256`. The frozen hash pins the journal binding or the cohort
  registration document. The report hash pins canonical JSON of the full
  journal report for a pair. For a cohort it hashes an object with
  `cohort_report` (the original aggregate report) and `execution_reports`
  (a map from each plan ID to its journal report hash or null). Member reports
  are taken from the same read snapshot as the cohort aggregate. Different
  replies with equal scores still give different target hashes. Canonical JSON
  uses sorted object keys, compact separators, ASCII escaping and no nonfinite
  numbers. Observations are sorted by plan ID, arm and stage before encoding.
- Replay requires the exact current target and accepts observations only for
  plans whose report passes current context and integrity checks. A changed
  outcome or policy decision can invalidate the target. Obtain a fresh report
  without an artifact to see the new statuses. A caller must review and bind
  any observations again. The source reports themselves stay private. The
  accounting report exposes identity hashes, transport labels, statuses,
  and accounting fields. It omits prompts, replies, rationales and answer labels.
- Every observation is `caller_supplied_unverified`. Its `evidence_sha256` is
  a caller-provided reference to evidence they can retain separately. The API
  neither reads that evidence nor authenticates its origin or allocation.
  `artifact_sha256` identifies the exact supplied bytes for an audit. Retain
  that digest to detect a later replacement. Content hashes identify bytes,
  with no guarantee of origin or uniqueness across copied stores.
- The registered OpenClaw `model.run` output drops usage and cost. Both
  provider fields stay `unavailable` even when caller observations are present.
  The report gives no billing verification, provider receipt or spending limit.

## Values and coverage

The seven required stage slots for **each task and arm** are `capture`,
`consolidation`, `verification`, `retrieval`, `task_execution`, `maintenance`,
and `evaluation`. Callers supply already allocated stage totals and are
responsible for attributing shared costs once across the chosen scope. Light,
REM and Deep costs roll into `consolidation` here. The API performs no
allocation, currency conversion, pricing, or amortization. The pair and cohort
reports may describe the same work and should never be added together.
[Evaluation cost design](evaluation.ja.md).

- One observation per `(plan_id, arm, stage)` with exact keys as shown above.
  `cost`, `input_tokens`, and `output_tokens` can each be null. At least one
  metric must be present. Input/output token counts are integers from 0 through
  `2**63 - 1`. No values are inferred from input/output byte counts or transport
  envelopes. The artifact allows up to 70 observations and 32,768 bytes, uses
  canonical compact JSON, and rejects duplicate keys, extra fields and slots.
- All money in one artifact uses the same explicit uppercase three-letter
  currency code. The code is a caller label checked for format. Use null for
  a usage-only artifact. Costs are nonnegative decimal strings with up to 18
  integer and 12 fractional digits, without signs, exponents or leading zeros.
  Arithmetic uses exact integer units at 12 decimal places. Totals and signed
  differences are rendered as decimal strings without trailing fractional zeros.
- The report retains both arms of every registered task, including unavailable,
  unstarted, stopped and invalid-verdict outcomes. Missing measurements are
  null, and an explicit zero requires an observation. Each metric has its own
  coverage count. Arm and overall totals are null until all slots in that scope
  have that metric. Observations may describe costs already incurred on an
  incomplete run. The reference-minus-baseline cost difference requires a
  complete source report and complete costs for both arms, and describes only
  the declared costs of this snapshot.
