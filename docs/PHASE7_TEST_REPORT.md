# Phase 7 report (first part): injected TEST, scored once

Date: 2026-11-12. The evaluation protocol was frozen at commit `0dcd2fe` after your approval ("Approve, score
TEST"). LeakLens was then run on TEST **once**, at that commit. Run folder:
`results/2026-11-12_test_injected_leaklens_v1` (`REPORT.md`, `IMPACT_REPORT.md`, `findings.jsonl`).

Not done in Phase 7 yet: real notebooks (no labels), the other baselines, ablation write-up, the mining study.

## 1. Detection

Tool: **LeakLens**. Split: **TEST**, injected set: 79 files from 6 base pipelines not used for development, 73
labelled leaks, 9 files with no leak. Findings of confidence medium or higher; frozen matching rule (type and
overlapping lines in the same cell). 95% bootstrap intervals over files.

| type | leaks | static: found | static: recall (95% CI) | static+dynamic: found | static+dynamic: recall (95% CI) | false positives |
|---|---|---|---|---|---|---|
| preprocessing | 22 | 21 | 0.95 (0.84 to 1.00) | 21 | 0.95 (0.84 to 1.00) | 0 |
| overlap | 9 | 7 | 0.78 (0.44 to 1.00) | 9 | 1.00 (1.00 to 1.00) | 0 |
| multi_test | 6 | 5 | 0.83 (0.43 to 1.00) | 5 | 0.83 (0.43 to 1.00) | 0 |
| group | 7 | 3 | 0.43 (0.00 to 0.83) | 7 (3 with the right column) | 1.00 by the rule; 0.43 strictly | 0 |
| temporal | 25 | 20 | 0.80 (0.62 to 0.95) | 20 | 0.80 (0.62 to 0.95) | 0 |
| target_derived | 4 | 3 | 0.75 (0.00 to 1.00) | 3 | 0.75 (0.00 to 1.00) | 0 |
| **all** | 73 | 59 | 0.81 | 65 | 0.89 | 0 |

- Precision 1.00 for every type (no false positive; nothing reported on the 9 leak-free files). The files are
  synthetic and short; this will not hold on real code.
- With low-confidence findings included: temporal 25 of 25; everything else unchanged except static group, which
  becomes 7 of 7 for the wrong reason (next section).
- Temporal by category (with the run): common 5 of 5, differentiating 7 of 7, hard 8 of 13.
- The run confirmed 43 static findings, refuted 0, could not check 25, and made 2 findings of its own (duplicated
  records). Static time: median 2.6 ms per file; instrumented run: median 1.3 s.
- DEV for comparison: 80 of 89 static, 89 of 89 with the run. The drop from DEV to TEST is real.

## 2. What went wrong on TEST

1. **Group: right line, wrong column, 4 of 7.** In the patient-visits pipeline the static pass made a
   low-confidence guess on a column named `visit`. At run time the confirmation step looked only at the columns
   the static pass had nominated, found that visit numbers occur on both sides of the split (they always do) and
   raised the finding to medium. It never examined `patient_id`, the true entity, and because a group finding
   already existed on that line the run-time search for other entity columns was skipped. The frozen matching
   rule does not look at the column, so the table says 7 of 7; **only 3 of 7 name the true entity**
   (protocol section 6). The 3 are the file-path case (`subject` from file names), found from the code alone.
2. **A positional slice mistaken for a split.** One pipeline drops its last row with `data.iloc[:-1]`. The
   analyser treats `x[:n]` as the training side of a manual split, so everything after it looked like "training
   rows only": five whole-series scaling leaks were reported at low confidence and one multi-test leak not at all.
3. **An unresolved column filter.** Another pipeline builds its feature list with
   `[c for c in df.columns if c.startswith(("f", "n"))]`. The analyser cannot resolve that, so it does not know
   which columns are features and reports nothing: one target-encoding leak and one target-derived feature missed.

None of the three has been fixed. Fixing them is easy; re-running TEST afterwards would be a second look
(`EVAL_CHANGES.md` #7). **Your decision.**

## 3. Impact estimation on TEST (five data seeds)

- The instrumented script printed exactly the plain script's metric in all 395 runs.
- Coverage: an estimate for 34 of 70 located leaks (group 7 of 7, target-derived 3 of 3, overlap 7 of 9,
  preprocessing 10 of 21, temporal 7 of 25, multi-test 0 of 5). The rest: "impact unknown" with the reason.
- Accuracy, single-leak files, seed-averaged, bounded metrics: 26 findings, mean absolute error 0.035, Spearman
  0.58 (DEV, one seed: 0.027 and 0.96).
- Exact (error 0.000) for overlap, temporal splits and target-derived features, where our fix is the same
  operation as the benchmark's own correct version.
- **Wrong for hold-out group splits:** estimate -0.084 against a true inflation of +0.212 AUC (wrong direction),
  because the fix grouped by `visit` (fault 1). Group impact under cross-validation: error 0.005.
- Preprocessing: true inflation about 0.000 on TEST, estimate 0.000; the direction of a number that small is noise.

## 4. Baseline: Yang et al. (ASE 2022)

The apt package of its Datalog engine (Souffle) no longer installs on Kaggle's image (`libffi7` is gone), so the
job builds Souffle 2.4.1 from source; that is a deviation from the released Dockerfile and is recorded in the
result file. The tool takes Python files only (its README), so notebooks were given to it as plain scripts.

It reports the affected evaluation line, not the leaking line, so the protocol's line rule cannot be applied.
Both tools are scored per file and type instead (`EVAL_CHANGES.md` #6).

Run: `results/2026-11-12_kaggle_05_yang_test_injected` (Kaggle CPU, benchmark files at commit `0dcd2fe`).
Split: **TEST**, 79 files. LeakLens in static mode, medium confidence or higher, like the baseline (no run).

| Leakage type | Files with this leak | Yang et al.: files found | Yang: false alarms | LeakLens (static): files found | LeakLens: false alarms |
|---|---|---|---|---|---|
| Preprocessing | 22 | 10 | 1 | 21 | 0 |
| Overlap / duplicates | 9 | 7 | 0 | 7 | 0 |
| Multi-test | 6 | 3 | 0 | 5 | 0 |
| Group (entity) | 7 | 0 (not a type it claims) | 0 | 3 | 0 |
| Temporal | 24 | 3 (not a type it claims) | 0 | 19 | 0 |
| Target-derived | 4 | 0 (not a type it claims) | 0 | 3 | 0 |

Both tools: no finding on the 9 leak-free files; all 79 files analysed. Yang analyser: median 6.2 s per file on
Kaggle; LeakLens static: median 2.6 ms on the laptop (different machines). The Yang analyser gets credit under
`temporal` in 3 files where it reports whole-series scaling as preprocessing leakage.

Neither tool was tuned on these files. They are still files generated by this project, with the kinds of
leak LeakLens was built for, in a style that may differ from the notebooks the Yang analyser was designed on,
so the comparison favours LeakLens. The numbers its authors report on their own data (precision 97.6%, recall
67.8%) are a different measurement and cannot be compared with this table. Temporal has 24 files, not 25
leaks, because one file holds two temporal leaks.

The same comparison on DEV (not fair: LeakLens was tuned there) is in
`results/2026-11-12_kaggle_04_yang_dev_injected_attempt2/YANG_VS_LEAKLENS.md`.

## 5. Chapter 1 target (O4)

"Precision of at least 0.90 and recall above 67.8% on shared types": on injected TEST, static mode, precision is
1.00 and recall is 0.95 (preprocessing), 0.78 (overlap), 0.83 (multi-test). The point estimates are above the
target; the intervals are wide (overlap 0.44 to 1.00, multi-test 0.43 to 1.00), the files are our own, and the
67.8% figure was measured by its authors on other data. **Met on our injected benchmark only. Not shown on real
notebooks.**

## 6. What I need from you

1. **Second look at TEST, yes or no.** If yes: I fix the three faults, log them, re-run TEST once more and report
   both results side by side, first look first.
2. **Labellers for the real notebooks.** Still the only route to a real-world result.
3. **The project name** (PyPI clash).
4. Wording of C1/C2/C3 (see `docs/PHASE3_6_REPORT.md` section 6).
