# CalibraEEG case study, static mode

`leaklens scan src kaggle scripts --min-confidence low` on the companion project at commit `a062f45`. Nothing was
executed. Files analysed: 78 of 78. Findings: 0.

Expected (CLAUDE.md Phase 7): leakage flagged in regime A (random windows) and regime B (within-patient), nothing in
regime C (leave-one-patient-out). Found: nothing in any regime. Correct for C; a miss for A and B. The regimes are
implemented with NumPy random masks and positional cuts over custom `Recording` objects
(`src/calibraeeg/train/regimes.py`), which the analyser does not model. See `docs/PHASE3_6_REPORT.md` section 4.
