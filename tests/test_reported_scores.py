"""Scores recorded at run time (EVAL_CHANGES #12): displayed values, metric return values, `.score`, and the
impact fallback when a notebook prints no `name: value` line or stops with an error after its scores."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from leaklens.dynamic.confirm import reported_values, run_instrumented
from leaklens.ingest import load


def _visits(tmp: Path) -> None:
    rng = np.random.default_rng(0)
    rows = []
    for p in range(60):
        base, lab = rng.normal(size=3), int(rng.random() < 0.5)
        for v in range(6):
            rows.append({"patient_id": p, "visit": v, **{c: base[i] + rng.normal(0, 0.3) for i, c in enumerate("abc")},
                         "y": lab})
    pd.DataFrame(rows).to_csv(tmp / "visits.csv", index=False)


SCRIPT = """
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
df = pd.read_csv('visits.csv')
X, y = df[['a', 'b', 'c']], df['y']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
rf = RandomForestClassifier(n_estimators=20, random_state=0).fit(X_train, y_train)
rf.score(X_test, y_test)
len(df)
accuracy_score(y_test, rf.predict(X_test))
"""


def test_runner_records_displayed_and_metric_values(tmp_path):
    _visits(tmp_path)
    script = tmp_path / "s.py"
    script.write_text(SCRIPT)
    log = run_instrumented(script, tmp_path)
    assert log["status"] == "ok"
    vals = reported_values(log)
    kinds = {k[0] for k, _, _ in vals}
    assert {"eval", "shown", "metric"} <= kinds
    shown = [(n, v) for k, n, v in vals if k[0] == "shown"]
    assert all(n != "len(df)" for n, _ in shown)  # integer counts are not scores
    assert any(n.startswith("rf.score") and 0 <= v <= 1 for n, v in shown)


def test_impact_measured_from_recorded_scores_after_a_late_error(tmp_path):
    _visits(tmp_path)
    nb = tmp_path / "nb.py"
    nb.write_text(SCRIPT + "raise RuntimeError('submission file missing')\n")
    from leaklens.dynamic.confirm import confirm_file

    src = load(nb)
    out = confirm_file(nb, src, [], with_impact=True, cwd=tmp_path)
    grp = [f for f in out if f.type == "group"]
    assert grp, [f.type for f in out]
    imp = grp[0].impact
    assert imp["status"] == "measured", imp
    assert imp["metric_source"] == "recorded at run time"
    assert imp["value_leaky"] > imp["value_fixed"]
    assert "GroupShuffleSplit" in imp["note"]


def test_printed_statistic_is_not_taken_as_the_metric_and_unreached_scores_are_skipped(tmp_path):
    """A notebook prints a descriptive `name: value` line before modelling and ends with a cross-validation that
    the fixed split does not touch (the C3b case): the headline must be the score the fix reaches."""
    _visits(tmp_path)
    script = tmp_path / "nb.py"
    script.write_text(
        "import pandas as pd\n"
        "from sklearn.model_selection import train_test_split, cross_val_score\n"
        "from sklearn.ensemble import RandomForestClassifier\n"
        "from sklearn.metrics import accuracy_score\n"
        "df = pd.read_csv('visits.csv')\n"
        "print(f'Average visits per patient: {len(df) / df.patient_id.nunique():.2f}')\n"
        "X, y = df[['a', 'b', 'c']], df['y']\n"
        "X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)\n"
        "rf = RandomForestClassifier(n_estimators=20, random_state=0).fit(X_train, y_train)\n"
        "acc = accuracy_score(y_test, rf.predict(X_test))\n"
        "cv = cross_val_score(RandomForestClassifier(n_estimators=5, random_state=0), X[['a']], y, cv=3)\n"
    )
    from leaklens.dynamic.confirm import confirm_file

    out = confirm_file(script, load(script), [], with_impact=True, cwd=tmp_path)
    grp = [f for f in out if f.type == "group" and "GroupShuffleSplit" in (f.impact or {}).get("note", "")]
    assert grp, [(f.type, f.impact) for f in out]
    imp = grp[0].impact
    assert imp["metric"].startswith("accuracy_score"), imp
    assert imp["value_leaky"] != 6.0
