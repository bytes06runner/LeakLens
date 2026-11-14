"""Real-notebook study (Review 2): agreement between labellers, and scoring of LeakLens against settled labels.

    # 1. agreement between the returned sheets (Cohen's kappa per type, notebook level) and the disagreement list
    uv run python benchmark/real/score_labels.py agree ~/Desktop/LeakLens_labelling/returned OUT_DIR

    # 2. static scan of the TEST notebooks (reads code, executes nothing; Rule 7 allows it on the laptop)
    uv run python benchmark/real/score_labels.py scan OUT_DIR [--split TEST]

    # 3. score the scan against the settled labels (benchmark/real/labels_TEST.csv)
    uv run python benchmark/real/score_labels.py score benchmark/real/labels_TEST.csv OUT_DIR

Sheets follow LABELLING_GUIDE.md section 6: labeller, notebook_id, leak_type, cell, line_start, line_end,
confidence, note, minutes. `cell` is the displayed cell number (all cells counted from 1), which is the analyser's
0-based cell index plus one. The settled label file has the same columns plus an optional `entity_column`: when it
is filled for a group label, a group finding matches only if it names that column (the strict rule of
EVAL_CHANGES #10). Matching and metrics are those of EVAL_PROTOCOL.md sections 2 to 4 (leaklens.evaluation.scoring).
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TYPES = ("preprocessing", "overlap", "multi_test", "group", "temporal", "target_derived")
NON_LEAK = {"none", "no_model", "cannot_read"}


def read_sheet(path: Path) -> list[dict]:
    rows = [r for r in csv.DictReader(path.open(newline="", encoding="utf-8-sig"))]
    return [
        {k.strip(): (v or "").strip() for k, v in r.items() if k} for r in rows if (r.get("notebook_id") or "").strip()
    ]


def presence(rows: list[dict]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        out[r["notebook_id"]]
        if r["leak_type"] in TYPES:
            out[r["notebook_id"]].add(r["leak_type"])
    return out


def cohen_kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def agree(sheet_dir: Path, out: Path) -> None:
    sheets = sorted(sheet_dir.glob("labelling_sheet_*.csv"))
    if len(sheets) != 2:
        raise SystemExit(f"need exactly two sheets in {sheet_dir}, found {len(sheets)}")
    a_rows, b_rows = read_sheet(sheets[0]), read_sheet(sheets[1])
    pa, pb = presence(a_rows), presence(b_rows)
    nbs = sorted(set(pa) & set(pb))
    only = sorted(set(pa) ^ set(pb))
    lines = [
        f"# Agreement between {sheets[0].name} and {sheets[1].name}",
        "",
        f"Notebooks labelled by both: {len(nbs)}" + (f"; by only one: {', '.join(only)}" if only else ""),
        "",
        "Notebook level: is there at least one leak of this type in the notebook?",
        "",
        "| type | both yes | A only | B only | both no | Cohen's kappa |",
        "|---|---|---|---|---|---|",
    ]
    summary = {}
    for t in TYPES:
        a = [t in pa[n] for n in nbs]
        b = [t in pb[n] for n in nbs]
        k = cohen_kappa(a, b)
        cells = (
            sum(x and y for x, y in zip(a, b, strict=True)),
            sum(x and not y for x, y in zip(a, b, strict=True)),
            sum(y and not x for x, y in zip(a, b, strict=True)),
            sum(not x and not y for x, y in zip(a, b, strict=True)),
        )
        summary[t] = {"kappa": k, "counts": cells}
        lines.append(
            f"| {t} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {'n/a' if k is None else f'{k:.2f}'} |"
        )
    out.mkdir(parents=True, exist_ok=True)
    with (out / "disagreements.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["notebook_id", "type", "labeller_A", "labeller_B", "decision", "note"])
        for n in nbs:
            for t in TYPES:
                if (t in pa[n]) != (t in pb[n]):
                    w.writerow([n, t, "yes" if t in pa[n] else "no", "yes" if t in pb[n] else "no", "", ""])
    (out / "AGREEMENT.md").write_text("\n".join(lines) + "\n")
    (out / "agreement.json").write_text(json.dumps(summary, indent=1))
    print("\n".join(lines))


def scan(out: Path, split: str) -> None:
    from leaklens.ingest import load
    from leaklens.static.analyzer import analyze

    rows = [r for r in csv.DictReader((HERE / "manifest.csv").open()) if r["split"] == split]
    out.mkdir(parents=True, exist_ok=True)
    with (out / "findings.jsonl").open("w") as f:
        for r in rows:
            t = time.perf_counter()
            src = load(ROOT / r["file"], display=r["notebook_id"])
            fs, trunc = analyze(src) if src.status == "ok" else ([], False)
            f.write(
                json.dumps(
                    {
                        "notebook_id": r["notebook_id"],
                        "status": src.status,
                        "reason": src.reason,
                        "skipped_cells": len(src.skipped_cells),
                        "truncated": trunc,
                        "seconds": round(time.perf_counter() - t, 4),
                        "findings": [x.to_dict() for x in fs],
                    }
                )
                + "\n"
            )
    print(f"scanned {len(rows)} {split} notebooks -> {out / 'findings.jsonl'}")


def score(labels_path: Path, out: Path, boot: int = 2000) -> None:
    from leaklens.evaluation.scoring import Label, Pred, summarise

    rows = read_sheet(labels_path)
    recs = [json.loads(line) for line in (out / "findings.jsonl").open()]
    items = [r["notebook_id"] for r in recs]
    labelled = {r["notebook_id"] for r in rows}
    missing = sorted(set(items) - labelled)
    if missing:
        raise SystemExit(f"{len(missing)} notebooks have no label row: {', '.join(missing[:10])}")
    labels, entity = [], {}
    for r in rows:
        if r["leak_type"] not in TYPES or r["notebook_id"] not in set(items):
            continue
        lab = Label(
            r["notebook_id"],
            r["leak_type"],
            (),
            int(r["cell"]) - 1,
            int(r["line_start"]),
            int(r["line_end"] or r["line_start"]),
            r.get("confidence", ""),
            r.get("note", ""),
        )
        labels.append(lab)
        if r["leak_type"] == "group" and r.get("entity_column"):
            entity[lab] = r["entity_column"]
    preds_lenient, preds_strict = [], []
    for rec in recs:
        for f in rec["findings"]:
            loc = f["location"]
            if loc["cell"] is None:
                continue
            p = Pred(rec["notebook_id"], f["type"], loc["cell"], loc["line_start"], loc["line_end"], f["confidence"])
            preds_lenient.append(p)
            if f["type"] == "group":
                # strict: the finding must name the labelled entity of an overlapping group label, if one is given
                cols = [
                    c
                    for lab, c in entity.items()
                    if lab.item_id == p.item_id
                    and lab.cell == p.cell
                    and lab.line_start <= p.line_end
                    and lab.line_end >= p.line_start
                ]
                if cols and not any(f"`{c}`" in f["message"] for c in cols):
                    # wrong entity: it cannot match (cell -1), so it is a false positive and the label a miss
                    p = Pred(p.item_id, "group", -1, p.line_start, p.line_end, p.confidence)
            preds_strict.append(p)
    report = {
        "notebooks": len(items),
        "labels": len(labels),
        "notebooks_with_leak": len({lab.item_id for lab in labels}),
        "unanalysable": sum(r["status"] != "ok" for r in recs),
    }
    md = [
        "# LeakLens (static) on the real TEST notebooks",
        "",
        f"{report['notebooks']} notebooks, {report['labels']} labelled leaks in {report['notebooks_with_leak']} "
        f"notebooks, {report['unanalysable']} notebooks LeakLens could not read. Labels: `{labels_path.name}`. "
        "Matching: EVAL_PROTOCOL.md section 2; group findings must name the labelled entity where one is given.",
        "",
    ]
    for name, preds in (("strict (headline)", preds_strict), ("lenient", preds_lenient)):
        for op in ("medium", "low"):
            table = summarise(preds, labels, items, None, op, boot)
            report[f"{name}|{op}"] = table
            md += [
                f"## {name}, confidence {op} or higher",
                "",
                "| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |",
                "|---|---|---|---|---|---|---|",
            ]
            for row in table:

                def f3(v):
                    return "n/a" if v is None else f"{v:.2f}"

                def ci(v):
                    return "n/a" if v is None else f"{v[0]:.2f} to {v[1]:.2f}"

                md.append(
                    f"| {row['type']} | {row['labels']} | {row['tp']} | {row['fp']} | {row['fn']} | "
                    f"{f3(row['precision'])} ({ci(row['precision_ci'])}) | "
                    f"{f3(row['recall'])} ({ci(row['recall_ci'])}) |"
                )
            md.append("")
    (out / "REPORT.md").write_text("\n".join(md) + "\n")
    (out / "summary.json").write_text(json.dumps(report, indent=1, default=str))
    print("\n".join(md))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("agree")
    a1.add_argument("sheet_dir")
    a1.add_argument("out")
    a2 = sub.add_parser("scan")
    a2.add_argument("out")
    a2.add_argument("--split", default="TEST", choices=["DEV", "TEST"])
    a3 = sub.add_parser("score")
    a3.add_argument("labels")
    a3.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "agree":
        agree(Path(a.sheet_dir).expanduser(), Path(a.out))
    elif a.cmd == "scan":
        scan(Path(a.out), a.split)
    else:
        score(Path(a.labels), Path(a.out))


if __name__ == "__main__":
    main()
