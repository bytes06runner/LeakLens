"""Embed tests/fixtures/taxonomy/*.py into docs/TAXONOMY.md between <!-- example: NAME --> markers.

Usage: uv run python scripts/sync_taxonomy_examples.py [--check]
With --check, exit 1 if the document is out of date instead of rewriting it.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "TAXONOMY.md"
FIXTURES = ROOT / "tests" / "fixtures" / "taxonomy"
BLOCK = re.compile(r"(<!-- example: (?P<name>[\w.]+) -->\n)```python\n.*?```\n(<!-- /example -->)", re.S)


def render(text: str) -> str:
    def sub(m: re.Match) -> str:
        code = (FIXTURES / m["name"]).read_text()
        return f"{m.group(1)}```python\n{code}```\n{m.group(3)}"

    return BLOCK.sub(sub, text)


def main() -> int:
    text = DOC.read_text()
    new = render(text)
    if "--check" in sys.argv:
        return 0 if new == text else 1
    DOC.write_text(new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
