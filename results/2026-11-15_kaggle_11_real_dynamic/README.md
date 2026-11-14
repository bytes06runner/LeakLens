# Kaggle job 11: static + instrumented run on 19 real TEST notebooks (second look code)

Run 2026-11-14/15, Kaggle CPU, internet off, `leaklens.sandbox`; code commit `6780bff` (rules of EVAL_CHANGES #17).
Notebooks: TEST notebooks with a group or temporal label, plus those with a medium group finding. `R*.ipynb`
(adapted copies) are not committed (Rule 9). Per-notebook outcome in `run_info.json`; reports in `R*.json`.

Group: R040 confirmed (`id`, raised to high). R074 found statically, run not reached at the split. R036 found
statically (LL-GRP-006); the run hit the 1200 s limit. R017: the run reached the split (and confirmed exact
duplicate rows across it, 3.8% of evaluation rows) but did not check `patient_nbr`, because `nbr` was not an
identifier suffix and the bare `no` in configs/static.yaml was read as false (fixed in EVAL_CHANGES #19; R017 re-run
in job 12). Group findings on R047, R077, R110 (not labelled): the runs did not reach the split ("error").
Temporal: R003 confirmed (4 splits), R022 confirmed (low), others not run or not reached.
