"""Static rules: every rule has positive and negative cases (CLAUDE.md Phase 4).

The taxonomy fixtures (tests/fixtures/taxonomy) mark each leaking line with `# LEAK: <type>`. The inline cases
below are hand-written patterns, several of them modelled on what real notebooks do. None is a benchmark item.
"""

import json
import textwrap
from pathlib import Path

import jsonschema
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from leaklens.ingest import load
from leaklens.static.analyzer import analyze, entity_strength, time_name

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = sorted((ROOT / "tests" / "fixtures" / "taxonomy").glob("*.py"))
SCHEMA = json.loads((ROOT / "src" / "leaklens" / "report" / "finding.schema.json").read_text())

HEAD = """
import numpy as np
import pandas as pd
from sklearn.model_selection import (train_test_split, cross_val_score, KFold, StratifiedKFold, GroupKFold,
                                     GroupShuffleSplit, TimeSeriesSplit, GridSearchCV, ShuffleSplit)
from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.utils import resample
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
"""


def scan(tmp_path, code: str, min_conf: str = "medium"):
    """(type, line) of every finding at or above min_conf; lines are relative to the first line of `code`."""
    body = textwrap.dedent(code).strip("\n")
    p = tmp_path / "case.py"
    p.write_text(HEAD + body + "\n")
    findings, _ = analyze(load(p))
    order = {"low": 0, "medium": 1, "high": 2}
    offset = HEAD.count("\n")
    for f in findings:
        jsonschema.validate(f.to_dict(), SCHEMA)
    return sorted((f.type, f.flat_line_start - offset) for f in findings if order[f.confidence] >= order[min_conf])


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_taxonomy_fixture(path):
    lines = path.read_text().splitlines()
    want = sorted((ln.split("# LEAK: ")[1].strip(), i) for i, ln in enumerate(lines, 1) if "# LEAK: " in ln)
    findings, _ = analyze(load(path))
    got = sorted((f.type, f.line_start) for f in findings if f.confidence != "low")
    assert got == want


# --------------------------------------------------------------------------- preprocessing

def test_scaler_fit_before_split(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X, y = df.drop(columns=["y"]), df["y"]
        X = StandardScaler().fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X, y)
        print(LogisticRegression().fit(X_train, y_train).score(X_test, y_test))
    """) == [("preprocessing", 3)]


def test_scaler_fit_on_all_rows_after_split(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X, y = df.drop(columns=["y"]), df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y)
        scaler = StandardScaler()
        scaler.fit(X)
        X_train = scaler.transform(X_train)
        X_test = scaler.transform(X_test)
        print(LogisticRegression().fit(X_train, y_train).score(X_test, y_test))
    """) == [("preprocessing", 5)]


def test_scaler_fit_on_training_rows_is_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X, y = df.drop(columns=["y"]), df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y)
        scaler = StandardScaler().fit(X_train)
        X_train = scaler.transform(X_train)
        X_test = scaler.transform(X_test)
        print(LogisticRegression().fit(X_train, y_train).score(X_test, y_test))
    """, "low") == []


def test_pipeline_inside_cv_is_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X, y = df.drop(columns=["y"]), df["y"]
        model = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=5), LogisticRegression())
        print(cross_val_score(model, X, y, cv=5).mean())
    """, "low") == []


def test_fillna_with_statistic_of_all_rows(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        df["age"] = df["age"].fillna(df["age"].median())
        X, y = df.drop("y", axis=1), df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y)
    """) == [("preprocessing", 2)]


def test_inplace_fillna_and_manual_minmax(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        df["age"].fillna(df["age"].mean(), inplace=True)
        df["fare"] = (df["fare"] - df["fare"].min()) / (df["fare"].max() - df["fare"].min())
        X, y = df.drop("y", axis=1), df["y"]
        print(cross_val_score(LogisticRegression(), X, y).mean())
    """) == [("preprocessing", 2), ("preprocessing", 3)]


def test_statistic_of_training_rows_is_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X, y = df.drop("y", axis=1), df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y)
        m = X_train["age"].mean()
        X_train["age"] = X_train["age"].fillna(m)
        X_test["age"] = X_test["age"].fillna(m)
        print(LogisticRegression().fit(X_train, y_train).score(X_test, y_test))
    """, "low") == []


def test_row_wise_statistic_is_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        df["row_mean"] = df[["a", "b"]].mean(axis=1)
        X, y = df.drop("y", axis=1), df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y)
    """, "low") == []


def test_supervised_selection_and_target_encoding(tmp_path):
    out = scan(tmp_path, """
        df = pd.read_csv("d.csv")
        df["city_rate"] = df.groupby("city")["y"].transform("mean")
        X, y = df.drop("y", axis=1), df["y"]
        X = SelectKBest(f_classif, k=5).fit_transform(X, y)
        X_train, X_test, y_train, y_test = train_test_split(X, y)
    """)
    assert out == [("preprocessing", 2), ("preprocessing", 4)]


def test_one_hot_encoding_is_low_confidence_only(tmp_path):
    code = """
        df = pd.read_csv("d.csv")
        X, y = df[["colour"]], df["y"]
        X = OneHotEncoder().fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X, y)
    """
    assert scan(tmp_path, code) == []
    assert scan(tmp_path, code, "low") == [("preprocessing", 3)]


# --------------------------------------------------------------------------- overlap

def test_smote_before_split(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X, y = df.drop("y", axis=1), df["y"]
        X_res, y_res = SMOTE().fit_resample(X, y)
        X_train, X_test, y_train, y_test = train_test_split(X_res, y_res)
    """) == [("overlap", 3)]


def test_smote_on_training_rows_is_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X, y = df.drop("y", axis=1), df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y)
        X_train, y_train = SMOTE().fit_resample(X_train, y_train)
        print(RandomForestClassifier().fit(X_train, y_train).score(X_test, y_test))
    """, "low") == []


def test_undersampling_before_split_is_not_overlap(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X, y = df.drop("y", axis=1), df["y"]
        X_res, y_res = RandomUnderSampler().fit_resample(X, y)
        X_train, X_test, y_train, y_test = train_test_split(X_res, y_res)
    """, "low") == []


def test_upsampling_with_resample_before_split(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        minority = resample(df[df.y == 1], replace=True, n_samples=1000)
        df = pd.concat([df[df.y == 0], minority])
        X_train, X_test, y_train, y_test = train_test_split(df.drop("y", axis=1), df["y"])
    """) == [("overlap", 2)]


def test_downsampling_by_concat_of_subsets_is_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        df = pd.concat([df[df.y == 0].head(500), df[df.y == 1]])
        X_train, X_test, y_train, y_test = train_test_split(df.drop("y", axis=1), df["y"])
    """, "low") == []


def test_model_fitted_on_all_rows_then_scored_on_test(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X, y = df.drop("y", axis=1), df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y)
        model = RandomForestClassifier()
        model.fit(X, y)
        print(accuracy_score(y_test, model.predict(X_test)))
    """) == [("overlap", 5)]


def test_training_score_and_final_refit_are_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X, y = df.drop("y", axis=1), df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y)
        model = RandomForestClassifier().fit(X_train, y_train)
        print(model.score(X_train, y_train), model.score(X_test, y_test))
        final = RandomForestClassifier().fit(X, y)
        submission = final.predict(pd.read_csv("unlabelled.csv"))
    """, "low") == []


# --------------------------------------------------------------------------- multi-test

def test_models_compared_on_the_test_set(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X_train, X_test, y_train, y_test = train_test_split(df.drop("y", axis=1), df["y"])
        scores = {}
        for name, model in {"lr": LogisticRegression(), "rf": RandomForestClassifier()}.items():
            model.fit(X_train, y_train)
            scores[name] = accuracy_score(y_test, model.predict(X_test))
        best = max(scores, key=scores.get)
        print(best, scores[best])
    """) == [("multi_test", 6)]


def test_best_score_so_far_comparison(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X_train, X_test, y_train, y_test = train_test_split(df.drop("y", axis=1), df["y"])
        best = 0
        for depth in range(1, 10):
            model = RandomForestClassifier(max_depth=depth).fit(X_train, y_train)
            acc = model.score(X_test, y_test)
            if acc > best:
                best = acc
        print(best)
    """) == [("multi_test", 6)]


def test_selection_on_a_validation_split_is_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X_train, X_test, y_train, y_test = train_test_split(df.drop("y", axis=1), df["y"])
        X_tr, X_val, y_tr, y_val = train_test_split(X_train, y_train)
        scores = {}
        for depth in (2, 4, 8):
            scores[depth] = RandomForestClassifier(max_depth=depth).fit(X_tr, y_tr).score(X_val, y_val)
        best = max(scores, key=scores.get)
        print(RandomForestClassifier(max_depth=best).fit(X_train, y_train).score(X_test, y_test))
    """, "low") == []


def test_loop_without_selection_is_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X_train, X_test, y_train, y_test = train_test_split(df.drop("y", axis=1), df["y"])
        for model in (LogisticRegression(), RandomForestClassifier()):
            print(model.fit(X_train, y_train).score(X_test, y_test))
    """, "low") == []


def test_grid_search_on_training_rows_is_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X_train, X_test, y_train, y_test = train_test_split(df.drop("y", axis=1), df["y"])
        search = GridSearchCV(RandomForestClassifier(), {"max_depth": [2, 4]}, cv=5).fit(X_train, y_train)
        print(search.score(X_test, y_test))
    """, "low") == []


def test_one_finding_per_evaluation_site(tmp_path):
    out = scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X_train, X_test, y_train, y_test = train_test_split(df.drop("y", axis=1), df["y"])
        rows = []
        for model in (LogisticRegression(), RandomForestClassifier()):
            pred = model.fit(X_train, y_train).predict(X_test)
            acc = accuracy_score(y_test, pred)
            auc = roc_auc_score(y_test, pred)
            rows.append({"acc": acc, "auc": auc})
        print(pd.DataFrame(rows).sort_values("acc"))
    """)
    assert out == [("multi_test", 6)]


# --------------------------------------------------------------------------- group

def test_random_split_with_patient_id(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("visits.csv")
        X = df.drop(columns=["patient_id", "outcome"])
        y = df["outcome"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
    """) == [("group", 4)]


@pytest.mark.parametrize("split", [
    "print(cross_val_score(RandomForestClassifier(), X, y, cv=5).mean())",
    "print(cross_val_score(RandomForestClassifier(), X, y, cv=KFold(5, shuffle=True)).mean())",
    "print(cross_val_score(RandomForestClassifier(), X, y, cv=StratifiedKFold(5)).mean())",
    "folds = list(ShuffleSplit(n_splits=3).split(X, y))",
    "search = GridSearchCV(RandomForestClassifier(), {'max_depth': [2, 3]}).fit(X, y)",
])
def test_row_level_cv_with_entity_column(tmp_path, split):
    assert scan(tmp_path, f"""
        df = pd.read_csv("eeg_windows.csv")
        X = df.drop(columns=["subject", "label"])
        y = df["label"]
        {split}
    """) == [("group", 4)]


@pytest.mark.parametrize("split", [
    "print(cross_val_score(RandomForestClassifier(), X, y, cv=GroupKFold(5), groups=df['subject']).mean())",
    "tr, te = next(GroupShuffleSplit(n_splits=1).split(X, y, groups=df['subject']))",
])
def test_group_aware_split_is_clean(tmp_path, split):
    assert scan(tmp_path, f"""
        df = pd.read_csv("eeg_windows.csv")
        X = df.drop(columns=["subject", "label"])
        y = df["label"]
        {split}
    """, "low") == []


def test_split_of_unique_entities_is_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("visits.csv")
        train_ids, test_ids = train_test_split(df["patient_id"].unique(), random_state=0)
        train, test = df[df.patient_id.isin(train_ids)], df[df.patient_id.isin(test_ids)]
    """, "low") == []


def test_one_row_per_entity_after_aggregation_is_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("visits.csv")
        agg = df.groupby("patient_id").mean()
        X_train, X_test, y_train, y_test = train_test_split(agg.drop(columns=["outcome"]), agg["outcome"])
    """, "low") == []


def test_descriptive_and_categorical_names_are_not_entities(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        df = pd.get_dummies(df, columns=["device"])
        X = df.drop(columns=["patient_age", "y"])
        X_train, X_test, y_train, y_test = train_test_split(X, df["y"])
    """) == []


def test_weak_identifier_is_low_confidence(tmp_path):
    code = """
        df = pd.read_csv("churn.csv")
        X = df.drop(columns=["customer_id", "churn"])
        X_train, X_test, y_train, y_test = train_test_split(X, df["churn"])
    """
    assert scan(tmp_path, code) == []
    assert scan(tmp_path, code, "low") == [("group", 3)]


def test_file_path_entity_one_row_per_file(tmp_path):
    assert scan(tmp_path, """
        import glob, os
        rows = []
        for path in glob.glob("scans/*/*.png"):
            rows.append({"patient": os.path.basename(os.path.dirname(path)), "f": len(path), "label": 1})
        df = pd.DataFrame(rows)
        print(cross_val_score(RandomForestClassifier(), df[["f"]], df["label"], cv=5).mean())
    """) == [("group", 6)]


def test_folder_name_used_as_label_is_not_an_entity(tmp_path):
    assert scan(tmp_path, """
        import glob, os
        feats, labels = [], []
        for path in glob.glob("images/*/*.png"):
            feats.append([len(path)])
            labels.append(os.path.basename(os.path.dirname(path)))
        X, y = np.array(feats), np.array(labels)
        print(cross_val_score(RandomForestClassifier(), X, y, cv=5).mean())
    """, "low") == []


def test_inline_suppression(tmp_path):
    p = tmp_path / "s.py"
    p.write_text(HEAD + 'df = pd.read_csv("v.csv")\nX = df.drop(columns=["patient_id", "y"])\n'
                 'a, b, c, d = train_test_split(X, df["y"])  # leaklens: ignore[group] -- within-patient model\n')
    findings, _ = analyze(load(p))
    assert [f.type for f in findings] == ["group"]
    assert findings[0].suppressed == {"by": "inline", "reason": "within-patient model"}


# --------------------------------------------------------------------------- temporal

TS = """
    df = pd.read_csv("load.csv", parse_dates=["ts"]).sort_values("ts")
    df["lag1"] = df["load"].shift(1)
    df["target"] = df["load"].shift(-1)
    df = df.dropna()
    X, y = df[["load", "lag1"]], df["target"]
"""


@pytest.mark.parametrize("split", [
    "a, b, c, d = train_test_split(X, y, test_size=0.2)",
    "a, b, c, d = train_test_split(X, y, shuffle=True)",
    "print(cross_val_score(Ridge(), X, y, cv=5))",
    "print(cross_val_score(Ridge(), X, y, cv=KFold(5)))",
    "print(cross_val_score(Ridge(), X, y, cv=KFold(5, shuffle=True)))",
])
def test_non_chronological_split_of_time_series(tmp_path, split):
    assert scan(tmp_path, TS + "    " + split) == [("temporal", 6)]


@pytest.mark.parametrize("split", [
    "a, b, c, d = train_test_split(X, y, test_size=0.2, shuffle=False)",
    "print(cross_val_score(Ridge(), X, y, cv=TimeSeriesSplit(5)))",
    "n = int(len(X) * 0.8); a, b = X.iloc[:n], X.iloc[n:]; print(Ridge().fit(a, y.iloc[:n]).score(b, y.iloc[n:]))",
])
def test_chronological_split_is_clean(tmp_path, split):
    assert scan(tmp_path, TS + "    " + split, "low") == []


def test_shuffle_then_positional_split(tmp_path):
    assert scan(tmp_path, TS + """
    df = df.sample(frac=1, random_state=0)
    X, y = df[["load", "lag1"]], df["target"]
    n = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:n], X.iloc[n:]
    """, "low") == []  # documented limitation: a manual positional split is not reported as a split point


def test_manual_random_sample_split(tmp_path):
    assert scan(tmp_path, TS + """
    test_idx = X.sample(frac=0.2, random_state=0).index
    X_train, X_test = X.drop(test_idx), X.loc[test_idx]
    """) == [("temporal", 7)]  # line 6 is blank


@pytest.mark.parametrize("feature,line", [
    ('df["f"] = df["load"].shift(-2)', 3),
    ('df["f"] = df["load"].rolling(5, center=True).mean()', 3),
    ('df["f"] = df["load"][::-1].rolling(5).mean()[::-1]', 3),
    ('df["f"] = df["load"].bfill()', 3),
    ('df["f"] = df["load"].fillna(method="bfill")', 3),
    ('df["f"] = df.groupby("meter")["load"].shift(-1)', 3),
])
def test_forward_looking_feature(tmp_path, feature, line):
    assert scan(tmp_path, f"""
        df = pd.read_csv("load.csv", parse_dates=["ts"]).sort_values("ts")
        df["target"] = df["load"].shift(-1)
        {feature}
        df = df.dropna()
        X, y = df[["load", "f"]], df["target"]
        a, b, c, d = train_test_split(X, y, shuffle=False)
    """) == [("temporal", line)]


def test_backward_looking_features_and_shifted_target_are_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("load.csv", parse_dates=["ts"]).sort_values("ts")
        df["target"] = df["load"].shift(-1)
        df["lag"] = df["load"].shift(1)
        df["roll"] = df["load"].rolling(5).mean()
        df["filled"] = df["load"].ffill()
        df = df.dropna()
        X, y = df.drop(columns=["target", "ts"]), df["target"]
        a, b, c, d = train_test_split(X, y, shuffle=False)
    """, "low") == []


def test_whole_series_scaling_is_reported_as_temporal(tmp_path):
    assert scan(tmp_path, TS + """
    X = StandardScaler().fit_transform(X)
    a, b, c, d = train_test_split(X, y, shuffle=False)
    """) == [("temporal", 7)]  # line 6 is blank


def test_date_column_without_order_evidence_is_low_confidence(tmp_path):
    code = """
        df = pd.read_csv("sales.csv", parse_dates=["sold_on"])
        X_train, X_test, y_train, y_test = train_test_split(df.drop(columns=["price"]), df["price"])
    """
    assert scan(tmp_path, code) == []
    assert scan(tmp_path, code, "low") == [("temporal", 2)]


def test_panel_forecast_is_temporal_not_group(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("sensors.csv", parse_dates=["ts"]).sort_values(["ts", "device_id"])
        df["lag"] = df.groupby("device_id")["temp"].shift(1)
        df["target"] = df.groupby("device_id")["temp"].shift(-1)
        df = df.dropna()
        print(cross_val_score(Ridge(), df[["temp", "lag"]], df["target"], cv=5))
    """, "low") == [("temporal", 5)]


# --------------------------------------------------------------------------- target-derived

def test_feature_computed_from_target(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        df["refund"] = df["churned"] * df["monthly"]
        X, y = df.drop(columns=["churned"]), df["churned"]
        X_train, X_test, y_train, y_test = train_test_split(X, y)
    """) == [("target_derived", 2)]


def test_target_thresholded_from_a_feature_that_stays(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        df["high"] = (df["price"] > 100).astype(int)
        X, y = df.drop(columns=["high"]), df["high"]
        X_train, X_test, y_train, y_test = train_test_split(X, y)
    """) == [("target_derived", 2)]


def test_lag_of_target_and_excluded_derivation_are_clean(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        df["y_lag"] = df["y"].shift(1)
        df["helper"] = df["y"] * 2
        X, y = df[["a", "y_lag"]], df["y"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, shuffle=False)
    """) == []


# --------------------------------------------------------------------------- data flow

def test_flow_through_user_function(tmp_path):
    assert scan(tmp_path, """
        def prepare(frame):
            frame = frame.copy()
            frame[["a", "b"]] = MinMaxScaler().fit_transform(frame[["a", "b"]])
            return frame

        def evaluate(X, y):
            X_train, X_test, y_train, y_test = train_test_split(X, y)
            return LogisticRegression().fit(X_train, y_train).score(X_test, y_test)

        df = prepare(pd.read_csv("d.csv"))
        print(evaluate(df.drop(columns=["y"]), df["y"]))
    """) == [("preprocessing", 3)]


def test_unresolved_variables_are_still_tracked(tmp_path):
    assert scan(tmp_path, """
        X = StandardScaler().fit_transform(X_from_another_cell)
        X_train, X_test, y_train, y_test = train_test_split(X, y_from_another_cell)
    """) == [("preprocessing", 1)]


def test_manual_cv_loop(tmp_path):
    assert scan(tmp_path, """
        df = pd.read_csv("d.csv")
        X, y = df.drop(columns=["participant_id", "y"]), df["y"]
        scores = []
        for train_idx, test_idx in KFold(5, shuffle=True).split(X):
            model = LogisticRegression().fit(X.iloc[train_idx], y.iloc[train_idx])
            scores.append(model.score(X.iloc[test_idx], y.iloc[test_idx]))
        print(np.mean(scores))
    """) == [("group", 4)]


def test_notebook_cells_and_line_map(tmp_path):
    nb = {"cells": [
        {"cell_type": "markdown", "source": ["# title"]},
        {"cell_type": "code", "execution_count": 1, "source": ["%matplotlib inline\n", "import pandas as pd\n",
            "from sklearn.model_selection import train_test_split\n",
                                                                "from sklearn.preprocessing import StandardScaler"]},
        {"cell_type": "code", "execution_count": 2, "source": ["df = pd.read_csv('d.csv')\n", "!ls\n",
            "X = StandardScaler().fit_transform(df.drop(columns=['y']))"]},
        {"cell_type": "code", "execution_count": 3, "source": ["%%bash\n", "echo hi"]},
        {"cell_type": "code", "execution_count": 4, "source": ["a, b, c, d = train_test_split(X, df['y'])"]},
    ], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    p = tmp_path / "n.ipynb"
    p.write_text(json.dumps(nb))
    src = load(p)
    assert src.order_used == "execution"
    assert src.skipped_cells == [{"cell": 3, "reason": "cell magic changes the language"}]
    findings, _ = analyze(src)
    assert [(f.type, f.cell, f.line_start, f.flat_line_start) for f in findings] == [("preprocessing", 2, 3, 7)]


def test_notebook_falls_back_to_cell_order(tmp_path):
    nb = {"cells": [{"cell_type": "code", "execution_count": None, "source": ["x = 1"]},
                    {"cell_type": "code", "execution_count": 5, "source": ["y = 2"]}],
          "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    p = tmp_path / "n.ipynb"
    p.write_text(json.dumps(nb))
    assert load(p).order_used == "cell"


def test_unparseable_file_is_reported_not_skipped(tmp_path):
    p = tmp_path / "py2.py"
    p.write_text("print 'python 2'\n")
    src = load(p)
    assert src.status == "unanalysable" and "does not parse" in src.reason


# --------------------------------------------------------------------------- names

@pytest.mark.parametrize("name,expected", [
    ("patient_id", "strong"), ("PatientID", "strong"), ("subject", "strong"), ("user_id", "strong"),
    ("speaker_id", "strong"), ("device_id", "strong"), ("device", "weak"), ("customer_id", "weak"), ("id", "weak"),
    ("patient_age", None), ("device_type", None), ("user_rating", None), ("price", None), ("label", None),
])
def test_entity_name_evidence(name, expected):
    assert entity_strength(name) == expected


@pytest.mark.parametrize("name,expected", [("date", True), ("order_date", True), ("timestamp", True), ("year", True),
                                           ("year_built", False), ("time_on_site", False), ("price", False)])
def test_time_name_evidence(name, expected):
    assert time_name(name) is expected


# --------------------------------------------------------------------------- robustness

_FRAGMENTS = [
    "df = pd.read_csv('a.csv')", "X = df.drop(columns=['y'])", "y = df['y']", "X = X.fillna(X.mean())",
    "X_train, X_test, y_train, y_test = train_test_split(X, y)", "m = LogisticRegression()", "m.fit(X_train, y_train)",
    "s = m.score(X_test, y_test)", "X = StandardScaler().fit_transform(X)", "df['f'] = df['y'].shift(-1)",
    "for a, b in KFold(3).split(X):\n    pass", "scores = {}", "scores[1] = s", "best = max(scores)", "X = X[::-1]",
    "df = df.sort_values('date')", "g = df.groupby('user_id')", "df['m'] = g['v'].transform('mean')", "del X",
    "X, y = y, X", "def f(a, b=1):\n    return a", "X = f(X)", "class C:\n    pass", "X = [X, y] * 3",
    "y = X.loc[:, 'a']",
    "X = pd.concat([X, X])", "lambda q: q", "X = df.iloc[:10]", "y = df.iloc[10:]", "import os", "x = 1 if y else 2",
    "with open('f') as fh:\n    pass", "try:\n    X = X + 1\nexcept Exception:\n    pass", "X = {**{}}",
    "X = X[y == 1]",
    "print(cross_val_score(m, X, y, cv=5).mean())", "X.fillna(0, inplace=True)", "df[['a', 'b']] = 0", "y = -y",
]


@settings(max_examples=150, deadline=None)
@given(st.lists(st.sampled_from(_FRAGMENTS), min_size=1, max_size=25))
def test_any_statement_order_is_analysed_without_error(tmp_path_factory, stmts):
    """The analyser is total: any ordering of valid statements gives schema-valid findings, never an exception."""
    p = tmp_path_factory.mktemp("prop") / "g.py"
    p.write_text(HEAD + "\n".join(stmts) + "\n")
    src = load(p)
    assert src.status == "ok"
    import leaklens.static.analyzer as an

    old, an.DEBUG = an.DEBUG, True  # surface internal errors instead of swallowing them
    try:
        findings, truncated = analyze(src)
    finally:
        an.DEBUG = old
    assert not truncated
    n = src.flat.count("\n") + 1
    for f in findings:
        jsonschema.validate(f.to_dict(), SCHEMA)
        assert 1 <= f.flat_line_start <= f.flat_line_end <= n


@settings(max_examples=60, deadline=None)
@given(st.lists(st.sampled_from(_FRAGMENTS), min_size=1, max_size=20))
def test_analysis_is_deterministic(tmp_path_factory, stmts):
    p = tmp_path_factory.mktemp("det") / "g.py"
    p.write_text(HEAD + "\n".join(stmts) + "\n")
    a = [f.to_dict() for f in analyze(load(p))[0]]
    b = [f.to_dict() for f in analyze(load(p))[0]]
    assert a == b
