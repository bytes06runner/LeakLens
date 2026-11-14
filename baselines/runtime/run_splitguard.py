"""splitguard 0.1.0 on the injected benchmark (EVAL_PROTOCOL.md section 7): as released, and with the true group
declared through its documented `mark_groups` call.

    python baselines/runtime/run_splitguard.py OUT_DIR --split TEST --python SPLITGUARD_VENV_PYTHON [--workers 6]

Writes OUT_DIR/splitguard__default/findings.jsonl and OUT_DIR/splitguard__true_column/findings.jsonl in the
format benchmark/injected/score.py reads. Pattern mapping: fit_before_split -> preprocessing, fit_after_split ->
overlap, group_leakage -> group; the finding's line is splitguard's reported call site.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmark" / "injected"
sys.path.insert(0, str(BENCH))
WRAPPER = Path(__file__).resolve().parent / "splitguard_wrapper.py"
PATTERN = {"fit_before_split": "preprocessing", "fit_after_split": "overlap", "group_leakage": "group"}
X_LINE = re.compile(r"^(\w+) = (\w+)\[(\w+)\]\s*$")  # e.g. `X = df[FEATURES]` in any naming style


def run_item(job) -> dict:
    row, entity, python = job
    from measure_inflation import prepare_data

    from leaklens.ingest import load

    src = load(BENCH / row["file"], display=row["file"])
    out = {"item_id": row["item_id"], "split": row["split"], "base": row["base"], "modes": {}}
    modes = {"default": None} | ({"true_column": entity} if entity else {})
    for mode, ent in modes.items():
        lines = src.flat.splitlines()
        inserted_at = None
        if ent:
            for i, line in enumerate(lines):
                m = X_LINE.match(line)
                if m:
                    lines.insert(i + 1, f'import splitguard; splitguard.mark_groups({m[1]}, {m[2]}["{ent}"])')
                    inserted_at = i + 2
                    break
        with tempfile.TemporaryDirectory(prefix="leaklens-sg-") as tmp:
            work = Path(tmp)
            prepare_data(row["base"], 0, json.loads(row["data_transform"]), True, work)
            script = work / "pipeline__flat.py"
            script.write_text("\n".join(lines) + "\n")
            p = subprocess.run([python, "-W", "ignore", str(WRAPPER), str(script)], cwd=work, capture_output=True,
                               text=True, timeout=900)
        js = next((ln[len("SPLITGUARD_JSON "):] for ln in p.stdout.splitlines() if ln.startswith("SPLITGUARD_JSON ")),
                  None)
        res = json.loads(js) if js else {"status": "error", "error": p.stderr[-300:], "findings": []}
        finds = []
        for f in res["findings"]:
            m = re.search(r":(\d+)", f["call_site"] or "")
            if not m or f["pattern"] not in PATTERN:
                continue
            ln = int(m[1])
            if inserted_at and ln >= inserted_at:
                ln -= 1  # undo the inserted declaration line
            cell, line = src.locate(ln)
            finds.append({"id": f"{row['item_id']}:{PATTERN[f['pattern']]}:{ln}", "type": PATTERN[f["pattern"]], "confidence": "medium", "suppressed": None,
                          "dynamic": {"status": "not_run"}, "raw": f,
                          "location": {"cell": cell, "line_start": line, "line_end": line}})
        seen, uniq = set(), []
        for f in finds:  # one finding per (line, type), as SPEC.md section 3 defines a finding
            k = (f["location"]["cell"], f["location"]["line_start"], f["type"])
            if k not in seen:
                seen.add(k)
                uniq.append(f)
        finds = uniq
        out["modes"][mode] = {"status": res["status"], "error": res["error"], "findings": finds,
                              "declared": bool(inserted_at) if ent else None}
    return out


def main() -> None:
    import yaml

    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--split", choices=["DEV", "TEST"], required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--items", default="")
    a = ap.parse_args()
    meta = yaml.safe_load((BENCH / "bases.yaml").read_text())
    rows = [r for r in csv.DictReader((BENCH / "manifest.csv").open()) if r["split"] == a.split
            and a.items in r["item_id"]]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(a.workers) as pool:
        recs = list(pool.map(run_item, [(r, meta[r["base"]].get("entity"), a.python) for r in rows]))
    (out / "splitguard_raw.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    for mode in ("default", "true_column"):
        d = out / f"splitguard__{mode}"
        d.mkdir(parents=True, exist_ok=True)
        with (d / "findings.jsonl").open("w") as f:
            for r in recs:
                m = r["modes"].get(mode) or r["modes"]["default"]
                f.write(json.dumps({"item_id": r["item_id"], "split": r["split"], "base": r["base"], "seed": 0, "static_seconds": 0.0, "dynamic_seconds": 0.0,
                                    "run_status": "ok", "status": "ok", "static": m["findings"], "dynamic": m["findings"]}) + "\n")
    errs = sum(1 for r in recs for m in r["modes"].values() if m["status"] != "ok")
    print(f"{len(recs)} items, {errs} runs with an error")


if __name__ == "__main__":
    main()
