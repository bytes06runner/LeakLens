"""Score a `findings.jsonl` produced by run_leaklens.py (or a baseline runner) against the injected labels.

    python benchmark/injected/score.py RUN_DIR [--tool leaklens] [--strict-entity]

Writes RUN_DIR/metrics.csv (one row per mode, operating point and leakage type), RUN_DIR/summary.json and
RUN_DIR/REPORT.md. The split is read from the findings themselves; nothing here reads benchmark code.
Metrics and matching: EVAL_PROTOCOL.md sections 2 to 4, implemented in leaklens.evaluation.scoring.

--strict-entity (EVAL_CHANGES.md #10) adds one condition for group leakage: a group finding matches a label only
if it names the true entity of the base pipeline (bases.yaml), or a variable the file assigns directly from that
column (`groups = data["subject"]`, found with `ast`). A group finding that names another column cannot match:
it counts as a false positive and its label as a miss. Outputs then go to *_strict files.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from leaklens.evaluation.scoring import TYPES, Label, Pred, label_from_row, prf, summarise

HERE = Path(__file__).resolve().parent


def fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3f}"


def fmt_ci(ci: tuple[float, float] | None) -> str:
    return "n/a" if ci is None else f"{ci[0]:.2f} to {ci[1]:.2f}"


def entity_aliases(item_id: str, entity: str) -> set[str]:
    """The entity column plus every variable assigned directly from it in the item's code."""
    from leaklens.ingest import load

    row = next(r for r in csv.DictReader((HERE / "manifest.csv").open()) if r["item_id"] == item_id)
    tree = ast.parse(load(HERE / row["file"], display=row["file"]).flat)
    names = {entity}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            v = node.value
            while isinstance(v, ast.Attribute) and v.attr in ("values", "to_numpy"):
                v = v.value
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "to_numpy":
                v = v.func.value
            key = None
            if isinstance(v, ast.Subscript) and isinstance(v.slice, ast.Constant):
                key = v.slice.value
            elif isinstance(v, ast.Attribute):
                key = v.attr
            if key == entity:
                names.add(node.targets[0].id)
    return names


def names_entity(message: str, aliases: set[str]) -> bool:
    named = re.findall(r"`([^`]+)`", message)
    return bool(named) and named[0] in aliases


def preds_from(findings: list[dict], item_id: str, drop_refuted: bool, aliases: set[str] | None = None) -> list[Pred]:
    out = []
    for f in findings:
        if f.get("suppressed") is not None:
            continue
        if drop_refuted and f["dynamic"]["status"] == "refuted":
            continue
        loc = f["location"]
        if aliases is not None and f["type"] == "group" and not names_entity(f.get("message", ""), aliases):
            # strict entity rule: wrong entity -> the finding cannot overlap any label (line -1)
            out.append(Pred(item_id, f["type"], loc["cell"], -1, -1, f["confidence"]))
            continue
        out.append(Pred(item_id, f["type"], loc["cell"], loc["line_start"], loc["line_end"], f["confidence"]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--tool", default="leaklens")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--strict-entity", action="store_true")
    a = ap.parse_args()
    run = Path(a.run_dir)
    records = [json.loads(line) for line in (run / "findings.jsonl").open()]
    records = [r for r in records if r["seed"] == min(x["seed"] for x in records)]  # detection is scored on one seed
    split = {r["split"] for r in records}
    assert len(split) == 1, "a run must contain one split"
    split = split.pop()
    items = [r["item_id"] for r in records]
    bases = {r["item_id"]: r["base"] for r in records}
    labels: list[Label] = [
        label_from_row(r)
        for r in csv.DictReader((HERE / "_groundtruth" / "labels.csv").open())
        if r["item_id"] in set(items)
    ]
    leaky_items = {lab.item_id for lab in labels}
    alias = {}
    if a.strict_entity:
        import yaml

        meta = yaml.safe_load((HERE / "bases.yaml").read_text())
        alias = {it: entity_aliases(it, meta[bases[it]]["entity"]) if meta[bases[it]].get("entity") else set()
                 for it in items}
    modes = ["static"] + (["dynamic"] if any("dynamic" in r for r in records) else [])
    rows_out, summary = [], {"tool": a.tool, "split": split, "items": len(items), "labels": len(labels), "modes": {}}
    md = [
        f"# {a.tool} on the injected benchmark, {split} split"
        + (" (strict entity rule, EVAL_CHANGES.md #10)" if a.strict_entity else ""),
        "",
        f"{len(items)} files, {len(labels)} labelled leaks, {len(items) - len(leaky_items)} files without a leak. "
        "Matching and metrics: EVAL_PROTOCOL.md sections 2 to 4. Intervals: 95% percentile bootstrap, "
        f"{a.boot} resamples of files (and of base pipelines, in brackets).",
        "",
    ]
    if split == "DEV":
        md += ["**DEV numbers are optimistic by design: the rules were written looking at these files.**", ""]
    for mode in modes:
        name = "static" if mode == "static" else "static+dynamic"
        summary["modes"][name] = {}
        for op in ("medium", "low"):
            preds = [p for r in records for p in preds_from(r.get(mode, r["static"]), r["item_id"], mode == "dynamic",
                                                            alias.get(r["item_id"]) if a.strict_entity else None)]
            table = summarise(preds, labels, items, bases, op, a.boot)
            summary["modes"][name][op] = table
            op_name = "confidence medium or higher (primary)" if op == "medium" else "all findings, low included"
            md += [
                f"## {name}, {op_name}",
                "",
                "| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |",
                "|---|---|---|---|---|---|---|---|",
            ]
            for row in table:
                rows_out.append(
                    {
                        "tool": a.tool,
                        "split": split,
                        "mode": name,
                        "operating_point": op,
                        **{k: (v if not isinstance(v, tuple) else f"{v[0]:.4f};{v[1]:.4f}") for k, v in row.items()},
                    }
                )
                md.append(
                    f"| {row['type']} | {row['labels']} | {row['tp']} | {row['fp']} | {row['fn']} | "
                    f"{fmt(row['precision'])} ({fmt_ci(row['precision_ci'])}) "
                    f"[{fmt_ci(row.get('precision_ci_bases'))}] | "
                    f"{fmt(row['recall'])} ({fmt_ci(row['recall_ci'])}) [{fmt_ci(row.get('recall_ci_bases'))}] | "
                    f"{fmt(row['f1'])} |"
                )
            md.append("")
            if op == "medium":
                # recall by label category (temporal categories are reported separately, EVAL_PROTOCOL section 4)
                by_cat: dict[str, list[int]] = defaultdict(lambda: [0, 0])
                from leaklens.evaluation.scoring import CONFIDENCE, match_item

                by_item_p, by_item_l = defaultdict(list), defaultdict(list)
                for p in preds:
                    if CONFIDENCE[p.confidence] >= CONFIDENCE[op]:
                        by_item_p[p.item_id].append(p)
                for lab in labels:
                    by_item_l[lab.item_id].append(lab)
                for it in items:
                    pairs, _, missed = match_item(sorted(by_item_p[it], key=lambda p: p.line_start), by_item_l[it])
                    for _, lab in pairs:
                        by_cat[lab.category][0] += 1
                    for lab in missed:
                        by_cat[lab.category][1] += 1
                md += ["Recall by label category:", "", "| category | found | missed | recall |", "|---|---|---|---|"]
                for cat in sorted(by_cat):
                    tp, fn = by_cat[cat]
                    md.append(f"| {cat} | {tp} | {fn} | {fmt(prf(tp, 0, fn)[1])} |")
                summary["modes"][name]["recall_by_category"] = {c: v for c, v in by_cat.items()}
                clean = [it for it in items if it not in leaky_items]
                alarms = [it for it in clean if by_item_p[it]]
                md += [
                    "",
                    f"Files without a leak that received a finding: {len(alarms)} of {len(clean)}"
                    + (f" ({', '.join(alarms)})" if alarms else "")
                    + ".",
                    "",
                ]
                summary["modes"][name]["clean_files"] = {"n": len(clean), "with_finding": len(alarms)}
    # coverage and runtime
    status = Counter(r["status"] for r in records)
    st = [r["static_seconds"] for r in records]
    md += [
        "## Coverage and runtime",
        "",
        f"- Files analysed: {status.get('ok', 0)} of {len(records)}.",
        f"- Static analysis time per file: median {statistics.median(st):.4f} s, mean {statistics.mean(st):.4f} s, "
        f"max {max(st):.4f} s (this machine: see registry).",
    ]
    summary["coverage"] = dict(status)
    summary["static_seconds"] = {"median": statistics.median(st), "mean": statistics.mean(st), "max": max(st)}
    dyn = [r for r in records if "dynamic" in r]
    if dyn:
        run_status = Counter(r.get("run_status") for r in dyn)
        ds = [r["dynamic_seconds"] for r in dyn]
        md.append(
            f"- Instrumented runs: {dict(run_status)}; time per file: median {statistics.median(ds):.2f} s, "
            f"max {max(ds):.2f} s."
        )
        summary["dynamic_runs"] = dict(run_status)
        summary["dynamic_seconds"] = {"median": statistics.median(ds), "max": max(ds)}
        # what the run did to static findings
        change = Counter()
        only_dynamic = Counter()
        for r in dyn:
            static_ids = {f["id"] for f in r["static"]}
            for f in r["dynamic"]:
                if f["id"] in static_ids or f["rule_id"] not in ("LL-OVL-004", "LL-GRP-004", "LL-TMP-003"):
                    change[(f["type"], f["dynamic"]["status"])] += 1
                else:
                    only_dynamic[(f["type"], f["confidence"])] += 1
        md += [
            "",
            "## What the instrumented run did",
            "",
            "| type | static findings confirmed | refuted | not checked | run error | found only by the run |",
            "|---|---|---|---|---|---|",
        ]
        for t in TYPES:
            only = sum(v for (tt, _), v in only_dynamic.items() if tt == t)
            md.append(
                f"| {t} | {change[(t, 'confirmed')]} | {change[(t, 'refuted')]} | {change[(t, 'not_run')]} | "
                f"{change[(t, 'error')]} | {only} |"
            )
        summary["dynamic_effect"] = {f"{t}|{s}": v for (t, s), v in change.items()}
        summary["dynamic_only"] = {f"{t}|{c}": v for (t, c), v in only_dynamic.items()}
    sfx = "_strict" if a.strict_entity else ""
    (run / f"REPORT{sfx}.md").write_text("\n".join(md) + "\n")
    with (run / f"metrics{sfx}.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0]))
        w.writeheader()
        w.writerows(rows_out)
    (run / f"summary{sfx}.json").write_text(json.dumps(summary, indent=1, default=str))
    print("\n".join(md))


if __name__ == "__main__":
    main()
