# leaklens on the injected benchmark, TEST split (strict entity rule, EVAL_CHANGES.md #10)

79 files, 73 labelled leaks, 9 files without a leak. Matching and metrics: EVAL_PROTOCOL.md sections 2 to 4. Intervals: 95% percentile bootstrap, 2000 resamples of files (and of base pipelines, in brackets).

## static, confidence medium or higher (primary)

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 21 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.955 (0.84 to 1.00) [0.89 to 1.00] | 0.977 |
| overlap | 9 | 7 | 0 | 2 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.778 (0.44 to 1.00) [0.40 to 1.00] | 0.875 |
| multi_test | 6 | 5 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.833 (0.43 to 1.00) [0.50 to 1.00] | 0.909 |
| group | 7 | 3 | 0 | 4 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.429 (0.00 to 0.83) [0.00 to 1.00] | 0.600 |
| temporal | 25 | 20 | 0 | 5 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.800 (0.62 to 0.95) [0.55 to 1.00] | 0.889 |
| target_derived | 4 | 3 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.750 (0.00 to 1.00) [0.25 to 1.00] | 0.857 |

Recall by label category:

| category | found | missed | recall |
|---|---|---|---|
| dynamic_only | 0 | 2 | 0.000 |
| group | 3 | 4 | 0.429 |
| standard | 36 | 3 | 0.923 |
| temporal_common | 5 | 0 | 1.000 |
| temporal_differentiating | 7 | 0 | 1.000 |
| temporal_hard | 8 | 5 | 0.615 |

Files without a leak that received a finding: 0 of 9.

## static, all findings, low included

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 21 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.955 (0.84 to 1.00) [0.89 to 1.00] | 0.977 |
| overlap | 9 | 7 | 0 | 2 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.778 (0.44 to 1.00) [0.40 to 1.00] | 0.875 |
| multi_test | 6 | 5 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.833 (0.43 to 1.00) [0.50 to 1.00] | 0.909 |
| group | 7 | 3 | 4 | 4 | 0.429 (0.00 to 0.83) [0.00 to 1.00] | 0.429 (0.00 to 0.83) [0.00 to 1.00] | 0.429 |
| temporal | 25 | 25 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| target_derived | 4 | 3 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.750 (0.00 to 1.00) [0.25 to 1.00] | 0.857 |

## static+dynamic, confidence medium or higher (primary)

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 21 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.955 (0.84 to 1.00) [0.89 to 1.00] | 0.977 |
| overlap | 9 | 9 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| multi_test | 6 | 5 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.833 (0.43 to 1.00) [0.50 to 1.00] | 0.909 |
| group | 7 | 3 | 4 | 4 | 0.429 (0.00 to 0.83) [0.00 to 1.00] | 0.429 (0.00 to 0.83) [0.00 to 1.00] | 0.429 |
| temporal | 25 | 20 | 0 | 5 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.800 (0.62 to 0.95) [0.55 to 1.00] | 0.889 |
| target_derived | 4 | 3 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.750 (0.00 to 1.00) [0.25 to 1.00] | 0.857 |

Recall by label category:

| category | found | missed | recall |
|---|---|---|---|
| dynamic_only | 2 | 0 | 1.000 |
| group | 3 | 4 | 0.429 |
| standard | 36 | 3 | 0.923 |
| temporal_common | 5 | 0 | 1.000 |
| temporal_differentiating | 7 | 0 | 1.000 |
| temporal_hard | 8 | 5 | 0.615 |

Files without a leak that received a finding: 0 of 9.

## static+dynamic, all findings, low included

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 21 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.955 (0.84 to 1.00) [0.89 to 1.00] | 0.977 |
| overlap | 9 | 9 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| multi_test | 6 | 5 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.833 (0.43 to 1.00) [0.50 to 1.00] | 0.909 |
| group | 7 | 3 | 4 | 4 | 0.429 (0.00 to 0.83) [0.00 to 1.00] | 0.429 (0.00 to 0.83) [0.00 to 1.00] | 0.429 |
| temporal | 25 | 25 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| target_derived | 4 | 3 | 0 | 1 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.750 (0.00 to 1.00) [0.25 to 1.00] | 0.857 |

## Coverage and runtime

- Files analysed: 79 of 79.
- Static analysis time per file: median 0.0026 s, mean 0.0021 s, max 0.0039 s (this machine: see registry).
- Instrumented runs: {'ok': 79}; time per file: median 1.33 s, max 12.68 s.

## What the instrumented run did

| type | static findings confirmed | refuted | not checked | run error | found only by the run |
|---|---|---|---|---|---|
| preprocessing | 15 | 0 | 6 | 0 | 0 |
| overlap | 7 | 0 | 0 | 0 | 2 |
| multi_test | 5 | 0 | 0 | 0 | 0 |
| group | 7 | 0 | 0 | 0 | 0 |
| temporal | 7 | 0 | 18 | 0 | 0 |
| target_derived | 2 | 0 | 1 | 0 | 0 |
