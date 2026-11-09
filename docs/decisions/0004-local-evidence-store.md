# ADR 0004: Local append-only evidence store on standard-library SQLite

- Date: 2026-11-10
- Status: Gate 2A locally accepted (110 combined tests and isolated wheel checks on macOS arm64 / Python 3.13.18); no crash/power-loss acceptance.
- Related: [contracts and acceptance (ja)](../contracts-and-acceptance.ja.md) §2, [Gate 2A usage](../gate-2a.md)

## Context

Gate 2A needs immutable captured evidence with provenance, replay idempotency, conflict rejection, and an integrity recheck, without adding dependencies, a CLI, an active pointer, or memory adoption.

## Decision

Use the Python standard-library `sqlite3` module and one database file.

- **Transactions:** the connection runs in autocommit mode and every capture uses an explicit `BEGIN IMMEDIATE` … `COMMIT`/`ROLLBACK`. The write lock is taken first, so two connections capturing the same event serialize; the second sees the first's committed row and gets `replayed` or a conflict.
- **Identity:** SHA-256 over the exact raw bytes (event, original source, canonical provenance encoding). `canonical_json` is this project's internal sidecar encoding (sorted keys, compact separators, ASCII); it is **not** RFC 8785 JCS and must not be described as such.
- **Immutability:** triggers abort `UPDATE`/`DELETE` on all tables; a partial unique index allows one independent root per (scope, source hash). These stop ordinary SQL and API misuse, not an actor who can edit the file.
- **Durability settings:** rollback-journal mode (not WAL, to keep read-only opens simple), `synchronous=FULL`, and `fullfsync=ON` (effective on macOS). Rationale: the intended guarantee is "a commit that returned is not lost on process crash and, on a filesystem that honors fsync, on power loss."
- **Header guard:** `application_id` and `user_version` are checked; unknown databases or versions are refused. Nothing migrates or fabricates missing provenance.
- **Read-only access:** a separate class opens SQLite with `mode=ro` and `query_only`; it has no capture API.

## Trust limits

- The capture boundary (adapter id/version, allowed origins, authorization revisions) is a **local boundary simulation**, not authentication. Nothing proves the caller is that adapter; origin labels such as `user_correction` are assertions by the configured boundary.
- A hash is an identity of bytes, not proof of truth, consent, or origin. Someone with write access to the file can alter rows and hashes together; `verify` detects inconsistent edits only. No signatures or MACs exist yet.
- Captured ancestors are rechecked (hashes, source bytes present, unexpiry, current authorization revision, same evaluation partition) in the capture transaction. This is point-in-time and local; it does not consult any exclusion or revocation ledger.

## Not covered

No crash-injection or power-loss testing; no network or shared filesystem support (SQLite locking on network filesystems is unreliable); no exclusion/revocation revision, promotion, active pointer, retrieval, verifier or evaluation integration; no migration. The combined suite passes 110 tests; connection-reopen and injected SQL rollback checks are not process-crash or power-loss acceptance.

---

## 要約（日本語）

標準ライブラリSQLiteの単一ファイルに、`BEGIN IMMEDIATE`の明示transactionで原子的に取り込む。同一性は生バイトのSHA-256。`canonical_json`は内部の出典sidecar符号化でRFC 8785 JCSではない。updated/deleteはtriggerで拒否するが、ファイルを書ける者の改ざんは防げない（整合性再検査は不整合な編集のみ検出）。journalはrollback方式、`synchronous=FULL`、`fullfsync=ON`。取込境界は認証ではなくローカルの境界模擬。祖先は同一transaction内で整合性・期限・現行許可版・評価partitionを再確認するが、除外／撤回台帳は参照しない。全110テストと別環境wheel検査は合格したが、接続の再open・SQL失敗注入をクラッシュ／電源断の受入とはしない。移行・採用処理は未実装。
