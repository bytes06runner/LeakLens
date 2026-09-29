"""Render notebooks as numbered text files for human labellers (no Jupyter needed).

Usage: uv run python benchmark/real/render_for_labelling.py OUT_DIR [--practice]

Every line is prefixed `[cell N | line M]`, with N counting ALL cells from 1 (as a person scrolling the notebook
would) and M counting lines inside that cell from 1. Markdown cells are shown as text so labellers see the
author's explanations. `cell_map.csv` maps displayed cell numbers to 0-based code-cell indices (SPEC.md), so
labels can be converted for scoring without the labellers having to think about it.

--practice renders the practice files in benchmark/real/practice/*.py (one cell per `# %%` block).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import nbformat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def cells_of(path: Path) -> list[tuple[str, str]]:
    if path.suffix == ".ipynb":
        nb = nbformat.read(path, as_version=4)
        return [(c.cell_type, c.source) for c in nb.cells]
    blocks, cur = [], []
    for line in path.read_text().splitlines():
        if line.strip() == "# %%":
            if cur:
                blocks.append(("code", "\n".join(cur)))
            cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append(("code", "\n".join(cur)))
    return blocks


def render(nid: str, path: Path, out: Path, cell_map: list[dict]) -> None:
    lines, code_idx = [f"# Notebook {nid}", ""], 0
    for n, (kind, src) in enumerate(cells_of(path), start=1):
        if kind == "code":
            lines.append(f"---------------- cell {n} (code) ----------------")
            for m, text in enumerate(src.splitlines() or [""], start=1):
                lines.append(f"[cell {n} | line {m}]  {text}")
            cell_map.append({"notebook_id": nid, "display_cell": n, "code_cell_index": code_idx})
            code_idx += 1
        elif kind == "markdown":
            lines.append(f"---------------- cell {n} (text) ----------------")
            lines.extend(f"    {t}" for t in src.splitlines())
        lines.append("")
    (out / f"{nid}.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--practice", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cell_map: list[dict] = []
    if a.practice:
        for p in sorted((HERE / "practice").glob("P*.py")):
            render(p.stem, p, out, cell_map)
    else:
        for row in csv.DictReader((HERE / "manifest.csv").open()):
            render(row["notebook_id"], ROOT / row["file"], out, cell_map)
    with (out / "cell_map.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["notebook_id", "display_cell", "code_cell_index"])
        w.writeheader()
        w.writerows(cell_map)
    print(f"rendered {len({c['notebook_id'] for c in cell_map})} notebooks to {out}")


if __name__ == "__main__":
    main()
