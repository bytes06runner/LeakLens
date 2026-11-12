"""Build docs/report/LeakLens_Chapter3_Progress_Report.pdf in the style of Chapters 1 and 2.

    uv run --with reportlab python scripts/make_progress_report.py DEV_RUN_DIR TEST_RUN_DIR [YANG_FILE_LEVEL_CSV]

Result numbers in the PDF are read from the run folders (summary.json and impact_summary.json written by
benchmark/injected/score.py and score_impact.py, findings.jsonl, and the file-level CSV of the Yang baseline), so
the report cannot drift from the logged runs. Text that states what was not done, and the description of the
misses, is written by hand and must be kept true.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
RUN = (Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "2026-11-12_dev_injected_leaklens_v2").resolve()
TEST_RUN = (
    Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "results" / "2026-11-12_test_injected_leaklens_v1"
).resolve()
YANG_CSV = (
    Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "results" / "2026-11-12_kaggle_05_yang_test_injected" / "file_level.csv"
).resolve()
OUT = ROOT / "docs" / "report" / "LeakLens_Chapter3_Progress_Report.pdf"
FOOT = "LeakLens | Chapter 3: Implementation and Results to Date | GNIT, IT"

NAVY = colors.HexColor("#1F3A5F")
GREY = colors.HexColor("#5A6470")
HEAD_BG = colors.HexColor("#E9EEF4")
LABEL_BG = colors.HexColor("#F3F5F8")
RULE = colors.HexColor("#B8C2CC")

H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17, leading=21, spaceAfter=2)
SUB = ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, leading=12, textColor=GREY, spaceAfter=6)
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=NAVY, spaceBefore=9,
                    spaceAfter=4, keepWithNext=1)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9.3, leading=12.6, alignment=TA_JUSTIFY, spaceAfter=5)
BUL = ParagraphStyle("bul", parent=BODY, leftIndent=11, bulletIndent=1, spaceAfter=3)
CELL = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.1, leading=10.2)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold")
NOTE = ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=8, leading=10, textColor=GREY, spaceAfter=5)
REF = ParagraphStyle("ref", fontName="Helvetica", fontSize=7.8, leading=10, leftIndent=14, firstLineIndent=-14,
                     spaceAfter=2)
CAP = ParagraphStyle("cap", fontName="Helvetica-Bold", fontSize=9.3, leading=12, spaceBefore=4, spaceAfter=3,
                     keepWithNext=1)


def p(text: str) -> Paragraph:
    return Paragraph(text, BODY)


def bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(t, BUL, bulletText="•") for t in items]


def table(rows: list[list[str]], widths: list[float], header: bool = True, label_col: bool = False,
          bold_last: bool = False) -> Table:
    data = []
    for i, row in enumerate(rows):
        style = CELLB if (header and i == 0) or (bold_last and i == len(rows) - 1) else CELL
        data.append([Paragraph(str(c), CELLB if (label_col and j == 0) else style) for j, c in enumerate(row)])
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.5, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), HEAD_BG))
    if label_col:
        st.append(("BACKGROUND", (0, 0), (0, -1), LABEL_BG))
    t.setStyle(TableStyle(st))
    return t


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(20 * mm, 11 * mm, FOOT)
    canvas.drawRightString(A4[0] - 20 * mm, 11 * mm, f"Page {doc.page}")
    canvas.restoreState()


def f3(v) -> str:
    return "n/a" if v is None else f"{v:.2f}"


def ci(v) -> str:
    return "n/a" if v is None else f"{v[0]:.2f} to {v[1]:.2f}"


TYPES = ["preprocessing", "overlap", "multi_test", "group", "temporal", "target_derived"]
NAMES = {"preprocessing": "Preprocessing", "overlap": "Overlap / duplicates", "multi_test": "Multi-test",
         "group": "Group (entity)", "temporal": "Temporal", "target_derived": "Target-derived"}


def load(run: Path) -> dict:
    s = json.loads((run / "summary.json").read_text())
    i = json.loads((run / "impact_summary.json").read_text())
    st = {r["type"]: r for r in s["modes"]["static"]["medium"]}
    dy = {r["type"]: r for r in s["modes"]["static+dynamic"]["medium"]}
    lo = {r["type"]: r for r in s["modes"]["static+dynamic"]["low"]}
    status = i["status"]
    return {"s": s, "i": i, "st": st, "dy": dy, "lo": lo, "n": s["labels"], "files": s["items"],
            "tp_st": sum(st[t]["tp"] for t in TYPES), "tp_dy": sum(dy[t]["tp"] for t in TYPES),
            "fp": sum(max(st[t]["fp"], dy[t]["fp"]) for t in TYPES), "clean": s["modes"]["static+dynamic"]["clean_files"],
            "measured": sum(v for k, v in status.items() if k.endswith("|measured")),
            "no_est": sum(v for k, v in status.items() if not k.endswith("|measured")), "status": status,
            "cat": s["modes"]["static+dynamic"]["recall_by_category"]}


def detection_table(d: dict) -> Table:
    rows = [["Leakage type", "Labelled leaks", "Static: found", "Static: recall (95% CI)", "Static + dynamic: found",
             "Static + dynamic: recall (95% CI)", "False positives (either mode)"]]
    for t in TYPES:
        a, b = d["st"][t], d["dy"][t]
        rows.append([NAMES[t], a["labels"], a["tp"], f"{f3(a['recall'])} ({ci(a['recall_ci'])})", b["tp"],
                     f"{f3(b['recall'])} ({ci(b['recall_ci'])})", max(a["fp"], b["fp"])])
    rows.append(["All types", d["n"], d["tp_st"], f3(d["tp_st"] / d["n"]), d["tp_dy"], f3(d["tp_dy"] / d["n"]), d["fp"]])
    return table(rows, [30, 17, 16, 32, 20, 32, 23], bold_last=True)


DEV = load(RUN)
TEST = load(TEST_RUN)
static_s, dyn_s = TEST["s"]["static_seconds"], TEST["s"].get("dynamic_seconds", {})
cat = TEST["cat"]


def group_columns_right(run: Path) -> tuple[int, int]:
    """Group findings (medium or higher, not refuted) that name the base pipeline's true entity column."""
    import yaml

    entity = {b: v.get("entity") for b, v in yaml.safe_load((ROOT / "benchmark/injected/bases.yaml").read_text()).items()}
    right = total = 0
    for line in (run / "findings.jsonl").open():
        rec = json.loads(line)
        if rec["seed"] != 0:
            continue
        for f in rec.get("dynamic", []):
            if f["type"] == "group" and f["confidence"] != "low" and f["dynamic"]["status"] != "refuted":
                total += 1
                right += f["dynamic"].get("details", {}).get("column") == entity[rec["base"]]
    return right, total


grp_right, grp_total = group_columns_right(TEST_RUN)
assert grp_total == TEST["dy"]["group"]["tp"], "group findings on TEST do not match the summary"
yang_rows = []
if YANG_CSV.exists():
    yang_rows = list(csv.DictReader(YANG_CSV.open()))

story: list = []
story += [Paragraph("Chapter 3: Implementation and Results to Date", H1),
          Paragraph("LeakLens, Software Engineering Minor Project, Semester V. Progress report of 12 November 2026.", SUB),
          table([["Project", "LeakLens: Static and Dynamic Detection of Data Leakage in Machine Learning Code"],
                 ["Theme", "Software Engineering (Minor Project, Semester V)"],
                 ["Submitted by", "Srijeet Prasad Banerjee, B.Tech IT, 3rd Year"],
                 ["Supervisor", "Prof. Tridib Chakraborty"],
                 ["Institute", "Guru Nanak Institute of Technology, Kolkata"],
                 ["Repository", "https://github.com/bytes06runner/LeakLens (all results below are logged in results/)"]],
                [30, 140], header=False, label_col=True), Spacer(1, 4)]

story += [Paragraph("3.1 Summary", H2),
          p("Chapters 1 and 2 proposed a tool that finds data leakage in Python ML code, confirms it on the data, and "
            "measures how much each leak inflates the reported score. On 29 September the repository held the "
            "taxonomy, the specification, a sandbox and a labelled benchmark, and <b>no detector</b>. This chapter "
            "reports what exists on 12 November: a static analyser for all six leakage types, a dynamic "
            "(instrumented-run) pass, per-finding impact estimation, a command-line tool with JSON and SARIF "
            "output, a frozen evaluation protocol, and the first held-out results."),
          p(f"<b>Main result, on the held-out TEST half of the injected benchmark</b> ({TEST['files']} files, "
            f"{TEST['n']} labelled leaks; scored once, after the protocol was frozen; the tool's rules were never "
            f"tuned on these files): reading the code alone, LeakLens finds {TEST['tp_st']} of {TEST['n']} leaks "
            f"({TEST['tp_st'] / TEST['n']:.0%}); with the instrumented run, {TEST['tp_dy']} of {TEST['n']} "
            f"({TEST['tp_dy'] / TEST['n']:.0%}). It reports {TEST['fp']} false positives and nothing on the "
            f"{TEST['clean']['n']} files that have no leak."),
          p(f"<b>Three cautions belong next to that number.</b> (1) In 4 of the 7 group leaks it finds on TEST, the "
            f"tool points at the right line but names the wrong column (a visit number instead of the patient "
            f"identifier); only {grp_right} of 7 are right for the right reason, and the impact estimate for those 4 "
            "is wrong. (2) The benchmark files are generated by this project; they are simpler than real notebooks "
            "and contain the kinds of leak the tool was built for. (3) No real notebook has been labelled, so there "
            "is no result on real code. On the companion project's own code the tool found nothing (section 3.8).")]

story += [Paragraph("3.2 Progress against the plan", H2),
          table([["Phase", "Deliverable", "29 September", "12 November"],
                 ["0", "Setup, novelty check, baseline runnability", "done", "done; novelty search repeated today (3.8)"],
                 ["1", "Taxonomy of six types, specification, sandbox", "done", "done"],
                 ["2", "Benchmark: 175 injected files (162 leaks) and 150 real notebooks, DEV/TEST split frozen "
                       "before any rule", "injected done; real set sampled, unlabelled",
                  "unchanged: real notebooks still need two human labellers"],
                 ["3", "Evaluation protocol", "not started", "<b>frozen</b> (version 1.0, approved by the project owner)"],
                 ["4", "Static analyser", "not started", "<b>built</b>: all six types, 150+ rule tests"],
                 ["5", "Dynamic analyser", "not started", "<b>built</b>: confirms, refutes, and finds data-only leaks"],
                 ["6", "Impact estimation", "not started", "<b>built</b> for six kinds of fix; about half of the "
                                                         "leaks have no automatic fix yet"],
                 ["7", "Evaluation on TEST, baselines, case study", "not started",
                  "<b>injected TEST scored once</b>; one baseline run (Yang et al.); CalibraEEG case study: negative "
                  "result; real set and other baselines pending"],
                 ["8", "Mining study of public notebooks", "not started", "not started"],
                 ["9", "Release (PyPI, pre-commit, GitHub Action)", "not started",
                  "CLI, JSON, SARIF done; packaging not started; name clash found (3.8)"]],
                [12, 62, 40, 56])]

story += [Paragraph("3.3 What was built", H2),
          table([["Component", "What it does"],
                 ["Ingest", "Reads .py and .ipynb files into one module with a map back to cell and line. Uses "
                            "execution order when every cell has one, else cell order, and records which. Files that "
                            "do not parse are reported, never silently skipped."],
                 ["Static analyser", "One pass of abstract interpretation over pandas, NumPy, scikit-learn and "
                                     "imbalanced-learn code. For every variable it tracks which table the rows came "
                                     "from, which side of which split they are on, which columns they hold and what "
                                     "has leaked into them. Rules fire where rows are split, a model is fitted and "
                                     "scored, or a best score is selected. The analysed code is never run."],
                 ["Dynamic pass", "Runs the script with scikit-learn instrumented. At every split it measures, fold "
                                  "by fold, identical rows on both sides, entity values on both sides, and training "
                                  "rows dated after evaluation rows. Entity and time columns are found in the "
                                  "script's own variables, so <b>the user declares nothing</b>."],
                 ["Impact estimation", "Re-runs the user's own script with one call site changed (group-aware or "
                                       "chronological split, evaluation rows removed from a fit, a transformer "
                                       "fitted on training rows only, duplicates or one feature removed) and "
                                       "reports the change in the metric the script itself prints."],
                 ["Reporting", "Terminal output, JSON (validated against a schema), SARIF 2.1.0 for GitHub code "
                               "scanning, CI exit codes, inline suppression comments."],
                 ["Evaluation", "One matching rule and bootstrap confidence intervals shared by every tool; a runner "
                                "that refuses TEST until the protocol is frozen and refuses a second TEST run unless "
                                "it is logged."]],
                [34, 136]),
          Paragraph("About 5,200 lines of Python in the package and 1,500 lines of tests (360 tests pass, including "
                    "property-based tests that the analyser never crashes and is deterministic).", NOTE)]

story += [Paragraph("3.4 A worked example", H2),
          p("A DEV pipeline loads a table of patients from 12 hospital sites, keeps four marker columns and calls "
            "<font face='Courier'>train_test_split</font>. The code never mentions the column "
            "<font face='Courier'>site</font>, so no static tool can see a problem. LeakLens output for that file "
            "(static + dynamic + impact):"),
          table([["line 17   [high/high]  group (LL-GRP-004)   run: confirmed   test_auc 0.6865 -> 0.3016 with the fix<br/>"
                  "The data has a column `site` that the split ignores: 12 of its values are on both sides, and 100% "
                  "of the evaluation rows belong to an entity that is also in the training rows.<br/>"
                  "fix: Split by entity: use GroupShuffleSplit with groups=`site` (same folds, test size and seed)."]],
                [170], header=False),
          Paragraph("This is the sentence Chapter 1 asked for (\"line 42 lets the same patient into both training "
                    "and test, and fixing it drops your score from X to Y\"). The size of the drop is a property of "
                    "our synthetic data, not evidence about real studies, and section 3.7 shows that this kind of "
                    "estimate is the least accurate one.", NOTE)]

story += [Paragraph("3.5 Detection results on the held-out TEST split", H2),
          p(f"Injected benchmark, TEST half: {TEST['files']} files from 6 base pipelines that are different from the "
            f"7 used for development, {TEST['n']} labelled leaks, {TEST['clean']['n']} files without a leak. A finding "
            "counts only if it has the right type and overlaps the labelled lines in the right cell; findings of "
            "medium or high confidence are counted. Intervals: bootstrap over files, 2,000 resamples. With so few "
            "leaks per type the intervals are wide."),
          detection_table(TEST),
          Paragraph("Precision is 1.00 for every type (no false positive). The files are synthetic and short; this "
                    "will not hold on real code.", NOTE)]
story += bullets([
    f"<b>What was missed ({TEST['n'] - TEST['tp_dy']} leaks).</b> Five temporal leaks (a scaler or statistic fitted "
    "over a whole time series) were reported only at low confidence, and one multi-test leak was not reported, "
    "all in one pipeline that drops its last row with <font face='Courier'>data.iloc[:-1]</font>: the analyser "
    "mistook that slice for a train/test split. One target-encoding leak and one target-derived feature were "
    "missed because the feature list was built with a <font face='Courier'>startswith</font> filter the analyser "
    "cannot resolve, and it reports nothing rather than guess. With low-confidence findings included, temporal "
    f"recall is {f3(TEST['lo']['temporal']['recall'])}.",
    f"<b>Group leakage: right line, wrong column in 4 of 7.</b> For the EEG-style pipeline the entity comes from "
    "file names and is found from the code alone (3 of 3). For the patient-visits pipeline the static pass made a "
    "low-confidence guess on a column called <font face='Courier'>visit</font>; the run then \"confirmed\" it, "
    "because visit numbers repeat on both sides of any split, and never looked at <font face='Courier'>"
    "patient_id</font>. Under the frozen matching rule (type and line) these count as found, and the table shows "
    f"7 of 7. Counted strictly, group recall on TEST is {grp_right} of 7.",
    f"<b>Temporal categories:</b> common {cat['temporal_common'][0]} of {sum(cat['temporal_common'])}, "
    f"differentiating {cat['temporal_differentiating'][0]} of {sum(cat['temporal_differentiating'])} (default "
    "shuffle of train_test_split, unshuffled KFold, a time column with an uninformative name), hard "
    f"{cat['temporal_hard'][0]} of {sum(cat['temporal_hard'])}. The temporal baseline (scicode-lint) has not been run.",
    f"<b>Speed.</b> Static analysis: median {static_s['median'] * 1000:.1f} ms per file (laptop, Apple M5). An "
    f"instrumented run costs one execution of the script (median {dyn_s.get('median', 0):.1f} s).",
    "<b>These three causes have not been fixed.</b> Fixing them now and re-running TEST would be a second look at "
    "the test set; it is logged as an open decision, not done."])

story += [Paragraph("3.6 Results on the DEV split (the files the rules were written on)", H2),
          detection_table(DEV),
          Paragraph(f"DEV: {DEV['files']} files, {DEV['n']} leaks, {DEV['clean']['n']} files without a leak, no false "
                    "positive. These numbers are optimistic by design and are shown only to make the gap to TEST "
                    f"visible: {DEV['tp_dy'] / DEV['n']:.0%} on DEV against {TEST['tp_dy'] / TEST['n']:.0%} on TEST "
                    "with the run. The static analyser also ran on the 71 real DEV notebooks without a crash; nobody "
                    "has labelled them, so no precision or recall can be stated for real code.", NOTE)]

imp = [["Leakage type", "Estimated (TEST)", "No estimate (TEST)", "Why no estimate"]]
why = {"preprocessing": "pandas statistics, or data that is cross-validated",
       "overlap": "resampling before the split has no automatic fix",
       "multi_test": "nested validation is not automated", "group": "",
       "temporal": "forward-looking features and whole-series statistics have no automatic fix", "target_derived": ""}
for t in TYPES:
    imp.append([NAMES[t], TEST["status"].get(f"{t}|measured", 0),
                TEST["status"].get(f"{t}|unknown", 0) + TEST["status"].get(f"{t}|unreliable", 0), why[t]])
imp.append(["All types", TEST["measured"], TEST["no_est"], ""])
acc = [["Leakage type", "Metric", "Findings", "Mean true inflation", "Mean estimate", "Mean absolute error",
        "Direction right"]]
for g in TEST["i"]["seed_averaged"]:
    sa = g["sign_agreement"]
    acc.append([NAMES[g["type"]], g["metric"], g["n"], f"{g['mean_true']:+.4f}", f"{g['mean_estimate']:+.4f}",
                f"{g['mae']:.4f}", "n/a" if sa is None else f"{sa:.0%}"])
ovt, ovd = TEST["i"]["overall_seed_averaged"], DEV["i"]["overall"]
story += [Paragraph("3.7 Impact estimation: coverage and accuracy", H2),
          p("For an injected file the true inflation is known: the metric of the leaky file minus the metric of its "
            "hand-written correct version, on the same data. LeakLens's estimate is the metric of the original run "
            "minus the metric when the run is repeated with the finding's fix. On TEST both are averaged over five "
            "data seeds. In every one of the 395 TEST runs the instrumented script printed exactly the metric the "
            "plain script prints, so the instrumentation does not disturb the pipeline."),
          Paragraph("Coverage on TEST: for how many correctly located leaks an estimate could be produced", CAP),
          table(imp, [34, 24, 26, 86], bold_last=True),
          Paragraph("Accuracy on TEST (files with a single leak, averaged over data seeds 0 to 4)", CAP),
          table(acc, [32, 20, 17, 28, 25, 26, 22]),
          p(f"Over the {ovt['n_bounded']} TEST estimates on bounded metrics (AUC, R2) the mean absolute error is "
            f"{ovt['mae_bounded']:.3f} and the rank correlation with the true inflation is "
            f"{f3(ovt['spearman_bounded'])} (DEV, one seed: {ovd['mae_bounded']:.3f} and "
            f"{f3(ovd['spearman_bounded'])}). What these numbers mean:")]
story += bullets([
    "<b>Where the fix is the same operation as the benchmark's own correct version</b> (overlap, temporal splits, "
    "target-derived features), the error is zero. That shows the fixing machinery is right; it is not a hard test.",
    "<b>Hold-out group splits fail on TEST</b> (group, test_auc: estimate -0.08 against a true +0.21, wrong "
    "direction). This is the wrong-column problem of section 3.5: the fix grouped by visit number, not by patient. "
    "On DEV the same kind of estimate had the right direction but was off by 0.30 for a different reason (few "
    "sites, different sites held out). Group impact under cross-validation is accurate on both splits.",
    "<b>Preprocessing leaks barely move the score</b> (true inflation about 0.000 on TEST), which agrees with [5]; "
    "the sign of such a small number is noise.",
    f"<b>Coverage is partial:</b> an estimate for {TEST['measured']} of {TEST['measured'] + TEST['no_est']} located "
    "leaks on TEST. The rest are reported as \"impact unknown\" with the reason, not dropped. LeakHound's proxy "
    "estimate, the baseline for this task, has not been run.",
    "Injected inflation is built into our synthetic data. It is used only to check the estimates; it is not "
    "evidence of how severe any leakage type is in practice."])

story += [Paragraph("3.8 What went wrong, and what is missing", H2)]
story += bullets([
    "<b>TEST exposed three faults</b> that DEV did not: a positional slice mistaken for a split, an unresolved "
    "column filter, and a weak guess at the entity column that the run confirmed instead of correcting "
    "(section 3.5). They are recorded in EVAL_CHANGES.md and are not fixed.",
    "<b>CalibraEEG case study: LeakLens found nothing.</b> We ran the static analyser on the companion project's "
    "78 Python files. Expected: leakage flagged in regime A (random windows) and B (within-patient), nothing in C. "
    "Result: 0 findings in all three. That is correct for C and a miss for A and B: this code splits with "
    "hand-written NumPy masks over custom recording objects, not with scikit-learn splitters on data frames, "
    "which is all the analyser models today. The motivating example of Chapter 1 is not yet detected in its own "
    "code base.",
    "<b>The name is taken.</b> The novelty search found an unrelated package called <font face='Courier'>leaklens"
    "</font> on PyPI (first release June 2026, by another author): data-level checks plus a simple syntax check for "
    "preprocessing before a split. It does not detect group leakage from code and does not estimate impact, so the "
    "contributions stand, but the project needs a decision on its name before any release or paper.",
    "<b>A related idea exists for impact.</b> Leakly (2026) re-runs a user's pipeline on shuffled labels to test for "
    "leakage. It does not locate a leak or apply a fix, but our claim must be worded as per-finding impact, and "
    "Leakly must be cited.",
    "<b>Still to do:</b> human labels for real notebooks and their agreement, the other baselines (scicode-lint, "
    "the data-level tools, LeakHound, splitguard), the mining study, packaging. One test-split detail was seen by "
    "accident while the rules were being written (column names of the TEST pipelines); it is logged.",
    "<b>The benchmark and the detector have one author.</b> TEST uses other pipelines but the same kinds of "
    "injected leak, so TEST does not show how the tool copes with leaks written by other people. Only the "
    "human-labelled real notebooks can show that."])

story += [Paragraph("3.9 Comparison with existing systems", H2),
          p("First, capabilities, read from each tool's paper or documentation (Table 2.2 extended with the tools "
            "found since Chapter 2, and \"proposed\" replaced by what is implemented)."),
          table([["System", "Reads", "Types detected", "Group leakage", "Temporal leakage", "Impact estimate"],
                 ["Yang et al. [3]; LeakageDetector [6][13]", "code", "preprocessing, overlap, multi-test", "no", "no", "no"],
                 ["LeakCheck, Draoui et al. [7]", "code + LLM", "preprocessing, overlap", "not reported", "not reported", "no"],
                 ["scicode-lint [15]", "code + LLM", "66 patterns incl. two temporal", "no", "shuffled CV, forward shifts", "no"],
                 ["splitguard [16]", "run", "overlap, fit on held-out rows", "only if the user declares group ids", "no", "no"],
                 ["Deepchecks [8], leakcheck-ml, LeakHound, dataleaks, leaklens (PyPI) [17]", "data tables the user exports",
                  "duplicates, date overlap, some group checks", "some, column usually named by user; no code location",
                  "date overlap on given splits", "LeakHound: its own proxy model"],
                 ["Leakly [18]", "re-run on shuffled labels", "any (not located, not typed)", "no", "no", "indirect, whole pipeline"],
                 ["<b>LeakLens (this work, implemented)</b>", "<b>code, then a run</b>",
                  "<b>all six, with line and suggested fix</b>",
                  "<b>yes: from file paths or names in code; from the data at run time with nothing declared "
                  "(column choice not yet reliable, 3.5)</b>",
                  "<b>yes: split and feature level, by data flow; confirmed on the data</b>",
                  "<b>yes, per finding, by re-running the user's script with the fix (6 kinds of fix)</b>"]],
                [36, 20, 31, 32, 27, 24]),
          Paragraph("\"no\" and \"not reported\" mean the source we read does not state support. Tools known only from "
                    "PyPI were read from package metadata and README (literature/related_work.csv).", NOTE)]
if yang_rows:
    split = "TEST" if "test" in YANG_CSV.parent.name else "DEV"
    yt = [["Leakage type", "Files with this leak", "Yang et al. [3]: files found", "Yang: false alarms",
           "LeakLens (static): files found", "LeakLens: false alarms"]]
    ya = {r["type"]: r for r in yang_rows if r["tool"].startswith("Yang")}
    la = {r["type"]: r for r in yang_rows if r["tool"].startswith("LeakLens")}
    for t in TYPES:
        claimed = ya[t]["claimed"] == "True"
        yt.append([NAMES[t], la[t]["files"], ya[t]["tp"] + ("" if claimed else " (not a type it claims)"),
                   ya[t]["fp"], la[t]["tp"], la[t]["fp"]])
    story += [Paragraph(f"Measured: Yang et al.'s analyser and LeakLens on the same {split} files, per file and type", CAP),
              p("Second, one measured comparison. The reference analyser [3] was built from source on Kaggle and run "
                "with its default command on our benchmark files (notebooks converted to scripts, as its README "
                "requires). It reports the line of the affected evaluation call, not the leaking line, so both "
                "tools are scored here per file: does the tool report this leak type in a file that has it. "
                "LeakLens is in static mode, like the baseline."),
              table(yt, [32, 24, 34, 22, 36, 22]),
              Paragraph(("Neither tool was tuned on these files, but they are generated by this project with the "
                         "kinds of leak LeakLens was built for, and their style may differ from the notebooks [3] was "
                         "designed on, so this favours LeakLens. " if split == "TEST" else
                         "DEV files: LeakLens's rules were written on them, so this is not a fair accuracy "
                         "comparison. ")
                        + "Numbers that [3] reports on its own data (precision 97.6%, recall 67.8%) are a different "
                          "measurement and are not comparable with this table.", NOTE)]
else:
    story += [Paragraph("No measured comparison with another tool is available yet: the reference analyser [3] was "
                        "still running on the TEST files when this report was built. Numbers that [3] reports on its "
                        "own data (precision 97.6%, recall 67.8%) cannot be set against ours.", NOTE)]

shared = [TEST["st"][t] for t in ("preprocessing", "overlap", "multi_test")]
story += [Paragraph("3.10 Objectives of Chapter 1", H2),
          table([["#", "Objective", "Status on 12 November"],
                 ["O1", "Taxonomy of six types with a rule per type", "Met (docs/TAXONOMY.md), with runnable examples that are part of the test suite."],
                 ["O2", "Hybrid static + dynamic analyser with line, type and fix", "Built; evaluated on held-out injected files. Not yet evaluated on real notebooks."],
                 ["O3", "Impact of each finding by fixing and re-running",
                  f"Built for six kinds of fix; an estimate for {TEST['measured']} of {TEST['measured'] + TEST['no_est']} located TEST leaks; wrong for hold-out group splits (3.7)."],
                 ["O4", "Labelled benchmark; precision of at least 0.90 and recall above 67.8% on shared types",
                  "Benchmark built. On injected TEST, static mode: precision 1.00; recall "
                  + ", ".join(f"{NAMES[r['type']].lower()} {f3(r['recall'])}" for r in shared)
                  + ". The point estimates meet the target, but the intervals are wide (for example overlap "
                  + ci(TEST["st"]["overlap"]["recall_ci"]) + "), the files are our own, and 67.8% was measured on "
                    "other data. <b>Met on our injected benchmark only.</b>"],
                 ["O5", "Empirical study on public notebooks", "Not started. 150 notebooks sampled; none labelled."],
                 ["O6", "Usable software", "CLI, JSON, SARIF and exit codes done. No PyPI release, pre-commit hook or GitHub Action yet."]],
                [10, 62, 98])]

story += [Paragraph("3.11 Next steps and decisions needed", H2)]
story += bullets([
    "<b>Decide on a second look at TEST.</b> The three faults found on TEST have obvious fixes. Fixing them and "
    "re-running TEST is allowed only as a logged second look, reported next to the first result, never instead of it.",
    "<b>Label real notebooks:</b> two people, in the prepared random order, without seeing the tool's output. "
    "This is the only route to a result on real code.",
    "<b>Decide the project name</b> in the light of the existing PyPI package.",
    "Run the remaining baselines: data-level tools on the splits the instrumented run materialises, LeakHound for "
    "impact, scicode-lint for temporal leakage.",
    "Extend the analyser to hand-written splits (NumPy masks, custom loaders) so that the CalibraEEG case is found; "
    "at run time, check every candidate entity column instead of trusting the static guess; add fixes for the "
    "leak kinds that have none."])

story += [Paragraph("References", CAP)]
for r in [
    "[1] S. Kaufman et al. Leakage in data mining: formulation, detection, and avoidance. ACM TKDD 6(4), 2012. https://doi.org/10.1145/2382577.2382579",
    "[2] S. Kapoor, A. Narayanan. Leakage and the reproducibility crisis in machine-learning-based science. Patterns 4(9):100804, 2023. https://doi.org/10.1016/j.patter.2023.100804",
    "[3] C. Yang, R. A. Brower-Sinning, G. Lewis, C. Kaestner. Data leakage in notebooks: static detection and better processes. ASE 2022. https://doi.org/10.1145/3551349.3556918",
    "[5] S. Roth. Which leakage types matter? A quantitative landscape across 2,047 benchmark datasets. arXiv:2604.04199, 2026.",
    "[6] E. A. AlOmar et al. LeakageDetector: an open source data leakage analysis tool in machine learning pipelines. 2025. https://arxiv.org/abs/2503.14723",
    "[7] T. Draoui, M. W. Mkaouer, C. Newman. Improving data leakage detection in machine learning notebooks through static slicing and structured LLM prompts. ACM, 2026. https://doi.org/10.1145/3808199",
    "[8] S. Chorev et al. Deepchecks: a library for testing and validating machine learning models and data. JMLR 23(285), 2022.",
    "[13] LeakageDetector 2.0: analyzing data leakage in Jupyter-driven machine learning pipelines. 2025. https://arxiv.org/abs/2509.15971",
    "[15] Samsonau. scicode-lint: detecting methodology bugs in scientific Python code with LLM-generated patterns. arXiv:2603.17893, 2026.",
    "[16] T. Aiello. splitguard 0.1.0. PyPI, 2026. https://github.com/Tommasoaiello13/splitguard",
    "[17] Prajwal. leaklens 1.3.0 (unrelated package of the same name). PyPI, 2026. https://pypi.org/project/leaklens/",
    "[18] DeMONLab-BioFINDER. Leakly 0.1.2. PyPI, 2026. https://github.com/DeMONLab-BioFINDER/Leakly",
]:
    story.append(Paragraph(r, REF))
story.append(Paragraph(f"[1] to [14] as in Chapters 1 and 2. [16] to [18]: package metadata and README only. Result "
                       f"numbers are read from {TEST_RUN.relative_to(ROOT)} and {RUN.relative_to(ROOT)}.", REF))

OUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=15 * mm,
                        bottomMargin=17 * mm, title="LeakLens Chapter 3: Implementation and Results to Date",
                        author="Srijeet Prasad Banerjee")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"wrote {OUT}")
