"""LeakLens Phase 2: true inflation of every injected benchmark item, 5 data seeds (internet off).

Runs our own generated code only (trusted_code=True in the sandbox). Installs the leaklens wheel from the
private dataset, locates benchmark/injected (Kaggle auto-extracts the archive), and runs measure_inflation.py.
Output: inflation.csv + run_info.json.
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time

t0 = time.time()
code_dir = os.path.dirname(glob.glob("/kaggle/input/**/CODE_VERSION.json", recursive=True)[0])
info = {"code_version": json.load(open(os.path.join(code_dir, "CODE_VERSION.json")))}
wheel = glob.glob(os.path.join(code_dir, "leaklens-*.whl"))[0]
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", wheel], check=True)

hits = glob.glob("/kaggle/input/**/benchmark/injected/measure_inflation.py", recursive=True)
if hits:
    shutil.copytree(os.path.dirname(os.path.dirname(hits[0])), "/tmp/bench/benchmark")
else:
    with tarfile.open(os.path.join(code_dir, "benchmark_injected.tar.gz")) as t:
        t.extractall("/tmp/bench", filter="data")
script = "/tmp/bench/benchmark/injected/measure_inflation.py"
p = subprocess.run([sys.executable, script, "/kaggle/working/inflation.csv", "--seeds", "0", "1", "2", "3", "4",
                    "--workers", "4"], capture_output=True, text=True)
info.update({"rc": p.returncode, "stdout_tail": p.stdout[-2000:], "stderr_tail": p.stderr[-2000:],
             "seconds": round(time.time() - t0, 1), "python": sys.version.split()[0]})
json.dump(info, open("/kaggle/working/run_info.json", "w"), indent=2)
print(json.dumps(info, indent=2))
