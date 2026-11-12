"""Accuracy of LeakLens's impact estimates against the true inflation of the injected benchmark.

    python benchmark/injected/score_impact.py RUN_DIR INFLATION_CSV

RUN_DIR/findings.jsonl comes from `run_leaklens.py --modes static dynamic --impact`; INFLATION_CSV from
`measure_inflation.py` on the same split and seeds. True inflation = metric(leaky file) - metric(its ground-truth
fixed version), signed so that positive means the leak makes the result look better. The estimate is
metric(original run) - metric(re-run with the finding's canonical fix), signed the same way.
EVAL_PROTOCOL.md section 5. Injected inflation is by construction (CLAUDE.md Rule 12): this script measures how
accurate the estimates are, not how severe leakage is.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from leaklens.dynamic.confirm import lower_is_better
from leaklens.evaluation.scoring import Pred, label_from_row, overlaps

HERE = Path(__file__).resolve().parent


def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3 or len(set(a)) < 2 or len(set(b)) < 2:
        return None
    from scipy.stats import spearmanr

    return float(spearmanr(a, b).statistic)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("inflation_csv")
    a = ap.parse_args()
    run = Path(a.run_dir)
    truth: dict[tuple[str, int], dict] = {}
    for r in csv.DictReader(open(a.inflation_csv)):
        if r["inflation"] not in ("", None):
            truth[(r["item_id"], int(r["seed"]))] = {
                "inflation": float(r["inflation"]),
                "metric": r["metric"],
                "leaky": float(r["leaky_value"]),
                "fixed": float(r["fixed_value"]),
            }
    labels = defaultdict(list)
    for r in csv.DictReader((HERE / "_groundtruth" / "labels.csv").open()):
        labels[r["item_id"]].append(label_from_row(r))
    rows, status = [], Counter()
    fidelity = []
    for line in (run / "findings.jsonl").open():
        rec = json.loads(line)
        item, seed = rec["item_id"], rec["seed"]
        t = truth.get((item, seed))
        if t and rec.get("metric"):
            fidelity.append(abs(rec["metric"]["value"] - t["leaky"]))
        for f in rec.get("dynamic", []):
            loc = f["location"]
            pred = Pred(item, f["type"], loc["cell"], loc["line_start"], loc["line_end"], f["confidence"])
            lab = next((x for x in labels[item] if overlaps(pred, x)), None)
            if lab is None or f["dynamic"]["status"] == "refuted":
                continue  # impact accuracy is defined for findings that match a labelled leak
            imp = f["impact"]
            status[(lab.type, imp["status"])] += 1
            if imp["status"] not in ("measured", "unreliable") or t is None:
                continue
            sign = -1 if lower_is_better(imp["metric"]) else 1
            est = sign * imp["delta"]
            rows.append(
                {
                    "item_id": item,
                    "seed": seed,
                    "type": lab.type,
                    "subtype": lab.subtype,
                    "rule_id": f["rule_id"],
                    "metric": imp["metric"],
                    "status": imp["status"],
                    "single_leak": len(labels[item]) == 1,
                    "value_leaky": imp["value_leaky"],
                    "value_fixed": imp["value_fixed"],
                    "estimate": round(est, 6),
                    "true_inflation": t["inflation"],
                    "abs_error": round(abs(est - t["inflation"]), 6),
                    "fix": imp.get("note", ""),
                }
            )
    with (run / "impact_vs_truth.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    md = [
        "# Impact estimates against true inflation (injected benchmark)",
        "",
        "Estimate: the script's own metric in the original run minus the metric when the run is repeated with the "
        "finding's canonical fix. Truth: leaky file minus its ground-truth fixed version, same data seed. Positive "
        "means the leak makes the result look better. Injected inflation is by construction (CLAUDE.md Rule 12): "
        "these numbers measure the accuracy of the estimate, not the severity of leakage.",
        "",
        f"Instrumentation check: in {len(fidelity)} files the instrumented run and the plain run of the leaky file "
        f"printed metrics that differ by at most {max(fidelity):.6f}.",
        "",
        "## What could be estimated",
        "",
        "| type | measured | unreliable | unknown (no automatic fix, or the fixed run failed) |",
        "|---|---|---|---|",
    ]
    types = ["preprocessing", "overlap", "multi_test", "group", "temporal", "target_derived"]
    for t in types:
        md.append(f"| {t} | {status[(t, 'measured')]} | {status[(t, 'unreliable')]} | {status[(t, 'unknown')]} |")
    md += [
        "",
        "## Accuracy, single-leak files, status `measured`",
        "",
        "| type | metric | n | mean true inflation | mean estimate | mean abs. error | median abs. error | "
        "sign agreement | Spearman |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    summary = {"status": {f"{t}|{s}": v for (t, s), v in status.items()}, "groups": []}
    groups = defaultdict(list)
    for r in rows:
        if r["single_leak"] and r["status"] == "measured":
            groups[(r["type"], r["metric"])].append(r)
    for (t, metric), rs in sorted(groups.items(), key=lambda kv: (types.index(kv[0][0]), kv[0][1])):
        est, tru = [r["estimate"] for r in rs], [r["true_inflation"] for r in rs]
        nz = [(e, x) for e, x in zip(est, tru, strict=True) if abs(x) > 1e-9]
        agree = sum(1 for e, x in nz if (e > 0) == (x > 0)) / len(nz) if nz else None
        rho = spearman(est, tru)
        g = {
            "type": t,
            "metric": metric,
            "n": len(rs),
            "mean_true": statistics.mean(tru),
            "mean_estimate": statistics.mean(est),
            "mae": statistics.mean(r["abs_error"] for r in rs),
            "median_ae": statistics.median(r["abs_error"] for r in rs),
            "sign_agreement": agree,
            "spearman": rho,
        }
        summary["groups"].append(g)
        md.append(
            f"| {t} | {metric} | {g['n']} | {g['mean_true']:+.4f} | {g['mean_estimate']:+.4f} | {g['mae']:.4f} | "
            f"{g['median_ae']:.4f} | {'n/a' if agree is None else f'{agree:.0%}'} | "
            f"{'n/a' if rho is None else f'{rho:.2f}'} |"
        )
    single = [r for r in rows if r["single_leak"] and r["status"] == "measured"]
    if single:
        bounded = [r for r in single if not lower_is_better(r["metric"])]
        rho = spearman([r["estimate"] for r in bounded], [r["true_inflation"] for r in bounded])
        summary["overall"] = {
            "n": len(single),
            "n_bounded": len(bounded),
            "mae_bounded": statistics.mean(r["abs_error"] for r in bounded) if bounded else None,
            "spearman_bounded": rho,
        }
        md += [
            "",
            f"Across all {len(bounded)} measured single-leak findings whose metric is bounded (AUC, AP, R2): "
            f"mean absolute error {summary['overall']['mae_bounded']:.4f}, Spearman rank correlation "
            f"{'n/a' if rho is None else f'{rho:.2f}'}. Error metrics (MAE) are listed per row above, not pooled.",
        ]
    multi = [r for r in rows if not r["single_leak"]]
    if multi:
        md += [
            "",
            "## Multi-leak files (truth is the joint effect of all leaks; not scored)",
            "",
            "| file | finding | metric | estimate for this finding | true joint inflation |",
            "|---|---|---|---|---|",
        ]
        md += [
            f"| {r['item_id']} | {r['type']} | {r['metric']} | {r['estimate']:+.4f} | {r['true_inflation']:+.4f} |"
            for r in multi
        ]
    (run / "IMPACT_REPORT.md").write_text("\n".join(md) + "\n")
    (run / "impact_summary.json").write_text(json.dumps(summary, indent=1))
    print("\n".join(md))


if __name__ == "__main__":
    main()
