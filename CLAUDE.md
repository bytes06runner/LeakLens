# LeakLens: Build Instructions for Claude Code

You are the lead research software engineer on LeakLens. Read this whole file before doing anything. Re-read "Integrity Rules" at the start of every session and before reporting any number.

## 1. What we are building and why

LeakLens detects **data leakage** in Python ML code (scripts and Jupyter notebooks): any path by which evaluation data influences training, which inflates reported scores.

The research gap, as narrowed by the Phase 0 novelty check (docs/PHASE0_REPORT.md, 2026-09-29):
1. **Coverage, from code.** Existing code-level tools (Yang et al. ASE 2022, NBLyzer, LeakageDetector 1.0/2.0, Draoui et al. 2026 LLM slicing) detect preprocessing, overlap and multi-test leakage. None detects **group leakage** (same patient/user/device in train and test) **from source code**. For **temporal leakage**, the Phase 1 novelty search (docs/NOVELTY_LOG.md) found scicode-lint (Samsonau 2026, LLM-executed patterns): it flags shuffled CV splitters on explicitly temporal data and forward-looking shifts/centered windows, but does not mention `train_test_split`'s default shuffle, treats unshuffled KFold as correct, and has no data-flow, dynamic confirmation or impact. LeakLens's temporal detection is therefore an **improvement over existing code-level checks, not a first** (decision 2026-09-29).
2. **Data-level checks exist but are disconnected from code.** Since September 2026, data-level tools (leakcheck-ml, LeakHound, dataleaks; also Deepchecks for dates, and BORG/bioLeak in R) detect group and temporal overlap once the user exports train/test tables and, for most, names the column. They give no code location and do not handle cross-validation folds. An entity/time overlap check is therefore **not novel on its own**; ours is novel only as the confirmation step of a code-level finding, with no user declaration.
3. **Severity mismatch.** Roth 2026 (arXiv:2604.04199) found scaler-on-full-data leakage changes AUC by at most 0.005, while boundary (group/temporal) leakage is invisible under random CV. Code-level tools focus on the least harmful type.
4. **Impact on the user's own pipeline is unmeasured.** Code-level tools give binary flags. LeakHound estimates inflation with its own proxy model on the given split; bioLeak and Roth measure inflation inside their own frameworks; mlwhatif re-executes user pipelines but only for data-cleaning what-ifs. None re-runs the user's own pipeline with a fix and reports the change in the user's own metric per finding.

LeakLens contributions (approved 2026-09-29):
- **C1. Group leakage detected from source code** (primary novelty; no existing tool does this), including CV helpers with default CV and file-path-derived entity IDs.
- **C1b. Temporal leakage by data-flow analysis plus confirmation on the actual data**, positioned as an improvement over existing code-level checks (scicode-lint), not a first. scicode-lint is a temporal baseline. The benchmark has its own category for cases where the approaches differ (e.g. `train_test_split`'s default shuffle on time-ordered data, unshuffled KFold, temporal evidence visible only through data flow, negative shift used for the target), and results on it are reported separately.
- **C2. Static-to-dynamic linking without user setup.** The static pass nominates the split call site and candidate entity/time columns; an instrumented run checks overlap at that call, fold by fold. Data-level tools are baselines for this dynamic pass, given the same materialised splits.
- **C3. Per-finding impact on the user's own pipeline**: canonical fix applied to a sandboxed copy, re-run, metric diff. On the injected benchmark the true inflation is known, so estimation error is measured and compared against LeakHound's proxy estimate. If the proxy is as good, we report that.
- **C4. A labelled benchmark including group and temporal leakage**, which no public dataset has.
- Supporting: a mining study of prevalence and measured impact; usable software (CLI, pre-commit, GitHub Action, SARIF, PyPI; MIT licence).

Companion project: CalibraEEG (same author). Its evaluation regimes are a free ground-truth case study (Phase 7).

## 2. Integrity Rules (non-negotiable)

1. **Novelty check first, and again at every phase boundary.** Before building, and at the end of every phase, re-run the novelty search (group/temporal leakage from code; per-finding impact by re-executing the user's pipeline; new leakage tools on PyPI/GitHub/arXiv). Log each search in `docs/NOVELTY_LOG.md`. If a tool covering C1 or C3 appears, stop and report.
2. **Never fabricate.** No invented citations, tool capabilities or numbers. Every literature claim goes in `literature/related_work.csv` with title, venue, year, DOI/URL and a `verified` column. Anything you could not open and read is marked unverified.
3. **The detector must not label its own benchmark.** Benchmark labels come from (a) injected leaks with known ground truth, and (b) human labels by me and a teammate. You may propose labels, but a human confirms every real-notebook label. Report inter-rater agreement (Cohen's kappa) on the double-labelled subset.
4. **Freeze the test split of the benchmark.** Split the benchmark into DEV and TEST before writing detection rules. Rules and thresholds are tuned on DEV only. TEST is scored once per release, and any rule change after seeing TEST results is logged in `EVAL_CHANGES.md` with the reason.
5. **Baselines run as released.** Existing tools are run with their published defaults. If a baseline cannot run on some input, report that as a coverage result; never drop those inputs silently.
6. **Report precision and recall per leakage type**, with confidence intervals. No single headline F1 hiding a weak type.
7. **Untrusted code never runs on the laptop.** Notebooks from the internet are executed only inside Kaggle sessions with **internet off**, and inside those sessions only through `leaklens.sandbox`: a child process with an allow-listed environment (Kaggle injects `KAGGLE_API_V1_TOKEN`, `KAGGLE_DATA_PROXY_TOKEN`, `KAGGLE_USER_SECRETS_TOKEN` into every session; these must not be visible), a throwaway working directory, and a timeout. Never put any token into a Kaggle session that runs untrusted code.
8. **No shaming.** The mining study reports aggregates. Never name individual notebook authors as leaky in outputs, papers or issues.
9. **Respect licences.** Store notebook URLs and hashes; redistribute notebook content only where the licence allows. The benchmark release includes only redistributable items plus a download script for the rest.
10. **Report bad results.** If LeakLens loses to a baseline on some type, that goes in the paper.
11. **No code from other tools.** LeakLens is MIT-licensed. Baselines may be installed and run in separate environments, but no code, rule, pattern or threshold from any other tool is copied into LeakLens (especially AGPL Deepchecks and LeakHound, and proprietary ReproGuard). ReproGuard is excluded entirely: do not read or use its check logic (see `docs/EXCLUDED_BASELINES.md`).
12. **Injected inflation is by construction.** The synthetic generators were adjusted after seeing seed-0 inflation (EVAL_CHANGES.md #1). True inflation on the injected benchmark may be used ONLY to evaluate detection and impact-estimation accuracy, where the true answer is known, never as evidence of real-world severity. Severity claims come only from real notebooks and the CalibraEEG case study. Wording: `docs/PAPER_WORDING.md`.

## 3. Compute and environment

- **Laptop (MacBook Air M5, fanless):** writing code, unit tests, small dev runs. Never runs untrusted code, never runs the full mining study. Local project data under ~5 GB.
- **Kaggle CPU sessions:** mining, large-scale static analysis, sandboxed re-execution. **This project needs no GPU.** Do not use GPU sessions; the GPU quota is reserved for CalibraEEG.
- Python 3.12, `uv`, pinned lockfile. Core: `libcst` or `ast`, `nbformat`, `nbconvert`, `pandas`, `numpy`, `scikit-learn`, `pytest`, `hypothesis`, `click`, `rich`, `sarif-om` (or hand-written SARIF), `kaggle`. Add others with a reason.
- Reuse the Kaggle workflow from CalibraEEG (code packaged as a private Kaggle Dataset, jobs pushed and pulled via the API, resumable, per-item checkpointing).
- **GitHub API access:** if mining GitHub, I will create a fine-grained, read-only public token and store it in the macOS keychain or an environment variable myself. **Never ask me to paste it into chat. Never print it. Never write it to the repo or to Kaggle.**
- **I am new to this workflow.** Any manual step (tokens, website settings, labelling UI) gets numbered steps, what success looks like, and a wait for my confirmation.

## 4. Leakage taxonomy (write `docs/TAXONOMY.md` in Phase 1)

Six types, each with a precise definition, a static rule, a dynamic check and a canonical fix. Map each to Kapoor & Narayanan's eight types and Yang et al.'s three.

| Type | Static signal | Dynamic confirmation |
|---|---|---|
| Preprocessing | fit/fit_transform of a transformer, selector, imputer or resampler on data that later flows to test | transformer statistics computed on rows later used for evaluation |
| Overlap / duplicates | resampling or augmentation before the split; concatenation of train and test | row fingerprints (exact and near-duplicate) present in both splits |
| Multi-test (selection) | test data used in more than one model/setting selection step | same evaluation rows scored for multiple candidates before a final report |
| Group (entity) | random splitter (train_test_split, KFold, ShuffleSplit) on data with a candidate entity column (patient_id, subject, user, device, session, file-derived IDs) | the same entity value appears in both splits |
| Temporal | shuffled split or random CV on data with a datetime or ordered index column; lag features computed before the split | max(train time) > min(test time) for the same series |
| Target-derived features (heuristic) | features computed from the label or post-outcome columns | very high single-feature predictive power; flag only, low severity |

Group-column detection is heuristic: column names, cardinality (many repeated values), and file-path-derived IDs. It must report its confidence and never claim certainty.

## 5. Repository structure

```
leaklens/
  CLAUDE.md
  EVAL_PROTOCOL.md       # frozen evaluation protocol (Phase 3)
  EVAL_CHANGES.md
  README.md
  pyproject.toml / uv.lock
  src/leaklens/
    ingest/              # .py and .ipynb loading, cell ordering, magics
    static/              # AST, data-flow graph, rules per type
    dynamic/             # instrumentation, row fingerprints, entity/time overlap
    impact/              # counterfactual fixes, sandbox runner, metric diff
    report/              # CLI output, JSON, SARIF, HTML
    cli.py
  integrations/          # pre-commit hook, GitHub Action
  benchmark/             # manifests, labels, injection scripts (no raw code unless licensed)
  baselines/             # runners for existing tools
  mining/                # corpus sampling and Kaggle jobs
  kaggle/                # notebooks + kernel-metadata.json + beginner README
  literature/related_work.csv
  tests/
  results/               # one folder per run, never overwritten, registry.csv
  docs/
```

## 6. Phases

Stop at the end of every phase with a short report (what was done, key numbers, surprises, what you need from me). Wait for my go.

### Phase 0: Setup and novelty check
- Environment, tests running, Kaggle connection verified (reuse existing credentials; do not ask me to paste them).
- Novelty check (Rule 1), with verified entries in `related_work.csv`. Specifically search for: group or subject leakage detection in code; temporal leakage detection in code; per-finding impact quantification by re-execution; existing leakage benchmarks and whether they are public (including the labelled data of Yang et al. 2022).
- Check whether existing tools can actually be run today (Yang et al.'s analyser, LeakageDetector, Draoui et al.'s LeakCheck/ml-slicer, Deepchecks). Record versions and licences.
- Report: what exists, where our gap is, which baselines are runnable.

### Phase 1: Taxonomy and specification
- Write `docs/TAXONOMY.md` (Section 4) with a minimal positive and negative code example per type.
- Write `docs/SPEC.md`: inputs supported, finding format (file, line, type, confidence, evidence, suggested fix), severity levels, exit codes for CI.

### Phase 2: Benchmark
- **Injected set:** take clean, runnable pipelines (tabular, time-series, grouped data such as EEG-style windows and multi-visit patient data) and inject each leakage type with a mutation script. Ground truth is known by construction. Also keep clean controls.
- **Real set:** sample real notebooks (Kaggle and GitHub), stratified by library and data type. You propose candidate labels; I and a teammate label independently using a simple labelling sheet you prepare with clear instructions; report kappa.
- Split into DEV and TEST **before** writing detection rules (Rule 4). Record the split in `benchmark/SPLIT.md` and commit it.
- Report: counts per type, per source, per split.

### Phase 3: Evaluation protocol (freeze)
- Write `EVAL_PROTOCOL.md`: metrics (precision, recall and F1 per type, with bootstrap CIs resampling notebooks), matching rule between a finding and a label (same type and overlapping line range), baselines and how they are run, runtime measurement, impact-estimation metrics.
- Commit "Freeze evaluation protocol" only after I approve a one-page plain-language summary.

### Phase 4: Static analyser
- Ingest notebooks in execution order where possible, falling back to cell order, and record which was used.
- Build a data-flow graph over DataFrames and arrays through pandas, NumPy and scikit-learn calls, including Pipelines, ColumnTransformer and common resamplers.
- Implement the rules per type on DEV only. Unit tests for every rule with positive and negative cases. Property-based tests with `hypothesis` for the graph builder where practical.
- Report DEV precision and recall per type.

### Phase 5: Dynamic analyser
- Instrument split functions, fit/transform calls, and evaluation calls by wrapping library entry points during a run.
- Row fingerprints (hashes, plus near-duplicate detection for numeric rows), entity-overlap and time-overlap checks, using candidate columns from static analysis.
- Dynamic runs on real notebooks only on Kaggle, internet off (Rule 7).
- Report: which static findings are confirmed or refuted dynamically, and new findings only the dynamic pass catches.

### Phase 6: Impact estimation
- For each confirmed finding, apply the canonical fix in a sandboxed copy (e.g. move the split before preprocessing, replace random split with GroupKFold or TimeSeriesSplit on the detected column), re-run, and diff the reported metric.
- Report impact as a distribution per leakage type. Flag fixes that fail to run as "impact unknown" rather than dropping them.
- This is our main new contribution. Be conservative: if a fix changes more than the leak (e.g. alters the model), mark the estimate as unreliable.

### Phase 7: Evaluation
- Score LeakLens and all runnable baselines on TEST once. Per-type precision and recall with CIs, runtime per notebook, share of inputs each tool can analyse.
- **CalibraEEG case study:** run LeakLens on the CalibraEEG code paths for regimes A (random windows), B (within-patient) and C (leave-one-patient-out). Expected: temporal/overlap leakage flagged in A, group leakage flagged in A and B, nothing in C. Report exactly what it finds, including misses.
- Ablations: static only vs static plus dynamic.

**Preprint checkpoint.** As soon as group detection works on the injected benchmark (end of Phase 4 on DEV, or Phase 7 on TEST, whichever first gives a defensible result), stop and flag to the project owner: evaluate posting an arXiv preprint to timestamp the contribution. Do not post anything without the owner's decision.

### Phase 8: Mining study
- Stratified sample of public notebooks (size decided with me, based on Kaggle CPU throughput). Prevalence per type with CIs.
- Impact on the re-executable subset (Phase 6 machinery).
- Key analysis: does prevalence line up with measured severity?

### Phase 9: Release and paper outputs
- CLI, pre-commit hook, GitHub Action, SARIF output tested against GitHub code scanning, docs, PyPI package, versioned release.
- `results/final/`: all tables and figures (CSV, LaTeX, PDF/PNG).
- `LIMITATIONS.md`: honest list (heuristic group detection, library coverage, sandbox fidelity, sample representativeness).
- Target venues to evaluate with me: MSR, ICSE tool/demo track, ASE, FSE, Journal of Open Source Software.

## 7. Working style

- Small commits, clear messages, tests before reporting a phase done.
- Config in YAML, no magic numbers in code.
- Every run logged to `results/registry.csv` with commit hash.
- Ask before deleting anything in `benchmark/` or `results/`.
- When reporting numbers, state the split (DEV or TEST), the leakage type, and the tool.
- Short, direct reports. No hype words. If something is bad, say so.

## 8. Start

Begin with Phase 0. Report and wait for my go.
