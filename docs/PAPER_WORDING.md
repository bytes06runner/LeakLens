# Agreed paper wording

Sentences the project owner has approved for the paper. Use them verbatim or keep their meaning exactly.

## Injected-benchmark inflation is by construction (decision 2026-09-29)

> The injected benchmark's inflation values are properties of our synthetic generators, which were designed (and,
> for group leakage, adjusted after a first measurement) so that each leak type can change the metric. We use them
> only where the true answer must be known: to score detection and to measure the accuracy of impact estimates. They
> are not evidence of how severe any leakage type is in practice. Severity claims in this paper rest only on real
> notebooks (Section X) and the CalibraEEG case study (Section Y).

## Temporal leakage positioning (decision 2026-09-29)

> Detecting temporal leakage from code is not new: scicode-lint [Samsonau 2026] flags shuffled cross-validation on
> explicitly temporal data and forward-looking features. LeakLens detects it through data-flow analysis and confirms
> it on the data; we report separately the cases where the two approaches differ.

## Excluded baseline (decision 2026-09-29)

See `docs/EXCLUDED_BASELINES.md` for the ReproGuard sentence.
