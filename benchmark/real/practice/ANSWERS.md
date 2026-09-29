# Practice answers

Cell and line numbers refer to the rendered practice files (`P1.txt` ... `P5.txt`, `[cell N | line M]`).

| File | leak_type | cell | line | confidence | Why |
|---|---|---|---|---|---|
| P1 | preprocessing | 3 | 4 | sure | `StandardScaler().fit_transform(X)` learns averages from all rows, before the split in cell 4 (Q1). |
| P1 | group | 4 | 1 | sure | The data has several visits per `patient_id` (cell 2 says so and counts them), and `train_test_split` is random, so the same patient lands in train and test (Q4). |
| P2 | none | | | sure | Dated data, but `TimeSeriesSplit` trains on the past only. `shift(-1)` creates the **answer** column `tomorrow`, not an input, which is normal forecasting (Q5). |
| P3 | multi_test | 3 | 6 | sure | Every `k` is scored on `X_test`, the best is kept, and its test score is reported (Q3). The scaler inside the pipeline is fine. |
| P4 | overlap | 3 | 3 | sure | Fraud rows are copied (`resample`) **before** the split in cell 4, so copies of the same transaction end up in train and test (Q2). |
| P4 | target_derived | 2 | 3 | likely | `refund_issued` is decided **after** the fraud investigation (see the comment in cell 2), so it gives the answer away (Q6). |
| P5 | none | | | sure | One row per customer (checked with `is_unique`), so a random split is fine; the scaler is inside the pipeline; the setting `C` is chosen with cross-validation on the training data only, and the test set is used once. |

Common mistakes to watch for:
- Labelling P2 as temporal because of `shift(-1)`: that line makes the target, not an input.
- Labelling P5 as group because it has `customer_id`: the ID never repeats.
- Missing the second leak in P1 or P4: always go through all six questions even after finding one leak.
