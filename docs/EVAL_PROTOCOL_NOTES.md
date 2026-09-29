# Notes to carry into EVAL_PROTOCOL.md (Phase 3)

Collected before the protocol is written, so they are not forgotten. Each becomes a section of the frozen
protocol.

1. **Use of injected inflation (decision 2026-09-29).** True inflation on the injected set is by construction. It may
   be used only to evaluate (a) detection and (b) impact-estimation accuracy (estimated vs true inflation per
   finding, e.g. absolute error, rank correlation, sign agreement), never as evidence of real-world severity.
   Severity claims come only from real notebooks and the CalibraEEG case study. Wording: `docs/PAPER_WORDING.md`.
2. **Differentiating category.** Results on `temporal_differentiating` and `temporal_hard` items are reported
   separately from `temporal_common`, for LeakLens and for scicode-lint.
3. **Multi-type leaks.** Labels carry `alt_types`; a finding matches a label if its type is the label's type or one
   of its `alt_types` (e.g. whole-series scaling on time-ordered data: temporal, or preprocessing).
4. **Dynamic-only leaks** (`dynamic_only`, raw duplicated records) are labelled at the split call; static-only runs
   are expected to miss them and are reported with that caveat, not excluded.
5. **Split unit.** DEV/TEST is by base pipeline; bootstrap CIs should resample items within split, and a
   sensitivity analysis should resample bases (items of one base are correlated).
6. **Inflation units differ by metric** (AUC, AP, R², MAE). Impact-estimation error is reported per metric, or on a
   normalised scale defined in the protocol.
