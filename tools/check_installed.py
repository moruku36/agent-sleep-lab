"""Exercise an installed wheel from outside the checkout, with no network use.

Usage: PATH/TO/installed/python /checkout/tools/check_installed.py /checkout
"""

import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import agent_sleep_lab


def main():
    checkout = Path(sys.argv[1]).resolve()
    installed = Path(agent_sleep_lab.__file__).resolve()
    assert not installed.is_relative_to(checkout / "src"), installed
    cli = Path(sys.executable).parent / "agent-sleep-lab"
    fixtures = [
        ("events", "events.synthetic.jsonl"),
        ("memory", "memory.candidates.synthetic.json"),
        ("promotion", "promotion-request.synthetic.json"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        def run(*args, expected=0):
            result = subprocess.run([str(cli), *args], cwd=tmp, capture_output=True, text=True)
            assert result.returncode == expected, (args, result.returncode, result.stdout, result.stderr)
            return result.stdout

        assert "sha256:" in run("schemas")
        for kind, name in fixtures:
            result = json.loads(run("validate", kind, str(checkout / "examples" / name), "--format", "json"))
            assert result["valid"] and result["records"] > 0, result
            print(kind, result["records"], "valid")
        bad = Path(tmp) / "bad.jsonl"
        bad.write_text('{"a":1,"a":2}\n', encoding="utf-8")
        assert "json.duplicate_key" in run("validate", "events", str(bad), expected=1)
        run("validate", "events", str(Path(tmp) / "missing.jsonl"), expected=2)
    print("installed wheel", importlib.metadata.version("agent-sleep-lab"), "OK")


if __name__ == "__main__":
    main()
