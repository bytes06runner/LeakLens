# Runnability probes

Four tiny, self-contained scripts written by us, used **only** to check that each baseline tool installs and
produces output (Phase 0). They are not benchmark items and are never used to tune or score LeakLens.

| File | Known ground truth |
|---|---|
| `p1_preprocessing_leak.py` | preprocessing leak (scaler fitted before split) |
| `p2_group_leak.py` | group leak (random split, repeated `patient_id`) |
| `p3_temporal_leak.py` | temporal leak (shuffled split, lag feature before split) |
| `p4_clean.py` | clean control |
