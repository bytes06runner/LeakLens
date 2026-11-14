"""LeakLens case studies on four public Kaggle notebooks (supervisor's Review 3), internet OFF.

Each notebook is untrusted code. It runs only inside `leaklens.sandbox.run_untrusted` (CLAUDE.md Rule 7):
offline check, clean environment without Kaggle's tokens, unprivileged user, throwaway directory, timeout.
Inside the sandbox, `leaklens scan --dynamic --impact` runs the notebook instrumented and re-runs it once per
finding with the canonical fix.

Only data paths are adapted: a `/kaggle/input/...` path that does not exist in this session is replaced by the
attached file with the same trailing path (Kaggle mounts datasets under different prefixes over time). Every
substitution is logged. Nothing else in the code is changed.

Outputs (/kaggle/working): <case>.json (LeakLens report), <case>.log, adaptations.json, run_info.json.
"""

import glob
import json
import os
import re
import subprocess
import sys
import time

T0 = time.time()
code_dir = os.path.dirname(glob.glob("/kaggle/input/**/CODE_VERSION.json", recursive=True)[0])
info = {"code_version": json.load(open(os.path.join(code_dir, "CODE_VERSION.json"))), "cases": {}}
wheel = glob.glob(os.path.join(code_dir, "leaklens-*.whl"))[0]
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", "--ignore-requires-python", wheel], check=True)
info["python"] = sys.version.split()[0]  # the wheel declares 3.12; Kaggle moved to 3.13 (recorded, not hidden)

from leaklens.sandbox import run_untrusted  # noqa: E402

CASES = ["C2a", "C2b", "C3a", "C3b"]
NEEDS = {"C2a": "tlvmc-parkinsons-freezing-gait-prediction", "C2b": "amp-parkinsons-disease-progression-prediction",
         "C3a": "predict-energy-behavior-of-prosumers", "C3b": "Walmart.csv"}  # a case runs only if its data is attached
TIMEOUT = 2400  # seconds per instrumented run inside LeakLens
SANDBOX_TIMEOUT = 4 * 3600
ALL_INPUT = [p for p in glob.glob("/kaggle/input/**/*", recursive=True) if os.path.isfile(p)]


def resolve(path: str) -> str | None:
    """An attached file whose path ends with the longest possible suffix of `path`."""
    parts = path.rstrip("/").split("/")
    for k in range(len(parts) - 1, 0, -1):
        suffix = "/" + "/".join(parts[-k:])
        hits = [p for p in ALL_INPUT if p.endswith(suffix)]
        if hits:
            return min(hits, key=len)
        dir_hits = sorted({p[: p.index(suffix) + len(suffix)] for p in ALL_INPUT if suffix + "/" in p})
        if dir_hits:
            return dir_hits[0]
    return None


def adapt(nb_path: str, out_path: str) -> list[dict]:
    nb = json.load(open(nb_path))
    subs = []
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]

        def fix(m):
            p = m.group(2)
            if os.path.exists(p.rstrip("/")):
                return m.group(0)
            q = resolve(p)
            if q is None:
                return m.group(0)
            q = q + ("/" if p.endswith("/") and not q.endswith("/") else "")
            subs.append({"from": p, "to": q})
            return m.group(1) + q + m.group(3)

        new = re.sub(r"""(['"])((?:/kaggle/input|\.\./input)/[^'"]+)(['"])""", fix, src)
        cell["source"] = new
    json.dump(nb, open(out_path, "w"))
    return subs


nb_dir = os.path.dirname(glob.glob("/kaggle/input/**/C2a.ipynb", recursive=True)[0])
adaptations = {}
for case in CASES:
    t = time.time()
    if not any(NEEDS[case] in p for p in ALL_INPUT):
        info["cases"][case] = {"skipped": f"data not attached ({NEEDS[case]})"}
        print(case, info["cases"][case], flush=True)
        continue
    adapted = f"/kaggle/working/{case}.ipynb"
    adaptations[case] = adapt(os.path.join(nb_dir, f"{case}.ipynb"), adapted)
    argv = [sys.executable, "-m", "leaklens.cli", "scan", f"{case}.ipynb", "--dynamic", "--impact", "--trust-code",
            "--min-confidence", "low", "--format", "json", "--timeout", str(TIMEOUT)]
    try:
        r = run_untrusted(argv, inputs={f"{case}.ipynb": adapted}, timeout_seconds=SANDBOX_TIMEOUT)
        open(f"/kaggle/working/{case}.json", "w").write(r.stdout)
        open(f"/kaggle/working/{case}.log", "w").write(r.stderr[-200000:])
        info["cases"][case] = {"returncode": r.returncode, "timed_out": r.timed_out, "seconds": round(r.seconds, 1)}
    except Exception as e:  # noqa: BLE001 - recorded, never hidden
        info["cases"][case] = {"error": f"{type(e).__name__}: {e}"[:500], "seconds": round(time.time() - t, 1)}
    print(case, info["cases"][case], flush=True)

json.dump(adaptations, open("/kaggle/working/adaptations.json", "w"), indent=1)
import importlib.metadata as md  # noqa: E402

info["versions"] = {}
for pkg in ("scikit-learn", "pandas", "numpy", "xgboost", "lightgbm", "scipy"):
    try:
        info["versions"][pkg] = md.version(pkg)
    except md.PackageNotFoundError:
        info["versions"][pkg] = None
info["seconds"] = round(time.time() - T0, 1)
json.dump(info, open("/kaggle/working/run_info.json", "w"), indent=2)
print(json.dumps(info, indent=2))
