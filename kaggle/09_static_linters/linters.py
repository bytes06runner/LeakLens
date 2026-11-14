"""Baselines found at the 2026-11-14 novelty check: leakray and unleak, run as released (CLAUDE.md Rule 5).

Both are static linters: they read files and never execute them. They are third-party code, so they run here
on Kaggle (internet on, for pip only) and not on the laptop. Inputs are our own files: the injected TEST split,
the four case-study notebooks and two CalibraEEG files. Raw outputs are kept; scoring is done afterwards with
the per-file rule used for Yang et al. (EVAL_CHANGES.md #6).
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

T0 = time.time()
OUT = "/kaggle/working"
code_dir = os.path.dirname(glob.glob("/kaggle/input/**/CODE_VERSION.json", recursive=True)[0])
info = {"code_version": json.load(open(os.path.join(code_dir, "CODE_VERSION.json"))), "python": sys.version.split()[0]}
with zipfile.ZipFile(os.path.join(code_dir, "benchmark_injected.zip")) as z:
    z.extractall("/tmp/bench")
inputs = sorted(glob.glob("/tmp/bench/benchmark/injected/items/*/pipeline.*"))
case_dir = os.path.dirname(glob.glob("/kaggle/input/**/C2a.ipynb", recursive=True)[0])
inputs += sorted(glob.glob(os.path.join(case_dir, "*.ipynb"))) + sorted(glob.glob(os.path.join(case_dir, "*.py")))
info["n_inputs"] = len(inputs)

INSTALL = {"unleak": ["unleak"], "leakray": ["git+https://github.com/tpong-dev/leakray"]}
TRIES = {
    "leakray": [["leakray", "{f}", "--format", "json"], ["leakray", "check", "{f}", "--format", "json"],
                ["leakray", "scan", "{f}", "--format", "json"], ["leakray", "{f}", "--json"], ["leakray", "{f}"]],
    "unleak": [["unleak", "{f}", "--format", "json"], ["unleak", "check", "{f}", "--format", "json"],
               ["unleak", "scan", "{f}", "--format", "json"], ["unleak", "{f}", "--json"], ["unleak", "{f}"]],
}


def sh(argv, timeout=300):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


for tool, pkgs in INSTALL.items():
    rc, out, err = sh([sys.executable, "-m", "pip", "install", "-q", *pkgs], 900)
    info[f"{tool}_install"] = {"rc": rc, "err": err[-800:]}
    rc, out, err = sh([sys.executable, "-m", "pip", "show", tool if tool != "leakray" else "leakray"])
    info[f"{tool}_pip_show"] = out[-600:]
    exe = shutil.which(tool)
    info[f"{tool}_exe"] = exe
    if exe is None:
        continue
    for h in (["--help"], ["--version"]):
        rc, out, err = sh([tool, *h])
        open(f"{OUT}/{tool}_{h[0].strip('-')}.txt", "w").write(out + "\n--- stderr ---\n" + err)
    # pick the first invocation that works on a known leaky file
    probe = next(f for f in inputs if "pre_scaler" in f)
    chosen = None
    for t in TRIES[tool]:
        argv = [a.replace("{f}", probe) for a in t]
        rc, out, err = sh(argv)
        if rc in (0, 1, 2) and out.strip() and "usage:" not in (out + err)[:200].lower():
            chosen = t
            break
    info[f"{tool}_invocation"] = chosen
    if chosen is None:
        continue
    os.makedirs(f"{OUT}/{tool}", exist_ok=True)
    res = {}
    for f in inputs:
        argv = [a.replace("{f}", f) for a in chosen]
        t = time.time()
        try:
            rc, out, err = sh(argv)
        except subprocess.TimeoutExpired:
            rc, out, err = None, "", "timeout"
        rel = f.split("/items/")[-1] if "/items/" in f else os.path.basename(f)
        res[rel] = {"rc": rc, "stdout": out, "stderr": err[-2000:], "seconds": round(time.time() - t, 3)}
    json.dump(res, open(f"{OUT}/{tool}/raw.json", "w"))
    info[f"{tool}_files"] = len(res)

info["seconds"] = round(time.time() - T0, 1)
json.dump(info, open(f"{OUT}/run_info.json", "w"), indent=2)
print(json.dumps(info, indent=2)[:4000])
