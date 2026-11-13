"""LeakLens Phase 7 baseline: scicode-lint 0.5.0 on the injected TEST files (Kaggle GPU, 2x T4).

Trusted inputs only (our generated benchmark files, plain-script rendering, as given to the Yang analyser).
Route 1: vLLM (scicode-lint's pinned version) serving Qwen/Qwen3-8B at 16-bit with the qwen3 reasoning parser.
Route 2 (only if route 1 does not come up): llama.cpp CUDA build serving Qwen3-8B Q8_0.
Per file: `scicode-lint lint FILE --pattern <leakage patterns> --format json`; raw output saved per file.
Writes scicode_test_results.json (incrementally) and run_info.json.
"""

import glob
import json
import os
import subprocess
import time
import urllib.request
import zipfile

T0 = time.time()
code_dir = os.path.dirname(glob.glob("/kaggle/input/**/CODE_VERSION.json", recursive=True)[0])
import yaml  # noqa: E402

cfg = yaml.safe_load(open(glob.glob("/kaggle/input/**/scicode_gpu.yaml", recursive=True)[0]))
OUT = "/kaggle/working"
info = {"code_version": json.load(open(os.path.join(code_dir, "CODE_VERSION.json"))), "cfg": cfg, "steps": []}


def save():
    json.dump(info, open(f"{OUT}/run_info.json", "w"), indent=2)


def sh(name, cmd, timeout=3600, **kw):
    t = time.time()
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, **kw)
        rc, log = p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        rc, log = -999, "TIMEOUT"
    info["steps"].append({"name": name, "rc": rc, "seconds": round(time.time() - t, 1), "log_tail": log[-2500:]})
    print(name, rc, round(time.time() - t, 1), flush=True)
    save()
    return rc == 0


def healthy(port):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=5)
        return True
    except Exception:  # noqa: BLE001
        return False


# benchmark files
hits = glob.glob("/kaggle/input/**/benchmark/injected/manifest.csv", recursive=True)
if hits:
    bench = os.path.dirname(hits[0])
else:
    with zipfile.ZipFile(os.path.join(code_dir, "benchmark_injected.zip")) as z:
        z.extractall("/tmp/bench")
    bench = "/tmp/bench/benchmark/injected"
import csv  # noqa: E402

items = [r for r in csv.DictReader(open(f"{bench}/manifest.csv")) if r["split"] == cfg["split"]]
info["n_items"] = len(items)
sh("nvidia_smi", "nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv")

# client (scicode-lint needs Python 3.13)
sh("client", f"pip install -q uv && uv venv -q -p {cfg['python_client']} /tmp/sc && "
             f"uv pip install -q -p /tmp/sc/bin/python scicode-lint=={cfg['scicode_lint_version']}")

# route 1: vLLM
route = None
ok = sh("vllm_install", f"pip install -q vllm=={cfg['vllm_version']}", timeout=2400)
if ok:
    log = open("/tmp/vllm.log", "w")
    srv = subprocess.Popen(
        ["python", "-m", "vllm.entrypoints.openai.api_server", "--model", cfg["vllm_model"],
         "--served-model-name", cfg["served_alias"], "--dtype", "half",
         "--tensor-parallel-size", str(cfg["tensor_parallel"]), "--max-model-len", str(cfg["max_model_len"]),
         "--gpu-memory-utilization", str(cfg["gpu_memory_utilization"]), "--reasoning-parser", "qwen3",
         "--enable-prefix-caching", "--port", "8000"], stdout=log, stderr=subprocess.STDOUT)
    t = time.time()
    while time.time() - t < cfg["vllm_start_timeout_minutes"] * 60 and srv.poll() is None:
        if healthy(8000):
            route = f"vllm {cfg['vllm_version']}, {cfg['vllm_model']} fp16, TP={cfg['tensor_parallel']}"
            break
        time.sleep(15)
    if route is None:
        srv.kill()
        info["vllm_log_tail"] = open("/tmp/vllm.log").read()[-4000:]
        save()

# route 2: llama.cpp CUDA
if route is None:
    rel, asset = cfg["fallback_llama_cpp_release"], cfg["fallback_llama_cpp_asset"]
    sh("llama_cpp", f"cd /tmp && wget -q https://github.com/ggml-org/llama.cpp/releases/download/{rel}/{asset} "
                    f"&& mkdir -p llama && tar xzf {asset} -C llama")
    sh("gguf", f"cd /tmp && wget -q https://huggingface.co/{cfg['fallback_gguf_repo']}/resolve/main/"
               f"{cfg['fallback_gguf_file']}", timeout=2400)
    binp = subprocess.run("find /tmp/llama -name llama-server -type f | head -1", shell=True, capture_output=True,
                          text=True).stdout.strip()
    env = {**os.environ, "LD_LIBRARY_PATH": os.path.dirname(binp) + ":" + os.environ.get("LD_LIBRARY_PATH", "")}
    log = open("/tmp/llama.log", "w")
    srv = subprocess.Popen([binp, "-m", f"/tmp/{cfg['fallback_gguf_file']}", "--alias", cfg["served_alias"],
                            "--jinja", "-ngl", "99", "-c", "32768", "-np", "4", "--host", "127.0.0.1",
                            "--port", "8000"], stdout=log, stderr=subprocess.STDOUT, env=env)
    t = time.time()
    while time.time() - t < 900 and srv.poll() is None:
        if healthy(8000):
            route = f"llama.cpp {rel} CUDA, {cfg['fallback_gguf_file']}"
            break
        time.sleep(10)
    if route is None:
        info["llama_log_tail"] = open("/tmp/llama.log").read()[-4000:]
info["route"] = route
save()

results = {}
if route:
    for i, r in enumerate(items):
        if time.time() - T0 > cfg["total_budget_minutes"] * 60:
            results[r["item_id"]] = {"status": "skipped: total budget exhausted"}
            continue
        src = f"{bench}/_groundtruth/leaky_py/{r['item_id']}.py"
        t = time.time()
        try:
            p = subprocess.run(["/tmp/sc/bin/scicode-lint", "lint", src, "--pattern", cfg["patterns"],
                                "--vllm-url", "http://127.0.0.1:8000", "--format", "json"],
                               capture_output=True, text=True, timeout=cfg["per_file_timeout_minutes"] * 60)
            rec = {"status": "done", "rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr[-1500:]}
        except subprocess.TimeoutExpired:
            rec = {"status": "timeout"}
        rec["seconds"] = round(time.time() - t, 1)
        results[r["item_id"]] = rec
        json.dump(results, open(f"{OUT}/scicode_test_results.json", "w"))
        print(i + 1, len(items), r["item_id"], rec["status"], rec["seconds"], flush=True)
info["total_seconds"] = round(time.time() - T0, 1)
save()
json.dump(results, open(f"{OUT}/scicode_test_results.json", "w"))
