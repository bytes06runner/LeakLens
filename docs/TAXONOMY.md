# LeakLens leakage taxonomy

Version 1.0 (Phase 1, 2026-09-29). This document defines what LeakLens calls leakage, how each type is detected
statically and confirmed dynamically, and the canonical fix used for impact estimation (Phase 6). The finding
format, severity levels and exit codes are in [`SPEC.md`](SPEC.md).

## 0. Terms

| Term | Meaning |
|---|---|
| **Evaluation rows** | Rows whose predictions are scored to produce a *reported* metric: a test set, a held-out validation set whose score is reported, or the held-out fold inside cross-validation. |
| **Training influence** | A row influences training if it is an input to any `fit` / `fit_transform` / `fit_resample` / `partial_fit`, or to any statistic (mean, std, quantile, vocabulary, category list, target mean, ...) whose value reaches the final model's inputs or parameters. |
| **Split point** | Code that partitions rows into training and evaluation rows: sklearn splitters and CV iterators, `cross_val_score` / `cross_validate` / `GridSearchCV` etc. (including their default CV), and manual partitions (`iloc[:n]`, boolean masks, `df.sample` + `drop`). |
| **Leakage** | Any path by which evaluation rows, or information not available at prediction time, influence training ([Kaufman et al. 2012](https://doi.org/10.1145/2382577.2382579)). |
| **Entity column** | A column (or array aligned with rows) identifying the unit the model must generalise across: patient, subject, user, device, session, site, recording file. |
| **Time column** | A datetime column, `DatetimeIndex`, or an ordered index that the data is known to be sorted by. |

A finding is always about a **flow** from a line of code to a reported metric. Code that leaks into a model whose
score is never reported is not a finding.

## 1. Overview

| Type | One-line definition | Kapoor & Narayanan (2023) | Yang et al. (2022) | Default severity |
|---|---|---|---|---|
| [`preprocessing`](#2-preprocessing) | A data-dependent transformation is fitted on rows that include evaluation rows | L1.2 pre-processing on train+test; L1.3 feature selection on train+test | Preprocessing leakage | low (scaling, imputing); **high** if the transformation uses the target (supervised feature selection, target encoding) |
| [`overlap`](#3-overlap--duplicates) | The same or derived rows appear on both sides of the split | L1.4 duplicates | Overlap leakage | high |
| [`multi_test`](#4-multi-test-selection) | Evaluation rows are used to choose among models or settings, then the chosen score is reported | L1 (no dedicated leaf) | Multi-test leakage | medium |
| [`group`](#5-group-entity) | One entity has rows on both sides of a split, while the claim is generalisation to new entities | L3.2 non-independence between train and test | not covered | high |
| [`temporal`](#6-temporal) | Training uses information from after the evaluation rows' prediction time | L3.1 temporal leakage | not covered | high |
| [`target_derived`](#7-target-derived-features-heuristic) | A feature is computed from the label or from information recorded after the outcome | L2 illegitimate features | not covered | low (flag only) |

**Out of scope for v1** (reported in `LIMITATIONS.md` in Phase 9): Kapoor L1.1 (no test set: scoring on training
data) and L3.3 (sampling bias in the test distribution, which needs domain knowledge).

**Severity priors** follow Roth ([arXiv:2604.04199](https://arxiv.org/abs/2604.04199)): estimation-type leakage
(for example a scaler fitted on all data) changed AUC by at most 0.005 in all nine conditions tested; selection
leakage was substantial; memorisation (duplicates) grew with model capacity; boundary leakage (group, temporal)
was invisible under random CV. Once Phase 6 measures a finding's impact, the measured value replaces the prior.

Kapoor & Narayanan's leaf names are quoted from the arXiv version
([2207.07048](https://arxiv.org/abs/2207.07048)); Yang et al.'s three types from their ASE'22 paper, section 2.

---

## 2. Preprocessing

**Definition.** A transformer, selector, imputer, encoder, vectoriser or hand-written statistic is fitted on a
set of rows that includes evaluation rows, and its output reaches the model that produces the reported metric.

**Static rule.**
1. A call `T.fit(D)` / `T.fit_transform(D)` / `T.partial_fit(D)` where `T` is a data-dependent transformer
   (catalogue in `configs/`, Phase 4: scalers, imputers, encoders, `PCA`, `TruncatedSVD`, `KBinsDiscretizer`,
   feature selectors, `CountVectorizer`, `TfidfVectorizer`, `TargetEncoder`, ...), or a pandas/NumPy statistic
   over rows (`mean`, `std`, `median`, `quantile`, `min`/`max`, `value_counts`, `groupby(...).transform`) whose
   result is used to transform features; **and**
2. `D` is data-flow-related to rows that later become evaluation rows (the split point comes after the fit on a
   shared ancestor, or evaluation rows are concatenated into `D`); **and**
3. the transformed output flows to the input of the evaluated model.

Fitting inside a `Pipeline` / `ColumnTransformer` that is itself fitted only on training rows is not a finding.
Subtype `supervised` (the fit also receives `y`, for example `SelectKBest(f_classif).fit(X, y)`, target encoding)
raises the severity prior to high.

**Dynamic check.** Instrument `fit` / `fit_transform` of catalogue transformers: record fingerprints of the rows
seen at fit time and compare with the rows later passed to the scoring call. Confirmed if the intersection is
non-empty.

**Canonical fix (Phase 6).** Move the split before the fit and apply `transform` to evaluation rows, or wrap the
transformer and model in a `Pipeline` fitted on training rows only.

<!-- example: preprocessing_pos.py -->
```python
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

rng = np.random.default_rng(0)
X, y = rng.normal(size=(200, 4)), rng.integers(0, 2, 200)
X = StandardScaler().fit_transform(X)  # LEAK: preprocessing
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
print(LogisticRegression().fit(X_train, y_train).score(X_test, y_test))
```
<!-- /example -->

<!-- example: preprocessing_neg.py -->
```python
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

rng = np.random.default_rng(0)
X, y = rng.normal(size=(200, 4)), rng.integers(0, 2, 200)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
model = make_pipeline(StandardScaler(), LogisticRegression()).fit(X_train, y_train)
print(model.score(X_test, y_test))
```
<!-- /example -->

## 3. Overlap / duplicates

**Definition.** Rows that are identical to, or derived from, evaluation rows are used for training. This includes
test data passed to `fit`, resampling or augmentation before the split (synthetic or copied rows land on both
sides), concatenating train and test, and duplicated records in the raw data.

**Static rule.** Any of:
1. data-flow from evaluation rows into a `fit` of the evaluated model or of a selection step;
2. a resampler or augmenter (`resample(..., replace=True)`, `fit_resample` of imbalanced-learn samplers,
   `df.sample(replace=True)`, `pd.concat` of a frame with a subset of itself, image/text augmentation helpers)
   applied to data **before** the split point that produces the evaluation rows;
3. `pd.concat` / `np.vstack` of training and evaluation data that then flows to `fit`.

Duplicates already present in the raw data cannot be seen statically; they are dynamic-only findings.

**Dynamic check.** At each split point, hash every row (exact fingerprint on the feature values) and report the
number of evaluation rows whose fingerprint also occurs in training rows. Near-duplicates for numeric rows use a
rounding-grid fingerprint (grid size in config). Report the fraction and compare with the duplicate rate inside
the training rows, so naturally repeated rows (for example low-cardinality categorical data) are not over-flagged.

**Canonical fix.** Split first; resample or augment training rows only (for example an imbalanced-learn
`Pipeline`); de-duplicate before the split for dynamic-only findings.

<!-- example: overlap_pos.py -->
```python
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.utils import resample

rng = np.random.default_rng(0)
X, y = rng.normal(size=(200, 4)), (rng.random(200) < 0.2).astype(int)
minority = resample(X[y == 1], n_samples=100, random_state=0)  # LEAK: overlap
X = np.vstack([X, minority])
y = np.concatenate([y, np.ones(100, dtype=int)])
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
print(RandomForestClassifier(random_state=0).fit(X_train, y_train).score(X_test, y_test))
```
<!-- /example -->

<!-- example: overlap_neg.py -->
```python
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.utils import resample

rng = np.random.default_rng(0)
X, y = rng.normal(size=(200, 4)), (rng.random(200) < 0.2).astype(int)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
minority = resample(X_train[y_train == 1], n_samples=100, random_state=0)
X_train = np.vstack([X_train, minority])
y_train = np.concatenate([y_train, np.ones(100, dtype=int)])
print(RandomForestClassifier(random_state=0).fit(X_train, y_train).score(X_test, y_test))
```
<!-- /example -->

## 4. Multi-test (selection)

**Definition.** The same evaluation rows are used to score more than one candidate (model, hyper-parameter
setting, feature set, threshold, early-stopping epoch), a candidate is chosen by that score, and the chosen
candidate's score on the same rows is reported.

**Static rule.** A scoring call on evaluation data (`score`, `predict` + metric, `evaluate`) inside a loop or
repeated over several fitted models, whose result feeds a comparison (`max`, `argmax`, `sorted`, `if score >
best`) that selects the reported model; or evaluation data passed as `eval_set` / `validation_data` for early
stopping and then used for the reported score.

**Dynamic check.** Count distinct fitted estimators (by object identity and parameters) scored on the same
evaluation-row fingerprint set before the final report. Confirmed if more than one.

**Canonical fix.** Select on a separate validation split or with CV on training rows (`GridSearchCV` on
training rows, nested CV), and score the chosen candidate once on the evaluation rows.

<!-- example: multi_test_pos.py -->
```python
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier

rng = np.random.default_rng(0)
X, y = rng.normal(size=(200, 4)), rng.integers(0, 2, 200)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
scores = {}
for k in (1, 3, 5, 7, 9):
    scores[k] = KNeighborsClassifier(k).fit(X_train, y_train).score(X_test, y_test)  # LEAK: multi_test
best = max(scores, key=scores.get)
print(best, scores[best])
```
<!-- /example -->

<!-- example: multi_test_neg.py -->
```python
import numpy as np
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.neighbors import KNeighborsClassifier

rng = np.random.default_rng(0)
X, y = rng.normal(size=(200, 4)), rng.integers(0, 2, 200)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
search = GridSearchCV(KNeighborsClassifier(), {"n_neighbors": [1, 3, 5, 7, 9]}, cv=5).fit(X_train, y_train)
print(search.best_params_, search.score(X_test, y_test))
```
<!-- /example -->

## 5. Group (entity)

**Definition.** Rows from the same entity (patient, subject, user, device, session, site, recording) appear in
both training and evaluation rows of a split or CV fold, while the evaluation is meant to estimate performance on
**new** entities.

Whether this is leakage depends on the claim ([Kapoor & Narayanan](https://doi.org/10.1016/j.patter.2023.100804),
L3: the test set must come from the distribution of scientific interest). A within-patient model evaluated on later
data from the same patients is a legitimate design. LeakLens therefore assumes new-entity generalisation when it
finds an entity column, reports its confidence, and lets the user declare otherwise (`# leaklens: ignore[group]`
on the split line, or a project config; see SPEC §6). This is also why group findings cannot be fully automatic.

**Static rule.**
1. A row-level splitter at a split point: `train_test_split`, `KFold`, `StratifiedKFold`, `ShuffleSplit`,
   `StratifiedShuffleSplit`, `RepeatedKFold`, `RepeatedStratifiedKFold`, or a CV helper
   (`cross_val_score`, `cross_validate`, `cross_val_predict`, `GridSearchCV`, `RandomizedSearchCV`, ...) with an
   integer or default `cv`; **and**
2. the split data is data-flow-related to a **candidate entity column**, detected by any of:
   - *name evidence*: the column or variable name matches entity tokens (configurable list: `patient`, `subject`,
     `user`, `customer`, `participant`, `device`, `session`, `site`, `hospital`, `record`, `recording`, `file`,
     `animal`, `household`, `store`, `id`, ...), including columns dropped before the split;
   - *file-path evidence*: values derived from file or directory names (`glob`, `os.listdir`, `Path.iterdir`,
     string splitting of a path) and replicated per row (loops appending one value per window,
     `np.repeat`);
   - *cardinality evidence* (dynamic only): many rows per value (thresholds in config);
3. **and** no group-aware splitter (`GroupKFold`, `StratifiedGroupKFold`, `GroupShuffleSplit`,
   `LeaveOneGroupOut`, `LeavePGroupsOut`, or `groups=` passed to a CV helper) is applied to that flow.

**Confidence.** `high`: name or file-path evidence **and** dynamic confirmation. `medium`: name or file-path
evidence only (static run). `low`: cardinality evidence only. Group findings never claim certainty.

**Dynamic check.** At the split point (each fold for CV), compute the set of entity values on each side and
report the number of shared entities and the fraction of evaluation rows belonging to entities also seen in
training.

**Canonical fix.** Replace the splitter with its group-aware counterpart on the detected column
(`train_test_split` → `GroupShuffleSplit`, `KFold` → `GroupKFold`, `StratifiedKFold` → `StratifiedGroupKFold`,
CV helper → same helper with `cv=GroupKFold(k)` and `groups=`), keeping test size, number of folds and random
seed.

<!-- example: group_pos.py -->
```python
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(0)
df = pd.DataFrame({"patient_id": np.repeat(np.arange(20), 10), "x": rng.normal(size=200)})
df["y"] = (df["patient_id"] % 2).astype(int)
X, y = df[["x"]].assign(p=df["patient_id"] * 0.1 + rng.normal(0, 0.01, 200)), df["y"]
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)  # LEAK: group
print(RandomForestClassifier(random_state=0).fit(X_train, y_train).score(X_test, y_test))
```
<!-- /example -->

<!-- example: group_neg.py -->
```python
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit

rng = np.random.default_rng(0)
df = pd.DataFrame({"patient_id": np.repeat(np.arange(20), 10), "x": rng.normal(size=200)})
df["y"] = (df["patient_id"] % 2).astype(int)
X, y = df[["x"]].assign(p=df["patient_id"] * 0.1 + rng.normal(0, 0.01, 200)), df["y"]
train_idx, test_idx = next(GroupShuffleSplit(test_size=0.25, random_state=0).split(X, y, groups=df["patient_id"]))
model = RandomForestClassifier(random_state=0).fit(X.iloc[train_idx], y.iloc[train_idx])
print(model.score(X.iloc[test_idx], y.iloc[test_idx]))
```
<!-- /example -->

File-path-derived entities (EEG-style windows), with the leak hidden in the default CV of `cross_val_score`:

<!-- example: group_pos_windows.py -->
```python
# EEG-style: fixed-length windows cut from per-subject recordings; subject identity comes from the file name.
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

rng = np.random.default_rng(0)
recordings = {f"sub-{i:02d}_run-1.npy": rng.normal(i % 3, 1.0, size=(6000,)) for i in range(8)}
windows, labels, subjects = [], [], []
for fname, signal in recordings.items():
    subject = fname.split("_")[0]
    for w in signal.reshape(-1, 500):
        windows.append([w.mean(), w.std()])
        labels.append(int(subject[-1]) % 2)
        subjects.append(subject)
X, y = np.array(windows), np.array(labels)
print(cross_val_score(LogisticRegression(), X, y, cv=5).mean())  # LEAK: group
```
<!-- /example -->

## 6. Temporal

**Definition.** Training uses information from after the prediction time of evaluation rows. Two subtypes:

- **T1 non-chronological split:** a shuffled split, or any CV other than a forward-chaining one, on time-ordered
  data. Note that unshuffled `KFold` is also leaky here: every fold except the last trains on later data.
- **T2 forward-looking features:** a feature at time *t* is computed from values after *t*: negative `shift`,
  `rolling(..., center=True)`, `bfill` / `fillna(method="bfill")`, interpolation across the split, or a
  whole-series statistic (the last case is also `preprocessing`; LeakLens reports it once, as `temporal`).
  Using `shift(-k)` to build the **target** is legitimate; only flows into features are findings.

**Static rule.** T1: a row-level splitter or CV helper (list in §5) other than `TimeSeriesSplit` (or a manual
`iloc[:n]` split after sorting by time) applied to data flow-related to a **time column** (dtype datetime,
`parse_dates=`, `pd.to_datetime`, `DatetimeIndex`, `sort_values` on a date-named column, name tokens `date`,
`time`, `timestamp`, `year`, `month`, `day`, configurable). T2: a forward-looking operation from the list above
whose result flows to the model's features.

**Dynamic check.** T1: at the split point, for each series (per entity if an entity column exists, otherwise
globally) compute `max(train time)` and `min(evaluation time)`; confirmed if the first exceeds the second. Report
the fraction of training rows dated after the earliest evaluation row. T2: dynamic confirmation is not attempted
in v1 (static only, medium confidence).

**Canonical fix.** T1: sort by time and split with `shuffle=False`, or `TimeSeriesSplit` with the same number of
folds. T2: replace the forward-looking operation with its backward-looking counterpart (`center=False`,
`ffill`, positive `shift`), computed within the training range.

<!-- example: temporal_pos.py -->
```python
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(0)
df = pd.DataFrame({"date": pd.date_range("2021-01-01", periods=365, freq="D")})
df["value"] = np.cumsum(rng.normal(size=365))
df["lag1"] = df["value"].shift(1)
df["target"] = df["value"].shift(-1)
df = df.dropna()
X, y = df[["value", "lag1"]], df["target"]
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)  # LEAK: temporal
print(Ridge().fit(X_train, y_train).score(X_test, y_test))
```
<!-- /example -->

<!-- example: temporal_neg.py -->
```python
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(0)
df = pd.DataFrame({"date": pd.date_range("2021-01-01", periods=365, freq="D")})
df["value"] = np.cumsum(rng.normal(size=365))
df["lag1"] = df["value"].shift(1)
df["target"] = df["value"].shift(-1)
df = df.dropna().sort_values("date")
X, y = df[["value", "lag1"]], df["target"]
X_train, X_test, y_train, y_test = train_test_split(X, y, shuffle=False)
print(Ridge().fit(X_train, y_train).score(X_test, y_test))
```
<!-- /example -->

T2, forward-looking feature under an otherwise correct `TimeSeriesSplit`:

<!-- example: temporal_pos_future_feature.py -->
```python
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

rng = np.random.default_rng(0)
df = pd.DataFrame({"date": pd.date_range("2021-01-01", periods=365, freq="D")})
df["value"] = np.cumsum(rng.normal(size=365))
df["smooth"] = df["value"].rolling(7, center=True).mean()  # LEAK: temporal
df["target"] = df["value"].shift(-1)
df = df.dropna()
print(cross_val_score(Ridge(), df[["value", "smooth"]], df["target"], cv=TimeSeriesSplit(5)).mean())
```
<!-- /example -->

## 7. Target-derived features (heuristic)

**Definition.** A feature is computed from the label, or records information that only exists after the outcome
([Kaufman et al. 2012](https://doi.org/10.1145/2382577.2382579); Kapoor L2). Whether a feature is legitimate
needs domain knowledge, so this type is a **flag only, low severity**, never an error.

**Static rule.** A feature column assigned from an expression whose data-flow includes the target column
(arithmetic, `where`, `map` of the target, `groupby(target)` statistics), before the target is separated from the
features.

**Dynamic check.** Single-feature predictive power on training rows: AUC (classification) or R² (regression) of a
depth-1 tree on that feature alone; flag above a configurable threshold. Reported with the score, as evidence
only.

**Canonical fix.** Remove the feature. Impact is estimated by re-running without it; the finding stays a flag
regardless of impact.

<!-- example: target_derived_pos.py -->
```python
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(0)
df = pd.DataFrame({"age": rng.integers(20, 90, 300), "bp": rng.normal(120, 15, 300)})
df["readmitted"] = (rng.random(300) < 0.3).astype(int)
df["followup_visits"] = df["readmitted"] * rng.integers(1, 4, 300)  # LEAK: target_derived
X_train, X_test, y_train, y_test = train_test_split(df.drop(columns="readmitted"), df["readmitted"], random_state=0)
print(LogisticRegression(max_iter=1000).fit(X_train, y_train).score(X_test, y_test))
```
<!-- /example -->

<!-- example: target_derived_neg.py -->
```python
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(0)
df = pd.DataFrame({"age": rng.integers(20, 90, 300), "bp": rng.normal(120, 15, 300)})
df["readmitted"] = (rng.random(300) < 0.3).astype(int)
df["prior_visits"] = rng.integers(0, 5, 300)
X_train, X_test, y_train, y_test = train_test_split(df.drop(columns="readmitted"), df["readmitted"], random_state=0)
print(LogisticRegression(max_iter=1000).fit(X_train, y_train).score(X_test, y_test))
```
<!-- /example -->

## 8. Overlaps between types

One line can match several types. LeakLens reports **one finding per (line, type)** and links related findings:

| Situation | Reported as |
|---|---|
| Whole-series normalisation on time-ordered data | `temporal` (T2) only |
| Oversampling before the split | `overlap` only (it is not a fit of a transformer) |
| Supervised feature selection on all rows | `preprocessing` (subtype `supervised`) |
| Random split on time-ordered data that also has an entity column | both `group` and `temporal`, linked |
| Target encoding fitted on all rows | `preprocessing` (subtype `supervised`), not `target_derived` |

## 9. About the examples

The examples are runnable (`tests/fixtures/taxonomy/*.py`) and are embedded here by
`scripts/sync_taxonomy_examples.py`; `tests/test_taxonomy_examples.py` fails if this file and the fixtures
disagree. Each leaking line carries `# LEAK: <type>` so that Phase 4 unit tests can check the reported line.
They are specification examples and unit-test inputs, **not benchmark items**: they are never used to score
LeakLens or baselines.
