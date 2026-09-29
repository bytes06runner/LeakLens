"""Integrity of the injected benchmark: files match the manifest, no ground-truth hints leak into items, and
every labelled line is exactly the code the operator injected (checked through notebook conversion and renaming).
"""

import csv
import hashlib
import sys
from pathlib import Path

import nbformat
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmark" / "injected"
sys.path.insert(0, str(BENCH))

import generate  # noqa: E402
import template  # noqa: E402

MANIFEST = list(csv.DictReader((BENCH / "manifest.csv").open()))
LABELS = list(csv.DictReader((BENCH / "_groundtruth" / "labels.csv").open()))
SPLIT = {r["base"]: r["split"] for r in csv.DictReader((BENCH / "split.csv").open())}


def item_lines(label):
    path = BENCH / label["file"]
    if path.suffix == ".ipynb":
        return nbformat.read(path, as_version=4).cells[int(label["cell"])].source.splitlines()
    return path.read_text().splitlines()


def test_manifest_hashes_match_files():
    for row in MANIFEST:
        assert hashlib.sha256((BENCH / row["file"]).read_bytes()).hexdigest() == row["sha256"], row["item_id"]


def test_no_ground_truth_hints_in_items():
    for row in MANIFEST:
        text = (BENCH / row["file"]).read_text()
        assert "#!LEAK" not in text and "#<" not in text and "LEAK" not in text, row["item_id"]


def test_split_is_by_base_and_frozen():
    for row in MANIFEST:
        assert row["split"] == SPLIT[row["base"]]
    for lab in LABELS:
        assert lab["split"] == SPLIT[lab["item_id"].split("__")[0]]


def test_split_composition():
    """2 DEV + 2 TEST bases per family (seeded, 2026-09-29), plus grp_imaging added to DEV afterwards (EVAL_CHANGES)."""
    meta = yaml.safe_load((BENCH / "bases.yaml").read_text())
    expected = {"tabular": ["DEV", "DEV", "TEST", "TEST"], "timeseries": ["DEV", "DEV", "TEST", "TEST"],
                "grouped": ["DEV", "DEV", "DEV", "TEST", "TEST"]}
    for fam, want in expected.items():
        assert sorted(SPLIT[b] for b, m in meta.items() if m["family"] == fam) == want
    assert SPLIT["grp_imaging"] == "DEV" and SPLIT["grp_eeg"] == "TEST"


def test_file_path_entity_case_in_both_splits():
    meta = yaml.safe_load((BENCH / "bases.yaml").read_text())
    splits = {SPLIT[b] for b, m in meta.items() if m.get("entity_source") == "file_path"}
    assert splits == {"DEV", "TEST"}


def test_generation_is_deterministic(tmp_path):
    before = (BENCH / "manifest.csv").read_text()
    import subprocess

    subprocess.run([sys.executable, str(BENCH / "generate.py")], cwd=BENCH, check=True, capture_output=True)
    assert (BENCH / "manifest.csv").read_text() == before


def _expected_leak_lines():
    """item_id -> leak index -> injected lines (marker stripped, renamed with the item's style)."""
    out = {}
    for _base, _m, _split, _tpl, item_id, mut in generate.items():
        style = generate.STYLES[generate.stable_int(item_id) % 3]
        per = {}
        for lines in mut.overrides.values():
            for line in lines:
                hit = template.LEAK_MARK.search(line)
                if hit:
                    code = line[: hit.start()]
                    renamed = generate.rename_identifiers(code.strip() + "\n", style).strip()
                    if mut.rename_col:
                        renamed = renamed.replace(f'"{mut.rename_col[0]}"', f'"{mut.rename_col[1]}"')
                    per.setdefault(int(hit.group(1)), []).append(renamed)
        out[item_id] = per
    return out


EXPECTED = _expected_leak_lines()


@pytest.mark.parametrize("label", LABELS, ids=lambda r: f"{r['item_id']}#{r['leak']}")
def test_labelled_lines_are_the_injected_code(label):
    src = item_lines(label)
    got = [src[int(n) - 1].strip() for n in label["lines"].split(";")]
    assert got == EXPECTED[label["item_id"]][int(label["leak"])]


def test_every_leaky_item_has_labels_and_clean_items_none():
    by_item = {}
    for lab in LABELS:
        by_item.setdefault(lab["item_id"], []).append(lab)
    for row in MANIFEST:
        n = len(by_item.get(row["item_id"], []))
        assert n == int(row["n_leaks"]), row["item_id"]
        if row["categories"] in ("clean", "trap"):
            assert n == 0


def test_label_types_are_known():
    from leaklens import LEAKAGE_TYPES

    for lab in LABELS:
        assert lab["type"] in LEAKAGE_TYPES
        for alt in filter(None, lab["alt_types"].split(";")):
            assert alt in LEAKAGE_TYPES
