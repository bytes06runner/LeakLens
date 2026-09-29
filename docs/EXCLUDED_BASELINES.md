# Excluded baselines

Tools we identified but do not run or compare against, with the reason. For the paper's threats-to-validity and
related-work sections.

## ReproGuard 0.5.2 (PyPI, first release 2026-08-09)

- **What it is:** a code-level scanner for notebooks and ML repositories. Its data-leakage checks are heuristic
  (regular expressions and name patterns). Its public rule titles cover preprocessing before a split,
  target-like column names in features, test data in a fitting call, and suspiciously high metrics. It has no
  group or temporal leakage rule.
- **Licence:** "ReproGuard Software License (RSL) Version 1.0", proprietary and source-available. Section 3
  permits personal and academic use of the scanner. **Section 4(d)** forbids using "the Software, its source code,
  its ideas, or its check logic to build, develop, or power a competing product, tool, plugin, or service"
  without written permission. Section 5 requires the credit "ReproGuard by Vipul Gote" wherever it is referenced.
- **Decision (2026-09-29):** excluded. LeakLens is a leakage detector, so benchmarking against ReproGuard and
  reporting the comparison could be read as using it to develop a competing tool.
- **What we did before the decision:** during the Phase 0 novelty check we downloaded the wheel from PyPI and
  read the rule titles and rule codes in its leakage module (LEAK001 to LEAK007) to establish whether it covers
  group or temporal leakage. It was never run. The local copy was deleted. No ReproGuard code, rule, pattern or
  threshold is used in LeakLens. LeakLens's rules derive from the taxonomy in `CLAUDE.md` section 4, which
  predates this review, and from the published literature.
- **Paper wording (suggested):** "ReproGuard by Vipul Gote was not evaluated because its licence prohibits use of
  its check logic for building competing tools. From its public documentation it targets pre-split
  preprocessing, target-like column names and test-data misuse, and has no group or temporal leakage rule."

## LeakCheck / ml-slicer (Draoui et al., PACMSE 2026): deferred, not excluded

Needs an LLM API key (per-notebook cost) and a running ml-slicer Docker service. No LLM budget at present.
An email asking the authors for access to their replication package and labelled benchmark (Zenodo, CC-BY-4.0,
files access-restricted) was sent by the project owner on 2026-09-29, with the supervisor in CC (date as reported
by the owner). Reply: pending. The decision on an LLM-based baseline is deferred to Phase 7.
