# Notebook-level scores on the real DEV notebooks

71 notebooks; labels `labels_DEV.csv`. A tool is right about a type in a notebook when it reports that type there and the notebook has a label of that type (EVAL_CHANGES #6); a group finding must name the labelled entity when one is given. 95% CIs resample notebooks. A notebook the tool could not analyse counts as analysed with no finding (Rule 5).

## LeakLens static, confidence medium+

| type | notebooks with label | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 20 | 10 | 9 | 10 | 0.53 (0.29 to 0.76) | 0.50 (0.27 to 0.72) |
| overlap | 5 | 3 | 0 | 2 | 1.00 (1.00 to 1.00) | 0.60 (0.00 to 1.00) |
| multi_test | 15 | 6 | 4 | 9 | 0.60 (0.27 to 0.90) | 0.40 (0.15 to 0.67) |
| group | 4 | 1 | 3 | 3 | 0.25 (0.00 to 1.00) | 0.25 (0.00 to 1.00) |
| temporal | 7 | 2 | 1 | 5 | 0.67 (0.00 to 1.00) | 0.29 (0.00 to 0.67) |
| target_derived | 6 | 1 | 1 | 5 | 0.50 (0.00 to 1.00) | 0.17 (0.00 to 0.50) |

## LeakLens static, confidence low+

| type | notebooks with label | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| preprocessing | 20 | 11 | 11 | 9 | 0.50 (0.30 to 0.71) | 0.55 (0.32 to 0.76) |
| overlap | 5 | 3 | 0 | 2 | 1.00 (1.00 to 1.00) | 0.60 (0.00 to 1.00) |
| multi_test | 15 | 8 | 7 | 7 | 0.53 (0.27 to 0.80) | 0.53 (0.27 to 0.80) |
| group | 4 | 1 | 19 | 3 | 0.05 (0.00 to 0.17) | 0.25 (0.00 to 1.00) |
| temporal | 7 | 3 | 5 | 4 | 0.38 (0.00 to 0.75) | 0.43 (0.00 to 0.86) |
| target_derived | 6 | 1 | 1 | 5 | 0.50 (0.00 to 1.00) | 0.17 (0.00 to 0.50) |

