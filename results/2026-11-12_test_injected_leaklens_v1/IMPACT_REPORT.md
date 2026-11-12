# Impact estimates against true inflation (injected benchmark)

Estimate: the script's own metric in the original run minus the metric when the run is repeated with the finding's canonical fix. Truth: leaky file minus its ground-truth fixed version, same data seed. Positive means the leak makes the result look better. Injected inflation is by construction (CLAUDE.md Rule 12): these numbers measure the accuracy of the estimate, not the severity of leakage.

Instrumentation check: in 395 files the instrumented run and the plain run of the leaky file printed metrics that differ by at most 0.000000.

## What could be estimated

| type | measured | unreliable | unknown (no automatic fix, or the fixed run failed) |
|---|---|---|---|
| preprocessing | 10 | 0 | 11 |
| overlap | 7 | 0 | 2 |
| multi_test | 0 | 0 | 5 |
| group | 7 | 0 | 0 |
| temporal | 7 | 0 | 18 |
| target_derived | 3 | 0 | 0 |

## Accuracy, single-leak files, status `measured`

| type | metric | n | mean true inflation | mean estimate | mean abs. error | median abs. error | sign agreement | Spearman |
|---|---|---|---|---|---|---|---|---|
| preprocessing | test_auc | 40 | -0.0003 | +0.0001 | 0.0004 | 0.0000 | 61% | 0.10 |
| overlap | cv_r2 | 5 | +0.0259 | +0.0259 | 0.0000 | 0.0000 | 100% | 1.00 |
| overlap | test_auc | 25 | +0.1969 | +0.1969 | 0.0000 | 0.0000 | 100% | 1.00 |
| group | cv_auc | 15 | +0.0753 | +0.0706 | 0.0542 | 0.0325 | 93% | 0.78 |
| group | test_auc | 15 | +0.2119 | -0.0840 | 0.2959 | 0.2888 | 0% | 0.48 |
| temporal | cv_auc | 15 | +0.0047 | +0.0047 | 0.0000 | 0.0000 | 100% | 1.00 |
| temporal | test_mae | 15 | +1.3322 | +1.3322 | 0.0000 | 0.0000 | 100% | 1.00 |
| target_derived | cv_auc | 5 | +0.4605 | +0.4605 | 0.0000 | 0.0000 | 100% | 1.00 |
| target_derived | cv_r2 | 5 | +0.0475 | +0.0475 | 0.0000 | 0.0000 | 100% | 1.00 |
| target_derived | test_auc | 5 | +0.4433 | +0.4433 | 0.0000 | 0.0000 | 100% | 1.00 |

Across all 130 measured single-leak findings whose metric is bounded (AUC, AP, R2): mean absolute error 0.0405, Spearman rank correlation 0.57. Error metrics (MAE) are listed per row above, not pooled.

## Accuracy after averaging over data seeds [0, 1, 2, 3, 4] (one row per finding, then per type and metric)

| type | metric | findings | mean true inflation | mean estimate | mean abs. error | sign agreement | Spearman |
|---|---|---|---|---|---|---|---|
| preprocessing | test_auc | 8 | -0.0003 | +0.0001 | 0.0003 | 60% | -0.14 |
| overlap | cv_r2 | 1 | +0.0259 | +0.0259 | 0.0000 | 100% | n/a |
| overlap | test_auc | 5 | +0.1969 | +0.1969 | 0.0000 | 100% | 1.00 |
| group | cv_auc | 3 | +0.0753 | +0.0706 | 0.0047 | 100% | 1.00 |
| group | test_auc | 3 | +0.2119 | -0.0840 | 0.2959 | 0% | 1.00 |
| temporal | cv_auc | 3 | +0.0047 | +0.0047 | 0.0000 | 100% | 1.00 |
| temporal | test_mae | 3 | +1.3322 | +1.3322 | 0.0000 | 100% | n/a |
| target_derived | cv_auc | 1 | +0.4605 | +0.4605 | 0.0000 | 100% | n/a |
| target_derived | cv_r2 | 1 | +0.0475 | +0.0475 | 0.0000 | 100% | n/a |
| target_derived | test_auc | 1 | +0.4433 | +0.4433 | 0.0000 | 100% | n/a |

Seed-averaged, all 26 single-leak findings with a bounded metric: mean absolute error 0.0348, Spearman 0.58.

## Multi-leak files (truth is the joint effect of all leaks; not scored)

| file | finding | metric | estimate for this finding | true joint inflation |
|---|---|---|---|---|
| grp_patients__combo1 | preprocessing | test_auc | +0.0022 | +0.2012 |
| grp_patients__combo1 | group | test_auc | -0.0424 | +0.2012 |
| tab_credit__combo5 | preprocessing | test_auc | +0.0001 | +0.0489 |
| tab_credit__combo5 | overlap | test_auc | +0.0489 | +0.0489 |
| ts_sales__combo3 | temporal | test_mae | +0.4489 | +0.4489 |
