"""Dynamic pass and impact estimation on small scripts we write here (trusted code, synthetic data).

Each test writes a data file and a script into a temporary directory, runs the static analyser, then the
instrumented run, and checks what the run confirmed, refuted or added.
"""

import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from leaklens.dynamic.confirm import confirm_file, parse_metric, run_instrumented, severity_from_delta
from leaklens.ingest import load

HEAD = """
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score, r2_score
from sklearn.model_selection import (train_test_split, cross_val_score, KFold, GroupKFold, GroupShuffleSplit,
                                     TimeSeriesSplit)
from sklearn.preprocessing import StandardScaler
"""


def grouped(tmp_path: Path, unique: bool = False, duplicates: bool = False) -> None:
    """60 patients x 8 visits. The label is a patient trait and features carry a patient fingerprint, so a model
    that has seen a patient recognises it: a row-level split inflates the score."""
    r = np.random.default_rng(0)
    n_pat, per = 60, 8
    pid = np.repeat(np.arange(n_pat), per)
    trait = r.normal(size=(n_pat, 4))
    X = trait[pid] + r.normal(0, 0.15, size=(n_pat * per, 4))
    y = (r.random(n_pat) < 0.5).astype(int)[pid]
    df = pd.DataFrame(X, columns=list("abcd"))
    df.insert(0, "patient_id", np.arange(len(df)) if unique else pid)
    df["y"] = y
    if duplicates:
        df = pd.concat([df, df.sample(frac=0.4, random_state=0)], ignore_index=True)
    df.to_csv(tmp_path / "data.csv", index=False)


def series(tmp_path: Path) -> None:
    r = np.random.default_rng(0)
    n = 600
    v = np.cumsum(r.normal(size=n))
    pd.DataFrame({"when": pd.date_range("2022-01-01", periods=n, freq="h"), "v": v}).to_csv(tmp_path / "data.csv",
                                                                                           index=False)


def run(tmp_path: Path, code: str, impact: bool = False):
    p = tmp_path / "pipeline.py"
    p.write_text(HEAD + textwrap.dedent(code).strip("\n") + "\n")
    out = confirm_file(p, load(p), [], with_impact=impact, timeout=180)
    offset = HEAD.count("\n")
    return {(f.type, f.flat_line_start - offset): f for f in out}


HOLDOUT = """
    df = pd.read_csv("data.csv")
    X, y = df[list("abcd")], df["y"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    model = RandomForestClassifier(n_estimators=60, random_state=0).fit(X_train, y_train)
    print(f"test_auc: {roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]):.4f}")
"""


def test_entity_column_never_named_in_code_is_found_at_run_time(tmp_path):
    grouped(tmp_path)
    out = run(tmp_path, HOLDOUT)
    f = out[("group", 3)]
    assert f.rule_id == "LL-GRP-004" and f.confidence == "high"
    assert f.dynamic["details"]["column"] == "patient_id" and f.dynamic["details"]["shared_entities"] > 40
    assert set(out) == {("group", 3)}


def test_unique_identifier_gives_no_group_finding(tmp_path):
    grouped(tmp_path, unique=True)
    assert run(tmp_path, HOLDOUT) == {}


def test_static_group_finding_is_refuted_when_the_identifier_is_unique(tmp_path):
    grouped(tmp_path, unique=True)
    out = run(tmp_path, """
        df = pd.read_csv("data.csv")
        X, y = df.drop(columns=["patient_id", "y"]), df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    """)
    f = out[("group", 3)]
    assert f.rule_id == "LL-GRP-001" and f.dynamic["status"] == "refuted"
    assert "unique" in f.dynamic["details"]["reason"]


def test_static_group_finding_is_confirmed_and_raised_to_high(tmp_path):
    grouped(tmp_path)
    out = run(tmp_path, """
        df = pd.read_csv("data.csv")
        X, y = df.drop(columns=["patient_id", "y"]), df["y"]
        print(cross_val_score(RandomForestClassifier(n_estimators=30, random_state=0), X, y, cv=5).mean())
    """)
    f = out[("group", 3)]
    assert f.rule_id == "LL-GRP-002" and f.dynamic["status"] == "confirmed" and f.confidence == "high"


def test_group_aware_split_gives_no_finding(tmp_path):
    grouped(tmp_path)
    assert run(tmp_path, """
        df = pd.read_csv("data.csv")
        X, y = df[list("abcd")], df["y"]
        cv = GroupKFold(n_splits=5)
        print(cross_val_score(RandomForestClassifier(n_estimators=30, random_state=0), X, y, cv=cv,
                              groups=df["patient_id"]).mean())
    """) == {}


def test_group_impact_is_measured_by_rerunning_with_a_group_aware_split(tmp_path):
    grouped(tmp_path)
    f = run(tmp_path, HOLDOUT, impact=True)[("group", 3)]
    imp = f.impact
    assert imp["status"] == "measured" and imp["metric"] == "test_auc"
    assert "GroupShuffleSplit(groups=patient_id)" in imp["note"]
    assert imp["value_leaky"] > 0.9 and imp["value_fixed"] < 0.75  # recognising patients vs new patients
    assert imp["delta"] == pytest.approx(imp["value_leaky"] - imp["value_fixed"], abs=1e-6)
    assert f.severity == "high"


def test_duplicated_records_are_found_only_by_the_run(tmp_path):
    grouped(tmp_path, unique=True, duplicates=True)
    out = run(tmp_path, HOLDOUT)
    f = out[("overlap", 3)]
    assert f.rule_id == "LL-OVL-004" and f.dynamic["details"]["evaluation_rows_identical_to_a_training_row"] > 0.2
    grouped(tmp_path, unique=True)
    assert ("overlap", 3) not in run(tmp_path, HOLDOUT)


TS = """
    df = pd.read_csv("data.csv", parse_dates=["when"]).sort_values("when")
    df["lag"] = df["v"].shift(1)
    df["target"] = df["v"].shift(-1)
    df = df.dropna()
    X, y = df[["v", "lag"]], df["target"]
"""


def test_time_overlap_confirms_a_random_split_and_measures_its_impact(tmp_path):
    series(tmp_path)
    out = run(tmp_path, TS + """
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
    print(f"test_r2: {r2_score(y_test, Ridge().fit(X_train, y_train).predict(X_test)):.4f}")
    """, impact=True)
    f = out[("temporal", 7)]
    assert f.dynamic["status"] == "confirmed" and f.confidence == "high"
    assert f.dynamic["details"]["training_rows_after_earliest_evaluation_row"] > 0.5
    assert f.impact["status"] == "measured" and "chronological" in f.impact["note"]


def test_chronological_splits_show_no_time_overlap(tmp_path):
    series(tmp_path)
    assert run(tmp_path, TS + """
    print(cross_val_score(Ridge(), X, y, cv=TimeSeriesSplit(4)).mean())
    a, b, c, d = train_test_split(X, y, shuffle=False)
    """) == {}


def test_model_fitted_on_all_rows_is_confirmed_and_fixed_by_dropping_evaluation_rows(tmp_path):
    grouped(tmp_path, unique=True)
    out = run(tmp_path, """
        df = pd.read_csv("data.csv")
        X, y = df[list("abcd")], df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
        model = RandomForestClassifier(n_estimators=60, random_state=0)
        model.fit(X, y)
        print(f"test_auc: {roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]):.4f}")
    """, impact=True)
    f = out[("overlap", 5)]
    assert f.dynamic["status"] == "confirmed" and f.dynamic["details"]["scored_rows_seen_in_fit"] == 1.0
    assert f.impact["status"] == "measured" and f.impact["value_leaky"] > f.impact["value_fixed"]
    assert "evaluation rows removed from the fit" in f.impact["note"]


def test_scaler_fitted_before_the_split_is_confirmed_and_refitted_on_training_rows(tmp_path):
    grouped(tmp_path, unique=True)
    out = run(tmp_path, """
        df = pd.read_csv("data.csv")
        X, y = df[list("abcd")], df["y"]
        X = StandardScaler().fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
        model = LogisticRegression().fit(X_train, y_train)
        print(f"test_auc: {roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]):.4f}")
    """, impact=True)
    f = out[("preprocessing", 3)]
    assert f.dynamic["status"] == "confirmed" and f.confidence == "high"
    assert f.impact["status"] == "measured" and "training rows only" in f.impact["note"]
    assert abs(f.impact["delta"]) < 0.05  # a scaler leak barely moves the score (Roth 2026); we report what we measure


def test_candidates_scored_on_the_same_rows_confirm_multi_test(tmp_path):
    grouped(tmp_path, unique=True)
    out = run(tmp_path, """
        df = pd.read_csv("data.csv")
        X, y = df[list("abcd")], df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
        scores = {}
        for depth in (1, 3, 6):
            m = RandomForestClassifier(n_estimators=20, max_depth=depth, random_state=0).fit(X_train, y_train)
            scores[depth] = roc_auc_score(y_test, m.predict_proba(X_test)[:, 1])
        print(max(scores.values()))
    """, impact=True)
    f = out[("multi_test", 7)]
    assert f.dynamic["status"] == "confirmed" and f.dynamic["details"]["candidates_scored_on_the_same_rows"] == 3
    assert f.impact["status"] == "unknown" and "not automated" in f.impact["note"]  # reported, not dropped


def test_instrumentation_does_not_change_what_the_script_prints(tmp_path):
    import subprocess
    import sys

    grouped(tmp_path)
    p = tmp_path / "pipeline.py"
    p.write_text(HEAD + textwrap.dedent(HOLDOUT + """
    folds = KFold(4, shuffle=True, random_state=1)
    rf = RandomForestClassifier(n_estimators=20, random_state=0)
    print(f"cv_auc: {cross_val_score(rf, X, y, cv=folds, scoring='roc_auc').mean():.6f}")
    """))
    plain = subprocess.run([sys.executable, "-W", "ignore", str(p)], cwd=tmp_path, capture_output=True, text=True)
    log = run_instrumented(p, tmp_path)
    assert log["status"] == "ok" and log["stdout"] == plain.stdout and "cv_auc" in plain.stdout


def test_failing_script_is_reported_as_an_error_not_as_clean(tmp_path):
    out = run(tmp_path, """
        df = pd.read_csv("missing.csv")
        X = df.drop(columns=["patient_id", "y"])
        a, b, c, d = train_test_split(X, df["y"])
    """)
    f = out[("group", 3)]
    assert f.dynamic["status"] == "error" and "missing.csv" in f.dynamic["details"]["reason"]
    assert f.confidence == "medium"  # the static finding is kept as it was


@pytest.mark.parametrize("stdout,expected", [("test_auc: 0.9123\n", ("test_auc", 0.9123)),
                                             ("loading\nAccuracy = 87.5%\ndone\n", ("Accuracy", 87.5)),
                                             ("cv_mae: 1.2e-3", ("cv_mae", 0.0012)), ("no numbers here\n", None)])
def test_parse_metric(stdout, expected):
    assert parse_metric(stdout) == expected


def test_severity_from_a_measured_impact():
    assert severity_from_delta("test_auc", 0.95, 0.60) == "high"
    assert severity_from_delta("test_auc", 0.80, 0.78) == "medium"
    assert severity_from_delta("test_auc", 0.801, 0.800) == "low"
    assert severity_from_delta("cv_mae", 9.0, 10.0) == "high"  # relative change for error metrics


def test_duplicate_impact_is_measured_by_removing_copies_before_the_split(tmp_path):
    grouped(tmp_path, unique=True, duplicates=True)
    f = run(tmp_path, HOLDOUT, impact=True)[("overlap", 3)]
    assert f.impact["status"] == "measured" and "duplicated rows removed before the split" in f.impact["note"]
    assert f.impact["value_leaky"] > f.impact["value_fixed"]


def test_cli_dynamic_and_impact_end_to_end(tmp_path):
    import json

    from click.testing import CliRunner

    from leaklens.cli import EXIT_FINDINGS, main

    grouped(tmp_path)
    p = tmp_path / "pipeline.py"
    p.write_text(HEAD + textwrap.dedent(HOLDOUT).strip("\n") + "\n")
    res = CliRunner().invoke(main, ["scan", str(p), "--dynamic", "--impact", "--trust-code", "--format", "json"])
    assert res.exit_code == EXIT_FINDINGS
    report = json.loads(res.output)
    assert report["scan"]["mode"] == "impact"
    (f,) = report["findings"]
    assert f["rule_id"] == "LL-GRP-004" and f["dynamic"]["status"] == "confirmed"
    assert f["impact"]["status"] == "measured" and f["impact"]["value_leaky"] > f["impact"]["value_fixed"]


def test_run_prefers_the_real_entity_over_a_weak_static_guess(tmp_path):
    """Fault found on TEST (EVAL_CHANGES #8): the code names only a visit number; the data also has patient_id."""
    grouped(tmp_path)
    df = pd.read_csv(tmp_path / "data.csv")
    df["visit"] = df.groupby("patient_id").cumcount()
    df.to_csv(tmp_path / "data.csv", index=False)
    f = run(tmp_path, """
        df = pd.read_csv("data.csv")
        df = df[df["visit"] >= 0]
        X, y = df[list("abcd")], df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
        model = RandomForestClassifier(n_estimators=60, random_state=0).fit(X_train, y_train)
        print(f"test_auc: {roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]):.4f}")
    """, impact=True)[("group", 4)]
    assert f.rule_id == "LL-GRP-001"  # the static pass nominated `visit`, at low confidence
    assert f.dynamic["status"] == "confirmed" and f.dynamic["details"]["column"] == "patient_id"
    assert f.confidence == "high" and "`patient_id`" in f.message and "visit" not in f.message
    assert "GroupShuffleSplit(groups=patient_id)" in f.impact["note"] and f.impact["delta"] > 0.1


def test_weak_column_alone_does_not_raise_confidence(tmp_path):
    grouped(tmp_path, unique=True)
    df = pd.read_csv(tmp_path / "data.csv").drop(columns=["patient_id"])
    df["visit"] = np.arange(len(df)) % 8
    df.to_csv(tmp_path / "data.csv", index=False)
    f = run(tmp_path, """
        df = pd.read_csv("data.csv")
        df = df[df["visit"] >= 0]
        X, y = df[list("abcd")], df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    """)[("group", 4)]
    assert f.dynamic["details"]["column"] == "visit" and f.confidence == "low"
