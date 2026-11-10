# Five-task paper development pilot

[Runtime guide](../../docs/runtime-guide.md) | [日本語](../../docs/runtime-guide.ja.md)

[tasks.json](tasks.json) contains five explicitly FICTIONAL paper-curation prompts.
They use different invented titles from the experience fixture. They were authored
with the consolidation design in mind: **development data, not an independent
holdout**. There are no real papers, authors, experiments or reported findings.

A live-response run would use the existing independent-raw baseline, already
independently accepted memories, fixed MiMo 2.6 Pro, alternating A/B order, one
call per arm/task (ten total), equal request/reply caps and a frozen local rubric.
The evaluator key belongs outside requests and outside this public fixture.
Use the runtime CLI manifest described in the guide; identical A/B requests are
rejected before dispatch. Record all ten outcomes including unknown/invalid;
never rerun an unknown arm. Explicitly authorize the applicable account budget:
post-generation byte checks are NOT max-token or monetary controls.

## Before a real run

1. Prepare eligible synthetic experience and independently accepted consolidation
   in a private v3 store; no fake verification of newly generated claims.
2. Freeze this task file's hash, the exact model, policy/snapshot, evaluator
   protocol/rubric hash, per-arm caps and total cost boundary.
3. Check planned input hashes differ and no evaluator key appears in requests.
4. Run the explicit paid CLI once and keep receipts in private journals.
5. Review actual paired outcomes and costs. Exact-match scoring alone cannot
   establish paper-curation quality or scientific performance improvement.

**No real-response run is recorded here.** The current execution status and
blocker are in [implementation status](../../docs/implementation-status.md).
CI exercises offline transport and contract regressions only. A prepared fixture
is not a measured performance result, agent integration or adoption receipt.
