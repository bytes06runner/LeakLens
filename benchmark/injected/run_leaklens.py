"""Run LeakLens on the injected benchmark and write its findings, one JSON line per item and mode.

    python benchmark/injected/run_leaklens.py OUT_DIR --split DEV [--modes static dynamic] [--impact]
                                              [--seeds 0] [--workers 4] [--items PATTERN]

Static mode reads the files and executes nothing. Dynamic and impact modes execute our own generated pipelines
(trusted code) on synthetic data produced by `datagen`, each in a throwaway directory.

`--split TEST` is refused unless EVAL_PROTOCOL.md is frozen (its status line says FROZEN): TEST is scored once per
release, after the project owner has approved the protocol (CLAUDE.md Rule 4).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))


def protocol_frozen() -> bool:
    head = (ROOT / "EVAL_PROTOCOL.md").read_text().splitlines()[:6]
    return any(line.startswith("**Status: FROZEN") for line in head)


def run_item(job: tuple[dict, list[str], bool, int, float]) -> dict:
    row, modes, impact, seed, timeout = job
    from measure_inflation import prepare_data

    from leaklens.dynamic.confirm import apply_events, measure_impact, parse_metric, run_instrumented
    from leaklens.ingest import load
    from leaklens.static.analyzer import analyze_with_hints

    out: dict = {"item_id": row["item_id"], "split": row["split"], "base": row["base"], "seed": seed}
    t = time.perf_counter()
    src = load(HERE / row["file"], display=row["file"])
    out["status"], out["reason"] = src.status, src.reason
    findings, hints = analyze_with_hints(src) if src.status == "ok" else ([], {})
    out["static_seconds"] = round(time.perf_counter() - t, 4)
    out["static"] = [f.to_dict() for f in findings]
    if "dynamic" not in modes or src.status != "ok":
        return out
    t = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="leaklens-bench-") as tmp:
        work = Path(tmp)
        prepare_data(row["base"], seed, json.loads(row["data_transform"]), True, work)
        script = work / "pipeline__leaklens_flat.py"
        script.write_text(src.flat + "\n")
        base = run_instrumented(script, work, hints, None, timeout)
        merged = apply_events(findings, base, src)
        out["run_status"], out["run_error"] = base.get("status"), base.get("error")
        metric = parse_metric(base.get("stdout", ""))
        out["metric"] = {"name": metric[0], "value": metric[1]} if metric else None
        out["dynamic_seconds"] = round(time.perf_counter() - t, 3)
        if impact and base.get("status") == "ok":
            t = time.perf_counter()
            for f in merged:
                if f.dynamic.get("status") != "refuted":
                    measure_impact(f, script, work, hints, base, timeout)
            out["impact_seconds"] = round(time.perf_counter() - t, 3)
        out["dynamic"] = [f.to_dict() for f in merged]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--split", choices=["DEV", "TEST"], required=True)
    ap.add_argument("--modes", nargs="+", default=["static"], choices=["static", "dynamic"])
    ap.add_argument("--impact", action="store_true")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--items", default="")
    ap.add_argument("--timeout", type=float, default=600)
    a = ap.parse_args()
    if a.split == "TEST" and not protocol_frozen():
        sys.exit("Refused: EVAL_PROTOCOL.md is not frozen. TEST is scored once, after the owner approves the protocol.")
    rows = [
        r for r in csv.DictReader((HERE / "manifest.csv").open()) if r["split"] == a.split and a.items in r["item_id"]
    ]
    jobs = [(r, a.modes, a.impact, s, a.timeout) for r in rows for s in a.seeds]
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as pool, (out_dir / "findings.jsonl").open("w") as f:
        for i, res in enumerate(pool.map(run_item, jobs), start=1):
            f.write(json.dumps(res) + "\n")
            f.flush()
            if i % 25 == 0:
                print(f"{i}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    print(f"done: {len(jobs)} runs in {time.time() - t0:.0f}s -> {out_dir / 'findings.jsonl'}")


if __name__ == "__main__":
    main()
