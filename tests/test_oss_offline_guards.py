"""Selected real guard boundary acceptance in disposable child processes.

Coordinator verification while the requested coding worker is quota-blocked.
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
worker.install_guards(directory)
"""


class GuardBoundaryTests(unittest.TestCase):
    def probe(self, body, *, setup=None):
        with tempfile.TemporaryDirectory(prefix="asl-guard-acceptance-") as root:
            root = Path(root).resolve()
            cwd = root / "worker"
            cwd.mkdir()
            outside = root / "outside.txt"
            outside.write_bytes(b"synthetic sentinel")
            if setup is not None:
                setup(cwd, outside)
            argv = [sys.executable, "-I", "-B", "-c", PRELUDE + body,
                    str(Path(worker.__file__).resolve()), str(outside)]
            code, output = parent.bounded_run(
                argv, cwd=str(cwd),
                env={"LC_ALL": "C", "TZ": "UTC", "HOME": str(cwd), "TMPDIR": str(cwd)},
                timeout=8, max_output=4096)
            self.assertEqual(code, 0, "isolated guard probe failed")
            self.assertEqual(outside.read_bytes(), b"synthetic sentinel")
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
scratch = directory / "synthetic.txt"
scratch.write_text("synthetic scratch")
assert scratch.read_text() == "synthetic scratch"
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
