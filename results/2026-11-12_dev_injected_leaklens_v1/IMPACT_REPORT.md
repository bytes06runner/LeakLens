# Impact estimates against true inflation (injected benchmark)

Estimate: the script's own metric in the original run minus the metric when the run is repeated with the finding's canonical fix. Truth: leaky file minus its ground-truth fixed version, same data seed. Positive means the leak makes the result look better. Injected inflation is by construction (CLAUDE.md Rule 12): these numbers measure the accuracy of the estimate, not the severity of leakage.

Instrumentation check: in 96 files the instrumented run and the plain run of the leaky file printed metrics that differ by at most 0.000000.

## What could be estimated

| type | measured | unreliable | unknown (no automatic fix, or the fixed run failed) |
|---|---|---|---|
| preprocessing | 7 | 0 | 23 |
| overlap | 6 | 0 | 4 |
| multi_test | 0 | 0 | 8 |
| group | 10 | 0 | 0 |
| temporal | 10 | 0 | 15 |
| target_derived | 6 | 0 | 0 |

## Accuracy, single-leak files, status `measured`

| type | metric | n | mean true inflation | mean estimate | mean abs. error | median abs. error | sign agreement | Spearman |
|---|---|---|---|---|---|---|---|---|
| preprocessing | test_ap | 4 | +0.0084 | +0.0000 | 0.0084 | 0.0000 | 0% | n/a |
| preprocessing | test_auc | 3 | +0.0000 | +0.0000 | 0.0000 | 0.0000 | n/a | n/a |
| overlap | test_ap | 2 | +0.4658 | +0.4662 | 0.0003 | 0.0003 | 100% | n/a |
| overlap | test_auc | 2 | +0.3528 | +0.3528 | 0.0000 | 0.0000 | 100% | n/a |
| overlap | test_r2 | 2 | +0.0349 | +0.0349 | 0.0000 | 0.0000 | 100% | n/a |
| group | cv_auc | 6 | +0.0762 | +0.0762 | 0.0000 | 0.0000 | 100% | 1.00 |
| group | test_auc | 3 | +0.0936 | +0.3933 | 0.2997 | 0.2997 | 100% | 1.00 |
| temporal | cv_mae | 3 | +0.0127 | +0.0127 | 0.0000 | 0.0000 | 100% | 1.00 |
| temporal | test_r2 | 6 | +0.0032 | +0.0032 | 0.0000 | 0.0000 | 100% | 1.00 |
| target_derived | cv_auc | 3 | +0.3703 | +0.3703 | 0.0000 | 0.0000 | 100% | 1.00 |
| target_derived | test_ap | 1 | +0.5079 | +0.5079 | 0.0000 | 0.0000 | 100% | n/a |
| target_derived | test_auc | 1 | +0.3475 | +0.3475 | 0.0000 | 0.0000 | 100% | n/a |

Across all 33 measured single-leak findings whose metric is bounded (AUC, AP, R2): mean absolute error 0.0283, Spearman rank correlation 0.95. Error metrics (MAE) are listed per row above, not pooled.

## Multi-leak files (truth is the joint effect of all leaks; not scored)

| file | finding | metric | estimate for this finding | true joint inflation |
|---|---|---|---|---|
| grp_users__combo2 | target_derived | cv_auc | +0.4770 | +0.4531 |
| grp_users__combo2 | group | cv_auc | +0.0000 | +0.4531 |
| ts_sensor__combo4 | temporal | cv_mae | +0.0085 | +0.3716 |
