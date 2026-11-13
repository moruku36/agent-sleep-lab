# Partial live development measurement

[日本語](live-development-measurement.ja.md) | [Status](implementation-status.md)

## What is measured

The selected-model adapter now records, per reserved call:

- `request_bytes`: exact UTF-8 serialized request body bytes.
- `cli_prompt_bytes`: UTF-8 bytes of the instruction, untrusted-data reminder
  and serialized request passed to the CLI.
- `transport_elapsed_ns`: a monotonic interval around the transport invocation,
  including CLI startup, account resolution, provider work and CLI cleanup.
- Existing response byte count/hash and allowlisted accounting observations.

This is **CLI-process elapsed time, not provider-only latency, time-to-first-token
or token usage**. Neither byte measure includes unknown transport serialization,
provider framing, hidden system text or billed reasoning. Byte limits remain
post-generation checks, not token or financial caps. Injected test transports
remain explicitly labelled; timing them is not live evidence.

Timing is retained on transport failure and rejected responses, and carried by
the existing Light/Deep and comparison journals. Unknown outcomes remain unknown;
no retry or recovery behavior changed. Missing usage/cost stays unavailable,
not zero. The implementation uses no credentials directly and changes no host,
model, route, auth or default configuration.

## Development pilot protocol — 2026-11-13

Owner-merged [PR #50](https://github.com/moruku36/agent-sleep-lab/pull/50) is the
baseline, merge `d90e3036c6440e34901a65659fe1096057f110f8`.
The previous blanket accounting precondition is narrowed: usage/billed-cost
acceptance is blocked, but a clearly labelled **partial** response/byte/time
measurement can proceed with already-authorized paid development use.

The private, one-shot protocol uses only new synthetic practice evidence:

1. Freeze the existing [five fictional tasks](../examples/paper-pilot/tasks.json),
   a separate lexical coverage rubric, model and finite limits before inference.
2. Run body-bound Light and Deep once each through the registered MiMo route.
   Deep is explicitly **extractive**: a candidate must quote one selected source
   verbatim. This is selection/extraction, not evidence of abstractive
   consolidation quality.
3. A separate deterministic verifier checks exact source equality, provenance
   integrity, pending candidate state and current bindings before registering
   receipts. The normal candidate evaluator and atomic adoption writer are used.
   This is the same operator with separate local verification mechanisms,
   **not an external independent reviewer or non-synthetic acceptance**.
4. Freeze the independent-raw comparison: identical complete raw evidence in
   A and B; only B adds accepted memory. Same byte/reply caps, alternating
   AB/BA order, one call per task/arm, all ten slots in the denominator.
5. Screen replies with the frozen lexical component checks; retain replies for
   direct review. This is not an exact-match fake-provider score, a semantic
   quality metric, an independent holdout or a statistical improvement claim.

Maximum new calls: 12 (2 sleep + 10 task), no retries/fallback, no connection
probe. Task request cap 16,384 bytes, reply cap 1,024 bytes; each sleep stage
reply cap 2,048 bytes. No hard per-call token/money cap is supplied by this CLI.
Intent files and production journals prevent automatic replay of a phase or
unknown arm. New synthetic stores are private and separate from prior unknown
operations and the staged real public document; no old operation is replayed.

Token counts, currency and all-phase actual billed cost remain unavailable.
The matching official CLI source omits accounting in both local and Gateway
envelopes. A session-wide cost summary cannot be attributed to a lean local
one-shot call, so it is not used as a substitute. No additional route was tested.

The private bundle has one-day expiry and a manual whole-bundle/derivative
deletion obligation, not an installed cleanup timer. Raw replies, detailed
rubric, private approval identifiers and journals are not published.

## Observations

Actual new MiMo calls: **2**, one body-bound Light and one Deep, both returned
through the registered local route with validated provider/model/no-fallback
envelopes. Light selected both events; Deep returned two exact-source candidates.

| Stage | Request bytes | CLI-prompt bytes | Reply bytes | CLI elapsed seconds |
|---|---:|---:|---:|---:|
| Light | 2,495 | 2,643 | 47 | 12.986 |
| Deep | 2,537 | 3,020 | 471 | 9.766 |
| Sum | 5,032 | 5,663 | 518 | 22.752 |

Both receipts have absent usage/last-call usage and null cost. No billed-cost or
token result is claimed. This was one sample per stage, not a latency benchmark.

The local preparer then failed **before its first receipt registration**:
the private caller supplied a fractional ISO timestamp longer than the receipt
schema permits. The Deep output itself remains valid and unchanged.
The coordinator recorded `trusted_preparation_failed`; it is not reset.
A corrected, separately guarded local preparation command is awaiting native
execution approval. It would reconcile prior effects and pass the saved candidates
through the existing verifier/evaluator/writer, without new model calls. It is
**pending, with no confirmed execution or success**; no schema or permission was weakened.
The tool wait timed out; a fresh official approval query still listed the original
request. No local preparation intent/completion artifact was observed. This is
not permission to resubmit or assume nondispatch; reconcile the original request.
A separate external SQLite read was refused by the host state-directory policy;
no copy or alternate read route was used.

Adoption and ten-task A/B execution remain **not performed**. The task/rubric
selection is fixed, but no executable comparison plan or ten requests have yet
been registered. This is a partial observation, not full live acceptance.
[Content-free summary](measurements/2026-11-13-live-development.json).

Verification: 3 focused behavior cases passed in one invocation (0.005s), then
451 unique full regression cases passed in one invocation (34.812s):
**454 local case executions / two test invocations**. These are offline tests,
not additional live calls. PR CI is a separate record.
