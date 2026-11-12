"""LeakLens baseline run: Yang et al.'s ASE'22 leakage analyser, as released, on the TEST split of the injected
benchmark.

Runs on a Kaggle CPU session WITH internet (needed to build the tool). Only trusted inputs are analysed: our own
generated benchmark files, fetched from the public LeakLens repository at a pinned commit. Only files whose
manifest row says split == TEST are downloaded. This job runs after the evaluation protocol was frozen (commit
0dcd2fe) and after LeakLens's own single TEST run; a baseline has no rules of ours to tune, so its TEST run does
not change anything in LeakLens.

The tool is built exactly as in kaggle/00b_yang_baseline (its own Dockerfile steps) and run with its default
command, `python -m src.main <file> -o`. Its result is read from the summary table of the HTML report it writes
(three rows: pre-processing leakage, overlap leakage, no independent test data), with the line numbers it lists.
A file the tool cannot analyse is recorded as such, never dropped (Rule 5). Nothing from the tool is copied into
LeakLens (Rule 11).
"""

import csv
import io
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

YANG_REPO = "https://github.com/malusamayo/leakage-analysis.git"
YANG_COMMIT = "a7d038bfec6b8ddbe21d87dde54b806aecdd79f7"  # same commit as the Phase 0 run
RAW = "https://raw.githubusercontent.com/bytes06runner/LeakLens/{commit}/benchmark/injected/{path}"
LEAKLENS_COMMIT = os.environ.get("LEAKLENS_COMMIT", "__LEAKLENS_COMMIT__")
SPLIT = "TEST"
NODE_VERSION = "16.20.2"
PER_FILE_TIMEOUT = 300

WORK = Path("/kaggle/working")
TOOL = Path("/tmp/leakage-analysis")
ITEMS = Path("/tmp/items")
report: dict = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "yang_commit": YANG_COMMIT,
                "leaklens_commit": LEAKLENS_COMMIT, "split": SPLIT, "steps": [], "items": {}}


def save() -> None:
    (WORK / "yang_test_results.json").write_text(json.dumps(report, indent=1))


def step(name: str, cmd: str, cwd: Path | None = None, timeout: int = 1800, env: dict | None = None) -> bool:
    t0 = time.time()
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, **(env or {})})
        rc, out = p.returncode, (p.stdout + p.stderr)
    except subprocess.TimeoutExpired as e:
        rc, out = -999, f"TIMEOUT after {timeout}s\n{e}"
    report["steps"].append({"name": name, "rc": rc, "seconds": round(time.time() - t0, 1), "log_tail": out[-1500:]})
    print(f"[{name}] rc={rc} ({time.time() - t0:.0f}s)", flush=True)
    save()
    return rc == 0


def fetch(path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(RAW.format(commit=LEAKLENS_COMMIT, path=path), dest)


ROW = re.compile(r"<tr>\s*<td>([^<]+)</td>\s*<td>(\d+)</td>\s*<td>(.*?)</td>\s*</tr>", re.S)


def read_summary(html: Path) -> dict | None:
    """The tool's own summary table: {row name: {"detected": n, "lines": [...]}}."""
    if not html.exists():
        return None
    out = {}
    for name, n, cell in ROW.findall(html.read_text(errors="replace")):
        out[name.strip()] = {"detected": int(n), "lines": [int(x) for x in re.findall(r'href="#(\d+)"', cell)]}
    return out or None


def analyse(path: Path, env: dict) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run(f"/tmp/yang-venv/bin/python -m src.main {path} -o", shell=True, cwd=TOOL,
                           capture_output=True, text=True, timeout=PER_FILE_TIMEOUT, env={**os.environ, **env})
        rc, tail = p.returncode, (p.stdout + p.stderr)[-600:]
    except subprocess.TimeoutExpired:
        rc, tail = -999, f"TIMEOUT after {PER_FILE_TIMEOUT}s"
    html = path.with_suffix(".html")
    return {"rc": rc, "seconds": round(time.time() - t0, 2), "summary": read_summary(html), "log_tail": tail}


node_bin = f"/tmp/node-v{NODE_VERSION}-linux-x64/bin"
path_env = {"PATH": f"{node_bin}:/tmp/yang-venv/bin:" + os.environ["PATH"]}

# Souffle. The tool's Dockerfile installs it from the Souffle apt PPA. That worked on 2026-09-29 and failed on
# 2026-11-12 on Kaggle's current image ("held broken packages", results/2026-11-12_kaggle_04_yang_dev_injected).
# So: try the PPA first (as released); if that fails, build Souffle 2.4.1 from source. Which route worked is
# recorded; the fallback is a deviation from the released build and is reported as such.
SOUFFLE_SRC = "2.4.1"
ok = step("apt_souffle", "set -e; apt-get update -qq; apt-get install -y -qq wget gnupg ca-certificates; "
          "wget -q https://souffle-lang.github.io/ppa/souffle-key.public "
          "-O /usr/share/keyrings/souffle-archive-keyring.gpg; "
          "echo 'deb [signed-by=/usr/share/keyrings/souffle-archive-keyring.gpg] "
          "https://souffle-lang.github.io/ppa/ubuntu/ stable main' > /etc/apt/sources.list.d/souffle.list; "
          "apt-get update -qq; apt-get install -y souffle 2>&1 | tail -40; souffle --version")
report["souffle_route"] = "apt PPA (as released)" if ok else None
if not ok:
    step("apt_souffle_cleanup", "rm -f /etc/apt/sources.list.d/souffle.list; apt-get update -qq; true")
    ok = step("souffle_from_source",
              "set -e; apt-get install -y -qq bison build-essential cmake flex libffi-dev libncurses5-dev "
              "libsqlite3-dev mcpp sqlite3 zlib1g-dev git >/dev/null; cd /tmp; "
              f"git clone -q --depth 1 --branch {SOUFFLE_SRC} https://github.com/souffle-lang/souffle.git souffle-src; "
              "cd souffle-src; cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DSOUFFLE_ENABLE_TESTING=OFF "
              "-DSOUFFLE_GIT=OFF >/dev/null; cmake --build build -j4 2>&1 | tail -5; cmake --install build >/dev/null; "
              "souffle --version", timeout=3300)
    report["souffle_route"] = f"built from source, tag {SOUFFLE_SRC} (fallback)" if ok else None
ok &= step("node", f"set -e; cd /tmp; wget -q https://nodejs.org/dist/v{NODE_VERSION}/node-v{NODE_VERSION}"
           f"-linux-x64.tar.xz; tar xf node-v{NODE_VERSION}-linux-x64.tar.xz; {node_bin}/node --version")
ok &= step("clone", f"set -e; git clone -q {YANG_REPO} {TOOL}; cd {TOOL}; git checkout -q {YANG_COMMIT}; "
           "git submodule update --init --recursive; git -C pyright log -1 --format=%H%n%cI")
ok &= step("pyright_build", "set -e; npm install -g lerna@4.0.0 >/dev/null; npm install >/dev/null 2>&1 || "
           "npm install; cd packages/pyright; npm run build", cwd=TOOL / "pyright", env=path_env, timeout=3000)
ok &= step("python38_venv", "set -e; pip install -q uv; uv venv -q -p 3.8 /tmp/yang-venv; "
           f"uv pip install -q -p /tmp/yang-venv/bin/python -r {TOOL}/requirements.txt; "
           "/tmp/yang-venv/bin/python --version", env=path_env)
report["build_ok"] = bool(ok)
save()

manifest = urllib.request.urlopen(RAW.format(commit=LEAKLENS_COMMIT, path="manifest.csv")).read().decode()
rows = [r for r in csv.DictReader(io.StringIO(manifest)) if r["split"] == SPLIT]
print(f"{len(rows)} {SPLIT} files", flush=True)
for i, r in enumerate(rows, 1):
    item = r["item_id"]
    src = ITEMS / item / Path(r["file"]).name
    fetch(r["file"], src)
    res = analyse(src, path_env) if ok else {"rc": None, "summary": None, "log_tail": "tool did not build"}
    res["format"] = r["format"]
    if res["summary"] is None and r["format"] == "ipynb" and ok:
        # The released tool could not analyse the notebook file. Record that, then also try the same code as a
        # plain .py file (our conversion), reported separately.
        py = ITEMS / item / "as_script" / "pipeline.py"
        fetch(f"_groundtruth/leaky_py/{item}.py", py)
        res["as_script"] = analyse(py, path_env)
    report["items"][item] = res
    if i % 10 == 0:
        print(f"{i}/{len(rows)}", flush=True)
        save()

report["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
save()
n_ok = sum(1 for v in report["items"].values() if v["summary"] is not None)
print(json.dumps({"build_ok": report["build_ok"], "files": len(rows), "analysed_as_released": n_ok}, indent=1))
