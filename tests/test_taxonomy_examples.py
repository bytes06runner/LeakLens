"""docs/TAXONOMY.md examples must match the runnable fixtures, and every fixture must be well-formed."""

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

from leaklens import LEAKAGE_TYPES

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = sorted((ROOT / "tests" / "fixtures" / "taxonomy").glob("*.py"))
LEAK_MARK = re.compile(r"#\s*LEAK:\s*(\w+)")


def test_doc_in_sync_with_fixtures():
    rc = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_taxonomy_examples.py"), "--check"]).returncode
    assert rc == 0, "run: uv run python scripts/sync_taxonomy_examples.py"


def test_every_fixture_is_embedded_in_doc():
    doc = (ROOT / "docs" / "TAXONOMY.md").read_text()
    for f in FIXTURES:
        assert f"<!-- example: {f.name} -->" in doc, f.name


def test_every_type_has_positive_and_negative():
    names = {f.stem for f in FIXTURES}
    for t in LEAKAGE_TYPES:
        assert f"{t}_pos" in names and f"{t}_neg" in names, t


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_leak_markers_match_filename(path):
    src = path.read_text()
    ast.parse(src)
    marks = LEAK_MARK.findall(src)
    leak_type = next(t for t in LEAKAGE_TYPES if path.stem.startswith(t))
    if "_neg" in path.stem:
        assert marks == [], "negative examples must not carry LEAK markers"
    else:
        assert marks and set(marks) == {leak_type}


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_runs(path):
    p = subprocess.run([sys.executable, "-W", "ignore", str(path)], capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-1000:]
