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

## 2026-09-29, Phase 2 boundary

Searched: web ("group leakage detection source code static analysis notebook GroupKFold tool 2026"; "arXiv 2026
data leakage ML code impact estimation re-execution counterfactual fix notebooks"), PyPI names (`leakage-lint`,
`mlleak`, `leakfinder`, `leakdetect`, `notebook-leakage`, `leak-audit`, `splitguard`, `groupleak`), GitHub
repositories created after 2026-09-20 and repositories mentioning "group leakage" created after 2026-09-01.

| New item | Level | Touches | Finding |
|---|---|---|---|
| **splitguard** 0.1.0 (Aiello, MIT, first release 2026-06-27) | **runtime**, instruments the user's own code | **C2 (partly), C1 (claim overlap)** | Patches `train_test_split`, CV `.split` and every `fit`; tracks held-out row identity; reports the exact line; per-fold CV tracking. Group leakage **only when the user registers group ids** (`mark_groups`/`guard(groups=...)`); no automatic entity inference in its source. No temporal, multi-test, target-derived, or impact. README markets it as "the one tool that automatically catches group leakage". |
| mlleak 0.1.1 (MIT, 2025-12-24) | data | – | Group/temporal overlap with declared columns; same category as leakcheck-ml. |
| (own repo) | – | – | The public LeakLens repository is already indexed by web search. |

**Missed earlier:** splitguard was released three months before Phase 0 and was not found by the Phase 0 or
Phase 1 searches (queries were phrased around "static analysis" and "notebooks"; its PyPI summary says "at
runtime"). Future searches add runtime/instrumentation phrasing.

**Verdict: partial overlap; reported to the project owner before Phase 3.** C1 as defined (group leakage found in
source code, with the entity inferred from names, cardinality or file paths, no execution, no declaration) is not
covered. C2's mechanism (checking entity overlap at the split call, per fold, pointing at the line) exists in
splitguard once groups are declared; LeakLens's remaining novelty in C2 is that the static pass supplies the
entity column so no declaration is needed. C3 is not covered. The README's claim "no code-level tool detects group
leakage" must be qualified: splitguard detects it at runtime with declared groups.
