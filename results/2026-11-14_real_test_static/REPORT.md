# LeakLens (static) on the real TEST notebooks

79 notebooks, 99 labelled leaks in 56 notebooks, 0 notebooks LeakLens could not read. Labels: `labels_TEST.csv`. Matching: EVAL_PROTOCOL.md section 2; group findings must name the labelled entity where one is given.

## strict (headline), confidence medium or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 39 | 21 | 29 | 18 | 0.42 (0.26 to 0.60) | 0.54 (0.37 to 0.71) |
| overlap | 8 | 4 | 6 | 4 | 0.40 (0.00 to 1.00) | 0.50 (0.00 to 0.88) |
| multi_test | 26 | 5 | 29 | 21 | 0.15 (0.05 to 0.31) | 0.19 (0.05 to 0.36) |
| group | 6 | 0 | 7 | 6 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |
| temporal | 15 | 3 | 8 | 12 | 0.27 (0.00 to 0.50) | 0.20 (0.00 to 0.47) |
| target_derived | 5 | 0 | 8 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

## strict (headline), confidence low or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 39 | 23 | 41 | 16 | 0.36 (0.23 to 0.51) | 0.59 (0.42 to 0.76) |
| overlap | 8 | 4 | 9 | 4 | 0.31 (0.00 to 0.67) | 0.50 (0.00 to 0.88) |
| multi_test | 26 | 6 | 39 | 20 | 0.13 (0.05 to 0.32) | 0.23 (0.08 to 0.41) |
| group | 6 | 1 | 78 | 5 | 0.01 (0.00 to 0.06) | 0.17 (0.00 to 1.00) |
| temporal | 15 | 7 | 24 | 8 | 0.23 (0.08 to 0.37) | 0.47 (0.12 to 0.75) |
| target_derived | 5 | 0 | 9 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

## lenient, confidence medium or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 39 | 21 | 29 | 18 | 0.42 (0.26 to 0.60) | 0.54 (0.37 to 0.71) |
| overlap | 8 | 4 | 6 | 4 | 0.40 (0.00 to 1.00) | 0.50 (0.00 to 0.88) |
| multi_test | 26 | 5 | 29 | 21 | 0.15 (0.05 to 0.31) | 0.19 (0.05 to 0.36) |
| group | 6 | 0 | 7 | 6 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |
| temporal | 15 | 3 | 8 | 12 | 0.27 (0.00 to 0.50) | 0.20 (0.00 to 0.47) |
| target_derived | 5 | 0 | 8 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

## lenient, confidence low or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 39 | 23 | 41 | 16 | 0.36 (0.23 to 0.51) | 0.59 (0.42 to 0.76) |
| overlap | 8 | 4 | 9 | 4 | 0.31 (0.00 to 0.67) | 0.50 (0.00 to 0.88) |
| multi_test | 26 | 6 | 39 | 20 | 0.13 (0.05 to 0.32) | 0.23 (0.08 to 0.41) |
| group | 6 | 1 | 78 | 5 | 0.01 (0.00 to 0.06) | 0.17 (0.00 to 1.00) |
| temporal | 15 | 7 | 24 | 8 | 0.23 (0.08 to 0.37) | 0.47 (0.12 to 0.75) |
| target_derived | 5 | 0 | 9 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

