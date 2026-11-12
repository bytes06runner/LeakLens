"""Report envelope and output formats: JSON, SARIF 2.1.0 and terminal text (docs/SPEC.md sections 3 and 8)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from leaklens import __version__
from leaklens.ingest import Source
from leaklens.report.findings import CONFIDENCE_ORDER, SEVERITY_ORDER, Finding

SCHEMA = "leaklens/report/v1"
_SARIF_LEVEL = {"high": "error", "medium": "warning", "low": "note", "info": "note"}
_RULE_TEXT = {
    "LL-PRE-001": "Transformer fitted on rows that include evaluation rows",
    "LL-PRE-002": "Statistic over rows applied before the split",
    "LL-PRE-003": "Target-dependent selection or encoding fitted before the split",
    "LL-OVL-001": "Evaluation rows flow into the model fit",
    "LL-OVL-002": "Resampling or augmentation before the split",
    "LL-OVL-003": "Training and evaluation rows concatenated into the fit",
    "LL-OVL-004": "Duplicate rows across the split (found at run time)",
    "LL-MUL-001": "Evaluation rows used to select among candidates",
    "LL-MUL-002": "Evaluation rows used for early stopping",
    "LL-GRP-001": "Row-level split on data with an entity column",
    "LL-GRP-002": "CV helper with default or integer cv on data with an entity column",
    "LL-GRP-003": "Row-level split on data whose entity comes from file paths",
    "LL-GRP-004": "Same entity on both sides of the split (found at run time)",
    "LL-TMP-001": "Non-chronological split of time-ordered rows",
    "LL-TMP-002": "Feature computed from later values",
    "LL-TMP-003": "Training rows dated after evaluation rows (found at run time)",
    "LL-TGT-001": "Feature computed from the target",
    "LL-TGT-002": "Single feature predicts the target almost perfectly (found at run time)",
}


def config_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()[:16]


def envelope(
    root: str, mode: str, sources: list[Source], findings: list[Finding], config: dict, commit: str | None = None
) -> dict:
    return {
        "schema": SCHEMA,
        "tool": {"name": "leaklens", "version": __version__, "commit": commit},
        "scan": {
            "root": root,
            "mode": mode,
            "started_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "config_hash": config_hash(config),
        },
        "files": [{"path": s.path, "status": s.status, "reason": s.reason, "ingest": s.ingest_info()} for s in sources],
        "findings": [f.to_dict() for f in findings],
    }


def to_sarif(report: dict) -> dict:
    """SARIF 2.1.0 for GitHub code scanning. Notebook findings point at the .ipynb file; the cell index and the
    line inside the cell are in `properties` because GitHub cannot highlight a notebook cell."""
    used = sorted({f["rule_id"] for f in report["findings"]})
    rules = [
        {
            "id": r,
            "name": r.replace("-", ""),
            "shortDescription": {"text": _RULE_TEXT.get(r, r)},
            "helpUri": "https://github.com/bytes06runner/LeakLens/blob/main/docs/TAXONOMY.md",
        }
        for r in used
    ]
    results = []
    for f in report["findings"]:
        loc = f["location"]
        is_nb = loc["cell"] is not None
        region = (
            {"startLine": loc["flat_line_start"], "endLine": loc["flat_line_end"]}
            if is_nb
            else {"startLine": loc["line_start"], "endLine": loc["line_end"]}
        )
        res = {
            "ruleId": f["rule_id"],
            "ruleIndex": used.index(f["rule_id"]),
            "level": _SARIF_LEVEL[f["severity"]],
            "message": {"text": f["message"] + " Suggested fix: " + f["suggested_fix"]["description"]},
            "locations": [
                {"physicalLocation": {"artifactLocation": {"uri": Path(loc["file"]).as_posix()}, "region": region}}
            ],
            "partialFingerprints": {"leaklens/v1": f["id"]},
            "properties": {
                "type": f["type"],
                "subtype": f["subtype"],
                "confidence": f["confidence"],
                "severity": f["severity"],
                "cell": loc["cell"],
                "line_in_cell": loc["line_start"],
                "dynamic": f["dynamic"],
                "impact": f["impact"],
                "evidence": [e["detail"] for e in f["evidence"]],
            },
        }
        if f["suppressed"] is not None:
            res["suppressions"] = [
                {
                    "kind": "inSource" if f["suppressed"]["by"] == "inline" else "external",
                    "justification": f["suppressed"].get("reason") or "",
                }
            ]
        results.append(res)
    notes = [
        {"level": "warning", "message": {"text": f"{x['path']}: {x['reason']}"}, "descriptor": {"id": "unanalysable"}}
        for x in report["files"]
        if x["status"] != "ok"
    ]
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "LeakLens",
                        "version": report["tool"]["version"],
                        "informationUri": "https://github.com/bytes06runner/LeakLens",
                        "rules": rules,
                    }
                },
                "results": results,
                "invocations": [{"executionSuccessful": True, "toolExecutionNotifications": notes}],
            }
        ],
    }


def terminal_lines(report: dict, min_confidence: str = "medium", verbose: bool = False) -> list[str]:
    out: list[str] = []
    by_file: dict[str, list[dict]] = {}
    hidden = 0
    for f in report["findings"]:
        if CONFIDENCE_ORDER[f["confidence"]] < CONFIDENCE_ORDER[min_confidence]:
            hidden += 1
            continue
        by_file.setdefault(f["location"]["file"], []).append(f)
    for path, fs in by_file.items():
        out.append(f"[bold]{path}[/bold]")
        for f in sorted(fs, key=lambda f: (-SEVERITY_ORDER[f["severity"]], f["location"]["flat_line_start"])):
            loc = f["location"]
            where = (
                f"cell {loc['cell']} line {loc['line_start']}"
                if loc["cell"] is not None
                else f"line {loc['line_start']}"
            )
            tag = " [dim](suppressed)[/dim]" if f["suppressed"] else ""
            dyn = f["dynamic"]["status"]
            extra = f" · run: {dyn}" if dyn != "not_run" else ""
            imp = f["impact"]
            if imp.get("status") == "measured":
                extra += f" · {imp['metric']} {imp['value_leaky']:.4f} -> {imp['value_fixed']:.4f} with the fix"
            out.append(f"  {where:<18} [{f['severity']}/{f['confidence']}] {f['type']} ({f['rule_id']}){tag}{extra}")
            out.append(f"      {f['message']}")
            out.append(f"      fix: {f['suggested_fix']['description']}")
            if verbose:
                out += [f"      evidence: {e['detail']}" for e in f["evidence"]]
    for x in report["files"]:
        if x["status"] != "ok":
            out.append(f"[yellow]{x['path']}: not analysed ({x['reason']})[/yellow]")
        elif x["ingest"]["skipped_cells"]:
            out.append(f"[yellow]{x['path']}: {len(x['ingest']['skipped_cells'])} cell(s) skipped[/yellow]")
    shown = sum(len(v) for v in by_file.values())
    ok = sum(1 for x in report["files"] if x["status"] == "ok")
    out.append(
        f"{shown} finding(s) in {ok} analysed file(s)"
        + (f"; {hidden} below --min-confidence {min_confidence} not shown" if hidden else "")
        + (f"; {len(report['files']) - ok} file(s) could not be analysed" if ok < len(report["files"]) else "")
    )
    return out
