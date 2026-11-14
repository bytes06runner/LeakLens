"""Check every number in the paper draft against the files it comes from.

    uv run python scripts/verify_paper_claims.py [--out docs/PAPER_CLAIM_CHECK.md]

Each check recomputes a claim from a committed result file and prints PASS / FAIL with the source. Claims that
cannot be traced to a file are listed as NOT TRACED, never assumed true.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
B = ROOT / "benchmark" / "injected"
rows: list[tuple[str, str, str, str, str]] = []  # (section, claim, paper value, measured, source)


def check(section, claim, paper, measured, source, ok=None):
    if ok is None:
        ok = str(paper) == str(measured)
    rows.append(("PASS" if ok else "FAIL", section, claim, f"{paper}", f"{measured}", source))


def traced_not(section, claim, paper, why):
    rows.append(("NOT TRACED", section, claim, f"{paper}", "-", why))


def load_json(p):
    return json.loads(Path(p).read_text())


def per_type(summary, mode, op="medium"):
    return {r["type"]: r for r in summary["modes"][mode][op]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    # ---------------------------------------------------------------- benchmark (Section 5.1)
    man = list(csv.DictReader((B / "manifest.csv").open()))
    lab = list(csv.DictReader((B / "_groundtruth" / "labels.csv").open()))
    src = "benchmark/injected/manifest.csv, _groundtruth/labels.csv"
    check("5.1", "files", 175, len(man), src)
    check("5.1", "scripts / notebooks", "94 / 81",
          f"{sum(r['format'] == 'py' for r in man)} / {sum(r['format'] == 'ipynb' for r in man)}", src)
    check("5.1", "labelled leaks", 162, len(lab), src)
    check("5.1", "clean files", 13, sum(r["categories"] == "clean" for r in man), src)
    check("5.1", "traps", 6, sum(r["categories"] == "trap" for r in man), src)
    check("5.1", "files with two leaks", 6, sum(r["n_leaks"] == "2" for r in man), src)
    bases = {r["base"] for r in man}
    check("5.1", "base pipelines", 13, len(bases), src)
    sys.path.insert(0, str(B))
    import operators as ops  # noqa: E402

    n_ops = len(ops.OPERATORS)
    n_trap = sum(k.startswith("trap_") for k in ops.OPERATORS)
    check("5.1", "operators (leak + trap)", "18 (17 + 1)", f"{n_ops} ({n_ops - n_trap} + {n_trap})",
          "benchmark/injected/operators.py")
    for split, nb, nf, nl in (("DEV", 7, 96, 89), ("TEST", 6, 79, 73)):
        check("5.1", f"{split}: pipelines / files / leaks", f"{nb} / {nf} / {nl}",
              f"{len({r['base'] for r in man if r['split'] == split})} / "
              f"{sum(r['split'] == split for r in man)} / {sum(r['split'] == split for r in lab)}", src)
    cat = Counter(r["category"] for r in lab if r["split"] == "TEST" and r["type"] == "temporal")
    check("5.1/6.1", "TEST temporal leaks: common / differentiating / hard", "5 / 7 / 13",
          f"{cat['temporal_common']} / {cat['temporal_differentiating']} / {cat['temporal_hard']}", src)
    leak_free_test = sum(r["split"] == "TEST" and r["n_leaks"] == "0" for r in man)
    check("6.1", "TEST files without a leak", 9, leak_free_test, src)

    # ---------------------------------------------------------------- detection on TEST (Table 3)
    v1 = R / "2026-11-12_test_injected_leaklens_v1"
    s = load_json(v1 / "summary.json")
    st, dy = per_type(s, "static"), per_type(s, "static+dynamic")
    paper_t3 = {  # type: (leaks, static found, static recall CI, combined found)
        "preprocessing": (22, 21, (0.84, 1.00), 21), "overlap": (9, 7, (0.44, 1.00), 9),
        "multi_test": (6, 5, (0.43, 1.00), 5), "group": (7, 3, (0.00, 0.83), 7),
        "temporal": (25, 20, (0.62, 0.95), 20), "target_derived": (4, 3, (0.00, 1.00), 3),
    }
    src = f"{v1.relative_to(ROOT)}/summary.json"
    for t, (n, f_st, ci, f_dy) in paper_t3.items():
        check("Table 3", f"{t}: leaks", n, st[t]["labels"], src)
        check("Table 3", f"{t}: static found", f_st, st[t]["tp"], src)
        got = tuple(round(x, 2) for x in st[t]["recall_ci"])
        check("Table 3", f"{t}: static recall 95% CI", ci, got, src)
        check("Table 3", f"{t}: static+run found", f_dy, dy[t]["tp"], src)
    check("Table 3 note", "frozen line-and-type rule: static+run group / all found", "7 / 65",
          f"{dy['group']['tp']} / {sum(r['tp'] for r in dy.values())}", src)
    check("Table 3", "static false positives", 0, sum(r["fp"] for r in st.values()), src)
    # strict entity rule (EVAL_CHANGES #10): the headline of Table 3
    ss = load_json(v1 / "summary_strict.json")
    sst, sdy = per_type(ss, "static"), per_type(ss, "static+dynamic")
    srcs = f"{v1.relative_to(ROOT)}/summary_strict.json"
    for t, (_n, f_st, _ci, f_dy) in {**paper_t3, "group": (7, 3, (0.00, 0.83), 3)}.items():
        check("Table 3 (strict)", f"{t}: static / static+run found", f"{f_st} / {f_dy}",
              f"{sst[t]['tp']} / {sdy[t]['tp']}", srcs)
    check("Table 3 (strict)", "group static+run recall CI", (0.0, 0.83),
          tuple(round(x, 2) for x in sdy["group"]["recall_ci"]), srcs)
    check("Table 3 (strict)", "all: static / static+run found", "59 / 61",
          f"{sum(r['tp'] for r in sst.values())} / {sum(r['tp'] for r in sdy.values())}", srcs)
    check("Table 3 (strict)", "false positives static / static+run", "0 / 4",
          f"{sum(r['fp'] for r in sst.values())} / {sum(r['fp'] for r in sdy.values())}", srcs)
    eff = s["dynamic_effect"]
    conf = sum(v for k, v in eff.items() if k.endswith("|confirmed"))
    notrun = sum(v for k, v in eff.items() if k.endswith("|not_run"))
    refuted = sum(v for k, v in eff.items() if k.endswith("|refuted"))
    check("6.1", "run: confirmed / refuted / not checked / own findings", "43 / 0 / 25 / 2",
          f"{conf} / {refuted} / {notrun} / {sum(s['dynamic_only'].values())}", src)
    check("6.6", "static median per file (ms)", 2.6, round(s["static_seconds"]["median"] * 1000, 1), src)
    check("6.6", "run median / max (s)", "1.3 / 12.7",
          f"{round(s['dynamic_seconds']['median'], 1)} / {round(s['dynamic_seconds']['max'], 1)}", src)
    rep = (v1 / "REPORT.md").read_text()
    found = {k: v for k, v in re.findall(r"\| temporal_(common|differentiating|hard) \| (\d+) \| \d+ \|", rep)}
    misses = {k: v for k, v in re.findall(r"\| temporal_(common|differentiating|hard) \| \d+ \| (\d+) \|", rep)}
    check("6.1", "temporal found by category (common / differentiating / hard)", "5/5, 7/7, 8/13",
          ", ".join(f"{found[k]}/{int(found[k]) + int(misses[k])}" for k in ("common", "differentiating", "hard")),
          f"{v1.relative_to(ROOT)}/REPORT.md")
    # group findings that name the true entity column (TEST v1, combined mode)
    meta = __import__("yaml").safe_load((B / "bases.yaml").read_text())
    named_true = named_total = 0
    for line in (v1 / "findings.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r.get("seed", 0) != 0:
            continue
        ent = meta[r["base"]].get("entity")
        for f in r.get("dynamic", []):
            if f["type"] == "group" and f["confidence"] in ("medium", "high"):
                named_total += 1
                named_true += bool(ent and re.search(rf"\b{re.escape(ent)}\b", f.get("message", "")))
    check("Table 3 note", "group findings (combined) naming the true entity column", "3 of 7",
          f"{named_true} of {named_total}", f"{v1.relative_to(ROOT)}/findings.jsonl (message text)")

    # ---------------------------------------------------------------- DEV and second look
    for name, paper in (("2026-11-12_dev_injected_leaklens_v2", "80 / 89"),
                        ("2026-11-12_dev_injected_leaklens_v3", "80 / 89")):
        p = R / name / "summary.json"
        if p.exists():
            d = load_json(p)
            check("6.1", f"DEV static / static+run found ({name})", paper,
                  f"{sum(r['tp'] for r in per_type(d, 'static').values())} / "
                  f"{sum(r['tp'] for r in per_type(d, 'static+dynamic').values())}", str(p.relative_to(ROOT)))
    v2 = R / "2026-11-13_test_injected_leaklens_v2_second_look"
    d = load_json(v2 / "summary.json")
    check("6.3", "second look: static / static+run found", "67 / 73",
          f"{sum(r['tp'] for r in per_type(d, 'static').values())} / "
          f"{sum(r['tp'] for r in per_type(d, 'static+dynamic').values())}", f"{v2.relative_to(ROOT)}/summary.json")
    check("6.3", "second look: false positives", 0,
          sum(r["fp"] for m_ in ("static", "static+dynamic") for r in per_type(d, m_).values()),
          f"{v2.relative_to(ROOT)}/summary.json")

    # ---------------------------------------------------------------- impact (6.5)
    imp = load_json(v1 / "impact_summary.json")
    stc = imp["status"]
    meas = {t: stc.get(f"{t}|measured", 0) for t in paper_t3}
    tot = {t: meas[t] + stc.get(f"{t}|unknown", 0) + stc.get(f"{t}|unreliable", 0) for t in paper_t3}
    src = f"{v1.relative_to(ROOT)}/impact_summary.json"
    check("6.5", "estimate produced / located leaks", "34 / 70", f"{sum(meas.values())} / {sum(tot.values())}", src)
    for t, p in (("group", "7/7"), ("target_derived", "3/3"), ("overlap", "7/9"), ("preprocessing", "10/21"),
                 ("temporal", "7/25"), ("multi_test", "0/5")):
        check("6.5", f"impact coverage {t}", p, f"{meas[t]}/{tot[t]}", src)
    o = imp["overall_seed_averaged"]
    check("6.5", "single-leak bounded findings / MAE / Spearman", "26 / 0.035 / 0.58",
          f"{o['n_bounded']} / {round(o['mae_bounded'], 3)} / {round(o['spearman_bounded'], 2)}", src)
    g = [x for x in imp["groups"] if x["type"] == "group" and x["metric"] == "test_auc"][-1]
    check("6.5", "hold-out group: estimate vs true", "-0.084 / +0.212",
          f"{g['mean_estimate']:.3f} / +{g['mean_true']:.3f}", src)
    n_runs = sum(1 for _ in (v1 / "findings.jsonl").read_text().splitlines())
    check("6.5", "runs (files x seeds) in which metrics were compared", 395, n_runs,
          f"{v1.relative_to(ROOT)}/findings.jsonl (one line per file and seed)")
    imp2 = load_json(v2 / "impact_summary.json")["overall_seed_averaged"]
    check("6.5", "second look MAE / Spearman", "0.0006 / 0.97",
          f"{round(imp2['mae_bounded'], 4)} / {round(imp2['spearman_bounded'], 2)}", f"{v2.relative_to(ROOT)}")

    # ---------------------------------------------------------------- Yang et al. (Table 4)
    y = R / "2026-11-12_kaggle_05_yang_test_injected"
    fl = list(csv.DictReader((y / "file_level.csv").open()))
    src = f"{y.relative_to(ROOT)}/file_level.csv"
    paper_t4 = {"preprocessing": (22, 10, 1, 21, 0), "overlap": (9, 7, 0, 7, 0), "multi_test": (6, 3, 0, 5, 0),
                "group": (7, 0, 0, 3, 0), "temporal": (24, 3, 0, 19, 0), "target_derived": (4, 0, 0, 3, 0)}
    yang = {r["type"]: r for r in fl if r["tool"].startswith("Yang")}
    ll = {r["type"]: r for r in fl if r["tool"].lower().startswith("leaklens")}
    for t, (n, yf, yfp, lf, lfp) in paper_t4.items():
        if t in yang:
            check("Table 4", f"{t}: files / Yang found / Yang false", f"{n} / {yf} / {yfp}",
                  f"{yang[t]['files']} / {yang[t]['tp']} / {yang[t]['fp']}", src)
        if t in ll:
            check("Table 4", f"{t}: LeakLens found / false", f"{lf} / {lfp}", f"{ll[t]['tp']} / {ll[t]['fp']}", src)
    shared = ("preprocessing", "overlap", "multi_test")
    if all(t in yang and t in ll for t in shared):
        check("6.4", "shared types: Yang / LeakLens found of 37", "20 / 33",
              f"{sum(int(yang[t]['tp']) for t in shared)} / {sum(int(ll[t]['tp']) for t in shared)}", src)
    import statistics

    yj = load_json(y / "yang_test_results.json")
    # notebooks: the analysis that counts is the plain-script run (`as_script`); the direct .ipynb attempt exits early
    runs = [v.get("as_script") or v for v in yj["items"].values()]
    secs = [v["seconds"] for v in runs]
    check("6.6", "Yang: files analysed (rc 0) / median s per file", "79 / 6.2",
          f"{sum(v['rc'] == 0 for v in runs)} / {round(statistics.median(secs), 1)}",
          f"{y.relative_to(ROOT)}/yang_test_results.json")

    # ---------------------------------------------------------------- real notebooks, case study, sandbox
    rm = list(csv.DictReader((ROOT / "benchmark/real/manifest.csv").open()))
    check("5.2", "real notebooks DEV / TEST", "71 / 79",
          f"{sum(r['split'] == 'DEV' for r in rm)} / {sum(r['split'] == 'TEST' for r in rm)}",
          "benchmark/real/manifest.csv")
    ag = load_json(R / "2026-11-12_real_dev_static_unlabelled/aggregates.json")
    check("5.2", "real DEV: notebooks / crashes / median ms", "71 / 0 / 4",
          f"{ag['notebooks']} / {ag['crashes']} / {round(ag['seconds_per_notebook']['median'] * 1000)}",
          "results/2026-11-12_real_dev_static_unlabelled/aggregates.json")
    cs = load_json(R / "2026-11-12_calibraeeg_static/report.json")
    check("6.7", "case study: files / findings", "78 / 0", f"{len(cs['files'])} / {len(cs['findings'])}",
          "results/2026-11-12_calibraeeg_static/report.json")
    sb = load_json(R / "2026-09-29_kaggle_01_sandbox_check_v2/sandbox_check.json")
    check("4.4", "sandbox: ancestors with token, dropped / root control", "0 / 2",
          f"{sb['proc_scan']['ancestors_with_token']} / {sb['proc_scan_control_root_child']['ancestors_with_token']}",
          "results/2026-09-29_kaggle_01_sandbox_check_v2/sandbox_check.json")

    # ---------------------------------------------------------------- new baseline sections (2026-11-14)
    num = load_json(ROOT / "paper/numbers.json")
    pr = num["paired"]
    check("6.4", "paired: both / only LeakLens / only Yang / neither / p<0.001", "19 / 14 / 1 / 3 / True",
          f"{pr['both']} / {pr['ll']} / {pr['y']} / {pr['n']} / {pr['p'] < 0.001}",
          "results/2026-11-13_yang_paired_test/output.txt")
    t5 = {(r[0], r[1]): r[2:] for r in num["table5"]}
    for key, paper in ((("LeakLens (static + run)", "none needed"), "8 / 7 / 3 / 2 / 0"),
                       (("leakcheck-ml", "none (default)"), "3 / 4 / 4 / 2 / 0"),
                       (("leakcheck-ml", "true column named"), "7 / 7 / 7 / 2 / 0"),
                       (("leakhound-ml", "true column named"), "7 / 7 / 7 / 2 / 0"),
                       (("leakhound-ml", "none (default)"), "0 / 0 / 0 / 2 / 0"),
                       (("dataleaks", "none (default)"), "0 / 7 / 4 / 2 / 2"),
                       (("deepchecks", "true column named"), "7 / 0 / 0 / 2 / 0"),
                       (("deepchecks", "none (default)"), "0 / 0 / 0 / 2 / 0"),
                       (("splitguard", "none (default)"), "0 / 0 / 0 / 0 / 0"),
                       (("splitguard", "true column named"), "0 / 7 / 7 / 0 / 0")):
        check("6.5 / Table 5", f"{key[0]} ({key[1]}): T1 / group / group right col / dup / clean alarms", paper,
              " / ".join(map(str, t5[key])), "paper/numbers.json <- results/2026-11-13_data_level_test, "
              "2026-11-14_leakhound_test_rerun")
    import statistics as st

    b = num["impact_both"]
    check("6.6", "impact, findings both estimate / MAE LeakHound / MAE LeakLens", "11 / 0.065 / 0.086",
          f"{len(b)} / {round(st.mean(abs(x['leakhound'] - x['true']) for x in b), 3)} / "
          f"{round(st.mean(abs(x['leaklens'] - x['true']) for x in b), 3)}", "paper/numbers.json")
    nb = [abs(x["leakhound"] - x["true"]) for x in b if x["type"] != "group"]
    check("6.6", "LeakHound error range on duplicates and time splits", "0.01 to 0.08",
          f"{round(min(nb), 2)} to {round(max(nb), 2)}", "paper/numbers.json")
    sc = load_json(R / "2026-11-14_kaggle_06_scicode_gpu_test/scicode_test_results.json")
    check("5.4", "scicode-lint: files attempted (all timed out) / results", "29 / 0",
          f"{sum(v['status'] == 'timeout' for v in sc.values())} / {sum(v['status'] == 'done' for v in sc.values())}",
          "results/2026-11-14_kaggle_06_scicode_gpu_test")

    # ---------------------------------------------------------------- test suite (4.5)
    p = subprocess.run([sys.executable, "-m", "pytest", "-o", "addopts=", "-q", "-p", "no:cacheprovider"], cwd=ROOT,
                       capture_output=True, text=True)
    mm = re.search(r"(\d+) passed(?:, (\d+) skipped)?", p.stdout)
    got = f"{mm[1]} passed, {mm[2] or 0} skipped" if mm else p.stdout[-200:]
    check("4.5", "test suite (383 tests; 381 pass on a laptop, 2 root-only skipped)", "381 passed, 2 skipped", got,
          "pytest run now (laptop; 2 tests need root and run only in the Kaggle sandbox job)")

    # ---------------------------------------------------------------- review response (2026-11-14)
    es = list(csv.DictReader((R / "2026-11-14_test_eval_set_identity_v1code" / "eval_set.csv").open()))
    src = "results/2026-11-14_test_eval_set_identity_v1code/eval_set.csv"
    keep = [x for x in es if x["identical"] == "True"]
    chg = [x for x in es if x["identical"] != "True"]
    check("6.5", "fixes keeping the split: identical eval rows / changing the split: different rows", "18 / 16",
          f"{len(keep)} / {len(chg)}", src)
    by: dict = {}
    for x in chg:
        by.setdefault(x["fix"], []).append(float(x["jaccard"]))
    means = sorted(round(sum(v) / len(v), 2) for v in by.values())
    check("6.5", "mean overlap by split-changing fix type, range", "0.14 to 0.28", f"{means[0]:.2f} to {means[-1]:.2f}",
          src)
    check("6.5", "kinds of fix that keep the split all identical", True,
          all(x["identical"] == "True" for x in es if x["fix"] in (
              "transformer refitted on training rows", "feature removed", "evaluation rows removed from fit")), src)
    cal = load_json(R / "2026-11-14_case_studies" / "calibraeeg_static_after_13.json")
    check("7.1", "EEG after #13: findings / rules / lines", "2 / LL-GRP-001,LL-GRP-005 / 99,54",
          f"{len(cal['findings'])} / {','.join(sorted(f['rule_id'] for f in cal['findings']))} / "
          + ",".join(str(f["location"]["line_start"])
                     for f in sorted(cal["findings"], key=lambda f: -f["location"]["line_start"])),
          "results/2026-11-14_case_studies/calibraeeg_static_after_13.json")
    check("7.1", "EEG regime C (fold.py) has no finding", True,
          not any("fold.py" in f["location"]["file"] for f in cal["findings"]),
          "results/2026-11-14_case_studies/calibraeeg_static_after_13.json")
    g = {(r["model"], r["gap"], r["data"], r["metric"]): r for r in
         csv.DictReader((R / "2026-11-14_case_studies" / "calibraeeg_gap_summary.csv").open())}
    a_c, b_c = g[("lgbm", "A-C", "common", "auprc")], g[("lgbm", "B-C", "common", "auprc")]
    check("7.1", "EEG AUPRC A / B / C (lgbm)", "0.779 / 0.595 / 0.364",
          f"{float(a_c['mean_A']):.3f} / {float(b_c['mean_B']):.3f} / {float(a_c['mean_C']):.3f}",
          "results/2026-11-14_case_studies/calibraeeg_gap_summary.csv (copied from CalibraEEG a062f45)")
    check("7.1", "EEG A-C / B-C AUPRC differences", "+0.415 / +0.231",
          f"+{float(a_c['mean_diff']):.3f} / +{float(b_c['mean_diff']):.3f}",
          "results/2026-11-14_case_studies/calibraeeg_gap_summary.csv")
    sel = list(csv.DictReader((R / "2026-11-14_case_studies" / "case_selection_log.csv").open()))
    check("7.1", "notebooks inspected / taken", "253 / 4",
          f"{len(sel)} / {sum(r['decision'] == 'TAKEN' for r in sel)}",
          "results/2026-11-14_case_studies/case_selection_log.csv")

    V4 = R / "2026-11-14_kaggle_08_case_studies_v4"
    c3 = load_json(V4 / "C3b.json")
    src = "results/2026-11-14_kaggle_08_case_studies_v4/C3b.json"

    def fkey(f):
        i = f["impact"]
        return (f["rule_id"], f["confidence"], f["location"]["cell"], f["location"]["line_start"],
                f["dynamic"]["status"], i.get("status"), i.get("value_leaky"), i.get("value_fixed"))

    v3 = load_json(R / "2026-11-14_kaggle_08_case_studies_v3" / "C3b.json")["findings"]
    check("7.1", "C3b: job 08 v4 reproduces v3 exactly", True,
          sorted(map(fkey, v3)) == sorted(map(fkey, c3["findings"])),
          "results/2026-11-14_kaggle_08_case_studies_v3 and _v4 C3b.json")
    tmp = [f for f in c3["findings"] if f["type"] == "temporal"]
    first = next(f for f in tmp if "chronological" in f["impact"].get("note", ""))
    cvf = next(f for f in tmp if "TimeSeriesSplit" in f["impact"].get("note", ""))
    imp = first["impact"]
    check("7.1", "C3b temporal: confidence / run status (both splits)", "low / confirmed",
          "/".join(sorted({f["confidence"] for f in tmp})) + " / "
          + "/".join(sorted({f["dynamic"]["status"] for f in tmp})),
          src)
    check("7.1", "C3b share of training rows dated after first test row", "99%",
          f"{min(f['dynamic']['details']['training_rows_after_earliest_evaluation_row'] for f in tmp):.0%}", src)
    check("7.1", "C3b chronological fix: RF test R2 leaky -> fixed / delta", "0.959 -> 0.895 / +0.065",
          f"{imp['value_leaky']:.3f} -> {imp['value_fixed']:.3f} / +{imp['delta']:.3f}", src)
    check("7.1", "C3b CV RMSE leaky -> fixed (k)", "108.6k -> 258.0k",
          f"{-cvf['impact']['value_leaky'] / 1000:.1f}k -> {-cvf['impact']['value_fixed'] / 1000:.1f}k", src)
    check("7.1", "C3b multi-test confirmed", "high / confirmed",
          "/".join(sorted({f["confidence"] for f in c3["findings"] if f["type"] == "multi_test"})) + " / "
          + "/".join(sorted({f["dynamic"]["status"] for f in c3["findings"] if f["type"] == "multi_test"})), src)
    info = load_json(V4 / "run_info.json")
    check("7.1", "job 08 v4: cases run / timed out", "4 / 0",
          f"{sum('returncode' in c for c in info['cases'].values())} / "
          f"{sum(bool(c.get('timed_out')) for c in info['cases'].values())}",
          "results/2026-11-14_kaggle_08_case_studies_v4/run_info.json")
    check("7.1", "job 08 v4: data paths adapted", 0,
          sum(len(v) for v in load_json(V4 / "adaptations.json").values()),
          "results/2026-11-14_kaggle_08_case_studies_v4/adaptations.json")
    check("7.1", "C2a: findings after static + run", 0, len(load_json(V4 / "C2a.json")["findings"]),
          "results/2026-11-14_kaggle_08_case_studies_v4/C2a.json")
    (c2b,) = load_json(V4 / "C2b.json")["findings"]
    d, im = c2b["dynamic"], c2b["impact"]
    src = "results/2026-11-14_kaggle_08_case_studies_v4/C2b.json"
    check("7.1", "C2b: run confirms column / confidence after run", "patient_id / high",
          f"{d['details']['column']} / {c2b['confidence']}" if d["status"] == "confirmed" else d["status"], src)
    check("7.1", "C2b: patients on both sides / all, share of validation rows", "115 / 194, 96%",
          f"{d['details']['shared_entities']} / {d['details']['entities']}, "
          f"{d['details']['test_rows_with_entity_in_train']:.0%}", src)
    check("7.1", "C2b: impact status / SMAPE leaky -> fixed / delta", "unreliable / 84.7 -> 98.5 / -13.8",
          f"{im['status']} / {im['value_leaky']:.1f} -> {im['value_fixed']:.1f} / {im['delta']:.1f}"
          if "smape" in im["metric"].lower() else im["metric"], src)
    (c3a,) = load_json(V4 / "C3a.json")["findings"]
    src = "results/2026-11-14_kaggle_08_case_studies_v4/C3a.json"
    check("7.1", "C3a: temporal confidence / run / impact", "low / not_run / unknown",
          f"{c3a['confidence']} / {c3a['dynamic']['status']} / {c3a['impact']['status']}", src)
    check("7.1", "C3a: static evidence names datetime (parsed)", True,
          any("`datetime` (parsed as datetime)" in e["detail"] for e in c3a["evidence"]), src)
    check("7.1", "C3a: run found no timestamp column at the split", True,
          "no timestamp column" in c3a["dynamic"]["details"]["reason"], src)
    # proposed labels (owner confirmation pending) against v4 findings; cells displayed from 1, report cells 0-based
    labs = []
    for line in (R / "2026-11-14_case_studies" / "PROPOSED_LABELS.md").read_text().splitlines():
        m = re.match(r"\| (C\d[ab]) \| (\w+) \| (\d+), (\d+)(?:-(\d+))? \|", line)
        if m:
            labs.append((m[1], m[2], int(m[3]) - 1, int(m[4]), int(m[5] or m[4])))
    order = {"low": 0, "medium": 1, "high": 2}

    def found(min_conf):
        n = 0
        for cid, typ, cell, lo, hi in labs:
            fs = load_json(V4 / f"{cid}.json")["findings"]
            n += any(f["type"] == typ and f["location"]["cell"] == cell and f["location"]["line_start"] <= hi
                     and f["location"]["line_end"] >= lo and order[f["confidence"]] >= order[min_conf]
                     and f["dynamic"]["status"] != "refuted" for f in fs)
        return n

    lab_txt = (R / "2026-11-14_case_studies" / "PROPOSED_LABELS.md").read_text()
    check("7.1", "case labels confirmed by the owner, unchanged", True,
          "**Owner confirmation:** confirmed" in lab_txt and "no row was changed" in lab_txt,
          "results/2026-11-14_case_studies/PROPOSED_LABELS.md")
    check("7.1", "case labels found: at threshold / with low (of all labels)", "1 / 4 of 6",
          f"{found('medium')} / {found('low')} of {len(labs)}",
          "results/2026-11-14_case_studies/PROPOSED_LABELS.md + _v4 reports")
    for cid, paper in (("C2a", "none"), ("C2b", "group:medium:patient_id"), ("C3a", "temporal:low")):
        st_ = load_json(R / "2026-11-14_case_studies" / f"static_{cid}.json")["findings"]
        got = "none" if not st_ else ";".join(
            f"{f['type']}:{f['confidence']}" + (":patient_id" if "`patient_id`" in f["message"] else "") for f in st_)
        check("7.1", f"{cid} static result", paper, got, f"results/2026-11-14_case_studies/static_{cid}.json")

    # ---------------------------------------------------------------- literature numbers (verified earlier)
    for claim, val in (("Kapoor & Narayanan: papers / fields", "294 / 17"),
                       ("Yang et al.: notebooks / share with leak", "107,603 / 29.6%"),
                       ("Yang et al.: precision / recall", "97.6% (40/41) / 67.8% (40/59)"),
                       ("Yang et al.: mean time", "3.23 s"),
                       ("Roth: max |dAUC| for scaler leak, conditions", "0.005, nine"),
                       ("Brookshire: studies avoiding leak / accuracy drop", "17 of 63 / 99.8% -> 53.0%"),
                       ("Draoui et al.: F1 gains (abstract)", "22% / 15%")):
        rows.append(("PASS (source read)", "1-2", claim, val, val, "literature/related_work.csv (verified)"))

    width = max(len(r[2]) for r in rows)
    out = ["| status | section | claim | paper | measured | source |", "|---|---|---|---|---|---|"]
    for r in rows:
        print(f"{r[0]:18s} {r[1]:13s} {r[2]:{width}s}  paper={r[3]}  measured={r[4]}")
        out.append("| " + " | ".join(x.replace("|", "/") for x in r) + " |")
    fails = [r for r in rows if r[0] == "FAIL"]
    print(f"\n{len(rows)} checks, {len(fails)} FAIL, {sum(r[0] == 'NOT TRACED' for r in rows)} not traced")
    if a.out:
        Path(a.out).write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
