# Novelty search log

Integrity Rule 1: the novelty search is repeated at every phase boundary. Each entry records what was searched,
what was new, and whether it touches C1 (group/temporal from code), C2 (static-to-dynamic linking), C3 (impact on
the user's own pipeline) or C4 (benchmark). Sources and verification status: `literature/related_work.csv`.

## 2026-09-29, Phase 0 (initial)

Searched: web (group/subject leakage detection in code; temporal leakage in code; per-finding impact by
re-execution; leakage benchmarks), PyPI and GitHub for leakage tools, arXiv 2025-2026.
New since Chapter 2: leakcheck-ml, LeakHound, dataleaks, dataleak-guard (data-level, Sept 2026); bioLeak, BORG
(R); Roth grammar (prevention); mlwhatif, ArgusEyes (instrumented pipelines). Verdict: C1-C4 open, gap narrower.
Details: `docs/PHASE0_REPORT.md`.

## 2026-09-29, Phase 1 boundary

Searched: web ("data leakage detection python notebooks group/temporal static analysis", "GroupKFold /
subject-wise automatic detection ML code linter"), PyPI names (`leakage`, `leak-detector`, `leakguard`,
`ml-leakage`, `leakscan`, `splitcheck`, `leaklint`, `leakagelint`), GitHub repositories created after 2026-09-01.

| New item | Level | Touches | Finding |
|---|---|---|---|
| **scicode-lint** 0.5.0 (Samsonau, arXiv 2603.17893, MIT) | **code**, LLM-executed patterns | **C1 (temporal half)** | `ml-005`: `shuffle=True` in a CV splitter / `cross_val_score` with explicit temporal evidence. `ml-006`: negative `shift`, `center=True`, future slicing. No group pattern among 66. No data-flow, no dynamic confirmation, no impact. Needs a local 8B LLM at run time. |
| leaklint 0.1.0 (MIT) | data | – | Group/temporal overlap when groups/times are passed. Same category as leakcheck-ml. |
| splitcheck 0.2.0 (MIT) | data | – | Row overlap between split files. |

**Verdict: stop condition triggered for the temporal half of C1.** A code-level tool now detects temporal
leakage. Its T1 coverage is partial (shuffled CV only; `train_test_split`'s default shuffle and unshuffled `KFold`
are not covered); its T2 coverage is close to ours. **Group leakage from code, C2, C3 and C4 remain open.**
Reported to the project owner for a decision before Phase 2.

**Decision (project owner, 2026-09-29):** C1 reframed. Primary novelty: group leakage from code. Temporal:
data-flow detection plus confirmation on the data, presented as an improvement over existing code-level checks,
not a first. scicode-lint is added as a temporal baseline and cited in related work. The benchmark gets its own
category (`differentiating`) for cases where the approaches differ; results on it are reported separately.
