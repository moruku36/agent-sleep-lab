# ADR 0005: Explicit runtime-store version 2 extension

- Date: 2026-11-10 JST
- Status: first slice locally accepted; combined152tests and fresh installed-wheel checks passed. Full adoption and remote publication status are separate.
- Related: [Gate 2B first slice](../gate-2b.md), [Gate 2A storage](0004-local-evidence-store.md)

## Decision

Keep the Gate 2A evidence tables and bytes and add `receipts` and `policy_revisions` in the same SQLite file, marked with `user_version=2` and the existing application ID. `RuntimeStore` creates a fresh v2 file or opens v2; it refuses a v1 file rather than upgrading it implicitly. An explicit `upgrade_store_v1_to_v2` adds empty extension tables and advances the version within one transaction. It does not rewrite evidence or invent missing provenance. Gate 2A v1 reader/writer classes refuse v2; callers must deliberately select the new API. Back up a real supported store before an eventual explicit upgrade; no production migration has been run here.

Receipt registration, current policy and evidence rechecks use the same store connection. This makes them available to a future single `BEGIN IMMEDIATE` adoption transaction; it is not an implemented adoption writer. Separate connections or stores are not atomic with that transaction. Artifacts are bounded SQLite blobs, so no external mutable receipt path or automatic URL fetch is needed.

Receipt IDs are immutable within their kind. Re-registration of the same claim ignores the newly stamped issue time and returns the original bytes/hash; it does not refresh receipt validity. Changed claim content conflicts. Resolution checks exact ID/hash and stored identity fields; it does not by itself grant adoption permission.

The current policy is separate from candidate snapshots and append-only. Expected-current CAS assigns consecutive revisions; construction/reopen does not reset it. Exclusions can only grow in this first slice. Removing an exclusion is not supported. Missing/corrupt policy fails closed. Policy revision is a combined authorization/exclusion revision here, not yet a mapping to the separate revisions in the future promotion request.

## Limits and review status

All boundaries are local simulations, not authentication. A caller who can construct boundary objects or write the database can forge assertions. Hashes and triggers detect or discourage inconsistent edits, not coordinated forgery. No signatures, remote source leases, active pointers, operation replay, candidate building or adoption receipts exist in this slice.

Upgrade/open compare complete table/index/trigger definitions with known DDL generated in a schema-only in-memory reference. Tests passed for missing/replaced triggers, column drift, preserved evidence and rollback of a partial extension. This is exact supported-format checking, not authentication or import-graph attestation. Operational policy/evidence checks still use only the store connection. The combined152tests and installed-wheel upgrade/receipt/policy/reopen checks passed. Process-crash, power-loss, network-filesystem durability and cross-process adoption acceptance remain pending.

## 日本語要約

出典の既存bytesを変えず、同一SQLiteファイルへ受領と方針の追記テーブルを加える明示的なv2形式です。v1からの変更は専用APIだけで行い、暗黙移行はしません。v1用APIはv2を拒否します。現在の方針はsnapshotと独立し、CASで版を進め、除外の取り消しは扱いません。採用writerは未実装です。定義全体の照合・不正形式の拒否・移行途中のrollbackを補強し、全152テストと別環境wheel受入が合格しました。採用writer・プロセスクラッシュ・電源断の受入は未完了です。
