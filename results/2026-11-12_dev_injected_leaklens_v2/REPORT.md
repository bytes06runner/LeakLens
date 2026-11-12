# leaklens on the injected benchmark, DEV split

96 files, 89 labelled leaks, 10 files without a leak. Matching and metrics: EVAL_PROTOCOL.md sections 2 to 4. Intervals: 95% percentile bootstrap, 2000 resamples of files (and of base pipelines, in brackets).

**DEV numbers are optimistic by design: the rules were written looking at these files.**

## static, confidence medium or higher (primary)

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 30 | 30 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| overlap | 10 | 8 | 0 | 2 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.800 (0.50 to 1.00) [0.33 to 1.00] | 0.889 |
| multi_test | 8 | 8 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| group | 10 | 3 | 0 | 7 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.300 (0.00 to 0.62) [0.00 to 1.00] | 0.462 |
| temporal | 25 | 25 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| target_derived | 6 | 6 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |

Recall by label category:

| category | found | missed | recall |
|---|---|---|---|
| dynamic_only | 0 | 2 | 0.000 |
| group | 3 | 7 | 0.300 |
| standard | 52 | 0 | 1.000 |
| temporal_common | 7 | 0 | 1.000 |
| temporal_differentiating | 6 | 0 | 1.000 |
| temporal_hard | 12 | 0 | 1.000 |

Files without a leak that received a finding: 0 of 10.

## static, all findings, low included

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 30 | 30 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| overlap | 10 | 8 | 0 | 2 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.800 (0.50 to 1.00) [0.33 to 1.00] | 0.889 |
| multi_test | 8 | 8 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| group | 10 | 3 | 0 | 7 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 0.300 (0.00 to 0.62) [0.00 to 1.00] | 0.462 |
| temporal | 25 | 25 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| target_derived | 6 | 6 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |

## static+dynamic, confidence medium or higher (primary)

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 30 | 30 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| overlap | 10 | 10 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| multi_test | 8 | 8 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| group | 10 | 10 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| temporal | 25 | 25 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| target_derived | 6 | 6 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |

Recall by label category:

| category | found | missed | recall |
|---|---|---|---|
| dynamic_only | 2 | 0 | 1.000 |
| group | 10 | 0 | 1.000 |
| standard | 52 | 0 | 1.000 |
| temporal_common | 7 | 0 | 1.000 |
| temporal_differentiating | 6 | 0 | 1.000 |
| temporal_hard | 12 | 0 | 1.000 |

Files without a leak that received a finding: 0 of 10.

## static+dynamic, all findings, low included

| type | labels | TP | FP | FN | precision (95% CI) | recall (95% CI) | F1 |
|---|---|---|---|---|---|---|---|
| preprocessing | 30 | 30 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| overlap | 10 | 10 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| multi_test | 8 | 8 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| group | 10 | 10 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| temporal | 25 | 25 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |
| target_derived | 6 | 6 | 0 | 0 | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 (1.00 to 1.00) [1.00 to 1.00] | 1.000 |

## Coverage and runtime

- Files analysed: 96 of 96.
- Static analysis time per file: median 0.0017 s, mean 0.0021 s, max 0.0046 s (this machine: see registry).
- Instrumented runs: {'ok': 96}; time per file: median 3.44 s, max 303.81 s.

## What the instrumented run did

| type | static findings confirmed | refuted | not checked | run error | found only by the run |
|---|---|---|---|---|---|
| preprocessing | 17 | 0 | 13 | 0 | 0 |
| overlap | 8 | 0 | 0 | 0 | 2 |
| multi_test | 8 | 0 | 0 | 0 | 0 |
| group | 3 | 0 | 0 | 0 | 7 |
| temporal | 7 | 0 | 18 | 0 | 0 |
| target_derived | 2 | 0 | 4 | 0 | 0 |
