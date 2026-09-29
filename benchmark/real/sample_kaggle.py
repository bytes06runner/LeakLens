"""Sample real Kaggle notebooks for the benchmark (read-only; nothing is executed).

Usage: uv run python benchmark/real/sample_kaggle.py [--dry-run]

1. For each stratum query, list notebooks via the Kaggle API in several orders (config: sampling.yaml).
2. Pool per stratum, de-duplicate across strata (first stratum wins), shuffle with the configured seed.
3. Walk each stratum's shuffled pool, pull notebooks one by one, keep those passing the source filters, until the
   stratum's target is reached. Rejections are recorded with the reason (nothing is dropped silently).
4. Assign DEV/TEST by author (seeded), then a single random labelling order across all kept notebooks.

Outputs:
  benchmark/raw/real/<ref-as-dir>/<notebook>.ipynb   raw notebooks (gitignored; Kaggle content)
  benchmark/real/pool.csv                            every listed candidate and what happened to it
  benchmark/real/manifest.csv                        kept notebooks: id, stratum, ref, url, author, sha256, split,
                                                     queue position, source stats
The pulled notebooks stay local; the repo stores only URLs and hashes (Integrity Rule 9).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import subprocess
import time
from pathlib import Path

import nbformat
import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = ROOT / "benchmark" / "raw" / "real"
CFG = yaml.safe_load((HERE / "sampling.yaml").read_text())


def kaggle(*args: str) -> str:
    p = subprocess.run(["uv", "run", "kaggle", *args], capture_output=True, text=True, cwd=ROOT, timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f"kaggle {' '.join(args)} failed: {p.stderr.strip()[-300:]}")
    return p.stdout


def list_refs(query: str, order: str, page: int) -> list[dict]:
    out = kaggle("kernels", "list", "--search", query, "--language", "python", "--kernel-type", "notebook",
                 "--sort-by", order, "--page-size", str(CFG["page_size"]), "-p", str(page), "--csv")
    if not out.strip() or out.startswith("No kernels"):
        return []
    return list(csv.DictReader(io.StringIO(out)))


def check_source(nb) -> tuple[bool, str, dict]:
    f = CFG["filters"]
    code = [c.source for c in nb.cells if c.cell_type == "code"]
    src = "\n".join(code)
    stats = {"code_cells": len(code), "code_lines": src.count("\n") + 1,
             "uses_keras_or_torch": any(k in src for k in ("keras", "torch"))}
    if not f["min_code_cells"] <= len(code) <= f["max_code_cells"]:
        return False, f"code_cells={len(code)} outside range", stats
    for key in ("require_any_import", "require_any_call", "require_any_metric"):
        if not any(tok in src for tok in f[key]):
            return False, f"no match for {key}", stats
    return True, "kept", stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="list and pool only; do not pull notebooks")
    a = ap.parse_args()
    rng = np.random.default_rng(CFG["seed"])

    pools, seen = {}, set()
    for stratum, spec in CFG["strata"].items():
        found = []
        for q in spec["queries"]:
            for order in CFG["sort_orders"]:
                for page in range(1, CFG["pages_per_order"] + 1):
                    for row in list_refs(q, order, page):
                        ref = row.get("ref")
                        if ref and ref not in seen:
                            seen.add(ref)
                            found.append({"ref": ref, "author": ref.split("/")[0], "title": row.get("title", ""),
                                          "query": q, "order": order})
                    time.sleep(0.5)
        pools[stratum] = [found[i] for i in rng.permutation(len(found))]
        print(f"{stratum}: {len(found)} unique candidates")

    pool_rows, kept = [], []
    for stratum, cands in pools.items():
        target, n_kept = CFG["strata"][stratum]["target"], 0
        for rank, c in enumerate(cands):
            row = {**c, "stratum": stratum, "pool_rank": rank, "status": "not_reached"}
            if not a.dry_run and n_kept < target:
                dest = RAW / c["ref"].replace("/", "__")
                try:
                    kaggle("kernels", "pull", c["ref"], "-p", str(dest))
                    files = sorted(dest.glob("*.ipynb"))
                    if not files:
                        row["status"] = "rejected: not a notebook file"
                    else:
                        nb = nbformat.read(files[0], as_version=4)
                        ok, reason, stats = check_source(nb)
                        row.update(stats)
                        row["status"] = "kept" if ok else f"rejected: {reason}"
                        if ok:
                            n_kept += 1
                            kept.append({**row, "file": files[0].relative_to(ROOT).as_posix(),
                                         "sha256": hashlib.sha256(files[0].read_bytes()).hexdigest()})
                except Exception as e:  # noqa: BLE001 - recorded, not hidden
                    row["status"] = f"error: {type(e).__name__}: {str(e)[:200]}"
                time.sleep(0.5)
            pool_rows.append(row)
        print(f"{stratum}: kept {n_kept}/{target}")

    fields = ["stratum", "pool_rank", "ref", "author", "title", "query", "order", "status", "code_cells",
              "code_lines", "uses_keras_or_torch"]
    with (HERE / "pool.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(pool_rows)
    if a.dry_run or not kept:
        return

    authors = sorted({k["author"] for k in kept})
    order = rng.permutation(len(authors))
    n_test = int(round(CFG["split"]["test_fraction"] * len(authors)))
    author_split = {authors[i]: ("TEST" if r < n_test else "DEV") for r, i in enumerate(order)}
    queue = rng.permutation(len(kept))
    for pos, i in enumerate(queue, start=1):
        kept[i]["queue"] = pos
    kept.sort(key=lambda k: k["queue"])
    for n, k in enumerate(kept, start=1):
        k["notebook_id"] = f"R{n:03d}"
        k["split"] = author_split[k["author"]]
        k["url"] = f"https://www.kaggle.com/code/{k['ref']}"
        k["licence"] = "unverified"
    fields = ["notebook_id", "queue", "split", "stratum", "ref", "url", "author", "title", "code_cells",
              "code_lines", "uses_keras_or_torch", "sha256", "file", "licence"]
    with (HERE / "manifest.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(kept)
    print(f"manifest: {len(kept)} notebooks, {len(authors)} authors")


if __name__ == "__main__":
    main()
