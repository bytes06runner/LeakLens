# Yang et al. (ASE 2022) and LeakLens on the same files, scored per file and type

Split: **DEV** of the injected benchmark, 96 files. Yang analyser at commit `a7d038bf`, default command, Souffle route: built from source, tag 2.4.1 (fallback). LeakLens: static mode, findings of confidence medium or higher, run `2026-11-12_dev_injected_leaklens_v2`.

A tool is right about a type in a file when it reports that type and the file has a labelled leak that accepts it; the hit counts for that label's primary type. This is looser than the protocol's line-overlap rule and is used here only because the Yang analyser reports the evaluation line, not the leaking line (EVAL_CHANGES.md #6).

**DEV: LeakLens's rules were written on these files; the Yang analyser has never seen them. This table is not a fair accuracy comparison. It shows which types each tool covers and that the baseline runs.**

## Yang et al. (notebooks converted to .py first, as its README requires)

Files analysed: 96 of 96. Leak-free files with a finding: 0 of 10.

| type | files with this leak | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|
| preprocessing | 30 | 7 | 1 | 23 | 0.88 | 0.23 |
| overlap | 10 | 6 | 0 | 4 | 1.00 | 0.60 |
| multi_test | 8 | 3 | 0 | 5 | 1.00 | 0.38 |
| group (not a type it claims) | 10 | 0 | 0 | 10 | n/a | 0.00 |
| temporal (not a type it claims) | 24 | 3 | 0 | 21 | n/a | 0.12 |
| target_derived (not a type it claims) | 6 | 0 | 0 | 6 | n/a | 0.00 |

## LeakLens, static

Files analysed: 96 of 96. Leak-free files with a finding: 0 of 10.

| type | files with this leak | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|
| preprocessing | 30 | 30 | 0 | 0 | 1.00 | 1.00 |
| overlap | 10 | 8 | 0 | 2 | 1.00 | 0.80 |
| multi_test | 8 | 8 | 0 | 0 | 1.00 | 1.00 |
| group | 10 | 3 | 0 | 7 | 1.00 | 0.30 |
| temporal | 24 | 24 | 0 | 0 | 1.00 | 1.00 |
| target_derived | 6 | 6 | 0 | 0 | 1.00 | 1.00 |

Given the 43 notebook files directly (.ipynb), the Yang analyser exits without a report; its README says notebooks must be converted first. The conversion used here is this benchmark's own plain-script rendering of each notebook (`_groundtruth/leaky_py`).

Yang analyser time per file: median 7.3 s, mean 7.4 s (Kaggle CPU). LeakLens static time is in the run's REPORT.md (laptop); the machines differ.
