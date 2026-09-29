# Labelling guide: finding data leakage in notebooks

For the two human labellers of the LeakLens real-notebook set. **No machine-learning research background is
needed.** You will read Python code and answer a fixed set of questions. You never run anything.

Time: about 10 to 15 minutes per notebook after the practice round. Take breaks; accuracy matters more than
speed.

---

## 1. The idea in one paragraph

A machine-learning notebook teaches a computer program (the **model**) using some data, then checks how good it is
on data it has **not** seen, and prints a score such as "accuracy 0.93". That score is only honest if the checking
data was kept completely separate from the teaching data. **Data leakage** is any way the checking data (or
information the model should not have) sneaks into the teaching step. It is like a student who saw the exam paper
while studying: the exam score looks great but says nothing about what they actually learned.

Your job: for each notebook, find every place where that separation is broken, and write down **where** (cell and
line) and **what kind** it is.

## 2. Words you will see

| Word | Plain meaning |
|---|---|
| **train / training data** | the data used to teach the model ("study material") |
| **test / validation data** | the data used to check the model ("the exam") |
| **split** | the line of code that divides data into train and test. Common names: `train_test_split`, `KFold`, `StratifiedKFold`, `ShuffleSplit`, `GroupKFold`, `TimeSeriesSplit`, `cross_val_score`, `cross_validate` |
| **fit** | "learn from this data". `something.fit(X)` or `fit_transform(X)` means *something* learned from X |
| **score / metric** | the printed result: `accuracy`, `roc_auc_score`, `f1_score`, `r2_score`, `mean_absolute_error`, `.score(...)` |
| **X, y** | usually X = the input columns (features), y = the answer column (the **target** or **label**) |
| **cross-validation (CV)** | doing the split several times ("folds") and averaging the scores. `cross_val_score(model, X, y, cv=5)` does this |
| **row** | one example (one patient visit, one sale, one image) |
| **column** | one piece of information about every row (age, price, date, patient_id) |

## 2b. What you receive

A folder with one text file per notebook (`R001.txt`, `R002.txt`, ...), the practice files, and an empty sheet.
Work through the notebooks **in number order** (R001, R002, ...), even if you skip one as `cannot_read`; the
order was randomised so that any first N notebooks form a fair sample. The files come from public Kaggle
notebooks; do not publish or share them outside the project.

## 3. How to label one notebook (step by step)

You get each notebook as a text file with every line numbered like `[cell 4 | line 7]`. Open it in any text
viewer. Also open the labelling sheet (section 6).

1. **Is there a model that is scored?** Search the file for `fit(` and for a score word (section 2). If no model
   is trained and scored, write one row with `leak_type = no_model` and move on.
2. **Find the split.** Search for the split names in section 2. Note its cell and line. If you find several,
   note them all.
3. **Find what the notebook reports.** Usually the last score that is printed. That is the result we care about.
4. **Go through the six questions (section 4)** in order. For each "yes", add a row to the sheet with the cell,
   line(s), type and how sure you are.
5. If all six answers are "no", add one row with `leak_type = none`.
6. Write down how many minutes the notebook took.

**Work alone.** Do not discuss notebooks with the other labeller until you have both finished all of them, and do
not use ChatGPT or any other AI tool. The study needs two independent human opinions; an AI tool would make them
not independent (and could be the same kind of tool we are testing).

## 4. The six questions, with worked examples

Each question has a plain explanation, what to search for, one example that **is** leakage and one that **is
not**. The line to write down is the one marked `<-- label this line` in the examples.

### Q1. Preprocessing: did something learn from ALL the data before the split?

Some steps "learn" numbers from the data: averages (scaling), which columns look useful (feature selection),
which words exist (text vectorising), how to fill missing values (imputing). If they learn from the whole dataset
**before** it is split, they have peeked at the test rows.

Search for: `StandardScaler`, `MinMaxScaler`, `RobustScaler`, `SimpleImputer`, `PCA`, `SelectKBest`,
`CountVectorizer`, `TfidfVectorizer`, `LabelEncoder`, `.fit_transform(`, `.mean()`, `.std()`, `fillna(df.mean())`.
Then ask: does this happen **above** the split line, on data that includes test rows?

Leakage (`preprocessing`):
```python
X = StandardScaler().fit_transform(X)            # <-- label this line
X_train, X_test, y_train, y_test = train_test_split(X, y)
```

Not leakage:
```python
X_train, X_test, y_train, y_test = train_test_split(X, y)
scaler = StandardScaler().fit(X_train)           # learned from training rows only
X_test = scaler.transform(X_test)
```
Also not leakage: the step is inside `make_pipeline(...)` / `Pipeline([...])` and the pipeline is given only
`X_train`, or it is inside `cross_val_score(pipeline, ...)`.

Special note: if the step also uses the answer column `y` (e.g. `SelectKBest(...).fit(X, y)`), write
`supervised` in the note column.

### Q2. Overlap: can the same (or copied) rows end up on both sides?

Search for: `resample(`, `SMOTE`, `RandomOverSampler`, `fit_resample`, `sample(replace=True)`, `pd.concat`,
`np.vstack`, `append`, augmentation, and a final `model.fit(X, y)` on everything.

Leakage (`overlap`): copying rows before the split, so copies land in both train and test.
```python
extra = resample(X[y == 1], n_samples=500)      # <-- label this line
X = pd.concat([X, extra]); y = pd.concat([y, pd.Series(1, index=extra.index)])
X_train, X_test, y_train, y_test = train_test_split(X, y)
```

Leakage (`overlap`): training on the test rows themselves, then scoring on them.
```python
model.fit(X, y)                                  # <-- label this line (X includes the test rows)
print(accuracy_score(y_test, model.predict(X_test)))
```

Not leakage: oversampling done after the split, on `X_train` only.

### Q3. Multi-test: was the exam used to choose between options?

If the notebook tries several models or settings, scores **each one on the test data**, keeps the best, and then
reports that best test score, the test data was used to choose. The reported score is too optimistic.

Search for: loops (`for ... in`) around `.fit` and a score on `X_test`; `max(`, `best`, `sorted(`; picking
the model with the highest test score; `eval_set=[(X_test, y_test)]` or `validation_data=(X_test, y_test)`
followed by reporting the test score.

Leakage (`multi_test`):
```python
for k in [1, 3, 5, 7]:
    score = KNeighborsClassifier(k).fit(X_train, y_train).score(X_test, y_test)   # <-- label this line
    ...keep the best k and print its score
```

Not leakage: `GridSearchCV(...).fit(X_train, y_train)` then one final score on `X_test`.

### Q4. Group: can the same person (or device, user, site, file) be on both sides?

Many datasets have several rows per person: several hospital visits per patient, several recordings per subject,
several sessions per user. If the split is random, the same person appears in both training and test. The model
can then recognise the **person** instead of learning the real pattern, and the score is too high for new people.

How to spot it:
1. Is there a column (or file/folder name) that identifies a person or unit? Names like `patient_id`, `subject`,
   `user_id`, `customer_id`, `device`, `session`, `site`, `hospital`, or IDs taken from file names such as
   `sub-01_...` or folders like `patient_017/`.
2. Does that ID repeat (several rows per ID)? Look for words like "visits", "sessions", "windows", "recordings",
   "scans", or a `groupby('patient_id')`. If each row has its own unique ID (e.g. one row per customer), it does
   **not** count.
3. Is the split random? `train_test_split`, `KFold`, `ShuffleSplit`, `StratifiedKFold`, or `cross_val_score(...,
   cv=5)` **without** `groups=`.

Leakage (`group`):
```python
df = pd.read_csv("visits.csv")       # several visits per patient_id
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)   # <-- label this line
```

Leakage (`group`), ID hidden in file names:
```python
for f in glob("data/sub-*_eeg.npy"):            # one file per subject, cut into many windows
    ...
scores = cross_val_score(model, X, y, cv=5)      # <-- label this line
```

Not leakage:
```python
GroupKFold(n_splits=5).split(X, y, groups=df["patient_id"])
```

Not sure? If you cannot tell whether an ID repeats, still label it and set confidence to `unsure`, with a note.
Also note: sometimes the notebook deliberately tests on the **same** people (for example "predict this patient's
next visit"). If the text says so clearly, write `none` and explain in the note.

### Q5. Temporal: did the model learn from the future to predict the past?

If rows have dates or times (sales per day, sensor readings per hour, prices), the honest test is: train on the
past, test on the later period. A random shuffle mixes future rows into training.

Look for: a date or time column (`date`, `time`, `timestamp`, `datetime`, `year`, `parse_dates=`,
`pd.to_datetime`, `.dt.`), words like "forecast", "time series", "next day".

Then check:
- **Random split on dated data**: `train_test_split(...)` (it shuffles unless it says `shuffle=False`),
  `KFold(...)`, `cross_val_score(..., cv=5)`, anything except `TimeSeriesSplit` or "first 80% / last 20%".
- **Features that look forward**: `.shift(-1)` or any negative shift used as an **input** column,
  `.rolling(..., center=True)`, `bfill`, reversed rolling windows `[::-1].rolling`.

Leakage (`temporal`):
```python
df = pd.read_csv("sales.csv", parse_dates=["date"])
X_train, X_test, y_train, y_test = train_test_split(X, y)   # <-- label this line (shuffles by default)
```

Leakage (`temporal`):
```python
df["next_day_price"] = df["price"].shift(-1)     # <-- label this line, if it is used as an INPUT column
```

Not leakage:
```python
df["target"] = df["price"].shift(-1)             # used only as the ANSWER column: this is normal forecasting
train, test = df.iloc[:800], df.iloc[800:]       # past vs future: correct
```

### Q6. Target-derived: is an input column secretly made from the answer?

An input column that is calculated from the answer, or that is only known **after** the outcome happened, gives
the answer away.

Leakage (`target_derived`):
```python
df["followup_visits"] = df["readmitted"] * 2     # <-- label this line (made from the answer column)
```
Other examples: "days in hospital" when predicting "was admitted", "refund issued" when predicting "fraud".
This one needs judgement. Use `likely` or `unsure` confidence unless it is obvious.

## 5. How sure are you?

| Value | When to use |
|---|---|
| `sure` | You can point to the exact line and the rule in section 4 clearly applies |
| `likely` | Probably leakage, but something is not fully visible (e.g. you cannot see the data file) |
| `unsure` | It could be leakage; you want it discussed later |

When both labellers have finished, differences are discussed and settled (adjudication). Unsure cases are fine;
guessing "none" to be safe is **not**.

## 6. The labelling sheet

File: `labelling_sheet_<your name>.csv` (open it in Excel, Numbers or Google Sheets). One row per finding. A
notebook with no leakage still gets exactly one row, with `none`.

| Column | What to write |
|---|---|
| `labeller` | your initials |
| `notebook_id` | from the file name, e.g. `R017` |
| `leak_type` | `preprocessing`, `overlap`, `multi_test`, `group`, `temporal`, `target_derived`, `none`, `no_model`, or `cannot_read` |
| `cell` | the cell number shown in `[cell N | line M]` |
| `line_start`, `line_end` | the line numbers inside that cell (same number if one line) |
| `confidence` | `sure`, `likely`, `unsure` |
| `note` | one short sentence: why. For Q1, write `supervised` if the step uses `y` |
| `minutes` | minutes spent on this notebook (first row of the notebook only) |

Example rows:

```
labeller,notebook_id,leak_type,cell,line_start,line_end,confidence,note,minutes
SB,R017,group,5,3,3,sure,"train_test_split on visits; patient_id repeats",12
SB,R017,preprocessing,4,8,8,likely,"StandardScaler fit on all rows before split",
SB,R018,none,,,,sure,"GroupKFold with groups=patient_id",9
```

## 7. Practice round (do this first)

Before the real notebooks, label the five practice files in `practice/` exactly as above, then compare with
`practice/ANSWERS.md`. They are small synthetic examples written for this project. If you disagree with an
answer, write down why; that helps us improve this guide. The practice results are not part of the study.

## 8. Frequently asked questions

- **The split is inside a function.** Label the line where the function is **called** if the split happens
  through it, and mention the function in the note.
- **One line has two problems** (e.g. random split on dated data that also has patient IDs). Add two rows, one
  per type, same line.
- **The notebook trains several models.** Label leaks for every model whose score is reported.
- **I cannot see the data, so I do not know whether IDs repeat.** Use the names, comments and printed outputs in
  the notebook; if still unclear, label with `unsure`.
- **Code I do not understand.** Write `unsure` with a note about what is unclear. Do not look it up with an AI
  tool; a normal web search of the function's documentation is fine.
- **Very long or broken notebook.** If it cannot reasonably be read, use `cannot_read` with a note.
