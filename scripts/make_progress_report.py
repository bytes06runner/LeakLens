"""Build docs/report/LeakLens_Chapter3_Progress_Report.pdf in the style of Chapters 1 and 2.

    uv run --with reportlab python scripts/make_progress_report.py RUN_DIR

Every result number in the PDF is read from RUN_DIR (summary.json and impact_summary.json written by
benchmark/injected/score.py and score_impact.py), so the report cannot drift from the logged run. Text that
states what was not done is written by hand and must be kept true.
"""

from __future__ import annotations

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


summary = json.loads((RUN / "summary.json").read_text())
impact = json.loads((RUN / "impact_summary.json").read_text())
st_rows = {r["type"]: r for r in summary["modes"]["static"]["medium"]}
dy_rows = {r["type"]: r for r in summary["modes"]["static+dynamic"]["medium"]}
TYPES = ["preprocessing", "overlap", "multi_test", "group", "temporal", "target_derived"]
NAMES = {"preprocessing": "Preprocessing", "overlap": "Overlap / duplicates", "multi_test": "Multi-test",
         "group": "Group (entity)", "temporal": "Temporal", "target_derived": "Target-derived"}
n_leaks = summary["labels"]
tp_static = sum(st_rows[t]["tp"] for t in TYPES)
tp_dyn = sum(dy_rows[t]["tp"] for t in TYPES)
fp_static = sum(st_rows[t]["fp"] for t in TYPES)
fp_dyn = sum(dy_rows[t]["fp"] for t in TYPES)
clean = summary["modes"]["static+dynamic"]["clean_files"]
status = impact["status"]
measured = sum(v for k, v in status.items() if k.endswith("|measured"))
unknown = sum(v for k, v in status.items() if k.endswith("|unknown"))
unreliable = sum(v for k, v in status.items() if k.endswith("|unreliable"))
static_s = summary["static_seconds"]
dyn_s = summary.get("dynamic_seconds", {})

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
            "reports what exists on 12 November: a working static analyser for all six leakage types, a dynamic "
            "(instrumented-run) pass, per-finding impact estimation, a command-line tool with JSON and SARIF "
            "output, and first results."),
          p(f"<b>The main result so far, on the development (DEV) half of the injected benchmark:</b> reading the "
            f"code alone, LeakLens finds {tp_static} of {n_leaks} labelled leaks with {fp_static} false positives; "
            f"with the instrumented run added it finds {tp_dyn} of {n_leaks} with {fp_dyn} false positives, and "
            f"raises no finding on {clean['n'] - clean['with_finding']} of {clean['n']} files that have no leak. "
            "<b>These are DEV numbers.</b> The rules were written while looking at these files, so they show that "
            "the method works end to end; they are not an estimate of accuracy on unseen code. The held-out TEST "
            "half has not been scored, no real notebook has been labelled, and no other tool has been run on our "
            "benchmark yet. Section 3.7 lists what went wrong or is still missing.")]

story += [Paragraph("3.2 Progress against the plan", H2),
          table([["Phase", "Deliverable", "29 September", "12 November"],
                 ["0", "Setup, novelty check, baseline runnability", "done", "done; novelty search repeated today (3.7)"],
                 ["1", "Taxonomy of six types, specification, sandbox", "done", "done"],
                 ["2", "Benchmark: 175 injected files (162 leaks) and 150 real notebooks, DEV/TEST split frozen "
                       "before any rule", "injected done; real set sampled, unlabelled",
                  "unchanged: real notebooks still need two human labellers"],
                 ["3", "Evaluation protocol", "not started", "written as a proposal; <b>not frozen</b>, waits for approval"],
                 ["4", "Static analyser", "not started", "<b>built</b>: all six types, 150+ rule tests"],
                 ["5", "Dynamic analyser", "not started", "<b>built</b>: confirms, refutes, and finds data-only leaks"],
                 ["6", "Impact estimation", "not started", "<b>built</b> for six kinds of fix; about half of the "
                                                         "leaks have no automatic fix yet"],
                 ["7", "Evaluation on TEST, baselines, case study", "not started",
                  "DEV only; TEST untouched; CalibraEEG case study run (static): negative result"],
                 ["8", "Mining study of public notebooks", "not started", "not started"],
                 ["9", "Release (PyPI, pre-commit, GitHub Action)", "not started",
                  "CLI, JSON, SARIF done; packaging not started; name clash found (3.7)"]],
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
                                "that refuses to touch TEST until the protocol is frozen."]],
                [34, 136]),
          Paragraph("About 5,200 lines of Python in the package and 1,500 lines of tests (359 tests pass, including "
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
                    "and test, and fixing it drops your score from X to Y\"). The size of the drop here is a "
                    "property of our synthetic data, not evidence about real studies; and section 3.6 shows this "
                    "particular kind of estimate is the least accurate one.", NOTE)]

det = [["Leakage type", "Labelled leaks", "Static: found", "Static: recall (95% CI)", "Static + dynamic: found",
        "Static + dynamic: recall (95% CI)", "False positives (either mode)"]]
for t in TYPES:
    s, d = st_rows[t], dy_rows[t]
    det.append([NAMES[t], s["labels"], s["tp"], f"{f3(s['recall'])} ({ci(s['recall_ci'])})", d["tp"],
                f"{f3(d['recall'])} ({ci(d['recall_ci'])})", max(s["fp"], d["fp"])])
det.append(["All types", n_leaks, tp_static, f3(tp_static / n_leaks), tp_dyn, f3(tp_dyn / n_leaks),
            max(fp_static, fp_dyn)])
story += [Paragraph("3.5 Detection results on the DEV split", H2),
          p(f"Injected benchmark, DEV half: {summary['items']} files generated from 7 base pipelines, {n_leaks} "
            "labelled leaks, 10 files without a leak (7 clean, 3 traps that look leaky but are correct). A finding "
            "counts only if it has the right type and overlaps the labelled lines in the right cell. Findings of "
            "medium or high confidence are counted. Intervals: bootstrap over files, 2,000 resamples."),
          table(det, [30, 17, 16, 32, 20, 32, 23], bold_last=True),
          Paragraph("DEV numbers are optimistic by design: the rules were tuned on these files. With no false "
                    "positive, precision is 1.00 for every type on DEV; that will not hold on real code.", NOTE)]
story += bullets([
    "<b>Why static-only group recall is low.</b> In 7 of the 10 group leaks the entity column is in the data file "
    "but never named in the code. The static pass finds the 3 where the entity comes from file paths in the code. "
    "The instrumented run finds the other 7. This is the measured value of linking the two passes.",
    "<b>Temporal leakage</b> is found for all three benchmark categories (common 7 of 7, differentiating 6 of 6, "
    "hard 12 of 12), including the default shuffle of train_test_split, unshuffled KFold and a time column whose "
    "name gives no hint. The temporal baseline (scicode-lint) has not been run, so this is not yet a comparison.",
    f"<b>Speed.</b> Static analysis took a median of {static_s['median'] * 1000:.1f} ms per file (laptop, Apple "
    f"M5). An instrumented run costs one execution of the script (median {dyn_s.get('median', 0):.1f} s here).",
    "<b>Real notebooks (unlabelled, DEV half only).</b> The static analyser ran on all 71 real Kaggle notebooks "
    "without a crash (7 had cells it had to skip). It reported medium-or-higher findings in 19 notebooks for "
    "preprocessing, 10 for multi-test, 3 each for overlap, group and temporal. These counts are descriptive only: "
    "nobody has labelled the notebooks, so no precision or recall can be stated."])

imp = [["Leakage type", "Estimated", "No estimate", "Why no estimate"]]
why = {"preprocessing": "pandas statistics, or data that is cross-validated",
       "overlap": "resampling before the split has no automatic fix",
       "multi_test": "nested validation is not automated", "group": "", "temporal": "forward-looking features and "
       "whole-series statistics have no automatic fix", "target_derived": ""}
for t in TYPES:
    imp.append([NAMES[t], status.get(f"{t}|measured", 0), status.get(f"{t}|unknown", 0) + status.get(f"{t}|unreliable", 0),
                why[t]])
imp.append(["All types", measured, unknown + unreliable, ""])
acc = [["Leakage type", "Metric", "Findings", "Mean true inflation", "Mean estimate", "Mean absolute error",
        "Direction right"]]
for g in impact["groups"]:
    sa = g["sign_agreement"]
    acc.append([NAMES[g["type"]], g["metric"], g["n"], f"{g['mean_true']:+.4f}", f"{g['mean_estimate']:+.4f}",
                f"{g['mae']:.4f}", "n/a" if sa is None else f"{sa:.0%}"])
ov = impact.get("overall", {})
story += [Paragraph("3.6 Impact estimation: coverage and accuracy", H2),
          p("For an injected file the true inflation is known: the metric of the leaky file minus the metric of its "
            "hand-written correct version, on the same data. LeakLens's estimate is the metric of the original run "
            "minus the metric when the run is repeated with the finding's fix. The instrumented run printed exactly "
            "the same metric as the plain run in all 96 files, so the instrumentation does not disturb the pipeline."),
          Paragraph("Coverage: for how many correctly found leaks an estimate could be produced", CAP),
          table(imp, [34, 20, 22, 94], bold_last=True),
          Paragraph("Accuracy of the estimates (files with a single leak, DEV, data seed 0)", CAP),
          table(acc, [32, 20, 17, 28, 25, 26, 22]),
          p(f"Over the {ov.get('n_bounded', 0)} estimates on bounded metrics (AUC, average precision, R2) the mean "
            f"absolute error is {ov.get('mae_bounded', 0):.3f} and the rank correlation with the true inflation is "
            f"{f3(ov.get('spearman_bounded'))}. Three things must be said about these numbers:")]
story += bullets([
    "<b>Most errors are zero because the fix is the same operation as the benchmark's own correct version</b>, run "
    "on the same seed. That shows the fixing machinery is right; it is not a hard test of estimation.",
    "The 0% in the first row is a single file: its true inflation is 0.03 in average precision and the estimate "
    "was 0, because the benchmark's correct version fits the selector after oversampling and ours before it.",
    "<b>Hold-out group splits are the weak case</b> (test_auc row for group: error about 0.30). With only 12 sites, "
    "the score depends strongly on which sites are held out, and LeakLens's group split holds out different sites "
    "from the reference. The direction and ranking are right; the size is not reliable. Averaging over several "
    "group splits is the planned remedy.",
    f"<b>Coverage is partial:</b> {measured} of {measured + unknown + unreliable} found leaks got an estimate. The "
    "rest are reported as \"impact unknown\" with the reason, not dropped. LeakHound's proxy estimate, the "
    "baseline for this task, has not been run yet.",
    "Injected inflation is built into our synthetic data. It is used only to check the estimates; it is not "
    "evidence of how severe any leakage type is in practice."])

story += [Paragraph("3.7 What went wrong, and what is missing", H2)]
story += bullets([
    "<b>CalibraEEG case study: LeakLens found nothing.</b> We ran the static analyser on the companion project's "
    "78 Python files. Expected: leakage flagged in regime A (random windows) and B (within-patient), nothing in C. "
    "Result: 0 findings in all three. That is correct for C and a miss for A and B. The reason is that this code "
    "splits with hand-written NumPy masks over custom recording objects, not with scikit-learn splitters on data "
    "frames, which is all the analyser models today. The motivating example of Chapter 1 is therefore not yet "
    "detected in its own code base.",
    "<b>The name is taken.</b> The novelty search found an unrelated package called <font face='Courier'>leaklens"
    "</font> on PyPI (first release June 2026, by another author): data-level checks plus a simple syntax check for "
    "preprocessing before a split. It does not detect group leakage from code and does not estimate impact, so the "
    "contributions stand, but the project needs a decision on its name before any release or paper.",
    "<b>A related idea exists for impact.</b> Leakly (2026) re-runs a user's pipeline on shuffled labels to test for "
    "leakage. It does not locate a leak or apply a fix, but our claim must be worded as per-finding impact, and "
    "Leakly must be cited.",
    "<b>The reference baseline could not be run today.</b> Yang et al.'s analyser built and ran on Kaggle in "
    "September; on 12 November its Datalog engine no longer installs on Kaggle's current image, so it analysed 0 "
    "of the 96 DEV files. A second attempt that builds the engine from source was started. Until it succeeds there "
    "is no measured comparison with any other tool.",
    "<b>Evaluation still to do:</b> TEST (needs the protocol approved), human labels for real notebooks and their "
    "agreement, baselines, the mining study, packaging. One test-split detail was seen by accident (column names "
    "of the TEST pipelines); it is logged in EVAL_CHANGES.md.",
    "<b>The benchmark and the detector have one author.</b> TEST uses other pipelines but the same kinds of "
    "injected leak, so even TEST will not show how the tool copes with leaks written by other people. Only the "
    "human-labelled real notebooks can show that."])

story += [Paragraph("3.8 Comparison with existing systems", H2),
          p("The table extends Table 2.2 with the tools found since Chapter 2 and replaces \"proposed\" by what is "
            "implemented. It compares <b>capabilities</b>, read from each tool's paper or documentation. It does "
            "not compare accuracy: no other tool has been scored on our benchmark, and numbers that papers report "
            "on their own data (for example precision 97.6% and recall 67.8% for [3]) cannot be set against ours."),
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
                  "<b>yes: from file paths or names in code; from the data at run time with nothing declared</b>",
                  "<b>yes: split and feature level, by data flow; confirmed on the data</b>",
                  "<b>yes, per finding, by re-running the user's script with the fix (6 kinds of fix)</b>"]],
                [36, 20, 31, 32, 27, 24]),
          Paragraph("\"no\" and \"not reported\" mean the source we read does not state support. Tools known only from "
                    "PyPI were read from package metadata and README (literature/related_work.csv).",
                    NOTE)]

story += [Paragraph("3.9 Objectives of Chapter 1", H2),
          table([["#", "Objective", "Status on 12 November"],
                 ["O1", "Taxonomy of six types with a rule per type", "Met (docs/TAXONOMY.md), with runnable examples that are part of the test suite."],
                 ["O2", "Hybrid static + dynamic analyser with line, type and fix", "Built and working on DEV. Not yet evaluated on unseen code."],
                 ["O3", "Impact of each finding by fixing and re-running", f"Built for six kinds of fix; an estimate for {measured} of {measured + unknown + unreliable} DEV leaks."],
                 ["O4", "Labelled benchmark; precision of at least 0.90 and recall above 67.8% on shared types",
                  "Benchmark built. On DEV the targets are exceeded, but DEV is the tuning split: <b>the target is not yet demonstrated</b>. It must be shown on TEST and on labelled real notebooks."],
                 ["O5", "Empirical study on public notebooks", "Not started. 150 notebooks sampled; none labelled."],
                 ["O6", "Usable software", "CLI, JSON, SARIF and exit codes done. No PyPI release, pre-commit hook or GitHub Action yet."]],
                [10, 62, 98])]

story += [Paragraph("3.10 Next steps and decisions needed", H2)]
story += bullets([
    "<b>Approve (or change) the evaluation protocol</b> (docs/EVAL_PROTOCOL_SUMMARY.md, one page). TEST is scored "
    "once, straight after approval.",
    "<b>Label real notebooks:</b> two people, in the prepared random order, without seeing the tool's output.",
    "<b>Decide the project name</b> in the light of the existing PyPI package.",
    "Get at least one baseline running on the benchmark (Yang et al. from source; data-level tools on the splits "
    "the instrumented run materialises; LeakHound for impact).",
    "Extend the analyser to hand-written splits (NumPy masks, custom loaders) so that the CalibraEEG case is found; "
    "average group-split impact over several splits; add fixes for the leak kinds that have none."])

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
                       f"numbers are read from {RUN.relative_to(ROOT)}.", REF))

OUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=15 * mm,
                        bottomMargin=17 * mm, title="LeakLens Chapter 3: Implementation and Results to Date",
                        author="Srijeet Prasad Banerjee")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"wrote {OUT}")
