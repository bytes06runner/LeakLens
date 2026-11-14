"""Link static findings to an instrumented run (Phase 5) and measure their impact by re-running with a fix
(Phase 6).

The static pass nominates call sites and columns; the run supplies facts about the data at those call sites.
A finding ends up `confirmed`, `refuted` or left `not_run` (no check exists for the rule, or its call site was
not reached). Findings that only the run can make (duplicate rows already in the raw data, an entity column the
code never mentions) are added. Nothing here executes code itself: `run_instrumented` starts
`leaklens.dynamic.runner` as a child process.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from leaklens.config import load_config
from leaklens.ingest import Source
from leaklens.report.findings import CONFIDENCE_ORDER, Finding

CFG = load_config("dynamic")
_LEVELS = ["low", "medium", "high"]
_METRIC = re.compile(r"^\s*([A-Za-z_][\w \-/()]*?)\s*[:=]\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*%?\s*$")
_GROUP_AWARE = ("Group", "LeaveOneGroupOut", "LeavePGroupsOut")
_NO_CHECK = {
    "LL-TMP-002": "forward-looking features are not checked at run time in this version (TAXONOMY section 6)",
    "LL-PRE-002": "pandas/NumPy statistics are not instrumented; only scikit-learn transformers are",
    "LL-MUL-002": "early stopping is not instrumented",
}


def parse_metric(stdout: str) -> tuple[str, float] | None:
    """The last `name: value` line a script printed: the metric it reports."""
    for line in reversed(stdout.splitlines()):
        m = _METRIC.match(line)
        if m:
            return m.group(1).strip(), float(m.group(2))
    return None


def lower_is_better(metric: str) -> bool:
    name = metric.lower()
    return any(tok in re.split(r"[^a-z0-9]+", name) or name.endswith(tok) for tok in CFG["lower_is_better_tokens"])


def run_instrumented(
    script: Path, cwd: Path, hints: dict | None = None, fix: dict | None = None, timeout: float = 600
) -> dict:
    """Run `script` (trusted code) in `cwd` with instrumentation. Returns the event log plus stdout and status."""
    with tempfile.TemporaryDirectory(prefix="leaklens-dyn-") as tmp:
        out = Path(tmp) / "events.json"
        argv = [sys.executable, "-W", "ignore", "-m", "leaklens.dynamic.runner", str(script), "--out", str(out)]
        for name, payload in (("hints", hints), ("fix", fix)):
            if payload is not None:
                p = Path(tmp) / f"{name}.json"
                p.write_text(json.dumps(payload))
                argv += [f"--{name}", str(p)]
        try:
            proc = subprocess.run(
                argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": f"no result within {timeout} s",
                "events": [],
                "stdout": "",
                "fix_applied": [],
                "split_positions": {},
            }
        log = (
            json.loads(out.read_text())
            if out.exists()
            else {
                "status": "error",
                "error": proc.stderr[-400:],
                "events": [],
                "fix_applied": [],
                "split_positions": {},
            }
        )
        log["stdout"], log["stderr"] = proc.stdout, proc.stderr[-2000:]
        return log


def _bump(f: Finding) -> None:
    f.confidence = _LEVELS[min(CONFIDENCE_ORDER[f.confidence] + 1, 2)]


def _set(f: Finding, status: str, **details) -> None:
    f.dynamic = {"status": status, "details": details} if details else {"status": status}


def _at(events: list[dict], kind: str, f: Finding) -> list[dict]:
    return [e for e in events if e["kind"] == kind and f.flat_line_start <= e["line"] <= f.flat_line_end]


def apply_events(findings: list[Finding], log: dict, src: Source) -> list[Finding]:
    """Set each finding's dynamic status from the event log and append the findings only the run can make."""
    if log.get("status") != "ok" and not log.get("events"):
        for f in findings:
            f.dynamic = {"status": "error", "details": {"reason": log.get("error") or log.get("status")}}
        return findings
    events = log["events"]
    splits = [e for e in events if e["kind"] == "split"]
    by_line: dict[int, list[dict]] = defaultdict(list)
    for e in splits:
        by_line[e["line"]].append(e)
    ent_min = CFG["entities"]["min_test_rows_shared"]
    time_min = CFG["time"]["min_train_after_test"]
    dup = CFG["duplicates"]

    for f in findings:
        if f.rule_id in _NO_CHECK or f.context.get("instrumented") is False:
            _set(f, "not_run", reason=_NO_CHECK.get(f.rule_id, _NO_CHECK["LL-PRE-002"]))
            continue
        if f.type == "group":
            folds = _at(events, "split", f)
            cols = f.context.get("entity_columns", [])
            # Every entity column found at run time at this split is a candidate, not only the ones the static
            # pass nominated: a strong-name column with repeated values beats a nominated weak-name one.
            seen = [(c, s) for e in folds for c, s in e["entities"].items() if c in cols or s["strength"] == "strong"]
            if not folds:
                _set(f, "not_run", reason="the split was not reached in the run")
            elif not seen:
                _set(f, "not_run", reason="the nominated column is not row-aligned with the split data at run time")
            else:
                live = [cs for cs in seen if cs[1]["test_rows_shared"] >= ent_min and cs[1]["n_unique"] < cs[1]["n"]]
                col, best = max(live or seen, key=lambda cs: (cs[1]["strength"] == "strong", cs[1]["test_rows_shared"]))
                if live:
                    nominated = next(iter(cols), None)
                    if col != nominated and nominated is not None:
                        f.message = f.message.replace(f"`{nominated}`", f"`{col}`").replace(
                            f"the same {nominated} ", f"the same {col} "
                        )
                        f.fix_description = f.fix_description.replace(f"`{nominated}`", f"`{col}`")
                        f.evidence.append(
                            {
                                "kind": "entity_column",
                                "detail": f"column `{col}` found at run time (name evidence); "
                                f"it replaces the static guess `{nominated}`",
                            }
                        )
                    _set(
                        f,
                        "confirmed",
                        column=col,
                        shared_entities=best["shared"],
                        entities=best["n_unique"],
                        test_rows_with_entity_in_train=round(best["test_rows_shared"], 4),
                    )
                    f.evidence.append(
                        {
                            "kind": "dynamic_overlap",
                            "value": best["test_rows_shared"],
                            "detail": f"{best['shared']} values of `{col}` occur on both sides of the split; "
                            f"{best['test_rows_shared']:.0%} of evaluation rows belong to them",
                        }
                    )
                    f.context["confirmed_column"] = col
                    if best["strength"] == "strong":  # a weak-name column that repeats proves little by itself
                        _bump(f)
                        if col not in cols:
                            _bump(f)  # same evidence as a run-time-only finding: strong name and measured overlap
                else:
                    why = (
                        "every value is unique: one row per entity"
                        if all(s["n_unique"] >= s["n"] for _, s in seen)
                        else "no value occurs on both sides of the split"
                    )
                    _set(f, "refuted", reason=f"`{col}`: {why}")
        elif f.rule_id == "LL-TMP-001":
            folds = _at(events, "split", f)
            vals = [(c, t["train_after_test"]) for e in folds for c, t in e["times"].items()]
            if not folds or not vals:
                _set(
                    f,
                    "not_run",
                    reason="no timestamp column is row-aligned with the split data at run time"
                    if folds
                    else "the split was not reached in the run",
                )
            else:
                col, worst = max(vals, key=lambda cv: cv[1])
                if worst >= time_min:
                    _set(f, "confirmed", column=col, training_rows_after_earliest_evaluation_row=round(worst, 4))
                    f.evidence.append(
                        {
                            "kind": "dynamic_overlap",
                            "value": worst,
                            "detail": f"{worst:.0%} of training rows are dated after the earliest "
                            f"evaluation row (`{col}`)",
                        }
                    )
                    f.context["confirmed_column"] = col
                    if f.confidence != "low":  # time overlap is certain once a date exists; it adds no evidence
                        _bump(f)  # that the task is a forecast, so a low finding stays low
                else:
                    _set(f, "refuted", reason=f"training rows are not later than evaluation rows (`{col}`)")
        elif f.canonical_fix == "fit_on_train_only" and f.type in ("preprocessing", "temporal"):
            fits = _at(events, "tfit", f)
            if not fits:
                _set(f, "not_run", reason="the fit was not observed in the run")
            elif any(s["n"] == t["n"] for t in fits for s in splits):
                _set(f, "confirmed", fitted_rows=fits[0]["n"], note="the fit saw every row of data that is split")
                _bump(f)
            elif any(s["n_train"] == t["n"] for t in fits for s in splits):
                _set(f, "refuted", reason="the fit saw exactly the training rows of a split")
            else:
                _set(f, "not_run", reason="fitted rows could not be related to a split by row count")
        elif f.rule_id in ("LL-OVL-001", "LL-OVL-003"):
            evals = [
                e
                for e in events
                if e["kind"] == "eval"
                and e.get("fit_line") is not None
                and f.flat_line_start <= e["fit_line"] <= f.flat_line_end
                and e["in_fit"] is not None
            ]
            if not evals:
                _set(f, "not_run", reason="no scoring call of a model fitted here was observed")
            else:
                worst = max(e["in_fit"] for e in evals)
                if worst >= CFG["fit_overlap"]["confirm_at"]:
                    _set(f, "confirmed", scored_rows_seen_in_fit=round(worst, 4))
                    f.evidence.append(
                        {
                            "kind": "dynamic_overlap",
                            "value": worst,
                            "detail": f"{worst:.0%} of the scored rows were among the fitted rows",
                        }
                    )
                    _bump(f)
                elif worst < CFG["fit_overlap"]["refute_below"]:
                    _set(f, "refuted", reason="none of the scored rows were among the fitted rows")
                else:
                    _set(f, "not_run", reason=f"only {worst:.1%} of scored rows were among the fitted rows")
        elif f.rule_id == "LL-OVL-002":
            folds = [e for ln in f.context.get("split_lines", []) for e in by_line.get(ln, []) if e["dup"]]
            worst = max((e["dup"]["test_in_train"] for e in folds), default=None)
            if worst is not None and worst >= dup["min_test_in_train"]:
                _set(f, "confirmed", evaluation_rows_identical_to_a_training_row=round(worst, 4))
                f.evidence.append(
                    {
                        "kind": "dynamic_overlap",
                        "value": worst,
                        "detail": f"{worst:.0%} of evaluation rows have an identical training row",
                    }
                )
                _bump(f)
            else:  # synthetic rows (SMOTE) are not exact copies, so the absence of copies refutes nothing
                _set(f, "not_run", reason="no identical rows across the split; synthetic rows cannot be checked")
        elif f.rule_id == "LL-MUL-001":
            metrics, evals, cvs = _at(events, "metric", f), _at(events, "eval", f), _at(events, "cv", f)
            groups: dict[str, set] = defaultdict(set)
            for e in metrics:
                groups[f"m{e['y_sig']}"].add(e["p_sig"])
            for e in evals:
                groups[f"e{e['x_sig']}"].add(e["params"])
            for e in cvs:
                groups[f"c{e['x_sig']}"].add(e["params"])
            n = max((len(v) for v in groups.values()), default=0)
            if not groups:
                _set(f, "not_run", reason="no scoring call was observed on this line")
            elif n >= 2:
                _set(f, "confirmed", candidates_scored_on_the_same_rows=n)
                _bump(f)
            else:
                _set(f, "refuted", reason="only one candidate was scored on these rows")
        elif f.type == "target_derived":
            feat = f.context.get("feature")
            hits = [e for e in events if e["kind"] == "single_feature" and e["feature"] == feat]
            if hits and max(e["score"] for e in hits) >= CFG["single_feature"]["confirm_at"]:
                best = max(hits, key=lambda e: e["score"])
                _set(f, "confirmed", single_feature_score=round(best["score"], 4), metric=best["metric"])
                f.evidence.append(
                    {
                        "kind": "single_feature_score",
                        "value": best["score"],
                        "detail": f"`{feat}` alone gives {best['metric']} {best['score']:.3f} on the target",
                    }
                )
                _bump(f)
            else:
                _set(f, "not_run", reason="single-feature score below the threshold or not computed")
        else:
            _set(f, "not_run", reason="no run-time check for this rule")

    return findings + _dynamic_only(findings, by_line, src)


def _locate(src: Source, line: int) -> tuple[int | None, int]:
    return src.locate(line)


def _new(
    src: Source,
    rule: str,
    type_: str,
    subtype: str,
    confidence: str,
    line: int,
    message: str,
    evidence: list[dict],
    fix: str,
    canonical: str | None,
    details: dict,
    context: dict,
) -> Finding:
    f = Finding(
        rule, type_, subtype, confidence, src.path, line, line, message, evidence, fix, canonical, context=context
    )
    f.cell, f.line_start = _locate(src, line)
    f.line_end = f.line_start
    f.set_id(" ".join(src.line_text(line).split()))
    f.dynamic = {"status": "confirmed", "details": details}
    return f


def _dynamic_only(findings: list[Finding], by_line: dict[int, list[dict]], src: Source) -> list[Finding]:
    out: list[Finding] = []
    dup = CFG["duplicates"]
    ent_min = CFG["entities"]["min_test_rows_shared"]
    time_min = CFG["time"]["min_train_after_test"]
    explained = {ln for f in findings if f.type == "overlap" for ln in f.context.get("split_lines", [])}

    def has(type_: str, line: int) -> bool:
        return any(f.type == type_ and f.flat_line_start <= line <= f.flat_line_end for f in findings)

    for line, folds in sorted(by_line.items()):
        call = folds[0]["call"]
        dups = [e["dup"] for e in folds if e["dup"]]
        if dups and line not in explained and not has("overlap", line):
            worst = max(dups, key=lambda d: d["test_in_train"])
            if (
                worst["test_in_train"] >= dup["min_test_in_train"]
                and worst["distinct_frac"] >= dup["min_distinct_frac"]
            ):
                out.append(
                    _new(
                        src,
                        "LL-OVL-004",
                        "overlap",
                        "raw_duplicates",
                        "high",
                        line,
                        f"{worst['test_in_train']:.0%} of the evaluation rows are identical to a training row: the "
                        "data "
                        "contains duplicated records, and the split puts copies on both sides.",
                        [
                            {
                                "kind": "dynamic_overlap",
                                "value": worst["test_in_train"],
                                "detail": f"{call}: identical rows on both sides of the split; "
                                f"{worst['distinct_frac']:.0%} of all rows are distinct",
                            }
                        ],
                        "Remove duplicated records before the split (for example drop_duplicates on the feature "
                        "columns).",
                        "deduplicate_before_split",
                        {"evaluation_rows_identical_to_a_training_row": round(worst["test_in_train"], 4)},
                        {"split_lines": [line]},
                    )
                )
        group_aware = call.startswith(_GROUP_AWARE) or "Group" in call.split(".")[0]
        if not group_aware and not has("group", line):
            best: tuple[str, dict] | None = None
            for e in folds:
                for c, s in e["entities"].items():
                    if s["strength"] == "strong" and s["n_unique"] < s["n"] and s["test_rows_shared"] >= ent_min:
                        if best is None or s["test_rows_shared"] > best[1]["test_rows_shared"]:
                            best = (c, s)
            if best is not None:
                c, s = best
                fix = "GroupShuffleSplit" if call == "train_test_split" else "GroupKFold"
                out.append(
                    _new(
                        src,
                        "LL-GRP-004",
                        "group",
                        "entity_overlap",
                        "high",
                        line,
                        f"The data has a column `{c}` that the split ignores: {s['shared']} of its values are on both "
                        f"sides, and {s['test_rows_shared']:.0%} of the evaluation rows belong to an entity that is "
                        "also "
                        "in the training rows.",
                        [
                            {"kind": "split_call", "detail": f"{call}: row-level, not group-aware"},
                            {
                                "kind": "entity_column",
                                "detail": f"column `{c}` found at run time ({s['n_unique']} values in "
                                f"{s['n']} rows; name evidence)",
                            },
                            {
                                "kind": "dynamic_overlap",
                                "value": s["test_rows_shared"],
                                "detail": f"{s['shared']} values of `{c}` occur on both sides of the split",
                            },
                        ],
                        f"Split by entity: use {fix} with groups=`{c}` (same folds, test size and seed).",
                        f"replace_splitter:{fix}",
                        {
                            "column": c,
                            "shared_entities": s["shared"],
                            "test_rows_with_entity_in_train": round(s["test_rows_shared"], 4),
                        },
                        {"entity_columns": [c], "confirmed_column": c},
                    )
                )
        if "TimeSeriesSplit" not in call and not has("temporal", line):
            vals = [(c, t["train_after_test"]) for e in folds for c, t in e["times"].items()]
            if vals:
                c, worst = max(vals, key=lambda cv: cv[1])
                if worst >= time_min:
                    out.append(
                        _new(
                            src,
                            "LL-TMP-003",
                            "temporal",
                            "T1",
                            "low",
                            line,
                            f"{worst:.0%} of the training rows are dated after the earliest evaluation row (`{c}`). If "
                            "the task is a forecast, the model is trained on the future.",
                            [
                                {"kind": "split_call", "detail": f"{call}: not a forward-chaining split"},
                                {"kind": "time_column", "detail": f"column `{c}` holds timestamps (found at run time)"},
                                {
                                    "kind": "dynamic_overlap",
                                    "value": worst,
                                    "detail": "training rows later than evaluation rows",
                                },
                            ],
                            "If rows are ordered in time, split chronologically (shuffle=False or TimeSeriesSplit).",
                            "replace_splitter:chronological",
                            {"column": c, "training_rows_after_earliest_evaluation_row": round(worst, 4)},
                            {"time_columns": [c], "confirmed_column": c},
                        )
                    )
    return out


# ------------------------------------------------------------------------------------------- impact (Phase 6)


def fix_for_finding(f: Finding, log: dict) -> tuple[dict | None, str | None]:
    """The run-time fix for a finding, or (None, reason) when this version has no automatic fix for it."""
    events = log.get("events", [])
    split_lines = sorted(
        {e["line"] for e in events if e["kind"] == "split" and f.flat_line_start <= e["line"] <= f.flat_line_end}
    )
    if f.type == "group":
        col = f.context.get("confirmed_column") or next(iter(f.context.get("entity_columns", [])), None)
        if not split_lines or col is None:
            return None, "the split call or the entity column was not found at run time"
        return {"kind": "group_split", "line": split_lines[0], "column": col}, None
    if f.rule_id in ("LL-TMP-001", "LL-TMP-003"):
        if not split_lines:
            return None, "the split call was not reached at run time"
        return {"kind": "time_split", "line": split_lines[0], "column": f.context.get("confirmed_column")}, None
    if f.rule_id in ("LL-OVL-001", "LL-OVL-003"):
        return {"kind": "fit_drop_test_rows", "line": f.flat_line_start}, None
    if f.type == "target_derived" and f.context.get("feature"):
        return {"kind": "drop_feature", "line": None, "column": f.context["feature"]}, None
    if f.rule_id == "LL-OVL-004":
        if not split_lines:
            return None, "the split call was not reached at run time"
        return {"kind": "dedupe_split", "line": split_lines[0]}, None
    if f.canonical_fix == "fit_on_train_only" and f.context.get("instrumented") is False:
        return None, "a pandas/NumPy statistic cannot be re-fitted on training rows automatically"
    if f.canonical_fix == "fit_on_train_only" and f.context.get("instrumented", True) and f.rule_id != "LL-PRE-002":
        fits = [
            e
            for e in events
            if e["kind"] == "tfit"
            and f.flat_line_start <= e["line"] <= f.flat_line_end
            and e["method"] == "fit_transform"
        ]
        if not fits:
            return None, "only a fit_transform call on one line can be re-fitted automatically in this version"
        for _, pos in sorted(log.get("split_positions", {}).items(), key=lambda kv: int(kv[0])):
            if pos["n"] == fits[0]["n"]:
                if pos["folds"] != 1 or pos["test"] is None:
                    return (
                        None,
                        "the data is cross-validated: re-fitting inside each fold is not automated in this version",
                    )
                return {
                    "kind": "fit_on_train_rows",
                    "line": fits[0]["line"],
                    "n": pos["n"],
                    "test_positions": pos["test"],
                }, None
        return None, "no split of the fitted rows was observed"
    return None, {
        "overlap": "moving a resampling step after the split is not automated in this version",
        "multi_test": "nested validation is not automated in this version",
        "temporal": "replacing a forward-looking feature is not automated in this version",
        "preprocessing": "a pandas/NumPy statistic cannot be re-fitted on training rows automatically",
    }.get(f.type, "no automatic fix")


def severity_from_delta(metric: str, leaky: float, fixed: float) -> str:
    delta = abs(leaky - fixed)
    if lower_is_better(metric):
        delta = delta / abs(fixed) if fixed else delta
    th = CFG["severity_from_impact"]
    return "high" if delta >= th["high"] else "medium" if delta >= th["medium"] else "low"


def eval_set_change(base: dict, fixed: dict) -> dict | None:
    """Compare the evaluation rows of the original and the fixed run (opt-in recording, LEAKLENS_RECORD_EVAL=1).

    Per split call present in both runs and per recorded fold: identical when the same row positions of the same
    number of rows are evaluated, or the same multiset of row fingerprints; otherwise the Jaccard overlap of the
    fingerprint sets and the change in evaluated rows.
    """
    a, b = base.get("eval_rows"), fixed.get("eval_rows")
    if not a or not b:
        return None
    from collections import Counter

    folds, identical, jac, n_a, n_b = 0, True, [], 0, 0
    lines = sorted(set(a) | set(b), key=int)
    for line in lines:
        fa = {r["fold"]: r for r in a.get(line, [])}
        fb = {r["fold"]: r for r in b.get(line, [])}
        for k in sorted(set(fa) | set(fb)):
            ra, rb = fa.get(k), fb.get(k)
            folds += 1
            if ra is None or rb is None:
                identical = False
                continue
            n_a += len(ra["pos"])
            n_b += len(rb["pos"])
            same = (ra["n"] == rb["n"] and ra["pos"] == rb["pos"]) or (
                ra["hash"] is not None and rb["hash"] is not None and Counter(ra["hash"]) == Counter(rb["hash"]))
            identical &= same
            if ra["hash"] is not None and rb["hash"] is not None:
                sa, sb = set(ra["hash"]), set(rb["hash"])
                jac.append(len(sa & sb) / max(len(sa | sb), 1))
            elif ra["n"] == rb["n"]:
                pa, pb = set(ra["pos"]), set(rb["pos"])
                jac.append(len(pa & pb) / max(len(pa | pb), 1))
    return {"identical": identical, "folds": folds, "split_lines": len(lines),
            "jaccard": round(sum(jac) / len(jac), 4) if jac else None, "n_eval_leaky": n_a, "n_eval_fixed": n_b}


def reported_values(log: dict) -> list[tuple[tuple, str, float]]:
    """Every score the run produced, in order: metric functions, `.score`, cross-validation helpers, and numeric
    values a notebook cell displays. Key = (kind, line, name, occurrence at that line and name)."""
    out, seen = [], {}
    for e in log.get("events", []):
        if e.get("kind") not in ("metric", "eval", "cv", "shown") or e.get("value") is None:
            continue
        name = e.get("name") or e.get("method") or e["kind"]
        k = (e["kind"], e["line"], name)
        seen[k] = seen.get(k, 0) + 1
        out.append(((*k, seen[k]), name, float(e["value"])))
    return out


def measure_impact(f: Finding, script: Path, cwd: Path, hints: dict, base: dict, timeout: float) -> None:
    """Re-run with the finding's canonical fix and record the change in the script's own printed metric."""
    fix, why = fix_for_finding(f, base)
    base_metric = parse_metric(base.get("stdout", ""))
    if fix is None:
        f.impact = {"status": "unknown", "note": why}
        return
    if base_metric is None and not reported_values(base):
        f.impact = {"status": "unknown", "note": "the script reports no score (no `name: value` line, metric call or "
                    "displayed value)"}
        return
    fixed = run_instrumented(script, cwd, hints, fix, timeout)
    if base_metric is None:
        measure_from_reported(f, base, fixed)
        return
    metric = parse_metric(fixed.get("stdout", ""))
    if fixed.get("status") != "ok" or metric is None or not fixed.get("fix_applied"):
        reason = fixed.get("error") or (
            "the fix did not apply at run time" if not fixed.get("fix_applied") else "the fixed run printed no metric"
        )
        f.impact = {
            "status": "unknown",
            "metric": base_metric[0],
            "value_leaky": base_metric[1],
            "note": f"fixed run failed: {reason}"[:300],
        }
        return
    same_metric = metric[0] == base_metric[0]
    sites = [sorted({e["line"] for e in log["events"] if e["kind"] == "split"}) for log in (base, fixed)]
    reliable = same_metric and sites[0] == sites[1]
    delta = base_metric[1] - metric[1]
    f.impact = {
        "status": "measured" if reliable else "unreliable",
        "metric": base_metric[0],
        "value_leaky": base_metric[1],
        "value_fixed": metric[1],
        "delta": round(delta, 6),
        "n_runs": 1,
        "note": "; ".join(dict.fromkeys(fixed["fix_applied"]))[:300]
        + ("" if reliable else " | the fixed run took a different path through the code"),
    }
    change = eval_set_change(base, fixed)
    if change is not None:
        f.impact["eval_set"] = change
    if reliable and f.type != "target_derived":
        f.severity = severity_from_delta(base_metric[0], base_metric[1], metric[1])


def measure_from_reported(f: Finding, base: dict, fixed: dict) -> None:
    """Impact from the scores the run itself produced (no printed `name: value` line): the last score of the
    original run that the fixed run also produced at the same call site is the headline; every shared score is
    kept. Both runs may stop with the same error after their scores (common in real notebooks)."""
    if not fixed.get("fix_applied"):
        f.impact = {"status": "unknown", "note": "the fix did not apply at run time"}
        return
    a = reported_values(base)
    b = {k: v for k, _, v in reported_values(fixed)}
    shared = [(k, name, v, b[k]) for k, name, v in a if k in b]
    if not shared:
        f.impact = {"status": "unknown", "note": "the fixed run produced none of the original run's scores: "
                    + (fixed.get("error") or "no score reached")[:200]}
        return
    k, name, leaky, fixed_v = shared[-1]
    same_end = base.get("status") == fixed.get("status") and (base.get("error") or "").split(":")[0] == (
        fixed.get("error") or "").split(":")[0]
    sites = [sorted({e["line"] for e in log["events"] if e["kind"] == "split"}) for log in (base, fixed)]
    reliable = same_end and sites[0] == sites[1]
    label = f"{name} (line {k[1]})"
    f.impact = {
        "status": "measured" if reliable else "unreliable",
        "metric": label,
        "metric_source": "recorded at run time",
        "value_leaky": leaky,
        "value_fixed": fixed_v,
        "delta": round(leaky - fixed_v, 6),
        "n_runs": 1,
        "all_scores": [{"score": f"{n} (line {kk[1]})", "leaky": x, "fixed": y} for kk, n, x, y in shared][-20:],
        "note": "; ".join(dict.fromkeys(fixed["fix_applied"]))[:300]
        + ("" if reliable else " | the fixed run took a different path or ended differently"),
    }
    change = eval_set_change(base, fixed)
    if change is not None:
        f.impact["eval_set"] = change
    if reliable and f.type != "target_derived":
        f.severity = severity_from_delta(label, leaky, fixed_v)


def confirm_file(
    path: Path,
    src: Source,
    findings: list[Finding],
    with_impact: bool = False,
    timeout: float = 600,
    cwd: Path | None = None,
    hints: dict | None = None,
) -> list[Finding]:
    """Dynamic pass for one file of trusted code: run it instrumented from its own directory."""
    from leaklens.static.analyzer import analyze_with_hints

    if hints is None:
        findings, hints = analyze_with_hints(src)
    cwd = cwd or path.resolve().parent
    with tempfile.TemporaryDirectory(prefix="leaklens-flat-") as tmp:
        script = Path(tmp) / (path.stem + "__leaklens_flat.py")
        script.write_text(src.flat + "\n")
        base = run_instrumented(script, cwd, hints, None, timeout)
        out = apply_events(findings, base, src)
        if with_impact:
            # a run that stopped with an error after producing scores (common in real notebooks: a missing
            # submission file, a removed library argument) can still be compared on those scores
            usable = base.get("status") == "ok" or bool(reported_values(base))
            for f in out:
                if f.dynamic.get("status") != "refuted" and usable:
                    measure_impact(f, script, cwd, hints, base, timeout)
                elif not usable:
                    f.impact = {"status": "unknown", "note": f"the original run failed: {base.get('error')}"[:300]}
    return out
