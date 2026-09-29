"""LeakLens: prove on a real Kaggle session (internet off) that the sandbox hides Kaggle's injected tokens.

Installs the leaklens wheel from the private dataset (no internet), then:
1. records which credential-like variable NAMES the parent session has (values never printed),
2. runs a child through leaklens.sandbox.run_untrusted with require_offline=True (the real network probe),
   and checks that none of those names, and none of their values, reach the child,
3. runs the repo's test suite (tests/test_sandbox.py and tests/test_smoke.py) if pytest is available,
4. records whether any KAGGLE_* variable holds a URL and whether its host answers with internet off
   (hosts are logged; tokens are not).
"""

import glob
import json
import os
import subprocess
import sys
import tarfile
import time
from urllib.parse import urlparse

out = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
code_dir = os.path.dirname(glob.glob("/kaggle/input/**/CODE_VERSION.json", recursive=True)[0])
out["code_version"] = json.load(open(os.path.join(code_dir, "CODE_VERSION.json")))
wheel = glob.glob(os.path.join(code_dir, "leaklens-*.whl"))[0]
out["pip_install_rc"] = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", wheel]).returncode

from leaklens.sandbox import SandboxRefused, network_reachable, run_untrusted  # noqa: E402

markers = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "ACCESS_KEY", "CREDENTIAL", "KAGGLE")
parent_secret_names = sorted(k for k in os.environ if any(m in k.upper() for m in markers))
parent_secret_values = {os.environ[k] for k in parent_secret_names if len(os.environ[k]) >= 8}
out["parent_secret_like_names"] = parent_secret_names
out["network_reachable"] = network_reachable()

dump = "import json, os; print(json.dumps(dict(os.environ)))"
try:
    res = run_untrusted([sys.executable, "-c", dump], require_offline=True)
    child_env = json.loads(res.stdout)
    out["child_env_names"] = sorted(child_env)
    out["leaked_names"] = sorted(set(parent_secret_names) & set(child_env))
    blob = json.dumps(child_env)
    out["leaked_value_count"] = sum(1 for v in parent_secret_values if v in blob)
    out["sandbox_ok"] = res.returncode == 0 and not out["leaked_names"] and out["leaked_value_count"] == 0
except SandboxRefused as e:
    out["sandbox_ok"] = False
    out["refused"] = str(e)

# Kaggle-internal endpoints: which KAGGLE_* variables hold URLs, and are their hosts reachable offline?
import socket  # noqa: E402

endpoints = {}
for k, v in os.environ.items():
    if k.startswith("KAGGLE") and v.startswith(("http://", "https://")):
        u = urlparse(v)
        port = u.port or (443 if u.scheme == "https" else 80)
        try:
            socket.create_connection((u.hostname, port), timeout=3).close()
            status = "REACHABLE"
        except OSError as e:
            status = f"unreachable ({type(e).__name__})"
        endpoints[k] = {"host": u.hostname, "port": port, "status": status}
out["kaggle_url_endpoints"] = endpoints

tests_tar = os.path.join(code_dir, "tests.tar.gz")
if os.path.exists(tests_tar):
    with tarfile.open(tests_tar) as t:
        t.extractall("/tmp/ll", filter="data")
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "/tmp/ll/tests/test_sandbox.py",
                        "/tmp/ll/tests/test_smoke.py", "-p", "no:cacheprovider"], capture_output=True, text=True)
    out["pytest_rc"] = p.returncode
    out["pytest_tail"] = (p.stdout + p.stderr)[-2000:]

print(json.dumps(out, indent=2))
json.dump(out, open("sandbox_check.json", "w"), indent=2)
