# Kaggle job 08, version 4: case studies C2a, C2b, C3a, C3b

Run on 2026-11-14 (Kaggle CPU, internet off, `leaklens.sandbox`, Python 3.13.18; wheel installed with
`--ignore-requires-python`). Library code: commit `81ede62` (`run_info.json`); `src/` and `configs/` are identical
at `40283fb`, so this is the current analyser. Command per case: `leaklens scan <case>.ipynb --dynamic --impact
--trust-code --min-confidence low --format json --timeout 2400`, inside the sandbox. All four cases finished;
none timed out. No data path needed adapting (`adaptations.json` is empty: the competition data mounted at the
paths the notebooks use). The adapted notebook copies `C*.ipynb` are not committed (Rule 9).

Exit codes: C2a 0 (no finding), C2b, C3a, C3b 1 (findings).

## Against the proposed labels (`../2026-11-14_case_studies/PROPOSED_LABELS.md`)

The labels were written before LeakLens was run on these notebooks and are **not yet confirmed by the owner**.
Cells are counted from 1 as displayed (the report's `cell` field is 0-based). Reporting threshold: medium.

| Case | Label | LeakLens (static, then the run) | Right column? | Verdict at the reporting threshold | Impact (re-run with the fix) |
|---|---|---|---|---|---|
| C2a | group, cell 63, lines 3-5 | nothing, in either pass | no | **miss** | none (no finding) |
| C2b | group, cell 48, line 1 | LL-GRP-001 medium; run **confirmed**: 115 of 194 `patient_id` values on both sides, 96% of validation rows belong to them; confidence raised to high | yes (`patient_id`) | **found** | **unreliable**: validation SMAPE 84.74 -> 98.49 with `GroupShuffleSplit(groups=patient_id)` |
| C3a | temporal, cell 74, line 5 | LL-TMP-001 low (evidence lists `datetime`, parsed as datetime); run **not confirmed**: no timestamp column row-aligned with the split data | yes (static evidence), not confirmed | **miss** (low only) | unknown: the chronological fix failed (no time column at the split) |
| C3b | temporal, cell 47, lines 25-27 | LL-TMP-001 low; run **confirmed** (`Date`, 99.3% of training rows dated after the first test row) | yes (`Date`) | **miss** (stays low after confirmation, by design) | measured: test R2 0.959 -> 0.895 |
| C3b | temporal, cell 54, lines 13-19 | LL-TMP-001 low; run **confirmed** (`Date`, 99.4%) | yes (`Date`) | **miss** (low) | measured: CV RMSE 108.6k -> 258.0k (`TimeSeriesSplit`) |
| C3b | multi-test, cell 51, line 3 | LL-MUL-001 high at cell 50 line 8 (the scoring call), confirmed (3 candidates) | n/a | **wrong line**: miss + false positive under the line rule | unknown (nested validation not automated) |
| C3b | (not labelled) | LL-MUL-001 high at cell 54 lines 13-19 (CV comparison of 3 models), confirmed | n/a | false positive, **unless** the owner decides the CV comparison counts as multi-test (open question in the labels) | unknown |
| C3b | (not labelled; labels say `Store` on both sides is legitimate) | LL-GRP-001 low on `Store` at both splits; run not confirmed | – | below threshold, not reported | measured but irrelevant (`GroupShuffleSplit(groups=Store)`: R2 0.959 -> -0.169) |

## Notes

- **C2a.** The accelerometer frames are read from files in a loop over `os.listdir` and concatenated; the file name
  (recording) is never stored in any frame, and the patient is only in the competition's metadata files, which the
  notebook does not read. Neither pass has anything to point at. The report records no run status when there is
  no finding to confirm, so this output cannot show whether the run reached the split (it took 101 s, consistent
  with reading the data). Recording the run status per file is listed as an improvement, not done.
- **C2b, impact marked unreliable.** The score is a value the notebook displays (`val_smape`, line 124 of the
  flattened script), so it has no input signature that would show the fix reached it; the tool's rule (EVAL_CHANGES
  #14) then marks the estimate unreliable even though the value changed. SMAPE is lower-is-better: the leak makes
  the validation error look 13.8 points lower. Reported as unreliable; the rule was not changed after seeing this.
- **C3a.** The notebook derives calendar features from `datetime` and drops it (displayed cell 68) before the split,
  so at run time no column of the split data holds timestamps; integer `year`/`day` columns are not treated as time.
- **C3b** reproduces job 08 v3 exactly (same six findings, same confidences, same impact values).
