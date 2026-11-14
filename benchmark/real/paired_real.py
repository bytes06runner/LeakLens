"""Paired comparison of LeakLens (static, medium+) and the Yang analyser on the real TEST notebooks.

    uv run python benchmark/real/paired_real.py LABELS LEAKLENS_RUN YANG_JSON OUT_JSON

One decision per (notebook, type) for the three types both tools report; a decision is correct when the tool reports
the type exactly when the notebook has a label of that type. Exact two-sided McNemar (binomial) test on the
discordant pairs. A notebook the Yang analyser could not analyse counts as no finding (Rule 5).
"""

from __future__ import annotations

import csv
import json
import sys
from math import comb
from pathlib import Path

YANG = {
    "Pre-processing leakage": "preprocessing",
    "Overlap leakage": "overlap",
    "No independence test data": "multi_test",
}
TYPES = ("preprocessing", "overlap", "multi_test")


def main() -> None:
    labels, run, yang_p, out = (Path(a) for a in sys.argv[1:5])
    truth: dict[str, set[str]] = {}
    for r in csv.DictReader(labels.open()):
        truth.setdefault(r["notebook_id"], set()).add(r["leak_type"])
    ll = {}
    for line in (run / "findings.jsonl").open():
        rec = json.loads(line)
        ll[rec["notebook_id"]] = {f["type"] for f in rec["findings"] if f["confidence"] != "low"}
    y = json.loads(yang_p.read_text())["items"]
    yp = {
        k: {YANG[t] for t, x in (v.get("summary") or {}).items() if t in YANG and x["detected"] > 0}
        for k, v in y.items()
    }
    a_only = b_only = both = neither = 0
    for nb in sorted(ll):
        for t in TYPES:
            has = t in truth.get(nb, set())
            a, b = (t in ll[nb]) == has, (t in yp.get(nb, set())) == has
            both += a and b
            neither += (not a) and (not b)
            a_only += a and not b
            b_only += b and not a
    n = a_only + b_only
    k = min(a_only, b_only)
    p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n) if n else 1.0
    res = {"decisions": both + neither + a_only + b_only, "both_right": both, "both_wrong": neither,
           "leaklens_only_right": a_only, "yang_only_right": b_only, "mcnemar_exact_p": p,
           "leaklens_right": both + a_only, "yang_right": both + b_only}
    out.write_text(json.dumps(res, indent=1))
    print(res)


if __name__ == "__main__":
    main()
