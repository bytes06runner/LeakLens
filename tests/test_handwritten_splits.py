"""Hand-written splits in research code (EVAL_CHANGES.md #13): random masks, entity attributes of items,
per-entity splits, and functions a module defines but never calls."""

from __future__ import annotations

import textwrap

from leaklens.ingest import load
from leaklens.static.analyzer import analyze


def scan(tmp_path, code: str, min_conf: str = "medium") -> list[tuple[str, str, int, str]]:
    p = tmp_path / "case.py"
    p.write_text(textwrap.dedent(code).strip("\n") + "\n")
    findings, _ = analyze(load(p))
    order = {"low": 0, "medium": 1, "high": 2}
    return sorted((f.type, f.rule_id, f.line_start, f.message) for f in findings
                  if order[f.confidence] >= order[min_conf])


MASK_SPLIT = """
import numpy as np

def run(index, seed):
    rng = np.random.default_rng(seed)
    recs = index.load()
    ri, wi, y = make_windows(recs)
    u = rng.random(len(ri))
    tr, te = u < 0.8, u >= 0.8
    model = fit_windows(recs, ri[tr], wi[tr], y[tr])
    score = evaluate(model, recs, ri[te], wi[te], y[te])
    subj = [recs[k].subject for k in ri[te]]
    return score
"""


def test_random_mask_split_over_items_with_an_entity_attribute(tmp_path):
    out = scan(tmp_path, MASK_SPLIT)
    assert [(t, r, ln) for t, r, ln, _ in out] == [("group", "LL-GRP-001", 8)]
    assert "`subject`" in out[0][3]


def test_random_mask_split_without_entity_evidence_is_not_a_group_finding(tmp_path):
    code = MASK_SPLIT.replace("    subj = [recs[k].subject for k in ri[te]]\n", "")
    assert scan(tmp_path, code, "low") == []


def test_complement_mask_with_invert(tmp_path):
    code = MASK_SPLIT.replace("tr, te = u < 0.8, u >= 0.8", "tr = u < 0.8\n    te = ~tr")
    out = scan(tmp_path, code)
    assert [t for t, *_ in out] == ["group"]


PER_SUBJECT = """
def split(recs):
    train, test = [], []
    by_subject = {}
    for r in recs:
        by_subject.setdefault(r.subject, []).append(r)
    for s, rs in by_subject.items():
        rs = sorted(rs, key=lambda r: r.name)
        cut = len(rs) // 2
        train += rs[:cut]
        test += rs[cut:]
    return train, test
"""


def test_per_entity_split_puts_every_entity_on_both_sides(tmp_path):
    out = scan(tmp_path, PER_SUBJECT)
    assert [(t, r, ln) for t, r, ln, _ in out] == [("group", "LL-GRP-005", 9)]
    assert "`train`" in out[0][3] and "`test`" in out[0][3].split("rest to")[1]


def test_leave_one_entity_out_is_not_flagged(tmp_path):
    code = """
    def lopo(recs, held_out):
        train = [r for r in recs if r.subject != held_out]
        test = [r for r in recs if r.subject == held_out]
        return train, test
    """
    assert scan(tmp_path, code, "low") == []


def test_pandas_groupby_per_patient_split(tmp_path):
    code = """
    import pandas as pd
    df = pd.read_csv("visits.csv")
    tr, te = [], []
    for pid, g in df.groupby("patient_id"):
        g = g.sort_values("visit")
        tr.append(g.iloc[:-1])
        te.append(g.iloc[-1:])
    """
    out = scan(tmp_path, code)
    assert [(t, r) for t, r, *_ in out] == [("group", "LL-GRP-005")]


def test_uncalled_function_is_analysed(tmp_path):
    code = """
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    def experiment(path):
        df = pd.read_csv(path)
        X, y = df.drop(columns="y"), df["y"]
        X = StandardScaler().fit_transform(X)
        X_tr, X_te, y_tr, y_te = train_test_split(X, y)
        return X_tr, X_te
    """
    assert [t for t, *_ in scan(tmp_path, code)] == ["preprocessing"]
