"""Run one data-level tool on one exported train/evaluation pair. Invoked with the tool's own interpreter.

    python run_split.py TOOL TRAIN_CSV TEST_CSV '{"group_col": ..., "time_col": ...}'

Prints one JSON object: {"flags": {"group": bool, "temporal": bool, "overlap": bool}, "columns": {...},
"impact": [...], "error": str|None}. Only each tool's published entry points and defaults are used (Rule 5);
hints are passed only through the tool's own documented parameters. The target column is `__target__`.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout

import pandas as pd

tool, train_csv, test_csv, hints = sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
T = "__target__"
out = {"flags": {"group": False, "temporal": False, "overlap": False}, "columns": {}, "impact": [], "error": None}


def main():
    if tool == "leakcheck-ml":
        cmd = ["leakcheck", train_csv, test_csv, "-t", T, "--json"]
        if hints.get("group_col"):
            cmd += ["-g", hints["group_col"]]
        if hints.get("time_col"):
            cmd += ["--time-col", hints["time_col"]]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        checks = json.loads(p.stdout)
        for c in checks:
            hit = c.get("status") in ("fail", "warn")
            if c["check"] == "group-leakage" and hit:
                out["flags"]["group"] = True
                out["columns"]["group"] = c.get("details", {}).get("column")
            elif c["check"] == "temporal" and hit:
                out["flags"]["temporal"] = True
                out["columns"]["temporal"] = c.get("details", {}).get("column")
            elif c["check"] in ("duplicates", "near-duplicates") and hit:
                out["flags"]["overlap"] = True
        return
    tr, te = pd.read_csv(train_csv), pd.read_csv(test_csv)
    if tool == "leakhound-ml":
        from leakhound import audit

        kw = {k: v for k, v in hints.items() if k in ("group_col", "time_col") and v}
        rep = audit(tr, te, target=T, measure_impact=True, **kw)
        for f in rep.findings:
            if not f.is_leak:
                continue
            if f.check == "group_split":
                out["flags"]["group"] = True
                out["columns"]["group"] = f.evidence.get("group_col")
            elif f.check == "temporal":
                out["flags"]["temporal"] = True
            elif f.check == "duplicates":
                out["flags"]["overlap"] = True
            elif f.check == "impact":
                out["impact"].append({k: v for k, v in f.evidence.items()})
        return
    if tool == "dataleaks":
        from dataleaks import DataLeaks

        meta = {"identifier_columns": [hints["group_col"]]} if hints.get("group_col") else {}
        rep = DataLeaks(pd.concat([tr, te]), target=T, train=tr, test=te, metadata=meta).run()
        for f in rep.findings:
            if f.detector == "split_overlap":
                out["flags"]["group"] = True
                out["columns"]["group"] = getattr(f, "affected_columns", None)
            elif f.detector in ("split_duplicates", "split_near_duplicates"):
                out["flags"]["overlap"] = True
            elif f.detector.startswith("temporal_"):
                out["flags"]["temporal"] = True
        return
    if tool == "deepchecks":
        from deepchecks.tabular import Dataset
        from deepchecks.tabular.checks import DateTrainTestLeakageOverlap, TrainTestSamplesMix

        kw = {"label": T, "cat_features": []}
        tc = hints.get("time_col")
        if tc and tc in tr.columns:
            tr[tc], te[tc] = pd.to_datetime(tr[tc], errors="coerce"), pd.to_datetime(te[tc], errors="coerce")
            kw["datetime_name"] = tc
        dtr, dte = Dataset(tr, **kw), Dataset(te, **kw)
        mix = TrainTestSamplesMix().run(dtr, dte).value
        out["flags"]["overlap"] = bool((mix.get("ratio") if isinstance(mix, dict) else mix) or 0)
        if "datetime_name" in kw:
            out["flags"]["temporal"] = float(DateTrainTestLeakageOverlap().run(dtr, dte).value or 0) > 0
        return
    raise SystemExit(f"unknown tool {tool}")


buf_o, buf_e = io.StringIO(), io.StringIO()
try:
    with redirect_stdout(buf_o), redirect_stderr(buf_e):
        main()
except Exception as e:  # noqa: BLE001 - recorded as a coverage result, never hidden
    out["error"] = f"{type(e).__name__}: {e}"
    out["trace"] = traceback.format_exc()[-800:]
print(json.dumps(out, default=str))
