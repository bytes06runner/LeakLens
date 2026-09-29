"""LeakLens Phase 0 smoke test: the sandbox profile used for untrusted notebooks (CPU, internet OFF).

Checks: (1) outbound network is blocked, (2) no credential-like environment variables are present
(names only are reported, never values), (3) Python and library versions, CPU and RAM, disk.
"""

import importlib
import json
import os
import platform
import shutil
import socket
import sys
import time

out = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
out["python"] = sys.version.split()[0]
out["platform"] = platform.platform()
out["cpu_count"] = os.cpu_count()
try:
    with open("/proc/meminfo") as f:
        out["mem_total_kb"] = int(f.readline().split()[1])
except OSError:
    out["mem_total_kb"] = None

versions = {}
for mod in ["numpy", "pandas", "sklearn", "scipy", "nbformat", "nbconvert", "click", "rich", "yaml",
            "imblearn", "xgboost", "lightgbm", "torch", "tensorflow", "keras", "statsmodels"]:
    try:
        versions[mod] = getattr(importlib.import_module(mod), "__version__", "unknown")
    except Exception as e:  # noqa: BLE001
        versions[mod] = f"not importable: {type(e).__name__}"
out["versions"] = versions

net = {}
for host, port in [("pypi.org", 443), ("github.com", 443), ("1.1.1.1", 53)]:
    try:
        socket.create_connection((host, port), timeout=5).close()
        net[f"{host}:{port}"] = "REACHABLE"
    except Exception as e:  # noqa: BLE001
        net[f"{host}:{port}"] = f"blocked ({type(e).__name__})"
out["network"] = net
out["network_blocked"] = all(v != "REACHABLE" for v in net.values())

markers = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "ACCESS_KEY", "CREDENTIAL", "KAGGLE_KEY")
out["credential_like_env_names"] = sorted(k for k in os.environ if any(m in k.upper() for m in markers))
out["kaggle_json_present"] = any(os.path.exists(p) for p in [os.path.expanduser("~/.kaggle/kaggle.json"),
                                                             os.path.expanduser("~/.kaggle/access_token")])
du = shutil.disk_usage("/kaggle/working") if os.path.exists("/kaggle/working") else None
out["working_free_gb"] = round(du.free / 1e9, 1) if du else None

print(json.dumps(out, indent=2))
with open("smoke_offline.json", "w") as f:
    json.dump(out, f, indent=2)
