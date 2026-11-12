"""Measure the true inflation of every injected item: metric(leaky) vs metric(fixed) on the same data.

Usage: python measure_inflation.py OUT_CSV --seeds 0 1 2 3 4 [--workers 4] [--items PATTERN] [--split DEV]

Runs our own generated code (trusted) through leaklens.sandbox with trusted_code=True. For each item and data
seed, the dataset is generated, the item's data transform applied (column rename: both versions; duplicated
records: leaky version only), then both versions run and the printed metric is parsed.
inflation = leaky - fixed if higher is better, else fixed - leaky; positive means the leak makes the result
look better than it is. Clean and trap items run too: their inflation must be exactly 0.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import datagen  # noqa: E402

from leaklens.sandbox import run_untrusted  # noqa: E402

METRIC = re.compile(r"^(\w+): (-?[\d.]+|nan)$", re.M)


def prepare_data(base: str, seed: int, transform: dict, leaky: bool, dest: Path) -> dict[str, Path]:
    written = datagen.write(base, seed, dest)
    if "data.csv" in written and transform:
        path = dest / "data.csv"
        df = pd.read_csv(path)
        if "rename" in transform:
            df = df.rename(columns=transform["rename"])
        if leaky and transform.get("duplicate_frac"):
            df = pd.concat([df, df.sample(frac=transform["duplicate_frac"], random_state=seed)], ignore_index=True)
        df.to_csv(path, index=False)
    tops = {rel.split("/")[0] for rel in written}
    return {top: dest / top for top in tops}


def run_one(args) -> dict:
    row, seed = args
    import json

    transform = json.loads(row["data_transform"])
    out = {"item_id": row["item_id"], "split": row["split"], "seed": seed, "metric": row["metric"]}
    for version, src in (("leaky", HERE / "_groundtruth" / "leaky_py" / f"{row['item_id']}.py"),
                         ("fixed", HERE / "_groundtruth" / "fixed" / f"{row['item_id']}.py")):
        with tempfile.TemporaryDirectory() as tmp:
            inputs = prepare_data(row["base"], seed, transform, version == "leaky", Path(tmp))
            inputs["pipeline.py"] = src
            t = time.time()
            res = run_untrusted([sys.executable, "-W", "ignore", "pipeline.py"], inputs=inputs, trusted_code=True,
                                timeout_seconds=600)
            m = METRIC.findall(res.stdout)
            value = float(m[-1][1]) if m and m[-1][0] == row["metric"] else None
            out[f"{version}_value"] = value
            out[f"{version}_rc"] = res.returncode
            out[f"{version}_seconds"] = round(time.time() - t, 2)
            if res.returncode != 0 or value is None:
                out[f"{version}_error"] = (res.stderr or res.stdout)[-400:].replace("\n", " | ")
    lv, fv = out.get("leaky_value"), out.get("fixed_value")
    if lv is not None and fv is not None:
        sign = 1 if row["higher_is_better"] == "True" else -1
        out["inflation"] = round(sign * (lv - fv), 6)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--items", default="")
    ap.add_argument("--split", choices=["DEV", "TEST"], help="only items of this split (default: all)")
    a = ap.parse_args()
    rows = [r for r in csv.DictReader((HERE / "manifest.csv").open())
            if a.items in r["item_id"] and a.split in (None, r["split"])]
    jobs = [(r, s) for r in rows for s in a.seeds]
    fields = ["item_id", "split", "seed", "metric", "leaky_value", "fixed_value", "inflation", "leaky_rc",
              "fixed_rc", "leaky_seconds", "fixed_seconds", "leaky_error", "fixed_error"]
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as pool, open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, res in enumerate(pool.map(run_one, jobs), start=1):
            w.writerow(res)
            f.flush()
            if i % 50 == 0:
                print(f"{i}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    print(f"done {len(jobs)} runs in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
