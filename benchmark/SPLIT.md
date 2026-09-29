# Benchmark DEV/TEST split

Integrity Rule 4: the split is fixed **before any detection rule is written**. Rules and thresholds are tuned on
DEV only; TEST is scored once per release; any later change goes in `EVAL_CHANGES.md`.

## Injected set

- **Split unit: base pipeline.** All items generated from one base are on the same side, so TEST code was never
  seen while writing rules. Per family, 2 bases were assigned to DEV and 2 to TEST by
  `benchmark/injected/make_split.py` (seed 20260929), committed in `24a42e2` before items existed.
- **Addition:** `grp_imaging` (per-patient image folders, file-path-derived entity) was added to DEV afterwards
  so that DEV has a file-path entity case; TEST was not changed (EVAL_CHANGES.md #2).
- The frozen assignment is `benchmark/injected/split.csv`. `tests/test_benchmark_injected.py` checks that every
  item and label carries its base's split, that file hashes match `manifest.csv`, and that regeneration is
  byte-identical.

### Items per split

| kind | DEV | TEST | total |
|---|---|---|---|
| clean | 7 | 6 | 13 |
| leaky | 86 | 70 | 156 |
| trap | 3 | 3 | 6 |
| total | 96 | 79 | 175 |

### Leaks per type and split

| type | DEV | TEST | total |
|---|---|---|---|
| group | 10 | 7 | 17 |
| multi_test | 8 | 6 | 14 |
| overlap | 10 | 9 | 19 |
| preprocessing | 30 | 22 | 52 |
| target_derived | 6 | 4 | 10 |
| temporal | 25 | 25 | 50 |
| total | 89 | 73 | 162 |

### Leaks per category and split

| category | DEV | TEST | total |
|---|---|---|---|
| dynamic_only | 2 | 2 | 4 |
| group | 10 | 7 | 17 |
| standard | 52 | 39 | 91 |
| temporal_common | 7 | 5 | 12 |
| temporal_differentiating | 6 | 7 | 13 |
| temporal_hard | 12 | 13 | 25 |
| total | 89 | 73 | 162 |

### Bases

| split | family | base | items |
|---|---|---|---|
| DEV | grouped | grp_imaging | 11 |
| DEV | grouped | grp_sites | 14 |
| DEV | grouped | grp_users | 13 |
| DEV | tabular | tab_churn | 12 |
| DEV | tabular | tab_fraud | 15 |
| DEV | timeseries | ts_energy | 17 |
| DEV | timeseries | ts_sensor | 14 |
| TEST | grouped | grp_eeg | 6 |
| TEST | grouped | grp_patients | 15 |
| TEST | tabular | tab_credit | 16 |
| TEST | tabular | tab_housing | 11 |
| TEST | timeseries | ts_air | 13 |
| TEST | timeseries | ts_sales | 18 |

### Formats

| format | DEV | TEST | total |
|---|---|---|---|
| ipynb | 43 | 38 | 81 |
| py | 53 | 41 | 94 |
| total | 96 | 79 | 175 |

`split.csv` sha256: `b9b8d3cf1f67cf777f968f2e45cbdf2a01ca2f643f9afe60f3fc1dbd693a1c59`

`manifest.csv` sha256: `bd5f2218f31d3872e8c9b685f6d68fd4c5f941ee5fa749ff19cc453b4fbad1c6`

`_groundtruth/labels.csv` sha256: `1e08e05ee17790351cf473c8111716fdf909b8a6cdc7ea74d82946d1d128a2f2`

**Caveats.** TEST has few leaks for some types (target_derived 4, multi_test 6, group 7), so per-type CIs on TEST
will be wide. Items of one base are correlated; the protocol (Phase 3) will resample bases as a sensitivity
check. True inflation on this set is by construction (CLAUDE.md Rule 12).

## Real set

Sampled 2026-09-29 by `benchmark/real/sample_kaggle.py` (config `benchmark/real/sampling.yaml`, seed 20260930),
**before any labels and before any detection rule**. Nothing was executed.

- Source: Kaggle notebooks found by 16 search queries in three strata (grouped / timeseries / tabular), each in
  three listing orders, two pages of 100. Pools: 2,594 / 2,066 / 2,157 unique candidates. Each stratum's pool was
  shuffled and walked until 50 notebooks passed the source filters (Python notebook, scikit-learn import, a fit
  call, a metric; 5 to 120 code cells). All 98 rejections are recorded with their reason in
  `benchmark/real/pool.csv` (44 no scikit-learn import, 17 cell count, 16 no fit, 12 no metric, 9 not a notebook).
- **Strata are query-based, not verified data types**: e.g. the "grouped" stratum contains some churn and EDA
  notebooks. Whether a notebook really has repeated entities or dates is decided by the labellers (Q4, Q5).
- **Split unit: author**, seeded 50/50 over the 139 authors: DEV 71 notebooks (69 authors), TEST 79 (70 authors).

| stratum | DEV | TEST | total |
|---|---|---|---|
| grouped | 26 | 24 | 50 |
| tabular | 22 | 28 | 50 |
| timeseries | 23 | 27 | 50 |
| total | 71 | 79 | 150 |

- **Labelling order** is the random `queue` column (R001 = first). Labellers work in that order, so if fewer than
  150 are labelled, the labelled subset is still a random sample, not a hand-picked one.
- The repo stores only URLs, hashes and metadata (`benchmark/real/manifest.csv`); notebooks and their numbered
  renderings stay local in `benchmark/raw/` (gitignored). Licences are `unverified` until checked per notebook.
