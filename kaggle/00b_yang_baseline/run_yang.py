"""LeakLens Phase 0: can Yang et al.'s ASE'22 leakage analyser be built and run today, as released?

Runs on a Kaggle CPU session WITH internet (needed to install the tool). Only trusted inputs are analysed:
our four runnability probes, fetched from the LeakLens repo at a pinned commit. No untrusted notebooks.

Build follows the tool's own Dockerfile: souffle from its apt PPA, the authors' pyright fork built with
npm + lerna 4, Python 3.8 venv with requirements.txt, then `python -m src.main <file> -o`.
Every step's exit code and log tail go to yang_build_report.json; a failed step is reported, not hidden.
"""

import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

YANG_REPO = "https://github.com/malusamayo/leakage-analysis.git"
YANG_COMMIT = "a7d038bfec6b8ddbe21d87dde54b806aecdd79f7"  # HEAD on 2026-09-29 (last push 2023-05-02)
LEAKLENS_RAW = "https://raw.githubusercontent.com/bytes06runner/LeakLens/{commit}/baselines/probes/{name}"
LEAKLENS_COMMIT = os.environ.get("LEAKLENS_COMMIT", "__LEAKLENS_COMMIT__")
PROBES = ["p1_preprocessing_leak.py", "p2_group_leak.py", "p3_temporal_leak.py", "p4_clean.py"]
NODE_VERSION = "16.20.2"  # pyright fork predates Node 18; the Dockerfile's apt nodejs is unpinned

WORK = Path("/kaggle/working")
TOOL = Path("/tmp/leakage-analysis")
PROBE_DIR = Path("/tmp/probes")
report: dict = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "yang_commit": YANG_COMMIT, "leaklens_commit": LEAKLENS_COMMIT, "steps": []}


def step(name: str, cmd: str, cwd: Path | None = None, timeout: int = 1800, env: dict | None = None) -> bool:
    t0 = time.time()
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, **(env or {})})
        rc, out = p.returncode, (p.stdout + p.stderr)
    except subprocess.TimeoutExpired as e:
        rc, out = -999, f"TIMEOUT after {timeout}s\n{e}"
    report["steps"].append({"name": name, "cmd": cmd, "rc": rc, "seconds": round(time.time() - t0, 1),
                            "log_tail": out[-3000:]})
    print(f"[{name}] rc={rc} ({time.time() - t0:.0f}s)", flush=True)
    save()
    return rc == 0


def save() -> None:
    (WORK / "yang_build_report.json").write_text(json.dumps(report, indent=2))


node_bin = f"/tmp/node-v{NODE_VERSION}-linux-x64/bin"
path_env = {"PATH": f"{node_bin}:/tmp/yang-venv/bin:" + os.environ["PATH"]}

ok = step("apt_souffle", "set -e; apt-get update -qq; apt-get install -y -qq wget gnupg ca-certificates; "
          "wget -q https://souffle-lang.github.io/ppa/souffle-key.public "
          "-O /usr/share/keyrings/souffle-archive-keyring.gpg; "
          "echo 'deb [signed-by=/usr/share/keyrings/souffle-archive-keyring.gpg] "
          "https://souffle-lang.github.io/ppa/ubuntu/ stable main' > /etc/apt/sources.list.d/souffle.list; "
          "apt-get update -qq; apt-get install -y -qq souffle; souffle --version")
ok &= step("node", f"set -e; cd /tmp; wget -q https://nodejs.org/dist/v{NODE_VERSION}/node-v{NODE_VERSION}"
           f"-linux-x64.tar.xz; tar xf node-v{NODE_VERSION}-linux-x64.tar.xz; {node_bin}/node --version")
ok &= step("clone", f"set -e; git clone -q {YANG_REPO} {TOOL}; cd {TOOL}; git checkout -q {YANG_COMMIT}; "
           "git submodule update --init --recursive; git -C pyright log -1 --format=%H%n%cI")
ok &= step("pyright_build", "set -e; npm install -g lerna@4.0.0 >/dev/null; npm install >/dev/null 2>&1 || "
           "npm install; cd packages/pyright; npm run build", cwd=TOOL / "pyright", env=path_env, timeout=3000)
ok &= step("python38_venv", "set -e; pip install -q uv; uv venv -q -p 3.8 /tmp/yang-venv; "
           f"uv pip install -q -p /tmp/yang-venv/bin/python -r {TOOL}/requirements.txt; "
           "/tmp/yang-venv/bin/python --version; uv pip list -p /tmp/yang-venv/bin/python", env=path_env)

PROBE_DIR.mkdir(exist_ok=True)
for name in PROBES:
    urllib.request.urlretrieve(LEAKLENS_RAW.format(commit=LEAKLENS_COMMIT, name=name), PROBE_DIR / name)

report["probe_results"] = {}
for name in PROBES:
    t0 = time.time()
    ran = step(f"analyse_{name}", f"/tmp/yang-venv/bin/python -m src.main {PROBE_DIR / name} -o",
               cwd=TOOL, env=path_env, timeout=600)
    outputs = {}
    fact_dir = PROBE_DIR / (name[:-3] + "-fact")
    if fact_dir.exists():
        for csv in sorted(fact_dir.glob("*.csv")):
            lines = csv.read_text(errors="replace").strip().splitlines()
            if lines and any(k in csv.stem.lower() for k in ("leak", "telemetry", "final")):
                outputs[csv.stem] = lines[:20]
    report["probe_results"][name] = {"exit_ok": ran, "seconds": round(time.time() - t0, 1),
                                     "html_written": (PROBE_DIR / (name[:-3] + ".html")).exists(),
                                     "leak_relations": outputs}
    save()

shutil.make_archive(str(WORK / "yang_outputs"), "gztar", PROBE_DIR)
report["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
report["build_ok"] = bool(ok)
save()
print(json.dumps({k: v for k, v in report.items() if k != "steps"}, indent=2))
