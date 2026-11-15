# Kaggle job 12: R017 re-run after EVAL_CHANGES #19

Run 2026-11-15, Kaggle CPU, internet off, `leaklens.sandbox`; code commit `9e919b0`. R017 only (adapted copy not
committed, Rule 9). The run checked `patient_nbr` at the split and confirmed group leakage at high confidence
(7001 patients on both sides); it also confirmed duplicated records across the split, as in job 11. With jobs 11
and 12, the second look finds all 4 real TEST group notebooks: R036, R040, R074 statically, R017 with the run.
