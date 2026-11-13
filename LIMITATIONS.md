# Limitations

Written 2026-11-12, at the end of the first implementation of Phases 4 to 6. This is the list a reviewer should
read before the results. It will be extended in Phase 9.

## What has and has not been measured

- **Results exist for the project's own injected benchmark only.** DEV numbers are optimistic by design (the
  rules were written on those files). TEST was scored once on 2026-11-12, after the protocol was frozen; it uses
  other pipelines but the same kinds of injected leak.
- **TEST exposed three faults**, fixed afterwards and re-checked in a logged second look, which is not a held-out
  result (`docs/PHASE7_TEST_REPORT.md` section 7). The injected benchmark is now saturated on DEV and TEST and
  cannot measure further progress. The faults were: a positional slice such as
  `data.iloc[:-1]` is mistaken for a train/test split; a feature list built with a `startswith` filter is not
  resolved, and then nothing is reported; and when the static pass nominates a weak entity column, the run
  confirms that column instead of looking for a better one, so 4 of 7 TEST group findings name the wrong column
  and their impact estimate is wrong.
- **No number on real notebooks yet.** The 150 sampled Kaggle notebooks have no human labels. The analyser has
  been run on the 71 real DEV notebooks only to check that it does not crash and to read what it flags; those
  findings are not labels and no precision is claimed from them.
- **The injected benchmark and the detector have the same author.** TEST uses different base pipelines and data
  but the same mutation operators as DEV. Injected results measure generalisation across pipelines, not across
  the ways people actually write leaks.
- **Only one baseline has been run** (Yang et al., scored per file, not by the protocol's line rule). The published numbers of other tools (for example Yang et al.:
  precision 97.6%, recall 67.8%) were measured on their own data and cannot be compared with ours.
- **Injected inflation is by construction** (CLAUDE.md Rule 12). It is used to check that impact estimates are
  accurate. It says nothing about how severe leakage is in real code.

## Static analysis

- **An entity column the code never mentions cannot be seen statically.** If a script loads a table that has a
  `patient_id` column and never names it, the static pass has no evidence. This is the main reason for the
  dynamic pass. Static-only group recall on DEV is low for exactly this reason.
- **Group detection is heuristic.** Evidence is the column or variable name, or derivation from file paths. A
  name can be wrong in both directions: `customer_id` may be unique per row (no leak), and an entity may sit in a
  column called `code`. Names in the "weak" list give low-confidence findings only. Whether a random split is a
  leak also depends on the claim: a within-patient model is a legitimate design, and the tool cannot know the
  claim. Group findings never state certainty.
- **Temporal T1 needs evidence that row order matters** (a time column and lag, window or sort operations). A
  table with a date column and a random split is reported at low confidence only, because it may be an ordinary
  tabular problem.
- **One pass, no fixpoint.** Loops are analysed once, branches are analysed in sequence, functions are inlined
  to a fixed depth and only when called. Code in functions that are never called is not analysed. Classes are
  opaque. Flows through `exec`, pickled objects or files written and read back are lost.
- **Library coverage.** pandas, NumPy, scikit-learn and imbalanced-learn are modelled by name. Keras, PyTorch,
  XGBoost and LightGBM models are recognised only as "something fitted and scored". Unknown calls are treated as
  depending on all their inputs, which can both hide a leak and carry a taint too far.
- **Manual positional splits** (`X[:n]`, `X[n:]`) are treated as chronological and are not checked as split
  points, so a shuffle followed by a positional split of time-ordered data is missed.
- **Preprocessing inside the training rows** (a scaler fitted on all training rows, then cross-validation on the
  training rows) is reported at low confidence only.
- **Multi-test** needs a visible selection (`max`, `sorted`, a comparison with the best score). Comparing models
  by eye in printed output is not detected. A selection set named like a validation set is assumed to be one.
- **Notebook order.** Execution order is used when every code cell has a unique execution count, else cell
  order. A notebook whose saved order differs from how it was actually run can give different findings.

## Dynamic pass

- **It executes the code.** It may only be used on trusted code, or through `leaklens.sandbox` in an offline
  Kaggle session. So far it has been run only on our own generated pipelines.
- **Entity and time columns are looked up in the script's own variables** that are row-aligned with the data
  being split. Data that was reordered, or frames that no longer exist at the split, are not found.
- **Entity evidence at run time is still the name** plus repetition. A column with repeated values and no
  entity-like name is not reported in this version (the taxonomy's "cardinality only, low confidence" case).
- **Row identity is by value.** Rows are compared by hashing their values (rounded), so synthetic neighbours made
  by SMOTE are not seen as copies, and naturally identical rows can look like duplicates (guarded by a
  distinct-row threshold).
- **Confirmation of a transformer fit uses row counts**, not row identity, because transformed values cannot be
  matched to the original rows.
- **No run-time check** for forward-looking features, pandas statistics or early stopping.
- **Only scikit-learn entry points are instrumented.** Splits and fits done by other libraries are not seen.
- **Thresholds** (`configs/dynamic.yaml`) were set on DEV.

## Impact estimation

- **Automatic fixes exist for six situations only:** duplicated records removed before a split, a row-level split replaced by a group-aware one, a
  non-chronological split replaced by a chronological one, evaluation rows removed from a model fit, a
  `fit_transform` on one line re-fitted on the training rows of a single hold-out split, and a feature removed.
  Everything else is reported as "impact unknown" with the reason: resampling before the split, multi-test
  selection, forward-looking features, pandas statistics, and any preprocessing leak under cross-validation.
- **A fix changes more than the leak in some cases.** A group-aware split changes which rows are evaluated and
  usually the size of the test set; a chronological split changes the test period. The estimate is the change in
  the user's metric under the canonical fix, not a causal decomposition. Estimates are marked unreliable when the
  fixed run takes a different path through the code.
- **One run, one seed** in the CLI. Small differences are within seed noise; the benchmark evaluation uses
  several data seeds.
- **The metric is read from the last `name: value` line the script prints.** Scripts that report results in
  another way give "impact unknown".

## Software

- **The name is taken.** A different package called `leaklens` exists on PyPI since June 2026
  (`docs/NOVELTY_LOG.md`). Nothing has been published; the project owner has to decide on the name.
- No PyPI release or HTML report yet (Phase 9). The pre-commit hook and the GitHub Action exist and were each run
  once for real (2026-11-13); the Action's SARIF upload to GitHub code scanning worked on this repository.
- **The four papers of the owner's comparison table have not been run against LeakLens** (`docs/COMPARISON_TABLE_CHECK.md`).
  Two of them could not even be opened to confirm what the table says about them.
