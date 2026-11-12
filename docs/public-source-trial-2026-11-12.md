# Public-information memory trial — 2026-11-12

**English** | [日本語](public-source-trial-2026-11-12.ja.md) | [Home](../README.md)

This is a dated execution report. [Implementation status](implementation-status.md)
remains the authority for current capabilities and merge state.

## Scope and version

One non-confidential task was completed: review this project's public runtime
guide, generate a grounded operating note, then use the adopted note while
reviewing a different installation plan.

The trial used main commit
[`9b6ecb59e266f157789af87d0b3ce5203fb32072`](https://github.com/moruku36/agent-sleep-lab/commit/9b6ecb59e266f157789af87d0b3ce5203fb32072)
**plus a separate local extension**. That extension was not committed, pushed or
merged when this trial finished. This documentation change does not include it.
Checking out the linked base alone does not reproduce the public-data path.

The only source was the
[pinned runtime guide](https://github.com/moruku36/agent-sleep-lab/blob/9b6ecb59e266f157789af87d0b3ce5203fb32072/docs/runtime-guide.md).
No private conversation, personal information, credentials or evaluation answers
were supplied as source material. Runtime data and answer keys remain outside
the public repository; this report publishes aggregate results and hashes only.

## What actually ran

| Stage | Observed result |
|---|---|
| Record | One reviewed public document captured as a real, non-synthetic event in an isolated SQLite store |
| Generate | An actual model response produced one pending candidate; claim length 2,080 UTF-8 bytes |
| Review | A separate source-grounding reviewer checked the exact candidate and source hashes |
| Adopt | Separate verification/evaluation receipts were registered; the existing atomic writer adopted one memory |
| Retrieve | One eligible memory returned in a 4,010-byte reference bundle; retrieval made no database writes |
| Use on a different task | Two actual responses completed: raw source alone, and the same raw source plus the adopted bundle |

Source, policy and adopted snapshot were rechecked after the downstream responses.
Generation and task execution used explicit model handoffs, not scripted fixture
answers. The harness did not automatically dispatch these model calls.
A separate review is not an authenticated provider attestation or an independent
scientific holdout.

The local extension kept the default synthetic-only rejection intact. It added
an explicit one-source approval boundary with an immutable URL, reviewed source
hash, exact scope, authorization revision and expiry, plus distinct public-data
database/receipt/bundle identities. It reused the existing atomic adoption
machinery instead of treating a JSON file write as adoption.

## Downstream comparison

The next task reviewed an installation plan containing unsafe assumptions about
real logs, automatic adoption, cost caps and retrying an unknown outcome.
The task and eight-item checklist were fixed before generating the memory.
Fresh sessions received the same complete raw-source prefix, the same selected
model configuration, tool permissions and 3,000-byte answer limit. Only the
memory condition received the adopted reference bundle.

| Measure | Raw source only | Raw source + memory |
|---|---:|---:|
| Predeclared checklist items satisfied | 7 / 8 | 8 / 8 |
| Task/reference request file | 14,482 bytes | 18,554 bytes |
| Answer | 2,990 bytes | 3,000 bytes |
| Completed responses / planned responses | 1 / 1 | 1 / 1 |

A condition-blinded assessor found one difference: the memory-added answer
explicitly included the registered OpenClaw connection requirement. The raw-only
answer omitted that condition. This is **one observed example**, not evidence of
reliable or causal performance improvement.

The memory condition added **4,072 bytes, about 28.1%**. Token usage, resolved model
revision and actual cost were unavailable. No cost or efficiency improvement was
measured, and byte limits are not token or monetary caps.

### Comparison limitations

- One pair only, without repetitions, counterbalanced order or an independent
  holdout. Both responses are retained in the denominator; neither was missing.
- The frozen files bind the task/reference content, not the complete opaque
  provider/system request. Session wrappers differed in assigned filenames and
  one duplicated tool-restriction sentence; actual tool and output limits matched.
- More context was supplied to the memory condition. Equal context size or equal
  monetary cost was not established.
- The blinded assessor flagged the memory-added answer's reference to an attached
  verification label as unverifiable from its source-only assessment packet.
  The actual request was checked and did contain the exact adopted bundle and
  eligibility label. Scores were unchanged. That label is not authentication.
- The next-task source describes the pinned base's synthetic runtime. Its
  restrictions must not be confused with capabilities of the unmerged extension.

## Local verification evidence

These results belong to the **local extension**, not to the documentation-only
change or to the linked base without modifications.

- Python 3.12.14 / SQLite 3.53.1, dedicated virtual environment.
- Direct dependencies: jsonschema 4.23.0, referencing 0.37.0 and
  rfc3339-validator 0.1.4. Transitive dependencies were not locked.
- Final full regression: **436 unique cases passed**, one invocation, 14.117s.
  Eleven cases exercised the new boundary. Including focused tests and repair:
  448 case executions over four invocations.
- One initial test-fixture error was corrected. A separate static review found
  authorization checks outside transactions; the checks were moved inside the
  capture/receipt transactions and generation reads were made snapshot-consistent.
  Three regression cases covered those failures.
- Documentation check: 517 relative file links across 87 Markdown files passed;
  anchors and external URLs were not checked by that tool.
- Installed code/schema bytes matched the final source. The 16-file local patch
  applied cleanly to its pinned base and reproduced the final changed files.
- Python 3.11/3.13 CI for that local extension was not run. This report does not
  substitute base-branch CI results for extension verification.

| Retained artifact | SHA-256 |
|---|---|
| Source document | `95951d590917a6d1c149b0e691eebe4d8abd18d1eef8353b701915191215fce2` |
| Generated candidate | `579c1331d81dc196710fb7cc62bf210fc3ad7595815341c60a64796576ece18f` |
| Adopted snapshot | `6032889a544c2861bf70d8be8ea3647172bf9e57bb61739722e3c1d937cf202b` |
| Retrieved bundle | `198d641f7e393a12d0ad6f823359d71b2b559419c58484d8076a441c1a8b7650` |
| Local extension patch | `3469212449244a095dc5a08591d6383e705b2ec4893b3a075435ce61b9d1dfca` |

The exact runtime artifacts were retained outside the repository. Hashes identify
those artifacts; publishing hashes alone is not a public reproduction package
or proof of authenticated execution.

## Permissions, retention and remaining work

The trial was explicitly authorized for public-only work and repository code
execution in a dedicated environment. It added no credentials, permissions,
external API service or paid MiMo execution. Existing denied or unknown provider
operations were not retried.

The one-source approval expires at **2026-11-13T10:58:36Z**. Expiry makes the memory
ineligible for retrieval; it does not physically erase source blobs, SQLite
pages, journals or copies. Physical erasure was not performed.

There was no remaining blocker for this completed one-off trial. It did **not**
complete automatic Light/Deep, permanent working-memory integration, the OSS
Contributor deployment, or the fixed five-task paid comparison.

Before continuing beyond this report:

1. Review and separately authorize publication of the local implementation.
   Its code is not supplied by this documentation-only change.
2. Define the target agent's real capture/retrieval/injection and independent
   review connection, with data scope and retention/deletion responsibilities.
3. For the existing MiMo route, verify registered OpenClaw access and applicable
   account authorization/budget. This trial neither provisioned them nor resolved
   previously recorded host-binding blockers.
4. Use repeated, comparable tasks and measured total costs before claiming a
   general quality or cost benefit.
