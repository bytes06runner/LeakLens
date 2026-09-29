# Kaggle workflow (beginner guide)

Heavy or untrusted work runs on Kaggle **CPU** sessions. The laptop only pushes code and pulls results.
LeakLens never uses GPU sessions (that quota belongs to CalibraEEG).

## One-time setup (already done, shared with CalibraEEG)

1. Kaggle account `srijeetbanerjee`, API token in `~/.kaggle/` with permissions `600`.
   Never paste it into chat, code, git, or a Kaggle session.
2. Check it works without printing it: `uv run kaggle kernels list --mine --page-size 3`.
   Success looks like a table of your kernels.

## Two session profiles

| Profile | `enable_internet` | Used for | May run untrusted code? |
|---|---|---|---|
| **sandbox** | `"false"` | executing notebooks from the internet (Phases 5, 6, 8) | yes, in a child process with a scrubbed environment |
| **tooling** | `"true"` | installing baseline tools, fetching our own code | **no**: only our code and trusted tools |

Phase 0 finding: even with internet off, Kaggle sets `KAGGLE_API_V1_TOKEN`, `KAGGLE_DATA_PROXY_TOKEN` and
`KAGGLE_USER_SECRETS_TOKEN` in the environment. The sandbox runner (Phase 5) must start untrusted code with an
allow-listed environment so these are not visible to it.

## Jobs

| Folder | Kernel slug | Profile | Purpose | Status |
|---|---|---|---|---|
| `00_smoke_offline/` | `leaklens-00-smoke-offline` | sandbox | network blocked? versions, CPU, RAM, env token names | done 2026-09-29 |
| `00b_yang_baseline/` | `leaklens-00b-yang-baseline` | tooling | build Yang et al.'s analyser, run on 4 probes | done 2026-09-29 |

## Everyday commands (from the repo root)

```bash
scripts/kaggle_push.sh kaggle/<job_folder>        # refuses if git is dirty; stamps the commit into the job
uv run kaggle kernels status srijeetbanerjee/<slug>
uv run kaggle kernels output srijeetbanerjee/<slug> -p results/<date>_<job>
```

After pulling, add one row to `results/registry.csv`. Result folders are never overwritten.
