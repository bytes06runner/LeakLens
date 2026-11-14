"""Summarise whether impact estimates compare the same evaluation rows (EVAL_CHANGES.md #11).

    python benchmark/injected/eval_set_report.py RUN_DIR

RUN_DIR is a run made with LEAKLENS_RECORD_EVAL=1 (impact mode). For every finding with a measured impact, the
`eval_set` record compares the evaluation rows of the original and the fixed run. Writes RUN_DIR/EVAL_SET.md and
RUN_DIR/eval_set.csv. Also checks the sign convention: estimate = (leaky - fixed), negated for lower-is-better
metrics, so a positive estimate always means the leak made the reported score look better.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from leaklens.dynamic.confirm import lower_is_better  # noqa: E402


def kind(note: str) -> str:
    n = note.lower()
    for key, name in (("groupkfold", "group-aware split"), ("groupshufflesplit", "group-aware split"),
                      ("chronological", "chronological split"), ("timeseriessplit", "chronological split"),
                      ("duplicated rows removed", "duplicates removed before split"),
                      ("refit", "transformer refitted on training rows"),
                      ("training rows", "transformer refitted on training rows"),
                      ("evaluation rows removed", "evaluation rows removed from fit"), ("feature", "feature removed")):
        if key in n:
            return name
    return note[:40] or "?"


def main() -> None:
    run = Path(sys.argv[1])
    rows = []
    for line in (run / "findings.jsonl").open():
        r = json.loads(line)
        for f in r.get("dynamic", []):
            imp = f.get("impact") or {}
            if imp.get("status") not in ("measured", "unreliable"):
                continue
            es = imp.get("eval_set") or {}
            sign = -1 if lower_is_better(imp["metric"]) else 1
            rows.append({"item_id": r["item_id"], "type": f["type"], "fix": kind(imp.get("note", "")),
                         "note": imp.get("note", "")[:120], "metric": imp["metric"],
                         "lower_is_better": lower_is_better(imp["metric"]), "status": imp["status"],
                         "estimate": round(sign * imp["delta"], 6),
                         # identical positions of identical rows: overlap is complete by definition (fingerprints
                         # differ there only because the fix changed the feature columns)
                         "identical": es.get("identical"),
                         "jaccard": 1.0 if es.get("identical") else es.get("jaccard"),
                         "n_eval_leaky": es.get("n_eval_leaky"), "n_eval_fixed": es.get("n_eval_fixed")})
    with (run / "eval_set.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    by = defaultdict(list)
    for x in rows:
        by[x["fix"]].append(x)
    md = ["# Do impact estimates compare the same evaluation rows?", "",
          f"{len(rows)} findings with a measured impact (seed 0). Identical: same row positions of the same rows, or "
          "the same multiset of row fingerprints, in every recorded fold of every split call. Jaccard: overlap of the "
          "evaluated rows' fingerprints, averaged over folds (1 when identical).", "",
          "| canonical fix | findings | identical eval rows | mean Jaccard | eval rows (leaky -> fixed, total) | "
          "estimate > 0 |", "|---|---|---|---|---|---|"]
    for k, xs in sorted(by.items()):
        jac = [x["jaccard"] for x in xs if x["jaccard"] is not None]
        md.append(f"| {k} | {len(xs)} | {sum(bool(x['identical']) for x in xs)} | "
                  f"{statistics.mean(jac):.3f} | {sum(x['n_eval_leaky'] or 0 for x in xs)} -> "
                  f"{sum(x['n_eval_fixed'] or 0 for x in xs)} | {sum(x['estimate'] > 0 for x in xs)} |"
                  if jac else f"| {k} | {len(xs)} | {sum(bool(x['identical']) for x in xs)} | n/a | n/a | "
                  f"{sum(x['estimate'] > 0 for x in xs)} |")
    lib = [x for x in rows if x["lower_is_better"]]
    md += ["", f"Sign convention: {len(lib)} estimates use a lower-is-better metric "
           f"({sorted({x['metric'] for x in lib})}); their delta is negated, so for every row a positive estimate "
           "means the leaky pipeline reported a better score than the fixed one."]
    (run / "EVAL_SET.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
