"""Build docs/report/LeakLens_Comparative_Table_Verified.pdf and docs/COMPARISON_TABLE_CHECK.md.

    uv run --with reportlab python scripts/make_comparison_table.py

A corrected version of the project's four-paper comparison table. Every cell about another paper says where it
was checked (2026-11-13) or that it could not be checked. Every cell about LeakLens carries one of three tags:
MEASURED (a logged run), BUILT (exists and is tested, not a comparison), NOT SHOWN (not true yet).
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "report" / "LeakLens_Comparative_Table_Verified.pdf"
MD = ROOT / "docs" / "COMPARISON_TABLE_CHECK.md"

M = "<font color='#1B7F3B'><b>MEASURED</b></font>"
B = "<font color='#1F4E9A'><b>BUILT</b></font>"
N = "<font color='#B3261E'><b>NOT SHOWN</b></font>"
U = "<font color='#8A6D00'><b>not checked</b></font>"

ROWS = [
    {
        "paper": "<b>LeakageDetector 2.0</b><br/>Truong, Zhang, Marchareddy, Lee, Busold, Socas, AlOmar. "
                 "arXiv:2509.15971, 2025.<br/><i>Checked: arXiv full text read.</i>",
        "does": ["VS Code extension for Jupyter notebooks; detects \"mainly Overlap, Preprocessing and Multi-test "
                 "leakage\".",
                 "Detection is Yang et al.'s static analyser, shipped as native binaries; Docker is optional.",
                 "Quick fixes, with optional GitHub Copilot suggestions."],
        "limits": ["No group or temporal leakage mentioned.",
                   "Static only: cannot see what is in the data.",
                   "Its multi-test fix inserts a placeholder call, load_test_data().",
                   "Reports no accuracy of its own: \"we did not assess the detection accuracy of the tool "
                   "separately\"; it relies on Yang et al.'s numbers.",
                   "No measurement of how much a leak changes the score."],
        "ours": [f"{M} Its detection engine (Yang et al.) and LeakLens were run on the same 79 held-out files, "
                 "scored per file: preprocessing 10 vs 21 of 22, overlap 7 vs 7 of 9, multi-test 3 vs 5 of 6. "
                 "No false alarm from either. The files are our own benchmark.",
                 f"{B} Looks for group and temporal leakage, which this tool does not.",
                 f"{B} Also runs the code and checks the data (repeated entities, duplicate rows).",
                 f"{B} Re-runs the script with a fix and reports the score change, for about half of the leaks.",
                 f"{N} \"Lighter because no Docker\": Docker is optional for this tool too.",
                 f"{N} \"0.95 to 0.43 AUPRC\": that figure is from CalibraEEG, where LeakLens found nothing."],
    },
    {
        "paper": "<b>Static Slicing and Structured LLM Prompts</b><br/>Draoui, Mkaouer, Newman. Proc. ACM Softw. "
                 "Eng. (FSE), 2026.<br/><i>Checked: abstract only (Sept. 2026); the publisher blocks the full "
                 "text.</i>",
        "does": ["Cuts a notebook into train/evaluate slices and asks an LLM about each (abstract).",
                 "Abstract: F1 better than prior work by 22% (preprocessing) and 15% (overlap).",
                 f"{U} 451 notebooks, GPT-4o-mini, 5-step checklist: stated in the original table, not confirmed "
                 "by us."],
        "limits": ["Covers preprocessing and overlap (abstract).",
                   "Needs an LLM service and a running slicer service to use.",
                   f"{U} \"14.3 seconds per notebook\" and \"cannot detect duplicate records\": not confirmed by us."],
        "ours": [f"{N} No head-to-head result: the tool needs a paid LLM key and its package is access-restricted, "
                 "so it was not run.",
                 f"{B} No LLM, no per-use cost, same answer every run.",
                 f"{M} Static analysis took a median of 2.6 ms per file on our files (a laptop). Their time is on "
                 "their notebooks, so this is not a like-for-like speed comparison.",
                 f"{B} Finds duplicate rows by checking the data at run time.",
                 f"{N} \"Catches sliding-window leaks\": not shown; the one real case tried (CalibraEEG) was missed."],
    },
    {
        "paper": "<b>Transfer Learning, Active Learning, or Low-Shot Prompting?</b><br/>Alturayeif, Hassine. "
                 "PeerJ Computer Science 11:e2730, 2025.<br/><i>Checked: could not be opened (publisher blocks "
                 f"automated access). Every detail in this row is {U}.</i>",
        "does": [f"{U} Trains models to label a code snippet as leaky or not (as described in the original table).",
                 f"{U} 1,904 snippets; F2 = 0.72 with active learning."],
        "limits": [f"{U} Works on separate snippets, not whole notebooks.",
                   f"{U} Says \"leaky or not\" without pointing to a line.",
                   "A different kind of work from ours: a trained classifier, not an analysis of how data flows."],
        "ours": [f"{N} No head-to-head result: no public code was found to run.",
                 f"{B} Analyses whole scripts and notebooks and reports the line.",
                 f"{M} On our held-out benchmark: no false alarm, 65 of 73 leaks found (first look).",
                 f"{N} \"90% precision or better\": true only on our own generated files. No real notebook has been "
                 "labelled, so there is no precision figure for real code."],
    },
    {
        "paper": "<b>scicode-lint</b><br/>Samsonau. arXiv:2603.17893, 2026.<br/><i>Checked: arXiv full text "
                 "read.</i>",
        "does": ["66 patterns for scientific Python; a small local LLM checks each pattern.",
                 "On Yang et al.'s human-labelled Kaggle notebooks: preprocessing leakage 65% precision at 100% "
                 "recall; multi-test 80% precision at 18% recall.",
                 "Has an overlap pattern for sliding windows (stride smaller than the window)."],
        "limits": ["\"Overlap leakage remains undetected\" on those notebooks (the paper gives no 0.0% figure).",
                   "24% precision for all \"critical\" findings on research code, judged by an LLM (not only "
                   "leakage).",
                   "11% precision for its AI-training patterns on held-out papers, judged by an LLM.",
                   "Needs \"a workstation GPU with 20GB+ VRAM\".",
                   "No measurement of how much a leak changes the score."],
        "ours": [f"{N} No head-to-head result: it needs a GPU, which this project's rules reserve for another "
                 "project. Its numbers above are on real, human-labelled notebooks; ours are on generated files.",
                 f"{B} Runs on a laptop CPU with no LLM.",
                 f"{M} Overlap on our held-out files: 7 of 9 from code, 9 of 9 with the run. Not the same data as "
                 "theirs.",
                 f"{B} Group leakage, which it has no pattern for.",
                 f"{N} Sliding-window overlap: scicode-lint has a pattern for it; LeakLens does not yet."],
    },
]

CLAIMS = [
    ("Detects six leak types, including group and temporal", "True", "Rules and tests for all six; TEST first look "
     "finds leaks of every type. scicode-lint also covers part of temporal, so do not say \"only we do\"."),
    ("Hybrid: static analysis plus an instrumented run that hashes rows and tracks entity ids", "True",
     "Built and tested; on TEST the run added the 2 duplicate-row leaks. It named the patient id correctly only in "
     "the second look, after a fix."),
    ("Reports the score drop after an automatic fix", "Partly", "Works for six kinds of fix: 34 of 70 located TEST "
     "leaks. None for multi-test, resampling, pandas statistics, forward-looking features."),
    ("Example \"AUPRC 0.95 to 0.43\"", "Not true for LeakLens", "That is the CalibraEEG measurement. LeakLens found "
     "nothing on the CalibraEEG code. Remove it."),
    ("Command-line tool", "True", "leaklens scan, with JSON and SARIF output."),
    ("Pre-commit hook", "True since 13 November", "Built today; a real pre-commit run failed a leaky file and passed "
     "a clean one."),
    ("GitHub Action / CI gating", "True since 13 November", "Built today; ran on GitHub and uploaded 8 findings to "
     "code scanning."),
    ("No Docker needed, unlike LeakageDetector 2.0", "Not an advantage", "LeakageDetector 2.0 no longer needs Docker "
     "either (its paper)."),
    ("Catches sliding-window leaks", "Not shown", "Missed on CalibraEEG; scicode-lint has a pattern for this and "
     "LeakLens does not."),
    ("Deterministic, no LLM, no GPU, no per-use cost", "True", "By design; tests check the output is identical on "
     "repeat runs."),
    ("Analyses whole notebooks and points at the line", "True", "The frozen scoring rule requires the right line; "
     "TEST results are under that rule."),
    ("At least 90% precision", "Only on our own files", "No false positive on DEV or TEST of the injected benchmark. "
     "No figure exists for real notebooks: none is labelled."),
    ("Reliable overlap detection", "On our own files", "7 of 9 from code, 9 of 9 with the run. Synthetic copies made "
     "by SMOTE cannot be confirmed at run time."),
    ("Better than these four papers", "Not shown", "None of the four was run against LeakLens. One measured "
     "comparison exists: Yang et al., the engine inside LeakageDetector 2.0, on our own files."),
]

NAVY = colors.HexColor("#14213D")
HEAD = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white)
CELL = ParagraphStyle("cell", fontName="Helvetica", fontSize=7.4, leading=9.4)
BUL = ParagraphStyle("bul", parent=CELL, leftIndent=7, bulletIndent=0, spaceAfter=2)
H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=18, spaceAfter=2)
SUB = ParagraphStyle("sub", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#5A6470"),
                     spaceAfter=6)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=8.6, leading=11.4, spaceAfter=4)


def cell(items: list[str]) -> list[Paragraph]:
    return [Paragraph(t, BUL, bulletText="•") for t in items]


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#5A6470"))
    canvas.drawString(15 * mm, 9 * mm, "LeakLens: comparison table, checked against evidence on 13 November 2026")
    canvas.drawRightString(landscape(A4)[0] - 15 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def grid(data: list[list], widths: list[float], tints: dict[int, str]) -> Table:
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C2CC")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4),
          ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    for col, colour in tints.items():
        st.append(("BACKGROUND", (col, 1), (col, -1), colors.HexColor(colour)))
    t.setStyle(TableStyle(st))
    return t


story = [
    Paragraph("Comparison of related research papers with LeakLens: checked version", H1),
    Paragraph("Software Engineering Minor Project. Replaces the earlier \"Comparative Literature Review Matrix\". "
              "Other papers: what we could read ourselves on 13 November 2026. LeakLens: only what a logged run or a "
              "test shows.", SUB),
    Paragraph(f"{M} = a number from a logged run in the repository. &nbsp; {B} = the feature exists and is tested; "
              f"it is a difference in what the tools do, not proof of better accuracy. &nbsp; {N} = the earlier "
              f"table claimed it, and it is not true or not demonstrated yet. &nbsp; {U} = we could not open the "
              "paper to confirm this detail.", BODY),
    Paragraph("<b>The one measured comparison is with Yang et al. (ASE 2022)</b>, which is the detection engine "
              "inside LeakageDetector 2.0. None of the other three tools could be run: one needs a paid LLM "
              "service, one has no public code that we found, one needs a GPU.", BODY),
]
data = [[Paragraph(h, HEAD) for h in ("1. Research paper", "2. What the paper does", "3. Limits (as far as we "
                                      "could check)", "4. How LeakLens compares, and what backs it")]]
for r in ROWS:
    data.append([Paragraph(r["paper"], CELL), cell(r["does"]), cell(r["limits"]), cell(r["ours"])])
story += [grid(data, [42, 62, 68, 95], {1: "#F7F9FC", 2: "#FFF8F7", 3: "#F3FAF2"}), PageBreak(),
          Paragraph("Check of each claim the earlier table made about LeakLens", H1),
          Paragraph("\"True\" means it can be shown from the repository today. Evidence: results/ and tests/ in "
                    "github.com/bytes06runner/LeakLens.", SUB)]
cdata = [[Paragraph(h, HEAD) for h in ("Claim in the earlier table", "Status", "What the evidence says")]]
for claim, status, why in CLAIMS:
    colour = "#1B7F3B" if status.startswith("True") else "#B3261E" if status.startswith("Not") else "#8A6D00"
    cdata.append([Paragraph(claim, CELL), Paragraph(f"<font color='{colour}'><b>{status}</b></font>", CELL),
                  Paragraph(why, CELL)])
story += [grid(cdata, [88, 34, 145], {}), Spacer(1, 6),
          Paragraph("<b>What can be said to the supervisor.</b> LeakLens does things the four papers do not describe: "
                    "it looks for group leakage, it checks the data by running the code, and it measures the score "
                    "change for a located leak. On our own held-out benchmark it found at least as many leaks of "
                    "every shared kind as the Yang et al. engine, with no false alarm. It has not been compared "
                    "head-to-head with these four tools, and it has no accuracy figure on real notebooks yet.", BODY)]

OUT.parent.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(str(OUT), pagesize=landscape(A4), leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm,
                  bottomMargin=15 * mm, title="LeakLens comparison table, checked version",
                  author="Srijeet Prasad Banerjee").build(story, onFirstPage=footer, onLaterPages=footer)

md = ["# Check of the four-paper comparison table (2026-11-13)", "",
      "Source of this file and of `docs/report/LeakLens_Comparative_Table_Verified.pdf`: "
      "`scripts/make_comparison_table.py`.", "",
      "## Claims the earlier table made about LeakLens", "", "| Claim | Status | Evidence |", "|---|---|---|"]
md += [f"| {c} | **{s}** | {w} |" for c, s, w in CLAIMS]
md += ["", "## What could be verified about the four papers", "",
       "| Paper | How it was checked | Corrections to the earlier table |", "|---|---|---|",
       "| LeakageDetector 2.0 (arXiv:2509.15971) | arXiv full text read | Docker is optional, so \"heavy Docker\" is "
       "wrong. The paper does not say the placeholder fix needs manual rewriting. It reports no accuracy of its own. |",
       "| Draoui et al. (FSE 2026) | abstract only; ACM page returns 403 | 451 notebooks, GPT-4o-mini, 14.3 s and the "
       "duplicate-records statement are unconfirmed. |",
       "| Alturayeif and Hassine (PeerJ CS 2025) | not opened; PeerJ returns 403 | Nothing confirmed, including title "
       "and numbers. Not in `literature/related_work.csv` before today. |",
       "| scicode-lint (arXiv:2603.17893) | arXiv full text read | 24% is for all critical findings, LLM-judged. 11% "
       "is its ai-training category on held-out papers. The paper says overlap \"remains undetected\" but gives no "
       "0.0% figure. 20GB+ VRAM is correct (our earlier note of 16 GB was wrong). The earlier table left out its "
       "65% precision at 100% recall for preprocessing on Yang et al.'s human-labelled notebooks, and its "
       "sliding-window overlap pattern. |",
       "", "## Which of the four could be run against LeakLens", "",
       "| Tool | Run? | Why |", "|---|---|---|",
       "| LeakageDetector 2.0 | engine only | A VS Code extension around the Yang et al. analyser, which was run on "
       "TEST (`results/2026-11-12_kaggle_05_yang_test_injected`). |",
       "| Draoui et al. | no | Needs a paid LLM key and an access-restricted package. Owner decision. |",
       "| Alturayeif and Hassine | no | No public code found. |",
       "| scicode-lint | no | Needs a 20 GB GPU; CLAUDE.md reserves the GPU quota for CalibraEEG. Owner decision. |"]
MD.write_text("\n".join(md) + "\n")
print(f"wrote {OUT} and {MD}")
