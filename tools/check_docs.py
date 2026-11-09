"""Check relative file links in the Gate 1 documentation (no network requests)."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
FILES = ("README.md", "README.ja.md", "docs/gate-1.md", "docs/gate-1.ja.md",
         "schemas/README.md", "reports/gate-1-progress.md")


if __name__ == "__main__":
    checked = 0
    for name in FILES:
        path = ROOT / name
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            file_part = target.split("#", 1)[0]
            if file_part:
                assert (path.parent / file_part).exists(), (name, target)
                checked += 1
    print(f"{checked} relative documentation file links OK (anchors not checked)")
