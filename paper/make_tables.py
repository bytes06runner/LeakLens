"""Generate the paper's measured tables from committed result files (no number is typed by hand).

    uv run python paper/make_tables.py

Writes paper/yang_measured_table.tex (Table 4), paper/baselines_table.tex (Table 5), paper/impact_table.tex
(Table 6) and paper/numbers.json (every number quoted in the new text).
"""

from __future__ import annotations

import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
B = ROOT / "benchmark" / "injected"
OUT = ROOT / "paper"
V1 = R / "2026-11-12_test_injected_leaklens_v1"
DL = R / "2026-11-13_data_level_test"
LH = R / "2026-11-14_leakhound_test_rerun"
YANG = R / "2026-11-12_kaggle_05_yang_test_injected"
numbers: dict = {}

labels = [r for r in csv.DictReader((B / "_groundtruth/labels.csv").open()) if r["split"] == "TEST"]
manifest = {r["item_id"]: r for r in csv.DictReader((B / "manifest.csv").open())}
meta = yaml.safe_load((B / "bases.yaml").read_text())
clean = [i for i, r in manifest.items() if r["split"] == "TEST" and r["n_leaks"] == "0"]


def accepts(lab):
    return {lab["type"], *[a for a in lab["alt_types"].split(";") if a and a != "nan"]}


def hit(finds, lab):
    cell = lab["cell"] if lab["cell"] not in ("", "nan") else None
    for f in finds:
        c = f["location"]["cell"]
        c = None if c is None else str(int(c))
        if f["type"] in accepts(lab) and c == cell and \
                int(lab["line_start"]) <= f["location"]["line_start"] <= int(lab["line_end"]):
            return f
    return None


def load(d: Path) -> dict:
    return {json.loads(x)["item_id"]: json.loads(x)["static"] for x in (d / "findings.jsonl").open()}


# ------------------------------------------------------------------ tools and modes
ll = {}
for line in (V1 / "findings.jsonl").open():
    r = json.loads(line)
    if r["seed"] == 0:
        ll[r["item_id"]] = [f for f in r["dynamic"] if f["confidence"] != "low"
                            and f["dynamic"]["status"] != "refuted"]
tools = [("LeakLens (static + run)", "none needed", ll, "leaklens")]
for name, _unused in (("leakcheck-ml", None), ("leakhound-ml", None), ("dataleaks", None), ("deepchecks", None),
                         ("splitguard", None)):
    base = LH if name == "leakhound-ml" else DL
    for mode, txt in (("default", "none (default)"), ("true_column", "true column named")):
        d = base / f"{name}__{mode}"
        if (d / "findings.jsonl").exists():
            tools.append((name, txt, load(d), mode))

T1 = [lab for lab in labels if lab["type"] == "temporal" and lab["subtype"] == "T1"]
G = [lab for lab in labels if lab["type"] == "group"]
DUP = [lab for lab in labels if lab["subtype"] == "raw_duplicates"]


def right_column(tool, mode, f, lab):
    ent = meta[lab["item_id"].split("__")[0]]["entity"]
    if tool.startswith("LeakLens"):
        return bool(re.search(rf"\b{re.escape(ent)}\b", f.get("message", "")))
    if tool == "splitguard":
        return mode == "true_column"  # the group was declared by us
    col = f.get("column")
    col = col[0] if isinstance(col, list) and col else col
    return col == ent


rows5 = []
for tool, hint, finds, mode in tools:
    t1 = sum(hit(finds.get(x["item_id"], []), x) is not None for x in T1)
    g_hits = [(x, hit(finds.get(x["item_id"], []), x)) for x in G]
    g = sum(h is not None for _, h in g_hits)
    gc = sum(h is not None and right_column(tool, mode, h, x) for x, h in g_hits)
    dp = sum(hit(finds.get(x["item_id"], []), x) is not None for x in DUP)
    alarms = sum(1 for i in clean if finds.get(i))
    rows5.append((tool, hint, t1, g, gc, dp, alarms))
numbers["table5"] = rows5
numbers["table5_denominators"] = {"T1": len(T1), "group": len(G), "raw_dup": len(DUP), "leak_free": len(clean)}

tex = [r"\begin{tabular}{@{}llrrrrr@{}}", r"\toprule",
       r"\textbf{Tool} & \textbf{Col.} & \textbf{T1} & \textbf{Grp} & \textbf{Grp, col.} & \textbf{Dup.} "
       r"& \textbf{Clean} \\",
       rf" & & /{len(T1)} & /{len(G)} & /{len(G)} & /{len(DUP)} & /{len(clean)} \\", r"\midrule"]
prev = None
for tool, hint, t1, g, gc, dp, al in rows5:
    pretty = {"leakhound-ml": "LeakHound", "deepchecks": "Deepchecks"}.get(tool, tool)
    shown = "" if tool == prev else pretty.replace("LeakLens", r"\tool{}")
    prev = tool
    shown_hint = {"none (default)": "no", "true column named": "yes", "none needed": "no"}[hint]
    tex.append(rf"{shown} & {shown_hint} & {t1} & {g} & {gc} & {dp} & {al} \\")
    if tool.startswith("LeakLens"):
        tex.append(r"\midrule")
tex += [r"\bottomrule", r"\end{tabular}"]
(OUT / "baselines_table.tex").write_text("\n".join(tex) + "\n")

# ------------------------------------------------------------------ Table 4 (Yang) + paired test
fl = list(csv.DictReader((YANG / "file_level.csv").open()))
yang = {r["type"]: r for r in fl if r["tool"].startswith("Yang")}
llf = {r["type"]: r for r in fl if r["tool"].lower().startswith("leaklens")}
names = [("preprocessing", "Preprocessing", ""), ("overlap", "Overlap / duplicates", ""),
         ("multi_test", "Multi-test", ""), ("group", r"Group$^{\dagger}$", ""),
         ("temporal", r"Temporal$^{\dagger}$", ""), ("target_derived", r"Target-derived$^{\dagger}$", "")]
tex = [r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
       r" & & \multicolumn{2}{c}{\textbf{Yang et al.~\cite{yang2022}}} & \multicolumn{2}{c}{\textbf{\tool{} (static)}} \\",
       r"\cmidrule(lr){3-4}\cmidrule(l){5-6}",
       r"\textbf{Leakage type} & \textbf{Files} & \textbf{Found} & \textbf{False} & \textbf{Found} & \textbf{False} \\",
       r"\midrule"]
for t, lab, _ in names:
    if t == "group":
        tex.append(r"\midrule")
    tex.append(rf"{lab} & {yang[t]['files']} & {yang[t]['tp']} & {yang[t]['fp']} & {llf[t]['tp']} & {llf[t]['fp']} \\")
tex += [r"\bottomrule", r"\end{tabular}"]
(OUT / "yang_measured_table.tex").write_text("\n".join(tex) + "\n")
pt = (R / "2026-11-13_yang_paired_test" / "output.txt").read_text()
numbers["paired"] = {k: int(v) for k, v in re.search(
    r"both (?P<both>\d+), only LeakLens (?P<ll>\d+), only Yang (?P<y>\d+), neither (?P<n>\d+)", pt).groupdict().items()}
numbers["paired"]["p"] = float(re.search(r"p = ([\d.e+-]+)", pt)[1])

# ------------------------------------------------------------------ Table 6 (impact vs LeakHound)
import subprocess  # noqa: E402

subprocess.run(["python", str(ROOT / "baselines/data_level/compare_impact.py"), str(LH), str(V1), "--out",
                str(LH / "IMPACT_VS_LEAKHOUND.md")], check=True, capture_output=True)
rows = json.loads((LH / "IMPACT_VS_LEAKHOUND.json").read_text())
per = defaultdict(lambda: {"n": 0, "comp": 0, "ll": [], "lh0": [], "lh1": []})
for x in rows:
    p = per[x["type"]]
    p["n"] += 1
    if not x["comparable_default"]:
        continue
    p["comp"] += 1
    lh = x["leakhound_true_column"] if x["leakhound_true_column"] is not None else x["leakhound_default"]
    x["leakhound_best"] = lh
    for key, val in (("ll", x["leaklens"]), ("lh0", x["leakhound_default"]), ("lh1", lh)):
        if val is not None:
            p[key].append(abs(val - x["true"]))


def cell(v):
    return f"{len(v)} ({statistics.mean(v):.3f})" if v else "0 (--)"


tex = [r"\begin{tabular}{@{}lrrlll@{}}", r"\toprule",
       r"\textbf{Type} & \textbf{N} & \textbf{Comp.} & \textbf{\tool{}} & \textbf{LH} & \textbf{LH, col.} \\",
       r"\midrule"]
for t in sorted(per):
    p = per[t]
    short = {"target_derived": "target-der.", "preprocessing": "preproc."}.get(t, t)
    tex.append(rf"{short} & {p['n']} & {p['comp']} & {cell(p['ll'])} & {cell(p['lh0'])} & {cell(p['lh1'])} \\")
tex += [r"\bottomrule", r"\end{tabular}"]
(OUT / "impact_table.tex").write_text("\n".join(tex) + "\n")
both = [x for x in rows if x["comparable_default"] and x["leaklens"] is not None
        and (x["leakhound_true_column"] is not None or x["leakhound_default"] is not None)]
numbers["impact"] = {t: {k: (len(v), round(statistics.mean(v), 3) if v else None) for k, v in p.items()
                         if k in ("ll", "lh0", "lh1")} | {"n": p["n"], "comp": p["comp"]} for t, p in per.items()}
numbers["impact_both"] = []
for x in both:
    lh = x["leakhound_true_column"] if x["leakhound_true_column"] is not None else x["leakhound_default"]
    numbers["impact_both"].append({"item": x["item_id"], "type": x["type"], "true": x["true"],
                                   "leaklens": x["leaklens"], "leakhound": lh})
(OUT / "numbers.json").write_text(json.dumps(numbers, indent=1, default=str))
print(json.dumps(numbers, indent=1, default=str))
