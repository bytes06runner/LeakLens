"""The matching rule and the metrics of EVAL_PROTOCOL.md, checked on hand-made cases."""

from leaklens.evaluation.scoring import Label, Pred, aggregate, bootstrap, counts, match_item, prf, summarise


def lab(item="a", type_="group", alts=(), cell=None, s=10, e=11, cat="group"):
    return Label(item, type_, tuple(alts), cell, s, e, cat)


def test_match_needs_same_type_cell_and_overlapping_lines():
    label = lab()
    assert match_item([Pred("a", "group", None, 11, 11)], [label])[0]
    assert not match_item([Pred("a", "group", None, 12, 12)], [label])[0]  # next line: no overlap
    assert not match_item([Pred("a", "temporal", None, 10, 10)], [label])[0]  # wrong type
    assert not match_item([Pred("a", "group", 2, 10, 10)], [label])[0]  # a notebook cell is not the same place
    assert not match_item([Pred("b", "group", None, 10, 10)], [label])[0]  # other item


def test_alt_types_are_accepted_and_counted_under_the_primary_type():
    label = lab(type_="temporal", alts=("preprocessing",), s=5, e=5)
    c = counts([Pred("a", "preprocessing", None, 5, 5)], [label], ["a"])
    assert c["a"]["temporal"] == [1, 0, 0] and c["a"]["preprocessing"] == [0, 0, 0]


def test_one_prediction_matches_one_label_and_extras_are_false_positives():
    labels = [lab(s=5, e=5)]
    preds = [Pred("a", "group", None, 5, 5), Pred("a", "group", None, 5, 5), Pred("a", "overlap", None, 9, 9)]
    c = counts(preds, labels, ["a"])
    assert c["a"]["group"] == [1, 1, 0] and c["a"]["overlap"] == [0, 1, 0]


def test_low_confidence_predictions_are_excluded_at_the_primary_operating_point():
    labels = [lab(s=5, e=5)]
    preds = [Pred("a", "group", None, 5, 5, "low")]
    assert counts(preds, labels, ["a"])["a"]["group"] == [0, 0, 1]
    assert counts(preds, labels, ["a"], "low")["a"]["group"] == [1, 0, 0]


def test_clean_item_with_a_finding_is_a_false_positive_and_missing_items_count():
    c = counts([Pred("clean", "temporal", None, 3, 3)], [lab(item="leaky")], ["clean", "leaky"])
    agg = aggregate(c, ["clean", "leaky"])
    assert agg["temporal"] == (0, 1, 0) and agg["group"] == (0, 0, 1)


def test_prf_undefined_cases():
    assert prf(0, 0, 0) == (None, None, None)
    assert prf(0, 0, 3) == (None, 0.0, None)
    assert prf(2, 0, 2) == (1.0, 0.5, 2 / 3)


def test_bootstrap_interval_contains_the_point_estimate_and_is_deterministic():
    items = [f"i{k}" for k in range(40)]
    labels = [lab(item=i, s=1, e=1) for i in items]
    preds = [Pred(i, "group", None, 1, 1) for i in items[:30]] + [Pred(i, "group", None, 9, 9) for i in items[30:35]]
    rows = {r["type"]: r for r in summarise(preds, labels, items, n_boot=400)}
    g = rows["group"]
    assert (g["tp"], g["fp"], g["fn"]) == (30, 5, 10)
    lo, hi = g["recall_ci"]
    assert lo <= g["recall"] <= hi and 0.55 < lo < hi < 0.9
    assert rows["overlap"]["precision_ci"] is None  # no finding of that type: precision undefined, not 1.0
    per_item = counts(preds, labels, items)
    units = {i: [i] for i in items}
    assert bootstrap(per_item, units, 200) == bootstrap(per_item, units, 200)
