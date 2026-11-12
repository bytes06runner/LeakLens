# Evaluation protocol: one-page summary for approval

Full text: [`EVAL_PROTOCOL.md`](../EVAL_PROTOCOL.md). **Nothing is scored on TEST until you approve this page.**

**What we measure.** For each of the six leakage types separately: precision (of the leaks the tool reports, how
many are real), recall (of the real leaks, how many the tool finds) and F1, each with a 95% confidence interval.
There is no single overall score, so a weak type cannot hide.

**When a report counts as correct.** The tool's finding must be in the same file and notebook cell as the labelled
leak, on overlapping lines, with the same leak type. Each finding can match one label. Extra findings are false
positives. Unfound labels are misses. The same rule and the same code score LeakLens and every other tool.

**Which findings count.** LeakLens gives each finding a confidence. The headline uses findings of medium or high
confidence, which is what the command line shows by default. Results with low-confidence findings included are
reported next to it.

**Two ways of running.** Static (reads the code, runs nothing) and static plus dynamic (also runs the file with
instrumentation). We report both, so the value added by the run is visible. Leaks that only exist in the data
(duplicate rows) still count against the static mode.

**Clean files.** We report how often a tool raises an alarm on a file that has no leak.

**Impact estimates.** On the injected benchmark we know how much each leak inflates the score. We compare
LeakLens's estimate (re-run with the fix) with that true value: average error, whether the direction is right, and
rank agreement. Fixes that cannot be applied are reported as "unknown", not dropped. These injected numbers show
how accurate the estimate is; they are not evidence of how bad leakage is in real code.

**Other tools.** Run exactly as released, with default settings. A tool that cannot run on an input gets that
counted, not hidden. Numbers other papers report on their own data are never mixed into our tables.

**The rules that keep it honest.**
1. Detection rules and thresholds are tuned on DEV only. DEV numbers are always labelled DEV.
2. TEST is scored once per release, all tools together. Any later change is logged with what had been seen.
3. Real notebooks are labelled by two people who do not see the tool's output; we report their agreement.
4. Bad results are reported.

**Known weak points, stated in the paper.** The injected benchmark and the tool have the same author (TEST uses
different pipelines but the same kinds of injected leak). Some types have few TEST leaks, so intervals are wide.
The names of the entity columns in TEST pipelines were seen once by accident (logged).

**Decision needed from you:** approve as is, or tell me what to change. After approval I commit "Freeze evaluation
protocol" and run TEST once.
