# LeakLens (static) on the real TEST notebooks

79 notebooks, 99 labelled leaks in 56 notebooks, 0 notebooks LeakLens could not read. Labels: `labels_TEST.csv`. Matching: EVAL_PROTOCOL.md section 2; group findings must name the labelled entity where one is given.

## strict (headline), confidence medium or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 39 | 21 | 29 | 18 | 0.42 (0.26 to 0.60) | 0.54 (0.37 to 0.71) |
| overlap | 8 | 4 | 6 | 4 | 0.40 (0.00 to 1.00) | 0.50 (0.00 to 0.88) |
| multi_test | 26 | 10 | 26 | 16 | 0.28 (0.14 to 0.53) | 0.38 (0.21 to 0.56) |
| group | 6 | 4 | 7 | 2 | 0.36 (0.00 to 1.00) | 0.67 (0.00 to 1.00) |
| temporal | 15 | 3 | 9 | 12 | 0.25 (0.00 to 0.50) | 0.20 (0.00 to 0.47) |
| target_derived | 5 | 0 | 8 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

## strict (headline), confidence low or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 39 | 23 | 41 | 16 | 0.36 (0.23 to 0.51) | 0.59 (0.42 to 0.76) |
| overlap | 8 | 4 | 9 | 4 | 0.31 (0.00 to 0.67) | 0.50 (0.00 to 0.88) |
| multi_test | 26 | 11 | 36 | 15 | 0.23 (0.12 to 0.52) | 0.42 (0.24 to 0.60) |
| group | 6 | 4 | 78 | 2 | 0.05 (0.00 to 0.15) | 0.67 (0.00 to 1.00) |
| temporal | 15 | 7 | 25 | 8 | 0.22 (0.07 to 0.36) | 0.47 (0.12 to 0.75) |
| target_derived | 5 | 0 | 9 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

## lenient, confidence medium or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 39 | 21 | 29 | 18 | 0.42 (0.26 to 0.60) | 0.54 (0.37 to 0.71) |
| overlap | 8 | 4 | 6 | 4 | 0.40 (0.00 to 1.00) | 0.50 (0.00 to 0.88) |
| multi_test | 26 | 10 | 26 | 16 | 0.28 (0.14 to 0.53) | 0.38 (0.21 to 0.56) |
| group | 6 | 4 | 7 | 2 | 0.36 (0.00 to 1.00) | 0.67 (0.00 to 1.00) |
| temporal | 15 | 3 | 9 | 12 | 0.25 (0.00 to 0.50) | 0.20 (0.00 to 0.47) |
| target_derived | 5 | 0 | 8 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

## lenient, confidence low or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 39 | 23 | 41 | 16 | 0.36 (0.23 to 0.51) | 0.59 (0.42 to 0.76) |
| overlap | 8 | 4 | 9 | 4 | 0.31 (0.00 to 0.67) | 0.50 (0.00 to 0.88) |
| multi_test | 26 | 11 | 36 | 15 | 0.23 (0.12 to 0.52) | 0.42 (0.24 to 0.60) |
| group | 6 | 4 | 78 | 2 | 0.05 (0.00 to 0.15) | 0.67 (0.00 to 1.00) |
| temporal | 15 | 7 | 25 | 8 | 0.22 (0.07 to 0.36) | 0.47 (0.12 to 0.75) |
| target_derived | 5 | 0 | 9 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

