# Paper draft: verification result and corrections (2026-11-13)

Draft checked: `LeakLens_Paper_Draft.pdf` (7 pages). Every number was recomputed from the committed result files
by `scripts/verify_paper_claims.py`; the full table is `docs/PAPER_CLAIM_CHECK.md` (84 checks). Text claims were
checked against the sources named below.

**Result: 83 of 84 numeric checks pass. Two statements need correcting; one result can be added.**

## Corrections

1. **Section 4.5, test suite.** Draft: "Its test suite has 371 passing tests". Measured: 371 tests; on a laptop
   369 pass and 2 are skipped because they need root (they run in the Kaggle sandbox job). Replace with:
   > Its test suite has 371 tests (369 run on a laptop; the 2 sandbox tests that need root run in the cloud job),
2. **Section 5.4, scicode-lint.** Draft: "scicode-lint needs a GPU with 20 GB of memory in its published setup".
   Its README (PyPI 0.5.0) says: "Requires a GPU with 16GB+ VRAM" and "native FP8 support". Replace with:
   > scicode-lint needs a GPU with at least 16 GB of memory and native FP8 support in its published setup;

## Addition (optional, recommended): significance of the Yang et al. comparison

Same files, same per-file rule as Table 4, no new run (`baselines/yang/paired_test.py`,
`results/2026-11-13_yang_paired_test/output.txt`). Suggested sentence for Section 6.4, after "...found 33 of 37
with none.":
> On the 37 file-and-type pairs the two tools share, LeakLens alone was right in 14 and the baseline alone in 1
> (both in 19, neither in 3); an exact McNemar test gives p < 0.001 (p = 0.00098). The difference comes from
> preprocessing leakage (12 against 1, p = 0.003); on overlap the tools agree on every file.

## Verified and unchanged

All of Tables 1, 3 and 4; every count in Sections 5 and 6 (benchmark sizes, DEV/TEST, temporal categories,
dynamic confirmation 43/0/25/2, impact coverage 34 of 70, MAE 0.035 and Spearman 0.58, second look 67/73 and
73/73 with MAE 0.0006 and Spearman 0.97, timings 2.6 ms / 1.3 s / 12.7 s / Yang 6.2 s, real-set 71/79, case
study 78 files / 0 findings, sandbox 0 vs 2); literature figures (Kapoor 294/17; Yang 107,603 / 29.6%,
97.6% (40/41), 67.8% (40/59), 100 notebooks of which 94 analysed, 3.23 s; Roth 0.005 in nine conditions;
Brookshire 17 of 63 and 99.8% to 53.0%; Draoui 22% / 15% from the abstract); six fix kinds; abstract
interpretation; property-based tests.

## What the paper must keep saying

The 33-vs-20 result and its p-value are on files this project generated. The paper's caveat in Section 6.4
("This comparison favours LeakLens...") and the statement that no result on human-labelled real notebooks exists
must stay; removing them would make the claims untrue.
