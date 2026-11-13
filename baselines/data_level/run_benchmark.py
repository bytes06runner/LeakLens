"""Run the data-level baselines on the splits each injected pipeline actually makes (EVAL_PROTOCOL.md section 7).

    python baselines/data_level/run_benchmark.py OUT_DIR --split TEST --venvs VENV_DIR [--workers 4]

For every item: run the pipeline once (our own generated code; seed 0) with `--dump-splits`, so each split call
writes the train and evaluation tables of up to five folds (every row-aligned column plus the target). Each tool
then gets every exported pair twice: with no column named (its default), and with the true column named (entity
column for grouped pipelines, time column for time series). A tool's detection of a type at a split counts as a
finding of that type at the split call's line (protocol section 7), in a findings.jsonl per tool and mode that
`benchmark/injected/score.py` scores with the frozen matching rule. LeakHound's impact estimates are kept.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmark" / "injected"
sys.path.insert(0, str(BENCH))
TOOLS = {"leakcheck-ml": "v-leakcheck-ml", "leakhound-ml": "v-leakhound-ml", "dataleaks": "v-dataleaks",
         "deepchecks": "v-deepchecks"}
ADAPTER = Path(__file__).resolve().parent / "run_split.py"


def true_hints(meta: dict, transform: dict) -> dict:
    if meta.get("entity"):
        return {"group_col": meta["entity"]}
    if meta.get("time_col"):
        return {"time_col": (transform.get("rename") or {}).get(meta["time_col"], meta["time_col"])}
    return {}


def run_item(job) -> dict:
    row, meta, venvs = job
    from measure_inflation import prepare_data

    from leaklens.ingest import load

    src = load(BENCH / row["file"], display=row["file"])
    transform = json.loads(row["data_transform"])
    rec = {"item_id": row["item_id"], "split": row["split"], "base": row["base"], "sites": [], "error": None}
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="leaklens-dl-") as tmp:
        work = Path(tmp)
        prepare_data(row["base"], 0, transform, True, work)
        script = work / "pipeline__flat.py"
        script.write_text(src.flat + "\n")
        dump, ev = work / "_splits", work / "_events.json"
        p = subprocess.run([sys.executable, "-W", "ignore", "-m", "leaklens.dynamic.runner", str(script),
                            "--out", str(ev), "--dump-splits", str(dump)], cwd=work, capture_output=True,
                           text=True, timeout=900)
        if not ev.exists():
            rec["error"] = "pipeline run failed: " + p.stderr[-300:]
            return rec
        index = json.loads(ev.read_text()).get("dump_index", [])
        hints = true_hints(meta, transform)
        modes = {"default": {}} | ({"true_column": hints} if hints else {})
        sites: dict = {}
        for e in index:
            if "error" in e or not e.get("has_target"):
                sites.setdefault(e["line"], {"line": e["line"], "call": e.get("call"), "folds": 0, "skipped": []})[
                    "skipped"].append(e.get("error") or "no target aligned")
                continue
            s = sites.setdefault(e["line"], {"line": e["line"], "call": e["call"], "folds": 0, "skipped": [],
                                             "tools": {}})
            s["folds"] += 1
            for tool, venv in TOOLS.items():
                py = str(Path(venvs) / venv / "bin" / "python")
                env_bin = str(Path(venvs) / venv / "bin")
                for mode, h in modes.items():
                    q = subprocess.run([py, str(ADAPTER), tool, str(dump / f"{e['base']}_train.csv"),
                                        str(dump / f"{e['base']}_test.csv"), json.dumps(h)],
                                       capture_output=True, text=True, timeout=900,
                                       env={"PATH": env_bin + ":/usr/bin:/bin", "HOME": tmp,
                                            "PYTHONWARNINGS": "ignore"})
                    try:
                        res = json.loads(q.stdout.strip().splitlines()[-1])
                    except Exception:  # noqa: BLE001
                        res = {"flags": {}, "error": (q.stderr or q.stdout)[-300:]}
                    agg = s["tools"].setdefault(tool, {}).setdefault(
                        mode, {"flags": {"group": False, "temporal": False, "overlap": False}, "columns": {},
                               "impact": [], "errors": []})
                    for k, v in (res.get("flags") or {}).items():
                        agg["flags"][k] = agg["flags"][k] or bool(v)
                    for k, v in (res.get("columns") or {}).items():
                        agg["columns"].setdefault(k, v)
                    if e["fold"] == 0:
                        agg["impact"] += res.get("impact") or []
                    if res.get("error"):
                        agg["errors"].append(res["error"][:200])
        for s in sites.values():
            cell, line = src.locate(s["line"])
            s["cell"], s["item_line"] = cell, line
        rec["sites"] = list(sites.values())
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def main() -> None:
    import yaml

    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--split", choices=["DEV", "TEST"], required=True)
    ap.add_argument("--venvs", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--items", default="")
    a = ap.parse_args()
    meta = yaml.safe_load((BENCH / "bases.yaml").read_text())
    rows = [r for r in csv.DictReader((BENCH / "manifest.csv").open()) if r["split"] == a.split
            and a.items in r["item_id"]]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as pool, (out / "sites.jsonl").open("w") as f:
        for i, rec in enumerate(pool.map(run_item, [(r, meta[r["base"]], a.venvs) for r in rows]), start=1):
            f.write(json.dumps(rec, default=str) + "\n")
            f.flush()
            print(f"{i}/{len(rows)} {rec['item_id']} sites={len(rec['sites'])} {rec.get('seconds')}s "
                  f"{rec['error'] or ''}", flush=True)
    # one findings.jsonl per tool and mode, in the format score.py reads
    recs = [json.loads(x) for x in (out / "sites.jsonl").open()]
    for tool in TOOLS:
        for mode in ("default", "true_column"):
            d = out / f"{tool}__{mode}"
            d.mkdir(exist_ok=True)
            with (d / "findings.jsonl").open("w") as f:
                for r in recs:
                    finds = []
                    for s in r["sites"]:
                        res = s.get("tools", {}).get(tool, {}).get(mode) or s.get("tools", {}).get(tool, {}).get(
                            "default")
                        if not res:
                            continue
                        for t, hit in res["flags"].items():
                            if hit:
                                finds.append({"type": t, "confidence": "medium", "suppressed": None,
                                              "dynamic": {"status": "not_run"},
                                              "location": {"cell": s["cell"], "line_start": s["item_line"],
                                                           "line_end": s["item_line"]},
                                              "column": res["columns"].get(t)})
                    f.write(json.dumps({"item_id": r["item_id"], "split": r["split"], "base": r["base"],
                                        "seed": 0, "status": "ok", "static": finds, "dynamic": finds}) + "\n")
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
