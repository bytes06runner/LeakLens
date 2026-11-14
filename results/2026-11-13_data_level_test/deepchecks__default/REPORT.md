# deepchecks on the injected benchmark, TEST split

79 files, 73 labelled leaks, 9 files without a leak. Matching and metrics: EVAL_PROTOCOL.md sections 2 to 4. Intervals: 95% percentile bootstrap, 2000 resamples of files (and of base pipelines, in brackets).

## static, confidence medium or higher (primary)

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 0 | 0 | 22 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| overlap | 9 | 2 | 0 | 7 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.222 (0.00 to 0.56) [0.00 to 0.60] | 0.364 |
| multi_test | 6 | 0 | 0 | 6 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| group | 7 | 0 | 0 | 7 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| temporal | 25 | 0 | 0 | 25 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| target_derived | 4 | 0 | 0 | 4 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |

Recall by label category:

| category | found | missed | recall |
|---|---|---|---|
| dynamic_only | 2 | 0 | 1.000 |
| group | 0 | 7 | 0.000 |
| standard | 0 | 39 | 0.000 |
| temporal_common | 0 | 5 | 0.000 |
| temporal_differentiating | 0 | 7 | 0.000 |
| temporal_hard | 0 | 13 | 0.000 |

Files without a leak that received a finding: 0 of 9.

## static, all findings, low included

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 0 | 0 | 22 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| overlap | 9 | 2 | 0 | 7 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.222 (0.00 to 0.56) [0.00 to 0.60] | 0.364 |
| multi_test | 6 | 0 | 0 | 6 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| group | 7 | 0 | 0 | 7 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| temporal | 25 | 0 | 0 | 25 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| target_derived | 4 | 0 | 0 | 4 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |

## static+dynamic, confidence medium or higher (primary)

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 0 | 0 | 22 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| overlap | 9 | 2 | 0 | 7 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.222 (0.00 to 0.56) [0.00 to 0.60] | 0.364 |
| multi_test | 6 | 0 | 0 | 6 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| group | 7 | 0 | 0 | 7 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| temporal | 25 | 0 | 0 | 25 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| target_derived | 4 | 0 | 0 | 4 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |

Recall by label category:

| category | found | missed | recall |
|---|---|---|---|
| dynamic_only | 2 | 0 | 1.000 |
| group | 0 | 7 | 0.000 |
| standard | 0 | 39 | 0.000 |
| temporal_common | 0 | 5 | 0.000 |
| temporal_differentiating | 0 | 7 | 0.000 |
| temporal_hard | 0 | 13 | 0.000 |

Files without a leak that received a finding: 0 of 9.

## static+dynamic, all findings, low included

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 22 | 0 | 0 | 22 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| overlap | 9 | 2 | 0 | 7 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.222 (0.00 to 0.56) [0.00 to 0.60] | 0.364 |
| multi_test | 6 | 0 | 0 | 6 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| group | 7 | 0 | 0 | 7 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| temporal | 25 | 0 | 0 | 25 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |
| target_derived | 4 | 0 | 0 | 4 | n/a (n/a) [n/a] | 0.000 (0.00 to 0.00) [0.00 to 0.00] | n/a |

## Coverage and runtime

- Files analysed: 79 of 79.
- Static analysis time per file: median 0.0000 s, mean 0.0000 s, max 0.0000 s (this machine: see registry).
- Instrumented runs: {'ok': 79}; time per file: median 0.00 s, max 0.00 s.

## What the instrumented run did

| type | static findings confirmed | refuted | not checked | run error | found only by the run |
|---|---|---|---|---|---|
| preprocessing | 0 | 0 | 0 | 0 | 0 |
| overlap | 0 | 0 | 2 | 0 | 0 |
| multi_test | 0 | 0 | 0 | 0 | 0 |
| group | 0 | 0 | 0 | 0 | 0 |
| temporal | 0 | 0 | 0 | 0 | 0 |
| target_derived | 0 | 0 | 0 | 0 | 0 |
