"""Group-leakage evidence found while analysing real notebooks (EVAL_CHANGES.md #17): overlapping entity lists
(LL-GRP-006), rows pooled from several source files without the file being kept (LL-GRP-007), weak identifiers
that the code itself treats as repeated keys, and the location of multi-test findings."""

from __future__ import annotations

import textwrap

from leaklens.ingest import load
from leaklens.static.analyzer import analyze


def scan(tmp_path, code: str, min_conf: str = "medium") -> list[tuple[str, str, str, int, int, str]]:
    p = tmp_path / "case.py"
    p.write_text(textwrap.dedent(code).strip("\n") + "\n")
    findings, _ = analyze(load(p))
    order = {"low": 0, "medium": 1, "high": 2}
    return sorted(
        (f.type, f.rule_id, f.confidence, f.line_start, f.line_end, f.message)
        for f in findings
        if order[f.confidence] >= order[min_conf]
    )


def groups(out):
    return [(r, c, a, b) for t, r, c, a, b, _ in out if t == "group"]


# ------------------------------------------------------------------ LL-GRP-006


def test_overlapping_subject_lists_are_a_group_leak(tmp_path):
    out = scan(
        tmp_path,
        """
        class Config:
            TRAIN_SUBJECTS = list(range(1, 110))
            TEST_SUBJECTS = list(range(51, 110))
        """,
    )
    assert groups(out) == [("LL-GRP-006", "high", 2, 3)]
    assert "share 59 of 59 values of `subject`" in out[0][5]


def test_disjoint_lists_and_non_entity_lists_are_not(tmp_path):
    out = scan(
        tmp_path,
        """
        ALL_SUBJECTS = list(range(1, 110))
        train_subject_ids = ALL_SUBJECTS[:80]
        test_subject_ids = ALL_SUBJECTS[80:]
        train_features = ["a", "b"]
        test_features = ["a", "b"]
        """,
    )
    assert groups(out) == []


# ------------------------------------------------------------------ LL-GRP-007

POOLED_INNER_LOOP = """
import os
import numpy as np
import scipy.io as sio
from sklearn.model_selection import train_test_split

def load_session(path):
    data, labels = [], []
    if not os.path.exists(path):
        return [], []
    for f in sorted(os.listdir(path)):
        m = sio.loadmat(os.path.join(path, f))
        for k in range(1, 25):
            data.append(m[f"trial{k}"])
            labels.append(k % 4)
    return data, labels

data, labels = load_session("eeg")
X = np.array([np.mean(t, axis=1).ravel() for t in data])
X_tr, X_te, y_tr, y_te = train_test_split(X, np.array(labels), test_size=0.2)
X_va, X_te2, y_va, y_te2 = train_test_split(X_te, y_te, test_size=0.5)
"""


def test_several_trials_per_file_pooled_and_split_at_random(tmp_path):
    out = scan(tmp_path, POOLED_INNER_LOOP)
    assert groups(out) == [("LL-GRP-007", "medium", 19, 19)]  # the re-split of the test side adds nothing


def test_blocks_per_file_stacked_with_vstack(tmp_path):
    out = scan(
        tmp_path,
        """
        import os
        import numpy as np
        import scipy.io as sio
        from sklearn.model_selection import StratifiedKFold, cross_val_score
        from sklearn.svm import LinearSVC

        X_list, y_list = [], []
        for i in range(1, 16):
            eeg = sio.loadmat(os.path.join("data", f"m{i}.mat"))["eeg"]
            feat = windows(eeg)
            X_list.append(feat)
            y_list.extend([1] * feat.shape[0])
        X = np.vstack(X_list)
        y = np.array(y_list)
        print(cross_val_score(LinearSVC(), X, y, cv=StratifiedKFold(10, shuffle=True)))
        """,
    )
    assert [r for r, *_ in groups(out)] == ["LL-GRP-007"]


def test_one_row_per_file_is_not_pooled(tmp_path):
    out = scan(
        tmp_path,
        """
        import os
        import numpy as np
        from PIL import Image
        from sklearn.model_selection import train_test_split

        images, labels = [], []
        for cls in os.listdir("train"):
            for f in os.listdir(os.path.join("train", cls)):
                images.append(np.asarray(Image.open(os.path.join("train", cls, f))))
                labels.append(cls)
        X = np.array(images)
        X_tr, X_te, y_tr, y_te = train_test_split(X, labels, test_size=0.2)
        """,
    )
    assert groups(out) == []


def test_pooled_rows_with_a_time_order_are_left_to_the_temporal_rule(tmp_path):
    out = scan(
        tmp_path,
        """
        import glob
        import pandas as pd
        from sklearn.model_selection import train_test_split

        frames = []
        for path in glob.glob("sales_*.csv"):
            frames.append(pd.read_csv(path, parse_dates=["date"]))
        df = pd.concat(frames).sort_values("date")
        X_tr, X_te, y_tr, y_te = train_test_split(df[["price"]], df["units"], test_size=0.2)
        """,
    )
    assert [r for r, *_ in groups(out)] == []


# ------------------------------------------------------------------ repeated weak keys


def test_weak_id_used_as_a_per_row_groupby_key_gets_medium_confidence(tmp_path):
    code = """
    import pandas as pd
    from sklearn.model_selection import train_test_split

    df = pd.read_csv("engines.csv")
    df["RUL"] = df.groupby("id")["cycle"].transform("max") - df["cycle"]
    X_tr, X_te, y_tr, y_te = train_test_split(df[["s1", "s2", "id"]], df["RUL"], test_size=0.2)
    """
    out = scan(tmp_path, code.replace(', "id"]]', "]]"))
    assert groups(out) == [("LL-GRP-001", "medium", 6, 6)]
    assert "`id`" in out[0][5]


def test_weak_id_without_per_row_groupby_stays_low(tmp_path):
    out = scan(
        tmp_path,
        """
        import pandas as pd
        from sklearn.model_selection import train_test_split

        df = pd.read_csv("engines.csv")
        X_tr, X_te, y_tr, y_te = train_test_split(df[["s1", "s2"]], df["id"] > 3, test_size=0.2)
        print(df["id"].nunique())
        """,
    )
    assert groups(out) == []


# ------------------------------------------------------------------ multi-test location


def test_multi_test_finding_spans_scoring_and_selection(tmp_path):
    out = scan(
        tmp_path,
        """
        from sklearn.model_selection import train_test_split
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.metrics import accuracy_score

        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2)
        scores = []
        for k in [1, 3, 5, 7]:
            m = KNeighborsClassifier(k).fit(X_tr, y_tr)
            scores.append(accuracy_score(y_te, m.predict(X_te)))

        best = max(scores)
        print(best)
        """,
    )
    mt = [(r, a, b) for t, r, _, a, b, _ in out if t == "multi_test"]
    assert mt == [("LL-MUL-001", 9, 11)]
