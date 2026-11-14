# Notebook-level scores on the real TEST notebooks

79 notebooks; labels `labels_TEST.csv`. A tool is right about a type in a notebook when it reports that type there and the notebook has a label of that type (EVAL_CHANGES #6); a group finding must name the labelled entity when one is given. 95% CIs resample notebooks. A notebook the tool could not analyse counts as analysed with no finding (Rule 5).

Yang analyser produced a report for 69 of 79 notebooks.

## LeakLens static, confidence medium+

| type | notebooks with label | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 23 | 16 | 5 | 7 | 0.76 (0.56 to 0.93) | 0.70 (0.50 to 0.88) |
| overlap | 7 | 5 | 1 | 2 | 0.83 (0.50 to 1.00) | 0.71 (0.33 to 1.00) |
| multi_test | 25 | 14 | 5 | 11 | 0.74 (0.53 to 0.92) | 0.56 (0.36 to 0.75) |
| group | 4 | 0 | 3 | 4 | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |
| temporal | 13 | 3 | 1 | 10 | 0.75 (0.00 to 1.00) | 0.23 (0.00 to 0.50) |
| target_derived | 4 | 1 | 4 | 3 | 0.20 (0.00 to 0.67) | 0.25 (0.00 to 1.00) |

## LeakLens static, confidence low+

| type | notebooks with label | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 23 | 18 | 8 | 5 | 0.69 (0.50 to 0.87) | 0.78 (0.61 to 0.95) |
| overlap | 7 | 5 | 3 | 2 | 0.62 (0.25 to 1.00) | 0.71 (0.33 to 1.00) |
| multi_test | 25 | 15 | 6 | 10 | 0.71 (0.52 to 0.90) | 0.60 (0.41 to 0.80) |
| group | 4 | 1 | 17 | 3 | 0.06 (0.00 to 0.18) | 0.25 (0.00 to 1.00) |
| temporal | 13 | 6 | 6 | 7 | 0.50 (0.21 to 0.80) | 0.46 (0.20 to 0.75) |
| target_derived | 4 | 1 | 5 | 3 | 0.17 (0.00 to 0.60) | 0.25 (0.00 to 1.00) |

## Yang et al. analyser (notebook as .py)

| type | notebooks with label | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 23 | 12 | 16 | 11 | 0.43 (0.25 to 0.62) | 0.52 (0.32 to 0.74) |
| overlap | 7 | 2 | 8 | 5 | 0.20 (0.00 to 0.50) | 0.29 (0.00 to 0.67) |
| multi_test | 25 | 9 | 19 | 16 | 0.32 (0.15 to 0.50) | 0.36 (0.18 to 0.56) |

