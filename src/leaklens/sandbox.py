"""Run untrusted code in a child process with a clean environment and a throwaway working directory.

This is the only sanctioned way to execute notebooks from the internet (CLAUDE.md Integrity Rule 7). It layers on
top of the Kaggle session, which provides the outer boundary (internet off, no personal credentials):

- **Environment:** the child sees only `env_allowlist` plus `env_fixed` from configs/sandbox.yaml. Any variable
  whose name contains a deny marker (TOKEN, SECRET, KAGGLE, ...) is dropped even if allow-listed. This removes
  the tokens Kaggle injects into every session.
- **Working directory:** a fresh temporary directory, also used as HOME and TMPDIR, deleted after the run.
- **Timeout:** the child runs in its own process group; on timeout the whole group is killed.
- **Privilege drop:** if the parent runs as root (Kaggle jobs do), the child runs as an unprivileged user created
  on demand. Without this, a root child can read the tokens from `/proc/<pid>/environ` of its ancestors even with
  a clean environment (measured on Kaggle, results/2026-09-29_kaggle_01b_sandbox_hardening_probe). If the user
  cannot be created, the run is refused.
- **Offline check:** the run is refused if any network probe succeeds, so an internet-enabled session cannot
  execute untrusted code by mistake.

Untrusted mode (the default) requires both the offline check and the privilege drop, so in practice it only runs
inside an offline Kaggle job. On a laptop it refuses. `trusted_code=True` skips both, for our own test snippets.

Known limits: it is not a filesystem jail (the child can read world-readable paths), and it cannot cut the
network route to Kaggle's data proxy (`dp.kaggle.net` stays reachable with internet off; `unshare -n` is not
permitted on Kaggle). The child cannot obtain the proxy token, and no integrations are attached to LeakLens
kernels, so the proxy gives it nothing to act on.
"""

from __future__ import annotations

import os
import pwd
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from leaklens.config import load_config


class SandboxRefused(RuntimeError):
    """Raised when the sandbox refuses to start a run (for example because the network is reachable)."""


@dataclass(frozen=True)
class SandboxResult:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    seconds: float
    outputs: dict[str, bytes] = field(default_factory=dict)


def _is_denied(name: str, markers: Sequence[str]) -> bool:
    upper = name.upper()
    return any(m in upper for m in markers)


def build_env(workdir: Path, parent_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Environment for the child: allow-listed parent variables + fixed values, with deny markers enforced."""
    cfg = load_config("sandbox")
    parent = os.environ if parent_env is None else parent_env
    markers = cfg["env_deny_markers"]
    env = {k: parent[k] for k in cfg["env_allowlist"] if k in parent and not _is_denied(k, markers)}
    env.update({k: str(v) for k, v in cfg["env_fixed"].items() if not _is_denied(k, markers)})
    tmp = workdir / "tmp"
    tmp.mkdir(exist_ok=True)
    env["HOME"] = str(workdir)
    env["TMPDIR"] = str(tmp)
    # Minimal PATH: the interpreter running LeakLens plus system binaries.
    env["PATH"] = os.pathsep.join([str(Path(sys.executable).parent), "/usr/bin", "/bin"])
    return env


def unprivileged_ids() -> tuple[int, int]:
    """(uid, gid) of the unprivileged sandbox user, created if needed. Requires a root parent."""
    if os.geteuid() != 0:
        raise SandboxRefused(
            "untrusted code needs a root parent to drop the child to an unprivileged user; "
            "a same-user child could read the parent's /proc/<pid>/environ. Run it in an offline Kaggle job."
        )
    name = load_config("sandbox")["unprivileged_user"]
    try:
        pw = pwd.getpwnam(name)
    except KeyError:
        created = subprocess.run(
            ["useradd", "--no-create-home", "--shell", "/usr/sbin/nologin", name], capture_output=True, text=True
        )
        try:
            pw = pwd.getpwnam(name)
        except KeyError:
            raise SandboxRefused(f"running as root and cannot create user {name!r}: {created.stderr.strip()}") from None
    if pw.pw_uid == 0:
        raise SandboxRefused(f"sandbox user {name!r} has uid 0")
    return pw.pw_uid, pw.pw_gid


def network_reachable() -> bool:
    """True if any configured probe target accepts a connection."""
    probe = load_config("sandbox")["network_probe"]
    for host, port in probe["targets"]:
        try:
            socket.create_connection((host, int(port)), timeout=probe["timeout_seconds"]).close()
            return True
        except OSError:
            continue
    return False


def run_untrusted(
    argv: Sequence[str],
    *,
    inputs: Mapping[str, Path] | None = None,
    collect: Sequence[str] = (),
    timeout_seconds: float | None = None,
    trusted_code: bool = False,
    network_probe: Callable[[], bool] = network_reachable,
    parent_env: Mapping[str, str] | None = None,
) -> SandboxResult:
    """Run `argv` in a throwaway directory with a clean environment.

    inputs:  {relative name: source path} copied into the working directory before the run.
    collect: relative paths read back (as bytes) after the run, before the directory is deleted.
    trusted_code: our own code only; skips the offline check and the privilege drop.
    """
    ids = None
    if not trusted_code:
        if network_probe():
            raise SandboxRefused("network is reachable; untrusted code runs only in an offline Kaggle session")
        ids = unprivileged_ids()

    cfg = load_config("sandbox")
    timeout = cfg["timeout_seconds"] if timeout_seconds is None else timeout_seconds
    workdir = Path(tempfile.mkdtemp(prefix=cfg["workdir_prefix"]))
    try:
        for rel, src in (inputs or {}).items():
            dest = workdir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if Path(src).is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)

        env = build_env(workdir, parent_env)
        drop = {}
        if ids is not None:
            uid, gid = ids
            for p in [workdir, *workdir.rglob("*")]:
                os.chown(p, uid, gid)
            drop = {"user": uid, "group": gid, "extra_groups": []}
        t0 = time.monotonic()
        proc = subprocess.Popen(
            list(argv), cwd=workdir, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True, **drop,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate()
            timed_out = True
        seconds = time.monotonic() - t0

        outputs = {}
        for rel in collect:
            p = workdir / rel
            if p.is_file():
                outputs[rel] = p.read_bytes()
        return SandboxResult(proc.returncode, stdout, stderr, timed_out, seconds, outputs)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
