# Check of the four-paper comparison table (2026-11-13)

Source of this file and of `docs/report/LeakLens_Comparative_Table_Verified.pdf`: `scripts/make_comparison_table.py`.

## Claims the earlier table made about LeakLens

| Claim | Status | Evidence |
|---|---|---|
| Detects six leak types, including group and temporal | **True** | Rules and tests for all six; TEST first look finds leaks of every type. scicode-lint also covers part of temporal, so do not say "only we do". |
| Hybrid: static analysis plus an instrumented run that hashes rows and tracks entity ids | **True** | Built and tested; on TEST the run added the 2 duplicate-row leaks. It named the patient id correctly only in the second look, after a fix. |
| Reports the score drop after an automatic fix | **Partly** | Works for six kinds of fix: 34 of 70 located TEST leaks. None for multi-test, resampling, pandas statistics, forward-looking features. |
| Example "AUPRC 0.95 to 0.43" | **Not true for LeakLens** | That is the CalibraEEG measurement. LeakLens found nothing on the CalibraEEG code. Remove it. |
| Command-line tool | **True** | leaklens scan, with JSON and SARIF output. |
| Pre-commit hook | **True since 13 November** | Built today; a real pre-commit run failed a leaky file and passed a clean one. |
| GitHub Action / CI gating | **True since 13 November** | Built today; ran on GitHub and uploaded 8 findings to code scanning. |
| No Docker needed, unlike LeakageDetector 2.0 | **Not an advantage** | LeakageDetector 2.0 no longer needs Docker either (its paper). |
| Catches sliding-window leaks | **Not shown** | Missed on CalibraEEG; scicode-lint has a pattern for this and LeakLens does not. |
| Deterministic, no LLM, no GPU, no per-use cost | **True** | By design; tests check the output is identical on repeat runs. |
| Analyses whole notebooks and points at the line | **True** | The frozen scoring rule requires the right line; TEST results are under that rule. |
| At least 90% precision | **Only on our own files** | No false positive on DEV or TEST of the injected benchmark. No figure exists for real notebooks: none is labelled. |
| Reliable overlap detection | **On our own files** | 7 of 9 from code, 9 of 9 with the run. Synthetic copies made by SMOTE cannot be confirmed at run time. |
| Better than these four papers | **Not shown** | None of the four was run against LeakLens. One measured comparison exists: Yang et al., the engine inside LeakageDetector 2.0, on our own files. |

## What could be verified about the four papers

| Paper | How it was checked | Corrections to the earlier table |
|---|---|---|
| LeakageDetector 2.0 (arXiv:2509.15971) | arXiv full text read | Docker is optional, so "heavy Docker" is wrong. The paper does not say the placeholder fix needs manual rewriting. It reports no accuracy of its own. |
| Draoui et al. (FSE 2026) | abstract only; ACM page returns 403 | 451 notebooks, GPT-4o-mini, 14.3 s and the duplicate-records statement are unconfirmed. |
| Alturayeif and Hassine (PeerJ CS 2025) | not opened; PeerJ returns 403 | Nothing confirmed, including title and numbers. Not in `literature/related_work.csv` before today. |
| scicode-lint (arXiv:2603.17893) | arXiv full text read | 24% is for all critical findings, LLM-judged. 11% is its ai-training category on held-out papers. The paper says overlap "remains undetected" but gives no 0.0% figure. 20GB+ VRAM is correct (our earlier note of 16 GB was wrong). The earlier table left out its 65% precision at 100% recall for preprocessing on Yang et al.'s human-labelled notebooks, and its sliding-window overlap pattern. |

## Which of the four could be run against LeakLens

| Tool | Run? | Why |
|---|---|---|
| LeakageDetector 2.0 | engine only | A VS Code extension around the Yang et al. analyser, which was run on TEST (`results/2026-11-12_kaggle_05_yang_test_injected`). |
| Draoui et al. | no | Needs a paid LLM key and an access-restricted package. Owner decision. |
| Alturayeif and Hassine | no | No public code found. |
| scicode-lint | no | Needs a 20 GB GPU; CLAUDE.md reserves the GPU quota for CalibraEEG. Owner decision. |
