# LeakLens specification

Version 1.0 (Phase 1, 2026-09-29). Defines what LeakLens accepts, what it reports, and how it behaves in CI.
Leakage types and their rules are defined in [`TAXONOMY.md`](TAXONOMY.md). The finding format is also given as
a JSON Schema: [`src/leaklens/report/finding.schema.json`](../src/leaklens/report/finding.schema.json).

## 1. Inputs

| Input | Handling |
|---|---|
| `.py` file | Parsed with the Python 3.12 `ast` module. |
| `.ipynb` file | Read with `nbformat` (v4). Code cells are concatenated into one module with a line map back to (cell index, line in cell). |
| Directory | Recursively collects `.py` and `.ipynb`; skips hidden directories, `.venv`, `site-packages`, `.ipynb_checkpoints`, and paths matched by `exclude` in the config. |

**Notebook cell order.** LeakLens uses **execution order** when every code cell that has source also has an
`execution_count` and the counts are unique; otherwise it falls back to **cell order**. The order used is
recorded per file in the report (`ingest.order_used`: `execution` or `cell`) because the two can give different
findings.

**IPython syntax.** Lines starting with `%`, `%%` or `!` are replaced by `pass` (same line count), and
`get_ipython()` calls are left as opaque calls. Cells whose magic changes the language (`%%bash`, `%%sql`, ...)
are skipped and listed in the report.

**Unanalysable inputs.** Files that fail to parse (syntax errors, Python 2) are reported with
`status: "unanalysable"` and a reason. They are never silently skipped: they count in the coverage figures
(EVAL_PROTOCOL, Phase 3) and affect the exit code (§7).

**Libraries modelled in v1.** pandas, NumPy, scikit-learn, imbalanced-learn. Keras / PyTorch training loops are
recognised only as "a model is fitted on X and evaluated on Y" (no layer-level modelling). Calls into unmodelled
libraries are treated conservatively as opaque functions whose outputs depend on all inputs.

## 2. Modes

| Mode | Command | Executes code? | Where it may run |
|---|---|---|---|
| **static** (default) | `leaklens scan PATH...` | never | anywhere, including CI and pre-commit |
| **dynamic** | `leaklens scan --dynamic PATH...` | yes, instrumented, inside `leaklens.sandbox` | trusted code: anywhere, with `--trust-code`. Untrusted code: only an offline Kaggle session (the sandbox refuses when online) |
| **impact** | `leaklens scan --impact PATH...` | yes: original and fixed copies | as dynamic |

Static mode never opens a network connection and never imports the analysed code.

## 3. Findings

One finding is reported per `(file, line range, type)`. Fields (the JSON Schema is authoritative):

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable hash of `rule_id`, file path relative to the scan root, and the normalised source of the flagged lines. The same code gives the same id across runs and machines. |
| `rule_id` | string | Rule that fired, e.g. `LL-GRP-001` (§5). |
| `type` | enum | `preprocessing`, `overlap`, `multi_test`, `group`, `temporal`, `target_derived`. |
| `subtype` | string or null | e.g. `supervised` (preprocessing), `T1` / `T2` (temporal), `file_path_entity` (group). |
| `severity` | enum | `info`, `low`, `medium`, `high` (§4). |
| `confidence` | enum | `low`, `medium`, `high`: how certain LeakLens is that the leak exists (independent of severity). |
| `location` | object | `file`, `line_start`, `line_end` (1-based, in the original file; for notebooks, in the cell), `cell` (notebook cell index or null), `flat_line_start` / `flat_line_end` (line in the concatenated module). |
| `message` | string | One sentence, e.g. "Random split on rows that share `patient_id` values; the same patient can be in train and test." |
| `evidence` | list | Each item: `kind` (`data_flow`, `entity_column`, `time_column`, `forward_op`, `dynamic_overlap`, `single_feature_score`, ...), `detail` (text), optional `location`, optional `value` (number). |
| `related` | list of ids | Findings about the same lines or the same flow (TAXONOMY §8). |
| `suggested_fix` | object | `description` (text), `canonical_fix` (machine-readable fix name used by Phase 6, e.g. `replace_splitter:GroupShuffleSplit`), optional `patch` (unified diff). |
| `dynamic` | object | `status`: `not_run`, `confirmed`, `refuted`, `error`; `details` (for example shared entities, overlap fraction). |
| `impact` | object | `status`: `not_run`, `measured`, `unreliable`, `unknown`; `metric` (name as printed by the notebook), `value_leaky`, `value_fixed`, `delta` (= leaky − fixed), `n_runs`, `note`. `unreliable` means the fix changed more than the leak; `unknown` means the fixed copy failed to run. |
| `suppressed` | object or null | Set when a suppression matched (§6): `by` (`inline` or `config`), `reason`. Suppressed findings are kept in JSON/SARIF output but do not affect the exit code. |

**Report envelope.** A scan produces one JSON document:
`{"schema": "leaklens/report/v1", "tool": {"name", "version", "commit"}, "scan": {"root", "mode", "started_utc",
"config_hash"}, "files": [{"path", "status", "reason", "ingest": {"order_used", "skipped_cells"}}],
"findings": [...]}`.

## 4. Severity

Severity estimates **how much the leak can distort the reported result**. Confidence is separate.

1. **Prior**, from the type and subtype (TAXONOMY §1): `preprocessing` low (`supervised` subtype: high),
   `overlap` high, `multi_test` medium, `group` high, `temporal` high, `target_derived` low. The priors follow the
   measured severity ranking in Roth (arXiv:2604.04199).
2. **Measured**, when impact mode ran and `impact.status == "measured"`: severity is set from `|delta|` using the
   thresholds in the config (defaults to be fixed in the Phase 3 protocol, before any TEST result is seen).
   `target_derived` findings stay at most `low` (flag only) whatever the impact.
3. `info` is used for context notes (for example "notebook ran in cell order; execution order unavailable").

## 5. Rule identifiers

| Prefix | Type | Initial rules (implemented in Phase 4) |
|---|---|---|
| `LL-PRE` | preprocessing | `001` transformer fit before split; `002` pandas/NumPy statistic over rows before split; `003` supervised selection/encoding before split |
| `LL-OVL` | overlap | `001` evaluation data flows to fit; `002` resampling/augmentation before split; `003` train+test concatenation into fit; `004` duplicate rows across split (dynamic only) |
| `LL-MUL` | multi_test | `001` repeated scoring on evaluation data feeding a selection; `002` evaluation data used for early stopping |
| `LL-GRP` | group | `001` row-level splitter with candidate entity column; `002` CV helper with default/integer CV and candidate entity column; `003` file-path-derived entity; `004` entity overlap across split (dynamic) |
| `LL-TMP` | temporal | `001` non-chronological split/CV on time-ordered data (T1); `002` forward-looking feature operation (T2); `003` time overlap across split (dynamic) |
| `LL-TGT` | target_derived | `001` feature computed from the target; `002` high single-feature score (dynamic) |

Rule ids are never reused. Retired rules are listed in `CHANGELOG.md` (Phase 9).

## 6. Suppression and project configuration

**Inline.** `# leaklens: ignore` on the flagged line suppresses all types there;
`# leaklens: ignore[group,temporal]` suppresses the listed types. The comment may carry a reason:
`# leaklens: ignore[group] -- within-patient model by design`.

**Project config.** `leaklens.yaml` at the scan root, or `[tool.leaklens]` in `pyproject.toml`:

```yaml
entity_columns: [patient_id]        # always treat as entity; raises group confidence
time_columns: [visit_date]
not_entities: [hospital_ward]       # never treat as entity
generalisation: new_entities        # or: within_entities (turns group findings into info)
ignore: [target_derived]            # types to suppress everywhere
exclude: ["notebooks/scratch/**"]
fail_on: high                       # see §7
min_confidence: medium
```

## 7. CLI exit codes (CI contract)

| Code | Meaning |
|---|---|
| `0` | No unsuppressed finding at or above `--fail-on` severity with at least `--min-confidence`, and every input was analysed. |
| `1` | At least one unsuppressed finding at or above the thresholds. |
| `2` | Usage or configuration error (bad flag, unreadable config, path not found). |
| `3` | Nothing could be analysed (every input unanalysable), or the requested mode is unavailable. With `--strict`, also when **any** input is unanalysable. |

Defaults: `--fail-on high --min-confidence medium`. `--fail-on never` always exits 0 or 2/3 (report-only
mode). If both 1 and 3 apply, the exit code is `1`: a confirmed leak matters more than a partly unanalysable
input, and the unanalysable files are still listed in the report.

## 8. Output formats

| Format | Flag | Notes |
|---|---|---|
| Terminal | default | Grouped by file; one line per finding with location, type, severity, confidence; details with `-v`. |
| JSON | `--format json` | The report envelope (§3). |
| SARIF 2.1.0 | `--format sarif` | For GitHub code scanning. `ruleId` = `rule_id`; `level`: high → `error`, medium → `warning`, low/info → `note`; confidence, impact and dynamic status in `properties`; suppressed findings use SARIF `suppressions`. Notebook findings point at the `.ipynb` file with the cell index in `properties` (GitHub cannot highlight cells). |
| HTML | `--format html` | Code with highlighted findings (Phase 9, optional). |

## 9. Non-functional requirements

| Requirement | Target (measured in Phase 7) |
|---|---|
| Static analysis time | median under 10 s per notebook on a Kaggle CPU session. For reference, Yang et al. report a 3.23 s mean. |
| Determinism | Same inputs, config and version give byte-identical JSON apart from timestamps. |
| No network in static mode | Enforced by design; tested. |
| No code execution in static mode | The analysed code is never imported or run. |
| Python | 3.12 (matches Kaggle). |
