"""Check relative file links in the implemented gate documentation (no network requests)."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
FILES = ("README.md", "README.ja.md", "docs/gate-1.md", "docs/gate-1.ja.md",
         "schemas/README.md", "reports/gate-1-progress.md",
         "docs/gate-2a.md", "docs/gate-2a.ja.md", "docs/decisions/0004-local-evidence-store.md",
         "docs/roadmap.ja.md", "reports/gate-2a-progress.md",
         "docs/implementation-status.md", "docs/implementation-status.ja.md",
         "docs/gate-2b.md", "docs/gate-2b.ja.md",
         "docs/decisions/0005-runtime-store-extension.md", "reports/gate-2b-progress.md",
         "docs/gate-2b-candidates.md", "docs/gate-2b-candidates.ja.md",
         "reports/gate-2b-candidates-progress.md")


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
