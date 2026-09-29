# Baselines

Existing tools are run **as released, with published defaults** (Integrity Rule 5). If a tool cannot analyse an
input, that is recorded as a coverage result, never dropped.

| Tool | Level | Version / commit | Where it runs | Environment | Status |
|---|---|---|---|---|---|
| Yang et al. leakage-analysis | code | `a7d038b` (2023-05-02) | Kaggle CPU job | Souffle (PPA), pyright fork, Node 16.20.2, Python 3.8 | runnable |
| scicode-lint | code (LLM-executed patterns) | 0.5.0 | needs vLLM + Qwen3-8B-FP8 on a >=16 GB GPU (published setup) | Python 3.13 | temporal baseline; CPU feasibility measured, see docs/SCICODE_TIMING.md |
| splitguard | runtime (instruments user code) | 0.1.0 | Kaggle CPU (offline) inside the sandbox | Python 3.12 | candidate baseline for the dynamic pass (C2); group only with declared ids; not yet run |
| LeakageDetector 2.0 | code (VS Code) | – | – | – | not tested (GUI only) |
| LeakCheck + ml-slicer | code + LLM | repo HEAD 2026-01-11 | – | LLM API key + Docker slicer | not run, decision pending |
| ReproGuard | code (heuristic) | 0.5.2 | – | – | not run: licence forbids use for a competing tool |
| Deepchecks | data | 0.19.1 | laptop | Python 3.11 env, see `data_level/deepchecks_env_freeze.txt` | runnable only in pinned old stack |
| leakcheck-ml | data | 0.3.0 | laptop / Kaggle | Python 3.12 | runnable |
| LeakHound `[impact]` | data | 0.5.0 | laptop / Kaggle | Python 3.12 | runnable |
| dataleaks | data | 0.1.2 | laptop / Kaggle | Python 3.12 | runnable |

- `probes/`: four tiny scripts we wrote to check each tool runs. **Not** benchmark items.
- `data_level/make_splits.py`, `data_level/run_tool.py`: feed the probes' leaky splits to data-level tools, with
  and without column hints.

Data-level tools need materialised train/test tables, so in Phase 7 they are compared against LeakLens's
**dynamic** pass on the same splits, and their "needs a hint" behaviour is reported.
