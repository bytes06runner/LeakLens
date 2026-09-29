"""LeakLens: how long does scicode-lint take per file on a Kaggle CPU session? (feasibility only)

Tooling profile (internet on) with trusted inputs only: four of our taxonomy examples from the private
leaklens-code dataset. The published scicode-lint setup needs vLLM on a >=16 GB GPU; here llama.cpp serves
Qwen3-8B (Q8_0) on CPU behind the same OpenAI-compatible API. Settings: configs/scicode_cpu_timing.yaml (copied
into the dataset). Every step, the server's token rates, per-file wall time and scicode-lint's JSON output are
saved to scicode_cpu_timing.json. Hard time caps per file and overall.
"""

import glob
import json
import os
import re
import subprocess
import time
import urllib.request

import yaml

T0 = time.time()
code_dir = os.path.dirname(glob.glob("/kaggle/input/**/CODE_VERSION.json", recursive=True)[0])
cfg_path = glob.glob("/kaggle/input/**/scicode_cpu_timing.yaml", recursive=True)
cfg = yaml.safe_load(open(cfg_path[0])) if cfg_path else None
out = {"code_version": json.load(open(os.path.join(code_dir, "CODE_VERSION.json"))), "cfg": cfg, "steps": []}


def save():
    json.dump(out, open("scicode_cpu_timing.json", "w"), indent=2)


def step(name, cmd, timeout=1800, **kw):
    t = time.time()
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, **kw)
        rc, log = p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        rc, log = -999, f"TIMEOUT {timeout}s"
    out["steps"].append({"name": name, "rc": rc, "seconds": round(time.time() - t, 1), "log_tail": log[-1500:]})
    print(name, rc, round(time.time() - t, 1), flush=True)
    save()
    return rc == 0


assert cfg, "config missing from dataset"
fixtures = {os.path.basename(p): p for p in glob.glob("/kaggle/input/**/fixtures/taxonomy/*.py", recursive=True)}
out["fixtures_found"] = sorted(fixtures)

rel, asset = cfg["llama_cpp_release"], cfg["llama_cpp_asset"]
ok = step("llama_cpp", f"set -e; cd /tmp; wget -q https://github.com/ggml-org/llama.cpp/releases/download/{rel}/{asset}; "
          f"mkdir -p llama && tar xzf {asset} -C llama; find llama -name llama-server -type f | head -1")
server_bin = subprocess.run("find /tmp/llama -name llama-server -type f | head -1", shell=True,
                            capture_output=True, text=True).stdout.strip()
ok &= step("model", f"set -e; cd /tmp; wget -q https://huggingface.co/{cfg['model_repo']}/resolve/main/{cfg['model_file']}; "
           f"ls -la {cfg['model_file']}", timeout=1800)
ok &= step("scicode_lint", f"set -e; pip install -q uv; uv venv -q -p {cfg['python']} /tmp/sc; "
           f"uv pip install -q -p /tmp/sc/bin/python scicode-lint=={cfg['scicode_lint_version']}; "
           "/tmp/sc/bin/scicode-lint --help | head -5")
out["setup_ok"] = bool(ok)
out["setup_seconds"] = round(time.time() - T0, 1)

server_log = open("/tmp/llama_server.log", "w")
srv = subprocess.Popen([server_bin, "-m", f"/tmp/{cfg['model_file']}", "--alias", cfg["served_alias"], "--jinja",
                        "-c", str(cfg["context_total"]), "-np", str(cfg["parallel_slots"]), "-t", str(cfg["threads"]),
                        "--host", "127.0.0.1", "--port", "8000"], stdout=server_log, stderr=subprocess.STDOUT)
t = time.time()
ready = False
while time.time() - t < 600:
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5)
        ready = True
        break
    except Exception:  # noqa: BLE001
        time.sleep(5)
out["server_ready"] = ready
out["server_load_seconds"] = round(time.time() - t, 1)
save()

out["files"] = {}
budget = cfg["total_budget_minutes"] * 60
for name in cfg["inputs"]:
    if not ready or time.time() - T0 > budget:
        out["files"][name] = {"status": "skipped (server not ready or total budget exhausted)"}
        continue
    remaining = budget - (time.time() - T0)
    timeout = min(cfg["per_file_timeout_minutes"] * 60, max(60, remaining))
    t = time.time()
    try:
        p = subprocess.run(["/tmp/sc/bin/scicode-lint", "lint", fixtures[name], "--pattern", cfg["patterns"],
                            "--vllm-url", "http://127.0.0.1:8000", "--format", "json"],
                           capture_output=True, text=True, timeout=timeout)
        rec = {"status": "done", "rc": p.returncode, "stdout": p.stdout[-6000:], "stderr": p.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        rec = {"status": f"timeout after {int(timeout)} s"}
    rec["seconds"] = round(time.time() - t, 1)
    out["files"][name] = rec
    print(name, rec["status"], rec["seconds"], flush=True)
    save()

srv.terminate()
server_log.close()
log = open("/tmp/llama_server.log").read()
rates = re.findall(r"(prompt eval|eval) time =\s*([\d.]+) ms /\s*(\d+) tokens.*?([\d.]+) tokens per second", log)
out["server_rates"] = [{"kind": k, "ms": float(ms), "tokens": int(n), "tok_per_s": float(r)} for k, ms, n, r in rates]
gen = [r for r in out["server_rates"] if r["kind"] == "eval"]
out["generated_tokens_total"] = sum(r["tokens"] for r in gen)
out["generation_tok_per_s_mean"] = round(sum(r["tok_per_s"] for r in gen) / len(gen), 2) if gen else None
out["server_log_tail"] = log[-3000:]
out["total_seconds"] = round(time.time() - T0, 1)
save()
print(json.dumps({k: v for k, v in out.items() if k not in ("steps", "server_log_tail")}, indent=2)[:6000])
