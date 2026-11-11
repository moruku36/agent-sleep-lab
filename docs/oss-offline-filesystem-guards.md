# Reviewed offline-worker filesystem audit contract

This contract applies to `oss_offline_worker.install_guards`, reused by the
[prompt-capture worker](../src/agent_sleep_lab/oss_prompt_capture_worker.py)
before source loading. It guards the existing reviewed-source route. It is not
filesystem isolation for arbitrary hostile Python. Current implementation,
execution and verification status belongs only in
[implementation status](implementation-status.md) ([日本語](implementation-status.ja.md)).

## Covered audit events

| Event | Checked authority |
| --- | --- |
| `open` | Write-mode path; flags include `O_WRONLY`, `O_RDWR`, `O_CREAT`, `O_TRUNC`, `O_APPEND` and the complete optional `O_TMPFILE` flag |
| `os.remove`, `os.rmdir`, `os.mkdir` | Path and audited `dir_fd`; `unlink` shares `os.remove` |
| `os.rename` | Both paths and both audited directory descriptors; `replace` shares this event |
| `os.link` | Both source and destination, both audited directory descriptors |
| `os.symlink` | Both target and destination, audited directory descriptor |
| `os.chmod`, `os.chown`, `os.utime` | Path and audited directory descriptor, including fd/l-prefixed variants that emit the same events |
| `os.truncate`, `os.chflags`, `os.setxattr`, `os.removexattr` | Path, including descriptor variants that emit the same events |
| `sqlite3.connect` | Only the absolute `<temporary cwd>/ledger.sqlite3` destination |

Known event shapes are checked; malformed arguments and authority failures raise
`PermissionError`. A mutation's audited directory descriptor must be the default
`-1` sentinel. Explicit descriptor paths are refused, even for in-temp files;
the hook never reconstructs authority from `/proc`, `/dev/fd` or descriptor state.

## Path rules

Mutation paths must be absolute, canonically spelled strict descendants of the
resolved temporary cwd. Strings, filesystem bytes and standard path-like inputs
use filesystem decoding. Empty/NUL paths, relative paths, `.`/`..` components,
repeated/trailing separators and leading `//` are refused when visible to the
hook. File APIs may reject invalid inputs before emitting an event. A path-like
object is checked in the spelling its filesystem conversion supplies.
The already-existing root also permits a `mkdir` attempt for the reviewed
ledger constructor's parent setup; removing or renaming the root is refused.

Every existing component below the root is inspected with `lstat`. Symlinks,
including dangling links and loops, are refused without following them. Other
inspection errors fail closed; a not-yet-created suffix is allowed. This rule
also refuses unlinking/renaming a symlink or mutating it with no-follow options.
An absolute in-temp symlink target and destination may be created, but subsequent
mutation through that link is refused. Relative symlink targets are refused.

All relative write-opens are refused because the `open` audit event omits
`os.open`'s `dir_fd`. Absolute opens can be checked because the OS ignores
`dir_fd` for an absolute path. Ordinary absolute scratch create/write/metadata/
rename/link/remove operations remain permitted, along with the designated
SQLite ledger and its native transaction files. SQLite URI and memory database
spellings are refused. Read opens are not confined to the temporary directory.

## Limits and verification scope

This is a path check at selected Python audit events, not an OS sandbox. It does
not control hostile Python, native extensions, arbitrary syscalls, unaudited APIs,
inherited descriptors or direct descriptor writes, custom openers, existing
hardlink aliases, mount aliases, or concurrent filesystem changes between check
and use. It assumes the parent's dedicated temporary cwd and reviewed code.
The SQLite connect check is not a SQL authorizer: native SQLite file operations,
including additional databases, are outside these Python path checks.

The stdlib-only worker, target commit/source pins, input/output payloads and
source/task/reference hash contracts stay unchanged. Existing network/process/
environment/cwd denials and resource bounds are retained. Host configuration,
authentication, sandbox controls, configured hooks, approvals and caller budgets
are unchanged.

[Disposable-child regression sources](../tests/test_oss_offline_guards.py) use
only temporary synthetic sentinels. They cover both endpoints, outside-file
content/metadata preservation, bytes/path-like paths, relative/ambiguous paths,
symlink components, descriptor/dir-fd refusal, writable flags, allowed scratch/
ledger work and shared guard installation in prompt capture. Ownership/flags/
xattr and malformed-event probes are side-effect-free event checks. The capture
reuse case uses a stand-in payload/loader and is not target integration evidence.
