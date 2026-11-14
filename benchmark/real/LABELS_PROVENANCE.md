# Real-notebook labels: how they were made

Files: `labels_TEST.csv` (79 notebooks, 122 rows) and `labels_DEV.csv` (71 notebooks, 93 rows), columns as in
`LABELLING_GUIDE.md` section 6 plus `entity_column` (filled for a group label when the entity is a column; empty when
it comes from file names, so the strict entity rule of EVAL_CHANGES #10 does not apply to that label).

## Who wrote them

- **Drafted by an AI coding assistant** (Claude, the assistant used to build LeakLens), on 2026-11-14, by reading the
  rendered code of each notebook (`render_for_labelling.py` output, the same text the human labellers were given)
  and answering the six questions of `LABELLING_GUIDE.md`. `labeller` is `ai_draft` on every row.
- **Not yet reviewed by a person.** The first author's review is recorded in `review/owner_review_TEST.csv` and
  `review/owner_review_DEV.csv` (columns `owner_decision` etc.) and summarised in `review/REVIEW_STATUS.md`.
  Until that file says the review is complete, these labels are a draft and any number scored against them is
  preliminary. CLAUDE.md Rule 3 requires a person to confirm every real-notebook label.
- No second, independent annotator. Cohen's kappa cannot be reported for this set; agreement between the draft and
  the first author's review (rows kept / changed / removed / added) is reported instead once the review exists.

## What the drafter had and had not seen

- **TEST (79):** LeakLens had never been run on these notebooks when the labels were written, and this commit
  freezes the labels before the first run. The Yang et al. analyser was running on them on Kaggle (job 10); its
  output had not been fetched. So the TEST labels are blind to both tools' output.
- **DEV (71):** not blind. LeakLens's static findings on the unlabelled DEV notebooks were read while the rules
  were written (EVAL_CHANGES #4) and again in later sessions. DEV numbers are reported separately and never as a
  held-out result.
- **Not independent of the tool's design.** The drafter wrote LeakLens's rules and knows what they look for. The
  labels follow the written guide, not the rules, but a reader should assume the two share blind spots: a leak
  that neither the guide nor the rules describe is likely to be missing from both. This is the main reason the
  set is not a substitute for independent human annotation.

## Conventions used

- `cell` is the displayed cell number (all cells counted from 1, as in the rendered text); the scorer subtracts 1.
- One row per leak; a notebook without a leak has one `none` row. Lines point at the cause of the leak (the fit,
  the resample, the split, the selection), not at the scoring call, as the guide asks.
- `unsure` marks rows where the code does not settle the question (for example a dataset that may contain
  duplicates, or a vocabulary fit on all texts). They are kept as labels; the scorer treats every row alike.
- Early stopping on the same folds whose out-of-fold score is reported, and a threshold or model chosen on the
  reported validation or test set, are labelled `multi_test` (guide Q3).
