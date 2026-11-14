# Real-world case studies: selection rule (fixed 2026-11-14, before any candidate was read or analysed)

Requested by the supervisor's review (Review 3): at least three real case studies, one each for EEG
subject-independent validation, patient-level leakage in healthcare ML, and time-series forecasting with
chronological leakage. For each: original code, leakage mechanism, LeakLens output, whether the correct
entity/time column was identified, the corrected pipeline, and the metric difference.

## Why a fixed rule

Picking public notebooks after seeing what LeakLens reports on them would select its successes. The rule below
picks the cases from what the code does, before LeakLens is run on them, and every notebook inspected is listed
with the reason it was taken or skipped (`results/<run>/case_selection_log.csv`).

## Case 1: EEG (subject-independent validation)

The companion project CalibraEEG (same first author), commit `a062f45`, regimes A (random windows pooled over
subjects), B (within-patient chronological split) and C (leave-one-patient-out). Ground truth is known by design.
Already analysed once (2026-11-12, static mode: no finding in any regime). **This case is not blind any more:**
the static analyser is extended for hand-written NumPy splits after that result (logged in EVAL_CHANGES.md), so
the paper reports both the original miss and the result after the extension, and says the extension was written
looking at this code. The metric difference is the one CalibraEEG measured itself between regimes (A or B vs C).

## Cases 2 and 3: public Kaggle notebooks

Source: `benchmark/real/pool.csv` (the sampling pool of the real-notebook study), excluding the 150 study
notebooks (`benchmark/real/manifest.csv`), walked in `pool_rank` order (a seeded random order fixed on
2026-09-29) within the stratum:

- Case 2 (healthcare, patient level): stratum `grouped`, queries about medical or patient data.
- Case 3 (forecasting, chronological): stratum `timeseries`.

A notebook qualifies when, **by reading its code and saved outputs (LeakLens not run)**:

1. Case 2: the data are medical or health records, and one patient (or subject) contributes several rows, as
   shown by the notebook's own outputs, the dataset's description, or a file/folder per patient.
   Case 3: rows are dated observations of one or more series, and the target is a later value of a series.
2. The reported evaluation ignores that structure: a row-level random split or random K-fold (case 2), or a
   shuffled split / random K-fold, or a feature computed from future values (case 3).
3. The notebook trains a model and prints a metric, using pandas / NumPy / scikit-learn (or a library with a
   scikit-learn interface), and its data are a public Kaggle dataset or competition that can be attached to a
   Kaggle session.
4. It can plausibly run on a Kaggle CPU session in under 30 minutes (no GPU-only code).

The first two qualifying notebooks per case are taken. They are executed only in a Kaggle session with the
internet off, through `leaklens.sandbox` (CLAUDE.md Rule 7). Labels (leak type, line, entity or time column)
are proposed by Claude and **confirmed by the project owner** before LeakLens's output is compared with them
(Rule 3). Authors are not named in the paper (Rule 8); code excerpts are shown only where the notebook's
licence allows, otherwise paraphrased.

## Clarification of criterion 1 for case 3 (2026-11-14, written before LeakLens was run on any candidate)

"The target is a later value of a series" is read as: the notebook (its text, title or competition) frames the
task as forecasting a series (sales, energy, demand), and the target is that series' value at the row's date, so
an honest evaluation scores later dates than it trains on. Explanatory models of a same-date quantity from
same-date inputs (e.g. a close price from that day's high and low, emissions from per-capita emissions and
population) do not qualify.

## Outcome

Healthcare: C2a (Parkinson's freezing of gait: many recordings per patient pooled sample by sample, random split)
and C2b (Parkinson's progression: baseline proteomics repeated over four UPDRS parts per patient, `patient_id`
kept as a feature, random split). The first notebook first marked as taken was excluded on closer reading under
criterion 4 (an unfinishable grid search), and its fork under criterion 4 (library arguments removed in current
versions); both before LeakLens was run on anything.
Forecasting: C3a (energy of prosumers, random split with date features) and C3b (weekly retail sales, random
split with year/month/week features).

Every inspected notebook, in pool order, with the reason it was taken or skipped:
`results/2026-11-14_case_studies/case_selection_log.csv`. Notebooks are identified there by a hash of their
Kaggle reference, not by name or pool rank (Rule 8); the mapping is kept outside the repository with the other
raw notebooks.
