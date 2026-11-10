"""Check relative file links in ALL repository Markdown, offline (not anchors)."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED = {".git", ".venv", "venv", "build", "dist", "__pycache__", "node_modules"}


def main():
    checked = files = 0
    errors = []
    for path in sorted(ROOT.rglob("*.md")):
        if EXCLUDED.intersection(path.relative_to(ROOT).parts):
            continue
        files += 1
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = target.strip()
            if target.startswith("<"):
                target = target.split(">", 1)[0][1:]
            else:
                target = target.split(' "', 1)[0]
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = path.parent / unquote(parsed.path)
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}: {target}")
            checked += 1
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"{checked} relative file links in {files} Markdown files OK (anchors not checked)")


if __name__ == "__main__":
    main()
