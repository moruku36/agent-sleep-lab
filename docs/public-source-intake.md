# Public-document intake staging

**English** | [日本語](public-source-intake.ja.md) | [Runtime guide](runtime-guide.md)

This library prepares **one reviewed public document** as a private,
non-synthetic artifact. It is not an import into the existing evidence/adoption
store and is not an agent connection. It does not fetch, search files, scan for
secrets, call models, create receipts or publish data. Existing synthetic-only
capture/retrieval/adoption gates are unchanged.

## Explicit boundary

The trusted caller creates `PublicDocumentApproval` independently of source
content, after checking public release and secrets. It binds an exact HTTPS URL,
SHA-256 of exact UTF-8 bytes (1..65,536), project/task family, approval reference
and revision, approval time and finite expiry. URL userinfo/query/fragment and
unsupported controls are refused. URL syntax is not proof of public origin, nor
SSRF protection: this module never fetches.

Only purpose `public_document_consolidation` and retention `until_expiry` are
supported. The caller must delete the entire private staging bundle and every
derivative on expiry or withdrawal. This is a recorded obligation, **not an
implemented timer, filesystem deletion or secure-erasure guarantee**. Do not use
this path for private transcripts, credentials, personal memories or evaluation
answers. Do not publish its returned artifact; repository test inputs remain
synthetic.

Approval is local caller configuration, not authentication, consent discovery,
copyright clearance or a claim that text has been automatically sanitized.
Document prose (including apparent instructions) cannot grant permission.
An arbitrary model-generated or source-supplied approval is not trusted.

## Library API

From an explicitly configured private caller, use
[public_source_intake.py](../src/agent_sleep_lab/public_source_intake.py):

1. Supply already acquired bytes, exact source URL, event ID, scope, observed /
   captured timestamps, a separate current approval and timezone-aware current time
   to `prepare_public_document(...)`.
2. Keep the returned canonical bytes outside this public checkout. They preserve
   original text exactly, label it `synthetic:false` and
   `state:staged_not_admitted`, and explicitly grant no model/adoption permission.
3. Use `intake_summary(artifact)` for content-free hashes and byte counts, never
   as an authorization validator. It omits source text, URL and approval reference.
4. Before each later use, call
   `recheck_public_document(artifact, approval=current_approval, now=current_time)`.
   Missing/withdrawn, changed-revision, expired or mismatched approvals refuse use;
   metadata/source tampering and noncanonical artifacts also fail closed.

The API cannot determine whether a caller passed an obsolete approval object.
The integration owner must resolve the actual current approval and enforce
withdrawal/deletion. There is no CLI, implicit state initialization, schema
migration, synthetic relabelling, verifier registration or paid dispatch.

## Verification and remaining acceptance

[Six behavior cases](../tests/test_public_source_intake.py) use only fictional
data. They cover exact-byte preservation, untrusted prose, content-free output,
separate approval / URI / hash / scope binding, withdrawal/expiry/revision/time,
review assertions, text bounds, artifact tampering and unchanged synthetic refusal.
Current execution results live in [implementation status](implementation-status.md).

A separately reviewed non-synthetic store admission, lifecycle/deletion enforcement,
Light/Deep current-approval propagation, independent verification/adoption and an
actual later-task input/use receipt are still required. Successful staging is not
completion of those capabilities. This independent slice neither imports nor
reconstructs the unpublished trial extension.
