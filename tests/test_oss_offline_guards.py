"""Selected real guard boundary acceptance in disposable child processes.

No pinned target code, external network, inference or production data is used.
These checks do not establish a sandbox for hostile Python or complete syscall
coverage. Parent process never installs an irreversible audit hook itself.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest

import support
from agent_sleep_lab import oss_offline_parent as parent
from agent_sleep_lab import oss_offline_worker as worker


PRELUDE = """
import importlib.util
import json
import os
from pathlib import Path
import resource
import socket
import sqlite3
import subprocess
import sys

spec = importlib.util.spec_from_file_location("guard_under_test", sys.argv[1])
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
directory = Path.cwd().resolve()
outside = Path(sys.argv[2])
def denied(operation):
    try:
        operation()
    except PermissionError:
        return
    raise AssertionError("guard did not deny operation")
"""


class GuardBoundaryTests(unittest.TestCase):
    def probe(self, body, *, setup=None, before_guard="", install_guard=True):
        with tempfile.TemporaryDirectory(prefix="asl-guard-acceptance-") as root:
            root = Path(root).resolve()
            cwd = root / "worker"
            cwd.mkdir()
            outside = root / "outside.txt"
            outside.write_bytes(b"synthetic sentinel")
            outside_empty = root / "outside-empty"
            outside_empty.mkdir()
            if setup is not None:
                setup(cwd, outside)
            before = outside.stat()
            script = PRELUDE + before_guard + "\n"
            if install_guard:
                script += "worker.install_guards(directory)\n"
            argv = [sys.executable, "-I", "-B", "-c", script + body,
                    str(Path(worker.__file__).resolve()), str(outside)]
            code, output = parent.bounded_run(
                argv, cwd=str(cwd),
                env={"LC_ALL": "C", "TZ": "UTC", "HOME": str(cwd), "TMPDIR": str(cwd)},
                timeout=8, max_output=4096)
            self.assertEqual(outside.read_bytes(), b"synthetic sentinel")
            after = outside.stat()
            self.assertEqual(
                (after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns,
                 after.st_ctime_ns, after.st_nlink),
                (before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns,
                 before.st_ctime_ns, before.st_nlink))
            self.assertTrue(outside_empty.is_dir())
            self.assertEqual(list(outside_empty.iterdir()), [])
            self.assertEqual({path.name for path in root.iterdir()},
                             {"worker", "outside.txt", "outside-empty"})
            self.assertEqual(code, 0, "isolated guard probe failed")
            self.assertEqual(output, b"guard-probe-ok\n")

    def test_socket_creation_is_denied_without_contacting_an_endpoint(self):
        self.probe("""
denied(lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM))
print("guard-probe-ok")
""")

    def test_process_environment_and_cwd_mutation_are_denied(self):
        self.probe("""
denied(lambda: subprocess.run([sys.executable, "-I", "-c", "pass"], check=True))
denied(lambda: os.system("exit 0"))
denied(lambda: os.putenv("ASL_GUARD_PROBE", "synthetic"))
denied(lambda: os.unsetenv("ASL_GUARD_PROBE"))
denied(lambda: os.chdir(directory))
# Event probes have no corresponding operating-system side effect.
for event in ("os.exec", "os.spawn", "os.fork", "os.forkpty", "os.posix_spawn"):
    denied(lambda event=event: sys.audit(event, "synthetic-event-probe"))
print("guard-probe-ok")
""")

    def test_external_text_bytes_raw_and_symlink_write_opens_are_denied(self):
        def setup(cwd, outside):
            (cwd / "external-link").symlink_to(outside)
        self.probe("""
denied(lambda: outside.open("w"))
denied(lambda: outside.open("a"))
denied(lambda: open(os.fsencode(outside), "wb"))
denied(lambda: os.open(outside, os.O_WRONLY | os.O_TRUNC))
denied(lambda: (directory / "external-link").open("w"))
print("guard-probe-ok")
""", setup=setup)

    def test_temp_file_and_designated_ledger_remain_operational(self):
        self.probe("""
# Reviewed Ledger calls mkdir(parents=True, exist_ok=True) on this parent.
try:
    os.mkdir(directory)
except FileExistsError:
    pass
else:
    raise AssertionError("temporary root should already exist")
directory.mkdir(parents=True, exist_ok=True)
folder = directory / "scratch"
os.mkdir(os.fsencode(folder))
scratch = folder / "synthetic.txt"
scratch.write_text("synthetic scratch")
assert scratch.read_text() == "synthetic scratch"
os.chmod(scratch, 0o600)
os.utime(scratch, ns=(1000000000, 2000000000))
os.truncate(os.fsencode(scratch), 9)
assert scratch.read_bytes() == b"synthetic"
hardlink = folder / "hardlink"
os.link(scratch, os.fsencode(hardlink))
assert hardlink.read_bytes() == b"synthetic"
alias = folder / "alias"
os.symlink(scratch, alias)
assert alias.read_bytes() == b"synthetic"
# Readable in-temp links are allowed, but mutation through a link is refused.
denied(lambda: alias.write_text("changed"))
renamed = folder / "renamed.txt"
os.rename(scratch, renamed)
replacement = folder / "replacement.txt"
replacement.write_text("replacement")
os.replace(renamed, replacement)
assert replacement.read_bytes() == b"synthetic"
os.unlink(hardlink)
os.remove(replacement)
# Link removal is deliberately refused too; the unguarded parent cleans up.
empty = directory / "empty"
empty.mkdir()
empty.rmdir()
with sqlite3.connect(directory / "ledger.sqlite3") as db:
    db.execute("CREATE TABLE synthetic (value TEXT)")
    db.execute("INSERT INTO synthetic VALUES (?)", ("synthetic row",))
    assert db.execute("SELECT value FROM synthetic").fetchone() == ("synthetic row",)
print("guard-probe-ok")
""")

    def test_other_sqlite_destinations_are_denied(self):
        self.probe("""
denied(lambda: sqlite3.connect(directory / "other.sqlite3"))
denied(lambda: sqlite3.connect(outside))
denied(lambda: sqlite3.connect(":memory:"))
assert not (directory / "other.sqlite3").exists()
print("guard-probe-ok")
""")

    def test_sqlite_ledger_symlinks_and_ambiguous_spellings_are_refused(self):
        def setup(cwd, outside):
            (cwd / "ledger.sqlite3").symlink_to(outside)
        self.probe("""
ledger = directory / "ledger.sqlite3"
denied(lambda: sqlite3.connect(ledger))
denied(lambda: sqlite3.connect(os.fsencode(ledger)))
denied(lambda: sqlite3.connect(str(directory) + "/./ledger.sqlite3"))
denied(lambda: sqlite3.connect("file:" + str(ledger), uri=True))
assert ledger.is_symlink()
print("guard-probe-ok")
""", setup=setup)

    def test_outside_single_path_mutations_are_denied_before_side_effects(self):
        self.probe("""
denied(lambda: os.remove(outside))
denied(lambda: os.unlink(os.fsencode(outside)))
denied(lambda: os.rmdir(outside.parent / "outside-empty"))
denied(lambda: os.mkdir(outside.parent / "outside-new"))
denied(lambda: os.chmod(outside, 0o777))
denied(lambda: os.truncate(outside, 0))
denied(lambda: os.utime(outside, ns=(1000000000, 2000000000)))
print("guard-probe-ok")
""")

    def test_rename_and_replace_check_source_and_destination(self):
        self.probe("""
source = directory / "source"
source.write_bytes(b"scratch source")
destination = directory / "destination"
for operation in (os.rename, os.replace):
    denied(lambda: operation(os.fsencode(outside), destination))
    denied(lambda: operation(source, os.fsencode(outside)))
    assert source.read_bytes() == b"scratch source"
    assert not destination.exists()
print("guard-probe-ok")
""")

    def test_hardlinks_check_source_and_destination(self):
        self.probe("""
source = directory / "source"
source.write_bytes(b"scratch source")
destination = directory / "destination"
denied(lambda: os.link(os.fsencode(outside), destination))
denied(lambda: os.link(source, outside.parent / "outside-new"))
assert not destination.exists()
assert source.stat().st_nlink == 1
print("guard-probe-ok")
""")

    def test_symlinks_check_target_and_destination_and_refuse_relative_targets(self):
        self.probe("""
source = directory / "source"
source.write_bytes(b"scratch source")
destination = directory / "destination"
denied(lambda: os.symlink(outside, destination))
denied(lambda: os.symlink(source, outside.parent / "outside-new"))
denied(lambda: os.symlink(os.fsencode(outside.parent / "outside-new"), destination))
for target in ("source", "../outside.txt"):
    denied(lambda target=target: os.symlink(target, destination))
assert not destination.is_symlink()
print("guard-probe-ok")
""")

    def test_symlink_components_and_endpoints_are_refused_for_mutations(self):
        def setup(cwd, outside):
            (cwd / "source").write_bytes(b"scratch source")
            (cwd / "internal-link").symlink_to(cwd / "source")
            (cwd / "external-link").symlink_to(outside)
            (cwd / "directory-link").symlink_to(outside.parent, target_is_directory=True)
            (cwd / "dangling-link").symlink_to(outside.parent / "outside-new")
            (cwd / "loop").symlink_to(cwd / "loop")
        self.probe("""
source = directory / "source"
for name in ("internal-link", "external-link", "dangling-link", "loop"):
    link = directory / name
    denied(lambda: link.open("w"))
    denied(lambda: os.remove(link))
    denied(lambda: os.chmod(link, 0o777))
    denied(lambda: os.truncate(link, 0))
    denied(lambda: os.rename(link, directory / "destination"))
    denied(lambda: os.replace(source, link))
    denied(lambda: os.link(link, directory / "destination"))
    denied(lambda: os.link(source, link))
    denied(lambda: os.symlink(link, directory / "destination"))
    denied(lambda: os.symlink(source, link))
denied(lambda: os.mkdir(directory / "directory-link" / "outside-new"))
denied(lambda: os.rmdir(directory / "directory-link" / "outside-empty"))
assert source.read_bytes() == b"scratch source"
print("guard-probe-ok")
""", setup=setup)

    def test_relative_and_ambiguous_mutation_paths_are_refused(self):
        self.probe("""
source = directory / "source"
source.write_bytes(b"scratch source")
for path in ("source", b"source", "../outside.txt", "", str(directory) + "/./source",
             str(directory) + "//source", str(directory) + "/scratch/../source",
             "/" + str(source), str(source) + "/"):
    denied(lambda path=path: open(path, "w"))
    denied(lambda path=path: os.remove(path))
denied(lambda: os.mkdir("relative-directory"))
denied(lambda: os.rename(source, "relative-destination"))
denied(lambda: os.link("source", directory / "hardlink"))
denied(lambda: os.symlink(source, "relative-link"))
denied(lambda: sqlite3.connect("ledger.sqlite3"))
# Invalid OS path spelling can fail before auditing; probe the hook without a syscall.
for path in (str(directory) + "/nul\\0name", None, 7):
    denied(lambda path=path: sys.audit("open", path, "w", os.O_WRONLY))
# The policy root itself must not be renamed or removed.
denied(lambda: os.rename(directory, directory / "moved-root"))
denied(lambda: os.rmdir(directory))
assert source.read_bytes() == b"scratch source"
print("guard-probe-ok")
""")

    def test_write_open_flags_cover_readonly_truncate_append_and_tmpfile(self):
        self.probe("""
for flags in (os.O_RDONLY | os.O_TRUNC, os.O_RDONLY | os.O_APPEND,
              os.O_RDONLY | os.O_CREAT, os.O_RDWR, os.O_WRONLY):
    denied(lambda flags=flags: os.open(os.fsencode(outside), flags))
if hasattr(os, "O_TMPFILE"):
    denied(lambda: os.open(outside.parent, os.O_TMPFILE | os.O_RDWR))
    denied(lambda: sys.audit("open", str(outside.parent), None, os.O_TMPFILE))
if hasattr(os, "O_DIRECTORY"):
    fd = os.open(outside.parent, os.O_RDONLY | os.O_DIRECTORY)
    os.close(fd)
source = directory / "source"
fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.close(fd)
fd = os.open(source, os.O_WRONLY | os.O_APPEND)
os.write(fd, b"scratch")
os.close(fd)
assert source.read_bytes() == b"scratch"
# Read access is not confined by this guard.
assert outside.read_bytes() == b"synthetic sentinel"
print("guard-probe-ok")
""")

    def test_descriptor_and_dir_fd_mutations_are_refused_without_inference(self):
        self.probe("""
denied(lambda: open(external_fd, "w", closefd=False))
denied(lambda: os.fdopen(local_fd, "w", closefd=False))
for fd in (external_fd, local_fd):
    denied(lambda: os.fchmod(fd, 0o777))
    denied(lambda: os.ftruncate(fd, 0))
    denied(lambda: os.truncate(fd, 0))
    if os.chmod in os.supports_fd:
        denied(lambda: os.chmod(fd, 0o777))
    if os.utime in os.supports_fd:
        denied(lambda: os.utime(fd, ns=(1000000000, 2000000000)))
for fd in (external_dir_fd, local_dir_fd):
    denied(lambda: os.open("outside.txt", os.O_WRONLY, dir_fd=fd))
    for operation, args in (
        (os.remove, ("outside.txt",)), (os.rmdir, ("outside-empty",)),
        (os.mkdir, ("outside-new",)), (os.chmod, ("outside.txt", 0o777)),
        (os.utime, ("outside.txt",))):
        if operation in os.supports_dir_fd:
            denied(lambda operation=operation, args=args: operation(*args, dir_fd=fd))
    if os.rename in os.supports_dir_fd:
        denied(lambda: os.rename("outside.txt", directory / "renamed", src_dir_fd=fd))
        denied(lambda: os.rename(directory / "source", "outside-new", dst_dir_fd=fd))
        denied(lambda: os.replace("outside.txt", directory / "renamed", src_dir_fd=fd))
        denied(lambda: os.replace(directory / "source", "outside-new", dst_dir_fd=fd))
    if os.link in os.supports_dir_fd:
        denied(lambda: os.link("outside.txt", directory / "hardlink", src_dir_fd=fd))
        denied(lambda: os.link(directory / "source", "outside-new", dst_dir_fd=fd))
    if os.symlink in os.supports_dir_fd:
        denied(lambda: os.symlink(directory / "source", "outside-new", dir_fd=fd))
# Even a known in-temp descriptor is refused when exposed in a mutation event.
if os.mkdir in os.supports_dir_fd:
    denied(lambda: os.mkdir(directory / "absolute-new", dir_fd=local_dir_fd))
for fd in (external_fd, local_fd, external_dir_fd, local_dir_fd):
    os.close(fd)
assert (directory / "source").read_bytes() == b"scratch source"
print("guard-probe-ok")
""", before_guard="""
external_fd = os.open(outside, os.O_RDWR)
external_dir_fd = os.open(outside.parent, os.O_RDONLY)
local_dir_fd = os.open(directory, os.O_RDONLY)
(directory / "source").write_bytes(b"scratch source")
local_fd = os.open(directory / "source", os.O_RDWR)
""")

    def test_related_metadata_events_and_malformed_authority_fail_closed(self):
        self.probe("""
# Portable event probes: no ownership, flags or xattr syscall is attempted.
for event, args in (
    ("os.chown", (outside, os.getuid(), os.getgid(), -1)),
    ("os.chflags", (outside, 0)),
    ("os.setxattr", (outside, b"user.synthetic", b"synthetic", 0)),
    ("os.removexattr", (outside, b"user.synthetic")),
    ("os.chown", (7, os.getuid(), os.getgid(), -1)),
    ("os.setxattr", (7, b"user.synthetic", b"synthetic", 0)),
    ("os.removexattr", (7, b"user.synthetic")),
    ("os.remove", (directory / "source", None)),
    ("os.rename", (directory / "source", directory / "destination", -1)),
    ("open", (outside, None, None))):
    denied(lambda event=event, args=args: sys.audit(event, *args))
print("guard-probe-ok")
""")

    def test_prompt_capture_run_installs_shared_guards_before_loading_sources(self):
        self.probe("""
# Stand-in payload/loader only: this verifies installation order and shared
# behavior, not pinned target integration or prompt correctness.
sys.path.insert(0, str(Path(sys.argv[1]).parent.parent))
from agent_sleep_lab import oss_prompt_capture_worker as capture
capture.validate_payload = lambda payload: ({}, b"task", b"reference", None)
capture.reference_notes = lambda reference: "synthetic notes"
def load_sources(sources):
    denied(lambda: os.remove(outside))
    denied(lambda: os.rename(directory / "source", outside))
    denied(lambda: os.open("outside.txt", os.O_TRUNC, dir_fd=external_dir_fd))
    (directory / "scratch").write_text("synthetic scratch")
    return {}
capture.base.load_sources = load_sources
capture.capture = lambda *args, **kwargs: {"synthetic_probe": True}
assert capture.run({}) == {"synthetic_probe": True}
os.close(external_dir_fd)
print("guard-probe-ok")
""", before_guard="""
external_dir_fd = os.open(outside.parent, os.O_RDONLY)
(directory / "source").write_text("synthetic source")
""", install_guard=False)

    def test_child_resource_limits_are_finite_and_do_not_leak_to_parent(self):
        import resource
        before = {name: resource.getrlimit(getattr(resource, name)) for name in (
            "RLIMIT_CPU", "RLIMIT_FSIZE", "RLIMIT_NOFILE", "RLIMIT_CORE")}
        self.probe("""
for name, expected in (
    ("RLIMIT_CPU", (5, 5)), ("RLIMIT_FSIZE", (1048576, 1048576)),
    ("RLIMIT_NOFILE", (64, 64)), ("RLIMIT_CORE", (0, 0))):
    assert resource.getrlimit(getattr(resource, name)) == expected
print("guard-probe-ok")
""")
        self.assertEqual(
            {name: resource.getrlimit(getattr(resource, name)) for name in before}, before)
