"""The sandbox must hide Kaggle's injected tokens and other secrets from untrusted code (Integrity Rule 7)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from leaklens.config import load_config
from leaklens.sandbox import SandboxRefused, build_env, run_untrusted

KAGGLE_INJECTED = ("KAGGLE_API_V1_TOKEN", "KAGGLE_DATA_PROXY_TOKEN", "KAGGLE_USER_SECRETS_TOKEN")
FAKE_VALUE = "fake-secret-value-7f3a9c"

# Child program: report its full environment, cwd, and whether it can see the files it was given.
DUMP = (
    "import json, os, pathlib; "
    "print(json.dumps({'env': dict(os.environ), 'cwd': os.getcwd(), "
    "'files': sorted(p.name for p in pathlib.Path('.').iterdir())}))"
)


@pytest.fixture
def poisoned_env(monkeypatch):
    """Parent environment as on Kaggle, plus other credentials a session might carry."""
    names = (*KAGGLE_INJECTED, "KAGGLE_KEY", "GITHUB_TOKEN", "AWS_SECRET_ACCESS_KEY", "OPENAI_API_KEY")
    for name in names:
        monkeypatch.setenv(name, FAKE_VALUE)
    monkeypatch.setenv("LANG", "C.UTF-8")
    return names


def _run_dump(**kw):
    res = run_untrusted([sys.executable, "-c", DUMP], trusted_code=True, **kw)
    assert res.returncode == 0, res.stderr
    return res, json.loads(res.stdout)


def test_kaggle_tokens_absent_in_child(poisoned_env):
    _, seen = _run_dump()
    for name in poisoned_env:
        assert name not in seen["env"], f"{name} leaked into the sandbox"
    assert not any("KAGGLE" in k.upper() for k in seen["env"])
    assert FAKE_VALUE not in json.dumps(seen["env"])


def test_child_env_is_exactly_the_allowlist(poisoned_env):
    cfg = load_config("sandbox")
    _, seen = _run_dump()
    allowed = set(cfg["env_allowlist"]) | set(cfg["env_fixed"]) | {"HOME", "TMPDIR", "PATH"}
    # The OS may add a few variables at exec time (e.g. macOS __CF_USER_TEXT_ENCODING); none may carry secrets.
    extra = set(seen["env"]) - allowed
    assert all(k.startswith("__CF") for k in extra), extra
    assert seen["env"]["LANG"] == "C.UTF-8"  # allow-listed variables do pass through


def test_throwaway_workdir_is_home_and_deleted(tmp_path):
    src = tmp_path / "nb.py"
    src.write_text("print('hi')\n")
    res, seen = _run_dump(inputs={"nb.py": src})
    cwd = Path(seen["cwd"])
    assert cwd.name.startswith(load_config("sandbox")["workdir_prefix"])
    assert Path(seen["env"]["HOME"]).resolve() == cwd.resolve()
    assert Path(seen["env"]["TMPDIR"]).resolve().parent == cwd.resolve()
    assert "nb.py" in seen["files"]
    assert not cwd.exists(), "working directory must be removed after the run"


def test_outputs_collected_before_cleanup():
    code = "open('metrics.json','w').write('{\"auc\": 0.5}')"
    res = run_untrusted([sys.executable, "-c", code], collect=["metrics.json"], trusted_code=True)
    assert json.loads(res.outputs["metrics.json"]) == {"auc": 0.5}


def test_timeout_kills_process_group():
    # The grandchild inherits the stdout pipe; if it survived, communicate() would block for 60 s.
    code = (
        "import subprocess, sys, time; "
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); time.sleep(60)"
    )
    res = run_untrusted([sys.executable, "-c", code], timeout_seconds=1, trusted_code=True)
    assert res.timed_out
    assert res.seconds < 10


def test_refuses_when_online():
    with pytest.raises(SandboxRefused):
        run_untrusted([sys.executable, "-c", "print(1)"], network_probe=lambda: True)


def test_untrusted_refused_without_root(monkeypatch):
    from leaklens import sandbox

    monkeypatch.setattr(sandbox.os, "geteuid", lambda: 1000)
    with pytest.raises(SandboxRefused, match="root parent"):
        run_untrusted([sys.executable, "-c", "print(1)"], network_probe=lambda: False)


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() != 0, reason="needs root (runs on Kaggle)")
def test_untrusted_runs_offline_as_unprivileged_user():
    code = "import os; print(os.geteuid())"
    res = run_untrusted([sys.executable, "-c", code], network_probe=lambda: False)
    assert res.returncode == 0, res.stderr
    assert int(res.stdout) != 0


def test_deny_markers_override_allowlist(tmp_path):
    cfg = load_config("sandbox")
    parent = {"LANG": "C", "KAGGLE_API_V1_TOKEN": FAKE_VALUE}
    # Even a name that someone later adds to the allow-list is dropped if it matches a deny marker.
    cfg["env_allowlist"].append("KAGGLE_API_V1_TOKEN")
    try:
        env = build_env(tmp_path, parent)
    finally:
        cfg["env_allowlist"].remove("KAGGLE_API_V1_TOKEN")
    assert "KAGGLE_API_V1_TOKEN" not in env
    assert env["LANG"] == "C"


def test_root_parent_refuses_if_user_cannot_be_created(monkeypatch):
    from leaklens import sandbox

    monkeypatch.setattr(sandbox.os, "geteuid", lambda: 0)
    monkeypatch.setattr(sandbox.pwd, "getpwnam", lambda name: (_ for _ in ()).throw(KeyError(name)))
    monkeypatch.setattr(sandbox.subprocess, "run", lambda *a, **k: type("R", (), {"stderr": "denied"})())
    with pytest.raises(SandboxRefused, match="cannot create user"):
        sandbox.unprivileged_ids()


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() != 0 or not Path("/proc/self/environ").exists(),
                    reason="needs root and /proc (runs on Kaggle)")
def test_child_cannot_read_ancestor_environ_via_proc(tmp_path):
    """/proc/<pid>/environ shows a process's environment as it was at start. Launch an intermediate parent whose
    starting environment holds a fake token; the sandboxed child must not find it in any ancestor's environ."""
    child = (
        "import os\n"
        "found = []\n"
        "pid = os.getppid()\n"
        "while pid > 0:\n"
        "    try:\n"
        f"        if b'{FAKE_VALUE}' in open(f'/proc/{{pid}}/environ', 'rb').read(): found.append(pid)\n"
        "    except OSError:\n"
        "        pass\n"
        "    try:\n"
        "        pid = int(open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()[1])\n"
        "    except OSError:\n"
        "        break\n"
        "print('LEAK' if found else 'clean')\n"
    )
    parent = (
        "import sys\n"
        "from leaklens.sandbox import run_untrusted\n"
        f"res = run_untrusted([sys.executable, '-c', {child!r}], network_probe=lambda: False)\n"
        "print(res.stdout.strip(), res.stderr.strip()[-300:])\n"
    )
    env = {**os.environ, "KAGGLE_DATA_PROXY_TOKEN": FAKE_VALUE}
    p = subprocess.run([sys.executable, "-c", parent], env=env, capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    assert p.stdout.startswith("clean"), p.stdout
