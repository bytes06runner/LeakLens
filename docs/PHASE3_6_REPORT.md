# Report for Phases 3 to 6 (and first steps of 7)

Date: 2026-11-12. Status: **static analyser, dynamic pass and impact estimation built and measured on DEV.
Stopped before TEST: the evaluation protocol needs your approval.**

*Update, same day: you approved the protocol; TEST was scored once and the Yang et al. baseline was run. See
[`PHASE7_TEST_REPORT.md`](PHASE7_TEST_REPORT.md). The text below is the report as written before TEST.*

You asked for the phases to be implemented in one session. I did not stop for a "go" between Phases 4, 5 and 6,
but I did stop at the one gate that cannot be undone: scoring TEST. Nothing has touched TEST.

## 1. What was done

| Phase | Done | Where |
|---|---|---|
| 3 | Evaluation protocol written as a **proposal** (not frozen) and a one-page summary for you | `EVAL_PROTOCOL.md`, `docs/EVAL_PROTOCOL_SUMMARY.md` |
| 3 | One scoring module for every tool: matching rule, per-type precision/recall, bootstrap CIs | `src/leaklens/evaluation/scoring.py` |
| 4 | Ingest of `.py` and `.ipynb` (execution order when available, magics, skipped cells reported) | `src/leaklens/ingest/` |
| 4 | Static analyser, rules for all six types, thresholds and catalogues in YAML | `src/leaklens/static/`, `configs/static.yaml` |
| 5 | Instrumented run: splits, fits, evaluations, metrics; confirm / refute; findings only the run can make | `src/leaklens/dynamic/`, `configs/dynamic.yaml` |
| 6 | Impact by re-running the script with one call site changed; six fix kinds | `src/leaklens/dynamic/confirm.py`, `runner.py` |
| 9 (part) | `leaklens scan` with terminal, JSON and SARIF output, exit codes, inline suppression | `src/leaklens/cli.py`, `src/leaklens/report/` |
| 7 (part) | CalibraEEG case study, static mode | section 4 |
| Rule 1 | Novelty search repeated | `docs/NOVELTY_LOG.md` |

359 tests pass (2 skipped, both pre-existing): positive and negative cases for every rule, the taxonomy examples,
`hypothesis` properties (the analyser is total and deterministic), the dynamic pass and each fix on small
synthetic scripts, the scoring rule, the CLI contract. `ruff` is clean. One repair on the way: `ruff` had been
excluding `src/leaklens` entirely (an old exclude pattern), so the package was never linted before today.

## 2. Key numbers

All on **DEV, injected set** (96 files, 89 leaks, 10 files with no leak), tool **LeakLens**, run
`results/2026-11-12_dev_injected_leaklens_v2`, findings of confidence medium or higher. DEV is the tuning split.

| type | leaks | static: found (recall, 95% CI) | static+dynamic: found | false positives |
|---|---|---|---|---|
| preprocessing | 30 | 30 (1.00, 1.00 to 1.00) | 30 | 0 |
| overlap | 10 | 8 (0.80, 0.50 to 1.00) | 10 | 0 |
| multi_test | 8 | 8 (1.00, 1.00 to 1.00) | 8 | 0 |
| group | 10 | 3 (0.30, 0.00 to 0.62) | 10 | 0 |
| temporal | 25 | 25 (1.00, 1.00 to 1.00) | 25 | 0 |
| target_derived | 6 | 6 (1.00, 1.00 to 1.00) | 6 | 0 |

- Precision is 1.00 for every type on DEV (no false positive, no finding on the 10 leak-free files). With the
  low-confidence findings included the table is the same.
- What the run did to static findings: 45 confirmed, 0 refuted, 35 not checked (no run-time check exists for
  pandas statistics and forward-looking features); 9 findings made only by the run (7 group, 2 duplicate rows).
- Static time: median 1.7 ms per file. Instrumented run: median 3.4 s per file, max about 5 minutes for the
  gradient-boosting pipelines when four ran at once on the laptop.
- The instrumented run printed the same metric as the plain run in all 96 files.
- Impact (`IMPACT_REPORT.md` in the run folder): an estimate for 41 of 89 found leaks (group 10/10,
  target-derived 6/6, overlap 8/10, temporal 10/25, preprocessing 7/30, multi-test 0/8). On the 35 single-leak
  estimates with a bounded metric: mean absolute error 0.027, Spearman 0.96 against true inflation (seed 0).
- Real DEV notebooks (71, unlabelled, static only, nothing executed): 0 crashes, 7 with skipped cells, median
  4 ms. Medium-or-higher findings in 19 notebooks for preprocessing, 10 multi-test, 3 overlap, 3 group,
  3 temporal, 1 target-derived. **Not a result**: no labels.

## 3. Surprises

1. **A package named `leaklens` already exists on PyPI** (another author, first release 2026-06-30, data-level
   checks plus an AST check for preprocessing before `train_test_split`). It does not cover C1 or C3, but the
   name, the command and the PyPI slot are taken. The earlier searches never checked the project's own name.
2. **Leakly** (2026) re-runs a user's pipeline on shuffled labels to test for leakage. Not per finding, no fix,
   but C3 must be worded as *per-finding* impact and Leakly cited.
3. **DEV is saturated.** 89 of 89 with no false positive means DEV can no longer tell a better rule from a worse
   one. It says nothing about unseen code. The same author wrote the benchmark and the tool.
4. **Static-only group recall is 0.30.** The benchmark hides the entity column from the code in 7 of 10 cases.
   C1 as worded ("group leakage detected from source code") holds only when the code names the entity or derives
   it from file paths; otherwise it is the static-to-dynamic link (C2) that finds it.
5. **Impact for hold-out group splits is off by about 0.30 AUC** (3 files, `grp_sites`): right direction, wrong
   size. With 12 sites the score depends on which sites are held out; our fix holds out different ones from the
   reference version. Most other errors are exactly zero, but only because our fix is the same operation as the
   benchmark's own fixed file on the same seed, which is a weak test.
6. **The Yang et al. baseline no longer builds on Kaggle**: Souffle's apt package fails with "held broken
   packages" on the current image (it worked on 2026-09-29). First attempt analysed 0 of 96 DEV files
   (`results/2026-11-12_kaggle_04_yang_dev_injected`). A second attempt builds Souffle from source; see section 5.

## 4. CalibraEEG case study (static, `calibraeeg` commit `a062f45`)

Expected (CLAUDE.md Phase 7): temporal/overlap flagged in regime A, group in A and B, nothing in C.
Found: **0 findings in 78 files, at any confidence.** Correct for C. **Missed for A and B.**

Why: regime A draws `u = rng.random(n)` and builds train/validation/test masks by comparing `u` with fractions;
regime B cuts each subject's list of `Recording` objects by position. Subject identity is an attribute of a
custom object. No scikit-learn splitter, no data frame, no column name: nothing the analyser models. The dynamic
pass was not run (the project needs its EEG cache and a GPU-sized run), and it would not see these splits either,
because it instruments scikit-learn entry points only.

I did not change any rule after seeing this. It is reported as a miss.

## 5. Baselines

| Tool | State on 2026-11-12 |
|---|---|
| Yang et al. (ASE 2022) | Attempt 1: build failed, 0 of 96 DEV files analysed. Attempt 2 (Souffle from source): still running on Kaggle when this report was written; its outcome is recorded in `results/registry.csv` |
| scicode-lint | not run (needs a 16 GB GPU; `docs/SCICODE_TIMING.md`) |
| leakcheck-ml, LeakHound, dataleaks, Deepchecks | not run on the benchmark yet (need the materialised splits; the instrumented run can now provide them) |
| splitguard | not run yet |

Because its findings point at the evaluation line, not at the source of the leak, the Yang analyser will be scored
per file and type (does it report this type in this file), and LeakLens will be reported the same way next to it.
That rule is not in the protocol draft yet; it is listed below.

## 6. What I need from you

1. **Protocol.** Read `docs/EVAL_PROTOCOL_SUMMARY.md` (one page). Approve it or tell me what to change. After
   approval I commit "Freeze evaluation protocol" and score TEST once. Two additions I propose before freezing:
   file-level scoring for tools that do not point at the leak's source line (section 5), and impact estimates
   averaged over several group splits when the fix is a single hold-out group split.
2. **Name.** Rename the project, or keep "LeakLens" and choose another package name. Nothing is published.
3. **Labels.** Who labels the real notebooks, and how many. Without labels there is no real-world number.
4. **C1 and C3 wording** in the light of surprises 2 and 4, and the still-open C2 wording (splitguard).
5. **Preprint checkpoint** (CLAUDE.md): group detection works on the injected benchmark on DEV. I do not think
   that is a defensible result yet (DEV, same author for tool and benchmark, CalibraEEG missed). My advice is to
   wait for TEST and some labelled real notebooks. Your decision.
6. Still open from September: scicode-lint route; repository public or private.
