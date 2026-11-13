| status | section | claim | paper | measured | source |
|---|---|---|---|---|---|
| PASS | 5.1 | files | 175 | 175 | benchmark/injected/manifest.csv, _groundtruth/labels.csv |
| PASS | 5.1 | scripts / notebooks | 94 / 81 | 94 / 81 | benchmark/injected/manifest.csv, _groundtruth/labels.csv |
| PASS | 5.1 | labelled leaks | 162 | 162 | benchmark/injected/manifest.csv, _groundtruth/labels.csv |
| PASS | 5.1 | clean files | 13 | 13 | benchmark/injected/manifest.csv, _groundtruth/labels.csv |
| PASS | 5.1 | traps | 6 | 6 | benchmark/injected/manifest.csv, _groundtruth/labels.csv |
| PASS | 5.1 | files with two leaks | 6 | 6 | benchmark/injected/manifest.csv, _groundtruth/labels.csv |
| PASS | 5.1 | base pipelines | 13 | 13 | benchmark/injected/manifest.csv, _groundtruth/labels.csv |
| PASS | 5.1 | operators (leak + trap) | 18 (17 + 1) | 18 (17 + 1) | benchmark/injected/operators.py |
| PASS | 5.1 | DEV: pipelines / files / leaks | 7 / 96 / 89 | 7 / 96 / 89 | benchmark/injected/manifest.csv, _groundtruth/labels.csv |
| PASS | 5.1 | TEST: pipelines / files / leaks | 6 / 79 / 73 | 6 / 79 / 73 | benchmark/injected/manifest.csv, _groundtruth/labels.csv |
| PASS | 5.1/6.1 | TEST temporal leaks: common / differentiating / hard | 5 / 7 / 13 | 5 / 7 / 13 | benchmark/injected/manifest.csv, _groundtruth/labels.csv |
| PASS | 6.1 | TEST files without a leak | 9 | 9 | benchmark/injected/manifest.csv, _groundtruth/labels.csv |
| PASS | Table 3 | preprocessing: leaks | 22 | 22 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | preprocessing: static found | 21 | 21 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | preprocessing: static recall 95% CI | (0.84, 1.0) | (0.84, 1.0) | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | preprocessing: static+run found | 21 | 21 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | overlap: leaks | 9 | 9 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | overlap: static found | 7 | 7 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | overlap: static recall 95% CI | (0.44, 1.0) | (0.44, 1.0) | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | overlap: static+run found | 9 | 9 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | multi_test: leaks | 6 | 6 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | multi_test: static found | 5 | 5 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | multi_test: static recall 95% CI | (0.43, 1.0) | (0.43, 1.0) | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | multi_test: static+run found | 5 | 5 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | group: leaks | 7 | 7 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | group: static found | 3 | 3 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | group: static recall 95% CI | (0.0, 0.83) | (0.0, 0.83) | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | group: static+run found | 7 | 7 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | temporal: leaks | 25 | 25 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | temporal: static found | 20 | 20 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | temporal: static recall 95% CI | (0.62, 0.95) | (0.62, 0.95) | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | temporal: static+run found | 20 | 20 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | target_derived: leaks | 4 | 4 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | target_derived: static found | 3 | 3 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | target_derived: static recall 95% CI | (0.0, 1.0) | (0.0, 1.0) | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | target_derived: static+run found | 3 | 3 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | all: static / static+run found | 59 / 65 | 59 / 65 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | Table 3 | false positives, both modes | 0 | 0 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | 6.1 | run: confirmed / refuted / not checked / own findings | 43 / 0 / 25 / 2 | 43 / 0 / 25 / 2 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | 6.6 | static median per file (ms) | 2.6 | 2.6 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | 6.6 | run median / max (s) | 1.3 / 12.7 | 1.3 / 12.7 | results/2026-11-12_test_injected_leaklens_v1/summary.json |
| PASS | 6.1 | temporal found by category (common / differentiating / hard) | 5/5, 7/7, 8/13 | 5/5, 7/7, 8/13 | results/2026-11-12_test_injected_leaklens_v1/REPORT.md |
| PASS | Table 3 note | group findings (combined) naming the true entity column | 3 of 7 | 3 of 7 | results/2026-11-12_test_injected_leaklens_v1/findings.jsonl (message text) |
| PASS | 6.1 | DEV static / static+run found (2026-11-12_dev_injected_leaklens_v2) | 80 / 89 | 80 / 89 | results/2026-11-12_dev_injected_leaklens_v2/summary.json |
| PASS | 6.1 | DEV static / static+run found (2026-11-12_dev_injected_leaklens_v3) | 80 / 89 | 80 / 89 | results/2026-11-12_dev_injected_leaklens_v3/summary.json |
| PASS | 6.3 | second look: static / static+run found | 67 / 73 | 67 / 73 | results/2026-11-13_test_injected_leaklens_v2_second_look/summary.json |
| PASS | 6.3 | second look: false positives | 0 | 0 | results/2026-11-13_test_injected_leaklens_v2_second_look/summary.json |
| PASS | 6.5 | estimate produced / located leaks | 34 / 70 | 34 / 70 | results/2026-11-12_test_injected_leaklens_v1/impact_summary.json |
| PASS | 6.5 | impact coverage group | 7/7 | 7/7 | results/2026-11-12_test_injected_leaklens_v1/impact_summary.json |
| PASS | 6.5 | impact coverage target_derived | 3/3 | 3/3 | results/2026-11-12_test_injected_leaklens_v1/impact_summary.json |
| PASS | 6.5 | impact coverage overlap | 7/9 | 7/9 | results/2026-11-12_test_injected_leaklens_v1/impact_summary.json |
| PASS | 6.5 | impact coverage preprocessing | 10/21 | 10/21 | results/2026-11-12_test_injected_leaklens_v1/impact_summary.json |
| PASS | 6.5 | impact coverage temporal | 7/25 | 7/25 | results/2026-11-12_test_injected_leaklens_v1/impact_summary.json |
| PASS | 6.5 | impact coverage multi_test | 0/5 | 0/5 | results/2026-11-12_test_injected_leaklens_v1/impact_summary.json |
| PASS | 6.5 | single-leak bounded findings / MAE / Spearman | 26 / 0.035 / 0.58 | 26 / 0.035 / 0.58 | results/2026-11-12_test_injected_leaklens_v1/impact_summary.json |
| PASS | 6.5 | hold-out group: estimate vs true | -0.084 / +0.212 | -0.084 / +0.212 | results/2026-11-12_test_injected_leaklens_v1/impact_summary.json |
| PASS | 6.5 | runs (files x seeds) in which metrics were compared | 395 | 395 | results/2026-11-12_test_injected_leaklens_v1/findings.jsonl (one line per file and seed) |
| PASS | 6.5 | second look MAE / Spearman | 0.0006 / 0.97 | 0.0006 / 0.97 | results/2026-11-13_test_injected_leaklens_v2_second_look |
| PASS | Table 4 | preprocessing: files / Yang found / Yang false | 22 / 10 / 1 | 22 / 10 / 1 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | Table 4 | preprocessing: LeakLens found / false | 21 / 0 | 21 / 0 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | Table 4 | overlap: files / Yang found / Yang false | 9 / 7 / 0 | 9 / 7 / 0 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | Table 4 | overlap: LeakLens found / false | 7 / 0 | 7 / 0 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | Table 4 | multi_test: files / Yang found / Yang false | 6 / 3 / 0 | 6 / 3 / 0 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | Table 4 | multi_test: LeakLens found / false | 5 / 0 | 5 / 0 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | Table 4 | group: files / Yang found / Yang false | 7 / 0 / 0 | 7 / 0 / 0 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | Table 4 | group: LeakLens found / false | 3 / 0 | 3 / 0 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | Table 4 | temporal: files / Yang found / Yang false | 24 / 3 / 0 | 24 / 3 / 0 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | Table 4 | temporal: LeakLens found / false | 19 / 0 | 19 / 0 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | Table 4 | target_derived: files / Yang found / Yang false | 4 / 0 / 0 | 4 / 0 / 0 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | Table 4 | target_derived: LeakLens found / false | 3 / 0 | 3 / 0 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | 6.4 | shared types: Yang / LeakLens found of 37 | 20 / 33 | 20 / 33 | results/2026-11-12_kaggle_05_yang_test_injected/file_level.csv |
| PASS | 6.6 | Yang: files analysed (rc 0) / median s per file | 79 / 6.2 | 79 / 6.2 | results/2026-11-12_kaggle_05_yang_test_injected/yang_test_results.json |
| PASS | 5.2 | real notebooks DEV / TEST | 71 / 79 | 71 / 79 | benchmark/real/manifest.csv |
| PASS | 5.2 | real DEV: notebooks / crashes / median ms | 71 / 0 / 4 | 71 / 0 / 4 | results/2026-11-12_real_dev_static_unlabelled/aggregates.json |
| PASS | 6.7 | case study: files / findings | 78 / 0 | 78 / 0 | results/2026-11-12_calibraeeg_static/report.json |
| PASS | 4.4 | sandbox: ancestors with token, dropped / root control | 0 / 2 | 0 / 2 | results/2026-09-29_kaggle_01_sandbox_check_v2/sandbox_check.json |
| FAIL | 4.5 | test suite (paper says '371 passing tests') | 371 passed, 0 skipped | 369 passed, 2 skipped | pytest run now (laptop; 2 tests need root and run only in the Kaggle sandbox job) |
| PASS (source read) | 1-2 | Kapoor & Narayanan: papers / fields | 294 / 17 | 294 / 17 | literature/related_work.csv (verified) |
| PASS (source read) | 1-2 | Yang et al.: notebooks / share with leak | 107,603 / 29.6% | 107,603 / 29.6% | literature/related_work.csv (verified) |
| PASS (source read) | 1-2 | Yang et al.: precision / recall | 97.6% (40/41) / 67.8% (40/59) | 97.6% (40/41) / 67.8% (40/59) | literature/related_work.csv (verified) |
| PASS (source read) | 1-2 | Yang et al.: mean time | 3.23 s | 3.23 s | literature/related_work.csv (verified) |
| PASS (source read) | 1-2 | Roth: max /dAUC/ for scaler leak, conditions | 0.005, nine | 0.005, nine | literature/related_work.csv (verified) |
| PASS (source read) | 1-2 | Brookshire: studies avoiding leak / accuracy drop | 17 of 63 / 99.8% -> 53.0% | 17 of 63 / 99.8% -> 53.0% | literature/related_work.csv (verified) |
| PASS (source read) | 1-2 | Draoui et al.: F1 gains (abstract) | 22% / 15% | 22% / 15% | literature/related_work.csv (verified) |
