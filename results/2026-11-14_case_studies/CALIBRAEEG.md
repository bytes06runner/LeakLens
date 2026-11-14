# Case 1: EEG subject-independent validation (CalibraEEG, commit a062f45)

Companion project of the first author; three evaluation regimes with known leakage status, on CHB-MIT
(23 patients). Code: `src/calibraeeg/train/regimes.py` (A, B) and `src/calibraeeg/train/fold.py` (C).

| Regime | Leakage mechanism | Expected | LeakLens 2026-11-12 (before #13) | LeakLens after EVAL_CHANGES #13 | Entity named |
|---|---|---|---|---|---|
| A: random 1-s windows pooled over patients | `u = rng.random(len(ri)); tr, va, te = u < f_tr, ...` on windows of all recordings; the same patient (and overlapping windows of one recording) on both sides | group (and overlap) | nothing | group, LL-GRP-001, medium, `regimes.py` line 99 | `subject` (attribute of the recordings) |
| B: within-patient chronological split | per-subject loop: first recordings to `train`, later ones to `test` | group (within-patient by design) | nothing | group, LL-GRP-005, medium, line 54 | `subject` |
| C: leave-one-patient-out | `fold.py` | nothing | nothing | nothing | n/a |

Not found: the overlap of adjacent 1-s windows in regime A (windows are built inside an unmodelled helper).

**Not a blind test.** The rules of EVAL_CHANGES #13 were written while looking at this code, after the earlier
miss. The earlier result (0 findings in 78 files) stays in the record.

**Metric difference** (measured by CalibraEEG itself, `results/summary/gap_summary.csv`, LightGBM, 23 patients,
paired on identical test seconds, subject bootstrap 95% CI). The corrected pipeline is regime C, implemented by
the CalibraEEG authors, not LeakLens's automatic fix (the model is a custom learner, outside the fixes LeakLens
can apply, and the runs need hours of GPU/CPU time):

| | AUPRC | AUROC |
|---|---|---|
| A (random windows) | 0.779 | 0.979 |
| B (within patient) | 0.595 | 0.972 |
| C (leave one patient out) | 0.364 | 0.892 |
| A - C | +0.415 (0.31 to 0.52) | +0.087 (0.04 to 0.14) |
| B - C | +0.231 (0.16 to 0.31) | +0.080 (0.04 to 0.13) |
