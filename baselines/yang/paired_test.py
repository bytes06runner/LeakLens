"""Paired comparison of the Yang et al. analyser and LeakLens (static) on the same files: exact McNemar test.

    python baselines/yang/paired_test.py YANG_RESULTS_JSON LEAKLENS_RUN_DIR

Uses exactly the per-file-and-type rule of score_file_level.py (EVAL_CHANGES.md #6). Units are (file, labelled
leak type) pairs restricted to the three types the Yang analyser claims. For each unit both tools are either right
or not; the test uses only the discordant units (one tool right, the other not). Two-sided exact binomial
p-value. No new data and no new run: it re-reads the two committed result files.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
YANG_TYPES = {"Pre-processing leakage": "preprocessing", "Overlap leakage": "overlap",
              "No independence test data": "multi_test"}
SHARED = ("preprocessing", "overlap", "multi_test")


def exact_mcnemar(b: int, c: int) -> float:
    n, k = b + c, min(b, c)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


def main() -> None:
    yang = json.loads(Path(sys.argv[1]).read_text())
    run = Path(sys.argv[2])
    items = sorted(yang["items"])
    truth: dict[str, dict[str, set[str]]] = defaultdict(dict)
    for r in csv.DictReader((ROOT / "benchmark/injected/_groundtruth/labels.csv").open()):
        if r["item_id"] in yang["items"]:
            acc = {r["type"], *[a for a in r["alt_types"].split(";") if a and a != "nan"]}
            truth[r["item_id"]].setdefault(r["type"], set()).update(acc)
    ll: dict[str, set[str]] = defaultdict(set)
    for line in (run / "findings.jsonl").open():
        rec = json.loads(line)
        if rec["seed"] == 0 and rec["item_id"] in yang["items"]:
            ll[rec["item_id"]] = {f["type"] for f in rec["static"] if f["confidence"] != "low"}

    def yang_types(item: str) -> set[str]:
        v = yang["items"][item]
        s = (v.get("as_script") or {}).get("summary") or v.get("summary") or {}
        return {YANG_TYPES[k] for k, x in s.items() if k in YANG_TYPES and x["detected"] > 0}

    both = only_ll = only_yang = neither = 0
    per_type = defaultdict(lambda: [0, 0, 0, 0])
    for it in items:
        for primary, accepted in truth[it].items():
            if primary not in SHARED:
                continue
            a, b = bool(ll[it] & accepted), bool(yang_types(it) & accepted)
            k = 0 if a and b else 1 if a else 2 if b else 3
            per_type[primary][k] += 1
            both, only_ll, only_yang, neither = (both + (k == 0), only_ll + (k == 1), only_yang + (k == 2),
                                                 neither + (k == 3))
    n = both + only_ll + only_yang + neither
    p = exact_mcnemar(only_ll, only_yang)
    print(f"units (file, type) on shared types: {n}")
    print(f"LeakLens right: {both + only_ll}   Yang right: {both + only_yang}")
    print(f"both {both}, only LeakLens {only_ll}, only Yang {only_yang}, neither {neither}")
    print(f"exact McNemar two-sided p = {p:.2e}")
    for t, (bb, l1, y1, nn) in per_type.items():
        print(f"  {t}: both {bb}, only LeakLens {l1}, only Yang {y1}, neither {nn}, "
              f"p = {exact_mcnemar(l1, y1):.3f}")


if __name__ == "__main__":
    main()
