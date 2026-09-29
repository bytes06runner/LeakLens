"""Run one data-level tool on the probe splits, with and without column hints. Invoked with the tool's own venv.

Usage: python run_tool.py <tool> <splits_dir>  -> prints one JSON object.
Only published entry points are used (Rule 5). Any exception is recorded, not hidden.
"""

import io
import json
import sys
import traceback
from contextlib import redirect_stdout

import pandas as pd

tool, d = sys.argv[1], sys.argv[2]
cases = {
    "group": ("group_train.csv", "group_test.csv", {"group_col": "patient_id"}),
    "temporal": ("temporal_train.csv", "temporal_test.csv", {"time_col": "date"}),
}
res = {"tool": tool, "cases": {}}


def run(train, test, hints):
    buf = io.StringIO()
    with redirect_stdout(buf):
        if tool == "leakcheck-ml":
            import subprocess
            cmd = ["leakcheck", f"{d}/{train}", f"{d}/{test}", "-t", "label", "--json"]
            if "group_col" in hints:
                cmd += ["-g", hints["group_col"]]
            if "time_col" in hints:
                cmd += ["--time-col", hints["time_col"]]
            p = subprocess.run(cmd, capture_output=True, text=True)
            return {"rc": p.returncode, "out": p.stdout[-4000:], "err": p.stderr[-1500:]}
        tr, te = pd.read_csv(f"{d}/{train}"), pd.read_csv(f"{d}/{test}")
        if tool == "leakhound-ml":
            from leakhound import audit
            r = audit(tr, te, target="label", measure_impact=True, **hints)
            return {"clean": r.clean, "render": r.render()[-4000:]}
        if tool == "dataleaks":
            from dataleaks import DataLeaks
            # Published train/test API. Its only split-level hint is identifier_columns; its temporal detectors
            # check feature timestamps against a prediction time, not split order, so no time hint applies.
            meta = {"identifier_columns": [hints["group_col"]]} if "group_col" in hints else {}
            r = DataLeaks(pd.concat([tr, te]), target="label", train=tr, test=te, metadata=meta).run()
            return {"risk": str(r.risk_level), "findings": [f"{f.detector}: {f.severity}" for f in r.findings]}
        if tool == "deepchecks":
            from deepchecks.tabular import Dataset
            from deepchecks.tabular.checks import DateTrainTestLeakageOverlap, TrainTestSamplesMix
            kw = {"label": "label", "cat_features": []}
            if "time_col" in hints:
                tr[hints["time_col"]] = pd.to_datetime(tr[hints["time_col"]])
                te[hints["time_col"]] = pd.to_datetime(te[hints["time_col"]])
                kw["datetime_name"] = hints["time_col"]
            dtr, dte = Dataset(tr, **kw), Dataset(te, **kw)
            out = {"samples_mix": str(TrainTestSamplesMix().run(dtr, dte).value)[:500]}
            if "time_col" in hints:
                out["date_overlap"] = str(DateTrainTestLeakageOverlap().run(dtr, dte).value)[:500]
            return out
    raise SystemExit(f"unknown tool {tool}")


for case, (train, test, hints) in cases.items():
    for mode, h in (("no_hints", {}), ("with_hints", hints)):
        try:
            res["cases"][f"{case}/{mode}"] = {"ok": True, "result": run(train, test, h)}
        except Exception as e:  # noqa: BLE001
            res["cases"][f"{case}/{mode}"] = {"ok": False, "error": f"{type(e).__name__}: {e}",
                                              "trace": traceback.format_exc()[-1500:]}
print(json.dumps(res, default=str))
