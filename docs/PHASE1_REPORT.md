# Phase 1 report: taxonomy, specification, sandbox

Date: 2026-09-29. Status: **complete, but stopped under Integrity Rule 1**: the phase-boundary novelty search
found a code-level tool covering part of temporal leakage. Decision needed before Phase 2 (§4).

## 1. Decisions from the Phase 0 review, applied

| # | Decision | Done |
|---|---|---|
| 1 | Approve C1-C4 and the narrower framing | `CLAUDE.md` §1 and README updated; novelty re-check at every phase boundary is now Rule 1 (`docs/NOVELTY_LOG.md`) |
| 2 | LeakCheck: no LLM budget; draft an access email | Draft given in chat (not sent); status in `docs/EXCLUDED_BASELINES.md` |
| 3 | ReproGuard excluded | `docs/EXCLUDED_BASELINES.md` records the licence clause and what was read before the decision; local copy deleted |
| 4 | MIT licence; no code from other tools | `LICENSE`; `pyproject.toml` licence metadata; new Integrity Rule 11 |
| 5 | Working copy at `~/Desktop/leaklens` | Cloned there at `e2a86a5` (clean, same HEAD); session moved |
| 6 | Sandbox with clean env, throwaway dir, internet off, and a test | `src/leaklens/sandbox.py`, `configs/sandbox.yaml`, `tests/test_sandbox.py`; verified on Kaggle (§3) |
| 7 | Draoui +22% / +15% | ACM page still 403; the published abstract (via Crossref and Semantic Scholar) states both figures; marked `from abstract` |
| 8 | CI | It was not broken: run #1 on `e2a86a5` succeeded. My Phase 0 check ran before GitHub registered it |

## 2. Phase 1 deliverables

- [`docs/TAXONOMY.md`](TAXONOMY.md): six types with definition, static rule, dynamic check, canonical fix,
  default severity and the mapping to Kapoor & Narayanan's eight leaf types and Yang et al.'s three. Both mappings
  were checked against the papers' text. It also covers group-leakage intent (why group findings carry
  confidence and can be declared away), the temporal subtypes T1 and T2, and how overlapping types are reported.
- 14 runnable examples in `tests/fixtures/taxonomy/` (positive and negative per type, plus a file-path-entity
  group case and a forward-looking temporal feature). Each leaking line carries `# LEAK: <type>`. The document
  embeds them via `scripts/sync_taxonomy_examples.py`; a test fails if they drift apart.
- [`docs/SPEC.md`](SPEC.md): inputs (including notebook execution-order rule), modes, finding fields, report
  envelope, severity (prior vs measured), rule ids, suppression and project config, CI exit codes, SARIF mapping,
  non-functional targets.
- [`src/leaklens/report/finding.schema.json`](../src/leaklens/report/finding.schema.json): JSON Schema for a
  finding; tests check it against the spec, the package's type list, the exit codes and a worked example.
- Tests: 55 collected; 53 pass and 2 skip locally (the skipped ones need root and `/proc`, so they run on Kaggle).

## 3. Sandbox: what the Kaggle checks showed

| Check (all on Kaggle CPU, internet off) | Result |
|---|---|
| `01_sandbox_check` v1 | 12 `KAGGLE_*` variables in the session; none of their names or values reached the child. **But `dp.kaggle.net` (the data proxy) is reachable with internet off.** |
| `01b_sandbox_hardening_probe` | Jobs run as **root**. A clean-env root child **can** read the session token from `/proc/<parent>/environ` and `/proc/1/environ`. The same child as a fresh unprivileged user **cannot** (PermissionError). `unshare -n` is not permitted, so the proxy route cannot be cut. The proxy answers 404 without a token; no integrations are attached to the kernel. |
| Fix | Untrusted mode now requires a root parent and runs the child as user `llsandbox`; it refuses on a laptop or while the network is reachable. `trusted_code=True` (our own snippets) skips both. |
| `01_sandbox_check` v2 (code `9c45944`) | Child runs as uid 1000 with exactly the 9 allow-listed variables. Scanning every ancestor's `/proc/<pid>/environ` for the real data-proxy token (by SHA-256, value never handled by the child): **0 found** (2 ancestors unreadable). **Control**, same scan without the privilege drop: found in 2 ancestors, so the scan itself works. `tests/test_sandbox.py` + `tests/test_smoke.py` run as root: **15 passed**, including the 2 root-only tests that skip on the laptop. |

Remaining limits, stated in the module docstring: not a filesystem jail (world-readable paths are readable), and
the data proxy stays reachable (but the child cannot obtain its token).

## 4. Novelty check at the Phase 1 boundary: stop condition

Full entry: [`docs/NOVELTY_LOG.md`](NOVELTY_LOG.md).

**scicode-lint** (Samsonau, arXiv 2603.17893, MIT, PyPI 0.5.0) is a code-level linter whose patterns are
answered by a local 8B LLM. Two of its 66 patterns are temporal leakage:

| LeakLens subtype | scicode-lint | Coverage of ours |
|---|---|---|
| T1 non-chronological split | `ml-005`: `shuffle=True` in `KFold` / `StratifiedKFold` / `cross_val_score` with explicit temporal evidence. Treats `shuffle=False` as correct; `train_test_split` (shuffles by default) is not mentioned | partial |
| T2 forward-looking features | `ml-006`: negative `shift`, `center=True`, future slicing | close to complete |
| Group | none | none |
| Static-to-dynamic confirmation (C2) | none (LLM yes/no per pattern, no data flow) | none |
| Impact on the user's pipeline (C3) | none | none |

So the claim "no code-level tool detects temporal leakage" is no longer true. `CLAUDE.md` and the README now say
so; C1 is marked "reframing pending".

**Options (my recommendation first):**

1. **Reframe C1 as group leakage from code (still unclaimed), plus temporal leakage by data flow with dynamic
   confirmation, and add scicode-lint as a baseline for temporal.** The comparison is informative:
   rule-plus-data-flow versus LLM questions, on the same benchmark, per type. It also covers T1 cases scicode-lint
   does not claim (default `train_test_split`, unshuffled `KFold`). Cost: scicode-lint needs a local 8B LLM. The
   paper runs it on a GPU (RTX 4000 Ada); CPU inference on Kaggle would be slow but may be feasible for a
   benchmark-sized run. That must be measured, and it must not use CalibraEEG's GPU quota without your say.
2. Keep C1 as is and cite scicode-lint as concurrent work. I don't recommend this: a reviewer would see it.
3. Drop temporal from C1 entirely and focus on group. This loses the CalibraEEG case study's temporal regime.

Correction to a web summary: scicode-lint's `ml-009` is about train and test drawn from the same source without
a disjoint split (for example two `.sample()` calls), not about window stride; checked in its `pattern.toml`.

## 5. What I need from you

1. Pick an option in §4 (recommended: 1).
2. If option 1: may I measure scicode-lint's run time on a Kaggle **CPU** session with a handful of our taxonomy
   examples (no GPU)?
3. Send the LeakCheck email when you are happy with the draft, and tell me the date so I can log it.
