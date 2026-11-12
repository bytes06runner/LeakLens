# Phase 2 report: benchmark

Date: 2026-09-29. Status: **injected set complete; real set sampled and split, waiting for human labels;
stopped for decisions (novelty finding, scicode-lint route, labelling size).**

## 1. Novelty re-check at the Phase 2 boundary (Rule 1): partial overlap found

**splitguard** (MIT, first release 2026-06-27; missed by the Phase 0/1 searches) instruments the user's code at
runtime: it patches `train_test_split`, CV `.split` and every `fit`, tracks held-out row identity, points at the
exact line and tracks CV folds. It detects group leakage **only for group ids the user registers**
(`mark_groups`, `guard(groups=...)`); its source has no entity inference. No temporal, multi-test,
target-derived or impact. Its README markets it as "the one tool that automatically catches group leakage".

| Contribution | Status after splitguard |
|---|---|
| C1 group leakage from source code, entity inferred (names, repetition, file paths), no execution | not covered |
| C2 overlap check at the split call, per fold, pointing at the line | **mechanism exists** in splitguard once groups are declared; our remaining novelty is that the static pass supplies the entity, so no declaration is needed |
| C3 impact on the user's pipeline | not covered |

README and CLAUDE.md now qualify the group claim ("no static tool; splitguard at runtime with declared ids").
Details: `docs/NOVELTY_LOG.md`, `literature/related_work.csv` (now 30 entries).

## 2. Your Phase 1-2 decisions, applied

| Item | Done |
|---|---|
| Nested stale `leaklens/` folder | deleted (was byte-identical to `e2a86a5` plus caches) |
| LeakCheck email | "sent" entry removed; recorded as drafted, sending not yet confirmed |
| Repo private | **not recorded: GitHub still serves it publicly** (unauthenticated API returns 200, and a web search already lists it) |
| By-construction inflation | CLAUDE.md Rule 12, `EVAL_CHANGES.md` #1, `docs/PAPER_WORDING.md`, `docs/EVAL_PROTOCOL_NOTES.md` |
| DEV file-path entity base | `grp_imaging` (per-patient image folders), 11 items; TEST unchanged (checked against `1b2084b`); `EVAL_CHANGES.md` #2 |

## 3. Injected set

175 files generated from 13 base pipelines by `benchmark/injected/generate.py` (mutation operators in
`operators.py`, synthetic data in `datagen.py`). Ground truth is known by construction; every leaky file has a
ground-truth fixed version in `_groundtruth/fixed/` for measuring true inflation. Counts (details and hashes:
`benchmark/SPLIT.md`):

| | DEV | TEST | total |
|---|---|---|---|
| files | 96 | 79 | 175 |
| clean / trap files | 7 / 3 | 6 / 3 | 13 / 6 |
| labelled leaks | 89 | 73 | 162 |
| group | 10 | 7 | 17 |
| temporal (common / differentiating / hard) | 25 (7 / 6 / 12) | 25 (5 / 7 / 13) | 50 |
| preprocessing | 30 | 22 | 52 |
| overlap (of which dynamic-only raw duplicates) | 10 (2) | 9 (2) | 19 |
| multi-test | 8 | 6 | 14 |
| target-derived | 6 | 4 | 10 |

The split is by base pipeline and was committed before any detection rule existed (`24a42e2`). The first true
inflation run on Kaggle failed for an infrastructure reason (item 3 in section 6) and was not repeated in
September; inflation on DEV was measured on 2026-11-12 (`results/2026-11-12_dev_injected_leaklens_v1`).

## 4. Real set

150 Kaggle notebooks sampled on 2026-09-29 in three query-based strata of 50, split by author into DEV (71)
and TEST (79), with a random labelling queue (`benchmark/real/manifest.csv`, `benchmark/SPLIT.md`). The labelling
guide, a practice set with answers and the numbered renderings are ready (`benchmark/real/`). **No notebook has
been labelled yet**, so there is no real-set result and no kappa. Licences are still `unverified`.

## 5. scicode-lint timing (details: `docs/SCICODE_TIMING.md`)

On a Kaggle CPU session, served by llama.cpp (not the published vLLM + FP8 GPU setup), with only its two temporal
patterns: 1.42 generated tokens/s; clean files took 8.2 and 18.2 minutes; both leaky files hit the 25-minute cap.
**CPU is not practical for the benchmark.** Options there; recommended: rent a small FP8-capable GPU for the
exact published setup (budget decision), and in parallel ask the author to run it on our TEST files.

## 6. Problems met (and fixed)

1. Group leaks first came out at about 0 inflation because my generators put the entity effect only into
   population-level signal; rebuilt (EVAL_CHANGES #1).
2. Notebook items were not reproducible byte for byte (`nbformat` assigns random cell ids); fixed (EVAL_CHANGES #3).
3. Two Kaggle dataset versions containing a `.tar.gz` never materialised although the API reported success, so the
   first inflation job failed. Now zip + `scripts/check_code_version.sh`, which waits until the dataset serves the
   current commit.
4. The Kaggle list API returns "Not found" when `--search` is combined with `--language`/`--kernel-type`; the
   sampler now searches by term only and filters after pulling.
5. Lint failures were hidden by piping `ruff` into `tail`; fixed.

## 7. What I need from you

1. Wording of C2 in the light of splitguard (still open).
2. scicode-lint: rent a small GPU for the published setup, ask the author to run it on our TEST files, or report
   it as "not run".
3. How many real notebooks you and a teammate will label (the queue order makes any prefix a random sample), and
   who the second labeller is.
4. Whether the repository should be private (it is public on GitHub today).

*(This section was a placeholder in the September report and was filled in on 2026-11-12 from the commit history
and `benchmark/SPLIT.md`; the four decisions are still open.)*
