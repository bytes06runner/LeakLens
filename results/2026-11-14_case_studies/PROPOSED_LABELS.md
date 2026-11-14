# Case studies C2a, C2b, C3a, C3b: proposed labels (written before LeakLens was run on these notebooks)

Proposed by Claude from reading the code (Rule 3: the project owner confirms or corrects each row before any
LeakLens output is compared with them). Cell and line numbers are as displayed (`[cell N | line M]`, all cells
counted from 1). The notebooks are public Kaggle notebooks, identified here only by case ID (Rule 8).

| Case | Leak | Cell, lines | Mechanism | True entity / time column | Confidence |
|---|---|---|---|---|---|
| C2a | group | 63, 3-5 | Accelerometer samples of many recordings of Parkinson's patients are concatenated (cells 29, 47, 54) and three row-level `train_test_split` calls put samples of the same recording, and of the same patient, on both sides. | The recording (file name, read in a loop over `os.listdir`); the patient via the competition metadata. **Not a column of the data frame.** | sure |
| C2b | group | 48, 1 | Baseline-visit proteomics merged with clinical scores melted over four UPDRS parts: up to four rows per patient with identical protein features (and `patient_id` itself as a feature); random `train_test_split`. | `patient_id` | sure |
| C3a | temporal | 74, 5 | Daily energy targets per prediction unit, with calendar features (`year`, `day`, `days_since_reference`, ...); random `train_test_split` puts later dates in training. | `datetime` (dropped in cell 68 after the calendar features are derived from it) | sure |
| C3b | temporal | 47, 25-27 | Weekly sales of 45 stores with `Year`, `Month`, `Week` features; random `train_test_split`. | `Date` | sure |
| C3b | temporal | 54, 13-19 | `cross_val_score` with `KFold(shuffle=True)` (cell 54, line 2) on the same weekly data. | `Date` | sure |
| C3b | multi_test | 51, 3 | The best model is chosen by its test RMSE (cell 50) and reported. | n/a | likely |

Not labelled: C2a cell 85 fits a scaler on the competition test set for a submission (no score is computed on it);
C3b keeps `Store` on both sides, which is legitimate for forecasting known stores.

**Owner confirmation:** confirmed on 2026-11-14 by the project owner (first author), all six rows as written
("Confirm all six"). This settles the two open questions as the table states them: the C3b multi-test leak is located
at the selection line (displayed cell 51, line 3), and C3b's cross-validated comparison of three models (cell 54) is
not labelled as a leak. The confirmation came after LeakLens's output on these notebooks had been shown to the
owner (job 08 v4, `../2026-11-14_kaggle_08_case_studies_v4/README.md`); no row was changed.
