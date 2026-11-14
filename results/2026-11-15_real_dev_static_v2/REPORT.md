# LeakLens (static) on the real DEV notebooks

71 notebooks, 66 labelled leaks in 44 notebooks, 0 notebooks LeakLens could not read. Labels: `labels_DEV.csv`. Matching: EVAL_PROTOCOL.md section 2; group findings must name the labelled entity where one is given.

## strict (headline), confidence medium or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 22 | 9 | 18 | 13 | 0.33 (0.16 to 0.57) | 0.41 (0.21 to 0.65) |
| overlap | 6 | 3 | 4 | 3 | 0.43 (0.00 to 1.00) | 0.50 (0.00 to 1.00) |
| multi_test | 16 | 2 | 20 | 14 | 0.09 (0.00 to 0.38) | 0.12 (0.00 to 0.32) |
| group | 5 | 0 | 8 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |
| temporal | 9 | 3 | 2 | 6 | 0.60 (0.00 to 1.00) | 0.33 (0.00 to 0.67) |
| target_derived | 8 | 0 | 1 | 8 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

## strict (headline), confidence low or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 22 | 9 | 29 | 13 | 0.24 (0.12 to 0.38) | 0.41 (0.21 to 0.65) |
| overlap | 6 | 3 | 4 | 3 | 0.43 (0.00 to 1.00) | 0.50 (0.00 to 1.00) |
| multi_test | 16 | 4 | 28 | 12 | 0.12 (0.02 to 0.36) | 0.25 (0.06 to 0.50) |
| group | 5 | 0 | 49 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |
| temporal | 9 | 4 | 15 | 5 | 0.21 (0.00 to 0.50) | 0.44 (0.00 to 0.80) |
| target_derived | 8 | 0 | 2 | 8 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

## lenient, confidence medium or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 22 | 9 | 18 | 13 | 0.33 (0.16 to 0.57) | 0.41 (0.21 to 0.65) |
| overlap | 6 | 3 | 4 | 3 | 0.43 (0.00 to 1.00) | 0.50 (0.00 to 1.00) |
| multi_test | 16 | 2 | 20 | 14 | 0.09 (0.00 to 0.38) | 0.12 (0.00 to 0.32) |
| group | 5 | 0 | 8 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |
| temporal | 9 | 3 | 2 | 6 | 0.60 (0.00 to 1.00) | 0.33 (0.00 to 0.67) |
| target_derived | 8 | 0 | 1 | 8 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

## lenient, confidence low or higher

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 22 | 9 | 29 | 13 | 0.24 (0.12 to 0.38) | 0.41 (0.21 to 0.65) |
| overlap | 6 | 3 | 4 | 3 | 0.43 (0.00 to 1.00) | 0.50 (0.00 to 1.00) |
| multi_test | 16 | 4 | 28 | 12 | 0.12 (0.02 to 0.36) | 0.25 (0.06 to 0.50) |
| group | 5 | 0 | 49 | 5 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |
| temporal | 9 | 4 | 15 | 5 | 0.21 (0.00 to 0.50) | 0.44 (0.00 to 0.80) |
| target_derived | 8 | 0 | 2 | 8 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

