"""Assign base pipelines to DEV or TEST (Integrity Rule 4). Run once; the result is committed and frozen.

Split unit = base pipeline, so every TEST item comes from code never seen while writing or tuning rules.
Per family (tabular, timeseries, grouped): 2 bases DEV, 2 bases TEST, chosen by a fixed seed.
"""

import csv
from pathlib import Path

import numpy as np
import yaml

SEED = 20260929
HERE = Path(__file__).resolve().parent
meta = yaml.safe_load((HERE / "bases.yaml").read_text())
out = HERE / "split.csv"
if out.exists():
    raise SystemExit(f"{out} exists: the split is frozen. Delete it only with the project owner's approval.")

rng = np.random.default_rng(SEED)
rows = []
for family in ("tabular", "timeseries", "grouped"):
    bases = sorted(b for b, m in meta.items() if m["family"] == family)
    order = rng.permutation(len(bases))
    for rank, i in enumerate(order):
        rows.append({"base": bases[i], "family": family, "split": "DEV" if rank < 2 else "TEST"})
with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["base", "family", "split"])
    w.writeheader()
    w.writerows(sorted(rows, key=lambda r: (r["family"], r["split"], r["base"])))
print(out.read_text())
