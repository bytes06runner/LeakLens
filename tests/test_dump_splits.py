"""--dump-splits writes each fold's tables for baseline tools, keeps entity columns, and never exports the label."""

import json
import subprocess
import sys

import pandas as pd

SCRIPT = """
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
rng = np.random.default_rng(0)
df = pd.DataFrame({"patient_id": np.repeat(np.arange(20), 5), "x": rng.normal(size=100)})
df["y"] = (df["patient_id"] % 2).astype(int)
X, y = df[["x"]], df["y"]
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
print("acc:", LogisticRegression().fit(X_train, y_train).score(X_test, y_test))
"""


def test_dump_splits(tmp_path):
    (tmp_path / "s.py").write_text(SCRIPT)
    out, dump = tmp_path / "ev.json", tmp_path / "splits"
    p = subprocess.run([sys.executable, "-m", "leaklens.dynamic.runner", str(tmp_path / "s.py"), "--out", str(out),
                        "--dump-splits", str(dump)], cwd=tmp_path, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    idx = json.loads(out.read_text())["dump_index"]
    assert len(idx) == 1 and idx[0]["has_target"]
    tr = pd.read_csv(dump / f"{idx[0]['base']}_train.csv")
    te = pd.read_csv(dump / f"{idx[0]['base']}_test.csv")
    assert len(tr) + len(te) == 100
    assert "patient_id" in tr.columns and "__target__" in tr.columns
    assert "y" not in tr.columns  # the label column must not reappear as a feature


def test_no_dump_by_default(tmp_path):
    (tmp_path / "s.py").write_text(SCRIPT)
    out = tmp_path / "ev.json"
    subprocess.run([sys.executable, "-m", "leaklens.dynamic.runner", str(tmp_path / "s.py"), "--out", str(out)],
                   cwd=tmp_path, check=True, capture_output=True)
    assert json.loads(out.read_text())["dump_index"] == []
    assert not (tmp_path / "splits").exists()
