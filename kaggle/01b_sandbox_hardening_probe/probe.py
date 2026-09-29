"""LeakLens: can a sandboxed child still reach Kaggle's session tokens or the data proxy? (internet off)

Follow-up to leaklens-01-sandbox-check, which showed dp.kaggle.net (KAGGLE_DATA_PROXY_URL) is reachable with
internet off. Records booleans and names only; never token values, never sends a token anywhere.
Questions:
 1. Does the job run as root? Which capabilities does it have?
 2. With a clean env, can a child still read tokens from /proc/<parent>/environ or /proc/1/environ?
 3. Does running the child as a fresh unprivileged user block that?
 4. Can we put the child in its own network namespace (unshare -n), cutting the data-proxy route?
 5. What does the data proxy answer without any token (status line only)?
"""

import json
import os
import pwd
import shutil
import socket
import subprocess
import sys
import tempfile

MARK = "KAGGLE_DATA_PROXY_TOKEN="
out = {"uid": os.getuid(), "euid": os.geteuid(), "user": pwd.getpwuid(os.getuid()).pw_name}
try:
    out["cap_eff"] = next(line.split()[1] for line in open("/proc/self/status") if line.startswith("CapEff"))
except Exception as e:  # noqa: BLE001
    out["cap_eff"] = f"error {e}"

clean_env = {"PATH": "/usr/bin:/bin", "HOME": "/tmp"}
reader = (
    "import os, sys\n"
    "res = {}\n"
    "for pid in (str(os.getppid()), '1'):\n"
    "    try:\n"
    "        res[pid if pid == '1' else 'parent'] = " + repr(MARK) + " in open(f'/proc/{pid}/environ', 'rb').read().decode('latin1')\n"
    "    except Exception as e:\n"
    "        res[pid if pid == '1' else 'parent'] = 'unreadable: ' + type(e).__name__\n"
    "import json; print(json.dumps(res))\n"
)


def run(argv, **kw):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=60, **kw)
    return {"rc": p.returncode, "out": p.stdout.strip()[-500:], "err": p.stderr.strip()[-300:]}


out["parent_has_token_in_env"] = MARK[:-1] in os.environ
out["child_same_user_reads_environ"] = run([sys.executable, "-c", reader], env=clean_env)

# Fresh unprivileged user (only possible if we are root).
user_ok = False
if os.geteuid() == 0:
    r = run(["useradd", "--no-create-home", "--shell", "/usr/sbin/nologin", "llsandbox"])
    out["useradd"] = r
    try:
        pw = pwd.getpwnam("llsandbox")
        user_ok = True
        wd = tempfile.mkdtemp()
        os.chown(wd, pw.pw_uid, pw.pw_gid)
        out["child_unprivileged_reads_environ"] = run(
            [sys.executable, "-c", reader], env=clean_env, cwd=wd, user=pw.pw_uid, group=pw.pw_gid, extra_groups=[]
        )
    except KeyError:
        pass
out["unprivileged_user_available"] = user_ok

# Network namespace.
probe_proxy = (
    "import socket\n"
    "try:\n"
    "    socket.create_connection(('dp.kaggle.net', 443), timeout=3).close(); print('REACHABLE')\n"
    "except OSError as e:\n"
    "    print('unreachable', type(e).__name__)\n"
)
out["proxy_from_plain_child"] = run([sys.executable, "-c", probe_proxy], env=clean_env)
out["unshare_path"] = shutil.which("unshare")
if out["unshare_path"]:
    out["proxy_from_netns_child"] = run(["unshare", "-n", sys.executable, "-c", probe_proxy], env=clean_env)

# Data proxy answer with NO credentials: status line only.
try:
    s = socket.create_connection(("dp.kaggle.net", 443), timeout=5)
    import ssl
    ss = ssl.create_default_context().wrap_socket(s, server_hostname="dp.kaggle.net")
    ss.sendall(b"GET / HTTP/1.1\r\nHost: dp.kaggle.net\r\nConnection: close\r\n\r\n")
    out["proxy_status_line_no_token"] = ss.recv(200).split(b"\r\n", 1)[0].decode("latin1")
    ss.close()
except Exception as e:  # noqa: BLE001
    out["proxy_status_line_no_token"] = f"error {type(e).__name__}: {e}"

out["kaggle_kernel_integrations_nonempty"] = bool(os.environ.get("KAGGLE_KERNEL_INTEGRATIONS"))
print(json.dumps(out, indent=2))
json.dump(out, open("hardening_probe.json", "w"), indent=2)
