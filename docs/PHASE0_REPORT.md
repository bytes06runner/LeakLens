# Phase 0 report: setup, novelty check, baseline runnability

Date: 2026-09-29. Status: **complete, waiting for go/no-go on Phase 1.**
Sources for every claim below are in [`literature/related_work.csv`](../literature/related_work.csv) with a `verified` column.

## 1. Verdict on novelty (Integrity Rule 1)

**The stop condition is not triggered.** We found no tool that
(a) detects group or temporal leakage by analysing Python ML **source code**, or
(b) estimates per-finding impact by **re-executing the user's own pipeline** with an automatic fix.

**The gap is narrower than Chapter 2 says.** Since Chapter 2 was written, several **data-level** tools
have appeared (all first released 2026-09-05 to 2026-09-26) that detect group and temporal leakage once the
user hands over the train and test tables. One of them also estimates inflation with a proxy model.

| What Chapter 2 claims | What we found | Consequence |
|---|---|---|
| No tool detects group leakage; none detects temporal leakage from code | True **for code**. For **data**: leakcheck-ml detects both with no column hints; LeakHound, dataleaks, BORG (R), bioLeak (R) and Deepchecks (dates only) detect one or both when columns or splits are declared | The dynamic entity/time overlap check (Phase 5) is **not novel on its own**. It must be linked to code, need no user declaration, and cover CV splitters |
| No tool estimates impact | LeakHound trains **its own model** on the given split and on a chronological split (+0.042 AUC on our temporal probe). bioLeak and Roth 2026 measure inflation inside their own frameworks. mlwhatif re-executes user pipelines with patches, but only for data-cleaning what-ifs | Our claim becomes: impact **on the user's own pipeline and reported metric**, by re-executing a fixed copy, per finding |
| Only one public labelled leakage dataset | Yang et al.'s labels are public (99 notebooks; no licence file). LeakCheck's Zenodo package (CC-BY-4.0) says it holds datasets, but the files are access-restricted | Still no public benchmark with group or temporal labels |
| ReproGuard: pattern rules | Confirmed: code-level regex heuristics (preprocessing before split, target-like column names, test data in fit, suspicious metrics). No group or temporal rule | Code-level, but no overlap with our new types |

### Sharpened contributions (proposed; your call)

1. **C1: group and temporal leakage from code.** Static rules on splitter calls (`train_test_split`, `KFold`,
   `ShuffleSplit`, `cross_val_score` with default CV) with a candidate entity or time column in the data flow,
   including IDs derived from file paths (EEG windows). No existing code-level tool covers this.
2. **C2: static-to-dynamic linking with no declaration.** Static analysis nominates the split call site and the
   candidate columns; the instrumented run checks overlap per fold at that call site. Data-level tools need the
   user to export split files and, for most, to name the column. They become **baselines for the dynamic pass**:
   we give them the same materialised splits and compare.
3. **C3: impact on the user's own pipeline.** Apply the canonical fix to a sandboxed copy, re-run, diff the
   metric the notebook reports. On the injected benchmark the true inflation is known (clean vs leaky version),
   so we can measure **estimation error** and compare against LeakHound's proxy estimate. This is the most
   defensible "better result" we can aim for, and it can also fail: if the proxy is as accurate, we say so.
4. **C4: benchmark with group and temporal labels**, which no public dataset has.

## 2. Baseline runnability (Integrity Rule 5)

Probes: four small scripts we wrote ([`baselines/probes`](../baselines/probes)). They are not benchmark items.
Data-level tools got the probes' leaky train/test splits, once with no hints and once with the column named.
Raw outputs: `results/2026-09-29_phase0_data_level_probe/`.

| Tool (version) | Level | Licence | Runs today? | Group probe | Temporal probe | Impact |
|---|---|---|---|---|---|---|
| Yang et al. analyser (commit a7d038b, 2023) | code | MIT | **Yes, on Kaggle** (§2.1). Preprocessing probe: detected. Clean probe: silent | **Not flagged** (only the model pair found) | **Not flagged**, including the lag feature built before the split | no |
| LeakageDetector 2.0 | code (IDE) | MIT | Not tested: VS Code extension, no CLI. Chapter 2 says 1.0 wraps Yang's analyser; not re-verified for 2.0 | – | – | no |
| LeakCheck / ml-slicer (Draoui 2026) | code + LLM | no licence file | **Not run.** Needs an LLM API key and an ml-slicer Docker service. Decision needed (§4) | – | – | no |
| ReproGuard 0.5.2 | code (heuristic) | proprietary RSL 1.0 | **Not run.** Licence §4(d) forbids using its ideas or check logic to build a competing tool. Decision needed (§4) | – | – | no |
| Deepchecks 0.19.1 (last release 2024-12) | data | AGPL-3.0 | **Fails** on Python 3.12 with current numpy/pandas/sklearn/setuptools. Runs on Python 3.11, numpy 1.26.4, pandas 2.2.3, sklearn 1.5.2, setuptools<81 | Samples Mix: ratio 0.0 (no group check exists) | Date overlap 1.0 **only when the datetime column is declared** | no |
| leakcheck-ml 0.3.0 | data | MIT | Yes | **Detected, no hints** (40/40 groups) | **Warned, no hints**; failed with hint | no |
| LeakHound 0.5.0 `[impact]` | data | AGPL-3.0 | Yes | Missed without hint; detected with hint; impact "no measurable inflation" | Missed without hint; detected with hint; **+0.042 AUC** proxy estimate | proxy model |
| dataleaks 0.1.2 | data | MIT | Yes | Detected (split_overlap, high) | **Missed** (its temporal checks look at feature timestamps, not split order) | no |

### 2.1 Yang et al. analyser

The laptop has no Docker, Homebrew or Souffle, so the tool cannot be built locally. Kaggle job
`kaggle/00b_yang_baseline` builds it as its Dockerfile does (Souffle PPA, authors' pyright fork with Node 16,
Python 3.8 venv) and runs it on the four probes. It works: build 190 s (pyright 128 s), 4.7 to 6.5 s per probe.
Details in §5.

## 3. Environment

| Item | Value |
|---|---|
| Laptop | Python 3.12.14 via uv 0.12.19; `uv sync`, `pytest` (4 passed), `ruff` clean |
| Pins | numpy 2.0.2, pandas 2.3.3, scikit-learn 1.6.1, scipy 1.16.3: identical to Kaggle CPU |
| Kaggle API | Works with existing credentials (`kaggle kernels list --mine`) |
| Kaggle sandbox profile (`leaklens-00-smoke-offline`, CPU, internet off) | Python 3.12.13; 4 CPUs; 32.9 GB RAM; 20.9 GB free in `/kaggle/working`; pypi.org, github.com and 1.1.1.1 all blocked |
| Other libraries on Kaggle | nbformat 5.10.4, nbconvert 6.4.5, imblearn 0.14.1, xgboost 3.2.0, lightgbm 4.6.0, torch 2.10.0+cpu, tensorflow 2.20.0, keras 3.13.2, statsmodels 0.14.6 |

## 4. Surprises and risks

1. **Kaggle injects three tokens into every session, even with internet off**:
   `KAGGLE_API_V1_TOKEN`, `KAGGLE_DATA_PROXY_TOKEN`, `KAGGLE_USER_SECRETS_TOKEN` (names only were logged).
   Untrusted notebooks could read them. Mitigation for Phase 5: run each untrusted notebook in a child process
   with a scrubbed environment (allow-list of variables), and test in Phase 5 whether any Kaggle-internal
   endpoint is reachable with internet off. Rule 7 as written ("no credentials attached") cannot be met by
   Kaggle settings alone.
2. **Five new data-level leakage tools appeared in September 2026.** The field is moving weekly. We should
   re-run the novelty search at every phase boundary and before submission.
3. **Deepchecks is effectively unmaintained** (last release 2024-12) and breaks on current Python stacks. We will
   run it in its own pinned Python 3.11 environment (`baselines/data_level/deepchecks_env_freeze.txt`).
4. **Numbers in Chapter 2 to correct**: none were wrong among those we checked (Yang 97.6/67.8/29.6/3.23,
   Kapoor 17 fields/294 papers/8 types, Brookshire 17 of 63 studies, Roth |dAUC|<=0.005). The Draoui "+22% / +15% F1"
   figures could not be opened (ACM page 403, Zenodo files restricted); they are marked unverified.
5. **macOS only**: numpy 2.0.2 on Apple Silicon prints spurious matmul overflow warnings in sklearn. Results are
   unaffected; Kaggle (Linux) does not show them.

## 5. Yang et al. build result

Kaggle job `srijeetbanerjee/leaklens-00b-yang-baseline`, CPU session with internet on (to install the tool),
LeakLens commit `76f2612`, tool commit `a7d038b` with its pyright submodule. Raw output:
`results/2026-09-29_kaggle_00b_yang_baseline/`.

| Step | Exit | Seconds |
|---|---|---|
| Souffle from PPA | 0 | 36.6 |
| Node 16.20.2 | 0 | 2.8 |
| Clone + submodule | 0 | 10.5 |
| pyright fork build (lerna 4) | 0 | 128.0 |
| Python 3.8 venv + requirements | 0 | 12.6 |

| Probe | Ground truth | Yang output | Seconds |
|---|---|---|---|
| p1 | preprocessing | `PreProcessingLeak` on `X` reaching `LogisticRegression.fit` (true positive) | 6.5 |
| p2 | group | model pair only, no leak relation (miss, as expected: type not supported) | 5.3 |
| p3 | temporal | model pair only, no leak relation (miss, as expected) | 6.3 |
| p4 | clean | model pair only, no leak relation (true negative) | 4.7 |

So Yang et al. is runnable as released, but only inside a Linux session. For Phase 7 it will run as a Kaggle job
over the benchmark (static analysis only, the analysed code is never executed).

## 6. What I need from you

1. **Go / no-go** on the sharpened contributions C1 to C4 (§1). In particular: is it acceptable that the dynamic
   overlap check is framed as linked-to-code rather than novel on its own?
2. **LeakCheck:** do you want it as a baseline? It needs an LLM API key (cost per notebook) and a local Docker
   service. If yes, which provider and budget? It only covers preprocessing and overlap.
3. **ReproGuard:** its licence forbids using its ideas for a competing tool. Options: (a) exclude it and say why
   in the paper, (b) email the author for written permission to benchmark it. I recommend (a) unless you want (b).
4. **Licence for LeakLens** itself. The repo currently has none (which means all rights reserved). MIT or
   Apache-2.0 are usual for research tools; AGPL would block some baselines' users. Your choice.
