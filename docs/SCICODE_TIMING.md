# scicode-lint on CPU: feasibility measurement and options

Decision asked for: how to run scicode-lint (the temporal baseline, decision 2026-09-29) on the benchmark.
Run: `results/2026-09-29_kaggle_02_scicode_cpu_timing/` (Kaggle CPU session, 4 cores, 32 GB; commit `6a33990`).

## What was run

- scicode-lint 0.5.0 (PyPI), Python 3.13, `--pattern ml-005,ml-006` (its two temporal patterns only).
- Its published setup is vLLM serving `RedHatAI/Qwen3-8B-FP8-dynamic` on a GPU with at least 16 GB (its README:
  "Not practical for laptops or CPU-only setups"). A CPU session cannot run that, so the same model family was
  served by llama.cpp (release b11249, CPU build) as `Qwen3-8B-Q8_0.gguf` behind the same OpenAI-compatible API.
  **This is not the published configuration**; outputs from it would not count as baseline results (Rule 5).
- Inputs: four of our taxonomy examples. Time caps: 25 min per file, 80 min overall.

## Results

| File | Ground truth | Wall time | Outcome |
|---|---|---|---|
| `temporal_pos.py` | temporal leak (T1) | > 1500 s | hit the 25-min cap |
| `temporal_neg.py` | clean | 1094 s | finished; 0 findings (correct) |
| `temporal_pos_future_feature.py` | temporal leak (T2) | > 1500 s | hit the 25-min cap |
| `preprocessing_neg.py` | clean (non-temporal) | 493 s | finished; 0 findings (correct) |

- Generation speed: **1.42 tokens/s** mean (llama.cpp log), prompt processing about 2.7 tokens/s.
- Setup: model download 172 s, everything else under 20 s. The client ran without modification against llama.cpp.
- The leaky files take longer, probably because the model reasons at length when it suspects a problem (its
  thinking budget is up to 3,584 tokens per pattern).

## Is CPU practical?

**No, not for the full benchmark.**
- Even with only the 2 temporal patterns, it takes 8 to 25+ minutes per file. The Phase 7 run needs at least the
  TEST items (79 injected + the real TEST notebooks, likely 50 to 75). That is roughly 50 to 75+ CPU-hours, and
  still not the published configuration.
- All 66 patterns would multiply generation by roughly 30, which makes it impossible.

## Options (nothing has been spent)

| # | Option | Fidelity to "as released" | Cost / resources | Notes |
|---|---|---|---|---|
| 1 | **Rent a cloud GPU with FP8 support (e.g. an NVIDIA L4) for a few hours; run exactly the published setup** | exact | small hourly GPU rental; hours to be estimated with a 10-file pilot first | Needs an account with a GPU provider (manual steps for you). Cleanest for Rule 5. **Recommended if a small budget is acceptable.** |
| 2 | Ask the scicode-lint author to run their tool on our TEST files | exact | free; depends on their goodwill and time | Polite email with the TEST file list; fits the collaborative tone of the LeakCheck request. Good fallback, or in parallel with 1. |
| 3 | Kaggle GPU (2x T4, shared with CalibraEEG's quota) | approximate: T4 cannot run the FP8 model as published (to be confirmed), so a 16-bit variant split over 2 GPUs | a few GPU-hours of CalibraEEG's quota | Only with your say-so on the quota. |
| 4 | Kaggle CPU, temporal patterns only, TEST only, llama.cpp | approximate (different runtime and quantisation) | about 50 to 75 CPU-hours over several sessions; free | Would have to be labelled "approximate configuration" in the paper. |
| 5 | Do not execute; compare against its pattern definitions only | none | free | Weakest; a reviewer could object. |

My recommendation: **1**, with **2** in parallel. If neither works, **4**, clearly labelled.
