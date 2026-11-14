"""Impact-estimation accuracy: LeakLens (re-run with a canonical fix) vs LeakHound (its own proxy model), injected
TEST, single-leak files, seed 0 (EVAL_PROTOCOL.md section 5, "Baseline for this task").

    python baselines/data_level/compare_impact.py DATA_LEVEL_RUN LEAKLENS_RUN [--out FILE.md]

True inflation and LeakLens's estimate come from LEAKLENS_RUN/impact_vs_truth.csv (seed 0). LeakHound's estimate
is the `inflation` of its impact finding of the matching kind at the same file's split, from DATA_LEVEL_RUN/
sites.jsonl (fold 0): group -> "*_group_aware", temporal -> "*_chronological", overlap -> "*_unseen_only",
target_derived / preprocessing -> "*_without_leak". LeakHound reports AUC for classification and R2 for
regression; an estimate is compared only when that is the pipeline's own metric (AUC or R2). Other metrics are
counted as "not comparable", never dropped.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

KIND = {"group": "group_aware", "temporal": "chronological", "overlap": "unseen_only",
        "target_derived": "without_leak", "preprocessing": "without_leak"}


def metric_family(m: str) -> str | None:
    return "AUC" if m.endswith("auc") else "R2" if m.endswith("r2") else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dl_run")
    ap.add_argument("ll_run")
    ap.add_argument("--out")
    a = ap.parse_args()
    lh: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for line in (Path(a.dl_run) / "sites.jsonl").open():
        r = json.loads(line)
        for s in r["sites"]:
            for mode, v in s.get("tools", {}).get("leakhound-ml", {}).items():
                lh[r["item_id"]][mode] += v.get("impact", [])
    rows = [r for r in csv.DictReader((Path(a.ll_run) / "impact_vs_truth.csv").open())
            if r["seed"] == "0" and r["single_leak"] == "True"]
    table, per = [], defaultdict(lambda: defaultdict(list))
    for r in rows:
        fam = metric_family(r["metric"])
        true = float(r["true_inflation"])
        ll = float(r["estimate"]) if r["status"] == "measured" and r["estimate"] not in ("", "nan") else None
        res = {"item_id": r["item_id"], "type": r["type"], "metric": r["metric"], "true": true, "leaklens": ll}
        for mode in ("default", "true_column"):
            est = None
            if fam:
                for e in lh[r["item_id"]].get(mode, []):
                    keys = [k for k in e if k != "inflation"]
                    if any(k.startswith(fam + "_") and k.endswith(KIND.get(r["type"], "?")) for k in keys):
                        est = float(e["inflation"])
                        break
            res[f"leakhound_{mode}"] = est
            res[f"comparable_{mode}"] = bool(fam)
        table.append(res)
        for tool in ("leaklens", "leakhound_default", "leakhound_true_column"):
            if fam and res[tool] is not None:
                per[r["type"]][tool].append(abs(res[tool] - true))
    out = ["# Impact estimates vs true inflation, injected TEST, single-leak files, seed 0", "",
           f"Rows: {len(table)} located single-leak findings with a LeakLens impact record (any status). "
           "Comparable = the pipeline reports AUC or R2 (LeakHound's own metrics).", "",
           "| type | findings | comparable | LeakLens: estimates / MAE | LeakHound (no column named): estimates / MAE "
           "| LeakHound (true column named): estimates / MAE |", "|---|---|---|---|---|---|"]
    for t in sorted({x["type"] for x in table}):
        xs = [x for x in table if x["type"] == t]
        comp = [x for x in xs if x["comparable_default"]]

        def cell(tool, comp=comp, t=t):
            n = sum(x[tool] is not None for x in comp)
            return f"{n} / {statistics.mean(per[t][tool]):.3f}" if per[t][tool] else f"{n} / n/a"

        out.append(f"| {t} | {len(xs)} | {len(comp)} | {cell('leaklens')} | {cell('leakhound_default')} | "
                   f"{cell('leakhound_true_column')} |")
    both = [x for x in table if x["comparable_default"] and x["leaklens"] is not None
            and x["leakhound_true_column"] is not None]
    if both:
        out += ["", f"On the {len(both)} findings where both tools give an estimate (LeakHound with the true column "
                f"named): LeakLens MAE {statistics.mean(abs(x['leaklens'] - x['true']) for x in both):.3f}, "
                f"LeakHound MAE {statistics.mean(abs(x['leakhound_true_column'] - x['true']) for x in both):.3f}; "
                f"sign agreement with the truth: LeakLens "
                f"{sum((x['leaklens'] > 0) == (x['true'] > 0) for x in both)}/{len(both)}, LeakHound "
                f"{sum((x['leakhound_true_column'] > 0) == (x['true'] > 0) for x in both)}/{len(both)}."]
    out += ["", "| item | type | metric | true | LeakLens | LeakHound (none) | LeakHound (true column) |",
            "|---|---|---|---|---|---|---|"]
    for x in table:
        f = lambda v: "-" if v is None else f"{v:+.3f}"  # noqa: E731
        out.append(f"| {x['item_id']} | {x['type']} | {x['metric']} | {x['true']:+.3f} | {f(x['leaklens'])} | "
                   f"{f(x['leakhound_default'])} | {f(x['leakhound_true_column'])} |")
    text = "\n".join(out) + "\n"
    print(text)
    if a.out:
        Path(a.out).write_text(text)
        Path(a.out).with_suffix(".json").write_text(json.dumps(table, indent=1))


if __name__ == "__main__":
    main()
