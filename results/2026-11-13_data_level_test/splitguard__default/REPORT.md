# splitguard on the injected benchmark, TEST split

79 files, 73 labelled leaks, 9 files without a leak. Matching and metrics: EVAL_PROTOCOL.md sections 2 to 4. Intervals: 95% percentile bootstrap, 2000 resamples of files (and of base pipelines, in brackets).

## static, confidence medium or higher (primary)

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 15 | 0 | 7 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.682 (0.48 to 0.88) [0.67 to 0.71] | 0.811 |
| overlap | 9 | 3 | 0 | 6 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.333 (0.00 to 0.67) [0.00 to 0.67] | 0.500 |
| multi_test | 6 | 0 | 0 | 6 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| group | 7 | 0 | 0 | 7 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| temporal | 25 | 3 | 0 | 22 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.120 (0.00 to 0.26) [0.00 to 0.27] | 0.214 |
| target_derived | 4 | 0 | 0 | 4 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |

Recall by label category:

| category | found | missed | recall |
|---|---|---|---|
| dynamic_only | 0 | 2 | 0.000 |
| group | 0 | 7 | 0.000 |
| standard | 18 | 21 | 0.462 |
| temporal_common | 0 | 5 | 0.000 |
| temporal_differentiating | 0 | 7 | 0.000 |
| temporal_hard | 3 | 10 | 0.231 |

Files without a leak that received a finding: 0 of 9.

## static, all findings, low included

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 15 | 0 | 7 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.682 (0.48 to 0.88) [0.67 to 0.71] | 0.811 |
| overlap | 9 | 3 | 0 | 6 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.333 (0.00 to 0.67) [0.00 to 0.67] | 0.500 |
| multi_test | 6 | 0 | 0 | 6 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| group | 7 | 0 | 0 | 7 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| temporal | 25 | 3 | 0 | 22 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.120 (0.00 to 0.26) [0.00 to 0.27] | 0.214 |
| target_derived | 4 | 0 | 0 | 4 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |

## static+dynamic, confidence medium or higher (primary)

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 15 | 0 | 7 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.682 (0.48 to 0.88) [0.67 to 0.71] | 0.811 |
| overlap | 9 | 3 | 0 | 6 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.333 (0.00 to 0.67) [0.00 to 0.67] | 0.500 |
| multi_test | 6 | 0 | 0 | 6 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| group | 7 | 0 | 0 | 7 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| temporal | 25 | 3 | 0 | 22 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.120 (0.00 to 0.26) [0.00 to 0.27] | 0.214 |
| target_derived | 4 | 0 | 0 | 4 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |

Recall by label category:

| category | found | missed | recall |
|---|---|---|---|
| dynamic_only | 0 | 2 | 0.000 |
| group | 0 | 7 | 0.000 |
| standard | 18 | 21 | 0.462 |
| temporal_common | 0 | 5 | 0.000 |
| temporal_differentiating | 0 | 7 | 0.000 |
| temporal_hard | 3 | 10 | 0.231 |

Files without a leak that received a finding: 0 of 9.

## static+dynamic, all findings, low included

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 15 | 0 | 7 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.682 (0.48 to 0.88) [0.67 to 0.71] | 0.811 |
| overlap | 9 | 3 | 0 | 6 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.333 (0.00 to 0.67) [0.00 to 0.67] | 0.500 |
| multi_test | 6 | 0 | 0 | 6 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| group | 7 | 0 | 0 | 7 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| temporal | 25 | 3 | 0 | 22 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.120 (0.00 to 0.26) [0.00 to 0.27] | 0.214 |
| target_derived | 4 | 0 | 0 | 4 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |

## Coverage and runtime

- Files analysed: 79 of 79.
- Static analysis time per file: median 0.0000 s, mean 0.0000 s, max 0.0000 s (this machine: see registry).
- Instrumented runs: {'ok': 79}; time per file: median 0.00 s, max 0.00 s.

## What the instrumented run did

| type | static findings confirmed | refuted | not checked | run error | found only by the run |
|---|---|---|---|---|---|
| preprocessing | 0 | 0 | 18 | 0 | 0 |
| overlap | 0 | 0 | 3 | 0 | 0 |
| multi_test | 0 | 0 | 0 | 0 | 0 |
| group | 0 | 0 | 0 | 0 | 0 |
| temporal | 0 | 0 | 0 | 0 | 0 |
| target_derived | 0 | 0 | 0 | 0 | 0 |
