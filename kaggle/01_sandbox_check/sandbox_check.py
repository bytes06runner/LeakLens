"""LeakLens: prove on a real Kaggle session (internet off) that the sandbox hides Kaggle's injected tokens.

Installs the leaklens wheel from the private dataset (no internet), then:
1. records which credential-like variable NAMES the parent session has (values never printed),
2. runs a child through leaklens.sandbox.run_untrusted with require_offline=True (the real network probe),
   and checks that none of those names, and none of their values, reach the child,
3. v2: checks that a sandboxed child cannot find the real KAGGLE_DATA_PROXY_TOKEN in any ancestor's
   /proc/<pid>/environ (the gap found by leaklens-01b-sandbox-hardening-probe; fixed by the privilege drop),
   and runs tests/test_sandbox.py + tests/test_smoke.py as root (root-only tests are skipped on the laptop),
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
    res = run_untrusted([sys.executable, "-c", dump])
    child_env = json.loads(res.stdout)
    out["child_env_names"] = sorted(child_env)
    out["leaked_names"] = sorted(set(parent_secret_names) & set(child_env))
    blob = json.dumps(child_env)
    out["leaked_value_count"] = sum(1 for v in parent_secret_values if v in blob)
    out["sandbox_ok"] = res.returncode == 0 and not out["leaked_names"] and out["leaked_value_count"] == 0
except SandboxRefused as e:
    out["sandbox_ok"] = False
    out["refused"] = str(e)

# v2: can the child find the real token in any ancestor's /proc/<pid>/environ? (boolean only)
token = os.environ.get("KAGGLE_DATA_PROXY_TOKEN", "")
# The child gets only a SHA-256 of the token (never the value) and hashes each environ entry it can read.
import hashlib  # noqa: E402

digest = hashlib.sha256(token.encode()).hexdigest()
ancestor_scan = (
    "import hashlib, os\n"
    f"target = {digest!r}\n"
    "found, unreadable, pid = 0, 0, os.getppid()\n"
    "while pid > 0:\n"
    "    try:\n"
    "        for entry in open(f'/proc/{pid}/environ', 'rb').read().split(b'\\0'):\n"
    "            if b'=' in entry and hashlib.sha256(entry.split(b'=', 1)[1]).hexdigest() == target: found += 1\n"
    "    except OSError:\n"
    "        unreadable += 1\n"
    "    try:\n"
    "        pid = int(open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()[1])\n"
    "    except OSError:\n"
    "        break\n"
    "print(found, unreadable, os.geteuid())\n"
)
r = run_untrusted([sys.executable, "-c", ancestor_scan])
found, unreadable, child_euid = (int(x) for x in r.stdout.split())
out["proc_scan"] = {"token_present_in_parent": bool(token), "ancestors_with_token": found,
                    "ancestors_unreadable": unreadable, "child_euid": child_euid, "stderr": r.stderr[-300:]}
# Control: the same scan without the privilege drop (trusted_code=True keeps root) must FIND the token,
# otherwise found == 0 above would not mean anything.
rc = run_untrusted([sys.executable, "-c", ancestor_scan], trusted_code=True)
c_found, c_unreadable, c_euid = (int(x) for x in rc.stdout.split())
out["proc_scan_control_root_child"] = {"ancestors_with_token": c_found, "ancestors_unreadable": c_unreadable,
                                       "child_euid": c_euid}
out["sandbox_ok"] = out["sandbox_ok"] and bool(token) and found == 0 and child_euid != 0 and c_found > 0

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

# Kaggle auto-extracts archives in datasets, so look for an extracted tests/ first, then the tarball.
found_tests = glob.glob("/kaggle/input/**/test_sandbox.py", recursive=True)
tests_dir = None
if found_tests:
    import shutil  # noqa: E402
    shutil.copytree(os.path.dirname(found_tests[0]), "/tmp/ll/tests")  # writable copy for pytest
    tests_dir = "/tmp/ll/tests"
elif os.path.exists(os.path.join(code_dir, "tests.tar.gz")):
    with tarfile.open(os.path.join(code_dir, "tests.tar.gz")) as t:
        t.extractall("/tmp/ll", filter="data")
    tests_dir = "/tmp/ll/tests"
out["tests_dir_found"] = tests_dir
if tests_dir:
    p = subprocess.run([sys.executable, "-m", "pytest", "-v", "-rs", f"{tests_dir}/test_sandbox.py",
                        f"{tests_dir}/test_smoke.py", "-p", "no:cacheprovider"], capture_output=True, text=True)
    out["pytest_rc"] = p.returncode
    out["pytest_tail"] = (p.stdout + p.stderr)[-4000:]

print(json.dumps(out, indent=2))
json.dump(out, open("sandbox_check.json", "w"), indent=2)
