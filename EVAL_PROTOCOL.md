# LeakLens evaluation protocol

**Status: FROZEN (version 1.0, 2026-11-12).** Approved by the project owner on 2026-11-12 in the working session,
after the one-page summary ([`docs/EVAL_PROTOCOL_SUMMARY.md`](docs/EVAL_PROTOCOL_SUMMARY.md)) was put to them; the
owner's reply was "Approve, score TEST". The text below is unchanged from the proposal of the same day except for
this status paragraph. It was written after DEV results had been seen (DEV is the tuning split, so that is
allowed) and **before any TEST result existed**. Every later change goes in [`EVAL_CHANGES.md`](EVAL_CHANGES.md).

## 1. What is evaluated

| Set | Items | Labels | Used for |
|---|---|---|---|
| Injected, DEV | 96 files, 89 leaks | by construction | writing and tuning rules and thresholds; reported as DEV, never as the result |
| Injected, TEST | 79 files, 73 leaks | by construction | scored **once per release**, all tools |
| Real, DEV | 71 Kaggle notebooks | two human labellers | tuning; agreement study |
| Real, TEST | 79 Kaggle notebooks | two human labellers | scored once per release |

The DEV/TEST assignment is in [`benchmark/SPLIT.md`](benchmark/SPLIT.md) (injected: by base pipeline; real: by
author). What was looked at while writing rules is disclosed in `EVAL_CHANGES.md` #4.

**Real set labels.** Labellers work from the numbered renderings and the labelling guide, in the random queue
order, **without seeing any tool output** (no anchoring). Cohen's kappa is reported per question on the
double-labelled subset. A real-set number is reported only for the labelled prefix of the queue, with its size.
LeakLens never labels its own benchmark (CLAUDE.md Rule 3).

## 2. Matching a finding to a label

A finding matches a label when all hold:

1. same file;
2. same notebook cell (for `.ipynb`; execution order is not used for matching, only cell index and line in cell);
3. the line ranges overlap by at least one line;
4. the finding's type is the label's `type` or one of its `alt_types` (EVAL_PROTOCOL_NOTES #3, for example
   whole-series scaling on time-ordered data: `temporal`, or `preprocessing`).

Matching is one-to-one inside a file: labels are taken in file order and each takes the first unused finding that
matches. An unmatched finding is a **false positive** for the type the tool reported. An unmatched label is a
**miss** for the label's primary type. A matched pair is a **true positive** for the label's primary type.
Subtype, rule id, message and the named entity or time column are **not** part of matching; for group findings the
share that name the true entity column is reported separately (§6).

Implementation: [`src/leaklens/evaluation/scoring.py`](src/leaklens/evaluation/scoring.py), tested in
`tests/test_scoring.py`. The same code scores every tool.

## 3. Operating points and modes

- **Primary operating point: confidence `medium` or higher**, the CLI default. **Secondary: all findings**
  (`low` included). Both are always reported; the primary one is the headline.
- **Modes.** `static`: code only, nothing executed. `static+dynamic`: the file is also run, instrumented. Dynamic
  findings are added; a static finding the run **refutes** is removed; a finding whose dynamic check could not run
  (`error`, or no check exists for that rule) is kept unchanged. The ablation "static only vs static+dynamic" is
  reported for every type.
- Dynamic-only leaks (`dynamic_only` category, raw duplicated records) are **included** in the static mode's
  recall denominator, with a note; they are not excluded.

## 4. Metrics

Per leakage type (never a single pooled F1, CLAUDE.md Rule 6):

- **Precision, recall, F1** from the counts of §2.
- **95% confidence intervals**: percentile bootstrap, 2,000 resamples of **files**, seed 20261112. As a
  sensitivity analysis the same bootstrap resampling **base pipelines** (injected set) or **authors** (real set),
  because files from one base are correlated. With few bases this second interval is wide; both are shown.
- A metric that is undefined (no finding of that type: precision; no label: recall) is reported as "n/a", never
  as 1.0 or 0.
- **Temporal** results are also split by category: `temporal_common`, `temporal_differentiating`,
  `temporal_hard` (decision 2026-09-29), for LeakLens and for scicode-lint when it can be run.

Per tool:

- **False-alarm rate on clean and trap files**: share of files with no leak that receive at least one finding.
- **Coverage**: share of files the tool could analyse. A file a tool cannot read, or crashes on, counts as
  analysed with zero findings for recall and is listed in the coverage column (Rule 5: never dropped).
- **Runtime**: seconds per file (median, mean, max), static and dynamic separately, with the machine named.

## 5. Impact estimation (injected set only for accuracy)

For an injected file the true inflation is known: `metric(leaky file) − metric(its ground-truth fixed version)`,
signed so that positive means the leak makes the result look better, averaged over data seeds 0 to 4
(`benchmark/injected/measure_inflation.py`).

LeakLens's estimate for a finding is `metric(original run) − metric(re-run with that finding's canonical fix)`
on the same seeds. Reported per leakage type and per metric (AUC, AP, R², MAE are not pooled):

- **status counts**: `measured`, `unreliable` (the fix changed more than the leak), `unknown` (the fixed run
  failed or no automatic fix exists). `unknown` and `unreliable` are reported, never dropped;
- for `measured` findings in **single-leak files**: mean and median absolute error against the true inflation,
  **sign agreement**, and Spearman rank correlation;
- multi-leak files are reported separately (the true inflation there is the joint effect of all leaks).
- **Baseline for this task**: LeakHound's proxy estimate on the same materialised splits, where it runs. If the
  proxy is as accurate, that is reported (Rule 10).

Injected inflation is by construction (Rule 12): it is used only to score detection and estimation accuracy,
never as evidence of real-world severity.

**Severity from measured impact** (SPEC §4): for metrics bounded in [0, 1] (AUC, AP, accuracy, F1, R²):
`high` if |Δ| ≥ 0.05, `medium` if ≥ 0.01, else `low`. For unbounded error metrics (MAE, RMSE): the same thresholds
on the relative change |Δ| / |fixed value|. `target_derived` stays at most `low`.

## 6. Secondary analyses

- Group findings: share whose named column is the true entity column (injected set: from `bases.yaml`).
- Dynamic pass: number of static findings confirmed, refuted and unchecked; findings only the dynamic pass makes.
- Notebook order: findings under execution order vs cell order, where they differ.

## 7. Baselines (run as released, published defaults; Rule 5)

| Tool | Level | How it is run | Types it can score on |
|---|---|---|---|
| Yang et al. analyser (ASE 2022) | code | built from source in a Kaggle CPU job (Linux, Souffle, Python 3.8) | preprocessing, overlap, multi-test |
| scicode-lint 0.5.0 | code (LLM) | published setup needs a 16 GB GPU; **not run so far** (`docs/SCICODE_TIMING.md`); reported as "not run", not as zero | temporal |
| leakcheck-ml, LeakHound, dataleaks, Deepchecks | data | given the train/test tables that LeakLens's instrumented run materialises at each split point, with **no column named** and, separately, with the true column named | group, temporal, duplicates |
| splitguard 0.1.0 | runtime | run on the file as released; without declared groups, and separately with the true group declared | overlap, group (declared) |

A data-level tool has no code location, so for it a detection at a split point is matched to labels **at that
split's lines**. A tool is scored only on the types it claims to detect; the other types are shown as "not
supported", which is a coverage result. Excluded baselines and reasons: `docs/EXCLUDED_BASELINES.md`.

Published numbers of other tools (for example precision 97.6% and recall 67.8% for Yang et al.) were measured on
their own data. They are quoted as background only and are **never** placed in the same table column as numbers
measured on this benchmark.

## 8. TEST discipline

1. TEST is scored by `benchmark/run_eval.py --split TEST`, which refuses to run unless the protocol is frozen
   (`EVAL_PROTOCOL.md` status FROZEN) and no TEST run exists for the current release tag.
2. One run per release, all tools in the same job. The run folder goes in `results/` with the commit hash in
   `results/registry.csv`.
3. Any change to rules, thresholds or the protocol after a TEST run is logged in `EVAL_CHANGES.md` with what had
   been seen, and the next TEST number is labelled as a second look.
4. DEV numbers are always labelled DEV. They are optimistic by design: the rules were written looking at DEV.

## 9. Known threats, stated up front

- **The injected benchmark and the detector have the same author.** TEST uses different base pipelines but the
  same mutation operators as DEV, so injected-TEST results measure generalisation across pipelines and data, not
  across leak styles. The real set, labelled by people, is the check on that.
- **TEST has few leaks for some types** (target_derived 4, multi_test 6, group 7): intervals will be wide.
- **Entity names in TEST bases were seen** (`EVAL_CHANGES.md` #4): TEST group results are not blind to names.
- **Real-set strata are query-based**, and Kaggle notebooks are not a sample of all ML code.
