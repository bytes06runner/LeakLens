"""Mutation operators that inject one leak into a clean base pipeline.

Each operator returns a `Mutation`: slot overrides for the leaky version (leak lines end with `#!LEAK<k>`), the
imports it needs, optional overrides for the canonically *fixed* version (default: the clean base), an optional
data transform or column rename, and the ground-truth label. Fixed versions are what Phase 6 should reproduce, so
true inflation = metric(leaky) - metric(fixed), signed so that positive means "looks better than it is".

Categories:
  standard                  preprocessing / overlap / multi_test / target_derived
  group                     group leakage
  temporal_common           temporal cases that scicode-lint's patterns (ml-005, ml-006) also claim
  temporal_differentiating  temporal cases LeakLens's taxonomy claims and scicode-lint's patterns do not mention
  temporal_hard             temporal cases neither tool's rules explicitly claim
  dynamic_only              leaks invisible in code (raw duplicated records)
  trap                      clean code that looks leaky
"""

from __future__ import annotations

from dataclasses import dataclass, field

LEAK = "  #!LEAK{k}"


@dataclass
class Label:
    type: str
    subtype: str | None
    category: str
    alt_types: tuple[str, ...] = ()


@dataclass
class Mutation:
    overrides: dict[str, list[str]] = field(default_factory=dict)
    imports: list[str] = field(default_factory=list)
    fixed_overrides: dict[str, list[str]] | None = None  # None: fixed version is the clean base
    fixed_imports: list[str] = field(default_factory=list)
    data_transform: dict | None = None
    rename_col: tuple[str, str] | None = None
    labels: dict[int, Label] = field(default_factory=dict)  # leak index -> label; empty for traps


def L(line: str, k: int) -> str:
    return line + LEAK.format(k=k)


def _score_rhs(slots) -> str:
    line = next(x for x in slots["fit_eval"] if x.startswith("score = "))
    return line[len("score = "):]


def _num_cols_scale(expr: str, k: int) -> list[str]:
    return [
        'num_cols = X.select_dtypes("number").columns',
        "X = X.copy()",
        L(f"X[num_cols] = {expr}", k),
    ]


# ------------------------------------------------------------------ preprocessing


def pre_scaler(base, meta, slots, variant, k):
    cls = {"standard": "StandardScaler", "minmax": "MinMaxScaler", "robust": "RobustScaler"}[variant]
    ts = meta["family"] == "timeseries"
    label = (Label("temporal", "T2_whole_series", "temporal_hard", ("preprocessing",)) if ts
             else Label("preprocessing", "scaler", "standard"))
    return Mutation(
        overrides={"presplit": _num_cols_scale(f"{cls}().fit_transform(X[num_cols])", k)},
        imports=[f"from sklearn.preprocessing import {cls}"],
        labels={k: label},
    )


def pre_imputer(base, meta, slots, variant, k):
    return Mutation(
        overrides={"presplit": _num_cols_scale(f'SimpleImputer(strategy="{variant}").fit_transform(X[num_cols])', k)},
        imports=["from sklearn.impute import SimpleImputer"],
        labels={k: Label("preprocessing", "imputer", "standard")},
    )


def pre_pandas_stats(base, meta, slots, variant, k):
    expr = {"zscore": "(X[num_cols] - X[num_cols].mean()) / X[num_cols].std()",
            "minmax": "(X[num_cols] - X[num_cols].min()) / (X[num_cols].max() - X[num_cols].min())"}[variant]
    ts = meta["family"] == "timeseries"
    label = (Label("temporal", "T2_whole_series", "temporal_hard", ("preprocessing",)) if ts
             else Label("preprocessing", "pandas_stats", "standard"))
    return Mutation(overrides={"presplit": _num_cols_scale(expr, k)}, labels={k: label})


def pre_select(base, meta, slots, variant, k):
    kbest = {"tab_churn": 10, "tab_fraud": 5}[base]
    leaky = [
        f"selector = SelectKBest(f_classif, k={kbest})",
        L("X = pd.DataFrame(selector.fit_transform(X, y), index=X.index)", k),
    ]
    mut = Mutation(
        overrides={"presplit": leaky},
        imports=["from sklearn.feature_selection import SelectKBest, f_classif"],
        labels={k: Label("preprocessing", "supervised", "standard")},
    )
    if base == "tab_fraud":  # clean base has no selection: the fix puts it inside a pipeline
        mut.fixed_overrides = {"model": [
            "model = make_pipeline(SelectKBest(f_classif, k=5),",
            "                      GradientBoostingClassifier(n_estimators=120, max_depth=3, random_state=0))"]}
        mut.fixed_imports = ["from sklearn.feature_selection import SelectKBest, f_classif",
                             "from sklearn.pipeline import make_pipeline"]
    return mut


def pre_target_encoding(base, meta, slots, variant, k):
    cat = meta["cat_col"]
    new = f"{cat}_rate"
    lines = [L(f'df["{new}"] = df.groupby("{cat}")[TARGET].transform("mean")', k),
             f'FEATURES = FEATURES + ["{new}"]']
    if base == "tab_credit":
        lines.append(f'NUMERIC = NUMERIC + ["{new}"]')
    return Mutation(overrides={"features": lines},
                    labels={k: Label("preprocessing", "supervised", "standard", ("target_derived",))})


# ------------------------------------------------------------------ overlap


def ovl_oversample_before_split(base, meta, slots, variant, k):
    if variant == "resample":
        pre = ["minority = X[y == 1]",
               L("extra = resample(minority, n_samples=4 * len(minority), random_state=0)", k),
               "X = pd.concat([X, extra])",
               "y = pd.concat([y, pd.Series(1, index=extra.index)])"]
    else:  # plain duplication of the minority class
        pre = [L("X = pd.concat([X] + [X[y == 1]] * 4)", k),
               "y = pd.concat([y] + [y[y == 1]] * 4)"]
    return Mutation(overrides={"presplit": pre, "balance": []},
                    labels={k: Label("overlap", "resample_before_split", "standard")})


def ovl_test_in_fit(base, meta, slots, variant, k):
    rhs = _score_rhs(slots)
    fit = {"concat": "model.fit(pd.concat([X_train, X_test]), pd.concat([y_train, y_test]))",
           "refit_all": "model.fit(X, y)"}[variant]
    return Mutation(overrides={"fit_eval": [L(fit, k), f"score = {rhs}"]},
                    labels={k: Label("overlap", "test_in_fit", "standard")})


def ovl_raw_duplicates(base, meta, slots, variant, k):
    slot = "split" if meta["shape"] == "holdout" else "cv"
    lines = list(slots[slot])
    idx = next(i for i, x in enumerate(lines) if "train_test_split(" in x or "cross_val_score(" in x)
    lines[idx] = L(lines[idx], k)
    return Mutation(overrides={slot: lines}, data_transform={"duplicate_frac": 0.3},
                    labels={k: Label("overlap", "raw_duplicates", "dynamic_only")})


# ------------------------------------------------------------------ multi-test


def _inner_cv(meta):
    if meta["family"] == "timeseries":
        return "TimeSeriesSplit(n_splits=3)", ["from sklearn.model_selection import TimeSeriesSplit"]
    if meta["family"] == "grouped":
        return "GroupKFold(n_splits=3)", ["from sklearn.model_selection import GroupKFold"]
    return "5", []


def mul_holdout_loop(base, meta, slots, variant, k):
    rhs = _score_rhs(slots)
    pick = "max" if meta["higher_is_better"] else "min"
    values = repr(meta["values"])
    leaky = [f"results = {{}}",
             f"for value in {values}:",
             f'    model.set_params(**{{"{meta["hparam"]}": value}})',
             "    model.fit(X_train, y_train)",
             L(f"    results[value] = {rhs}", k),
             f"best = {pick}(results, key=results.get)",
             "score = results[best]"]
    inner, imps = _inner_cv(meta)
    fit_args = "X_train, y_train"
    if meta["family"] == "grouped":
        fit_args += f', groups=df["{meta["entity"]}"].iloc[train_idx]'
    fixed = [f'search = GridSearchCV(model, {{"{meta["hparam"]}": {values}}}, cv={inner}, scoring="{meta["scoring"]}")',
             f"search.fit({fit_args})",
             "model = search.best_estimator_",
             f"score = {rhs}"]
    return Mutation(overrides={"fit_eval": leaky},
                    fixed_overrides={"fit_eval": fixed},
                    fixed_imports=["from sklearn.model_selection import GridSearchCV", *imps],
                    labels={k: Label("multi_test", "test_set_tuning", "standard")})


CV_SETUP = {  # base -> (setup lines, cv expression, groups expression)
    "tab_housing": (["cv = KFold(n_splits=5, shuffle=True, random_state=0)"], "cv", None),
    "tab_churn": (["cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)"], "cv", None),
    "ts_sensor": (["cv = TimeSeriesSplit(n_splits=5)"], "cv", None),
    "ts_air": (["cv = TimeSeriesSplit(n_splits=5)"], "cv", None),
    "grp_eeg": (["cv = GroupKFold(n_splits=4)"], "cv", "groups"),
    "grp_users": ([], "GroupKFold(n_splits=5)", 'df["user_id"]'),
}


def mul_cv_loop(base, meta, slots, variant, k):
    setup, cv, groups = CV_SETUP[base]
    g = f", groups={groups}" if groups else ""
    # sklearn scorers are all "higher is better" (neg_* for errors), so the leaky selection always takes max.
    leaky = [*setup,
             "results = {}",
             f"for value in {meta['values']!r}:",
             f'    model.set_params(**{{"{meta["hparam"]}": value}})',
             L(f'    results[value] = cross_val_score(model, X, y, cv={cv}{g}, scoring="{meta["scoring"]}").mean()', k),
             f"best = max(results, key=results.get)",
             "scores = np.array([results[best]])"]
    inner = "TimeSeriesSplit(n_splits=3)" if meta["family"] == "timeseries" else "3"
    fixed = [*setup,
             f'search = GridSearchCV(model, {{"{meta["hparam"]}": {meta["values"]!r}}}, cv={inner}, '
             f'scoring="{meta["scoring"]}")',
             f'scores = cross_val_score(search, X, y, cv={cv}{g}, scoring="{meta["scoring"]}")']
    return Mutation(overrides={"cv": leaky},
                    fixed_overrides={"cv": fixed},
                    fixed_imports=["from sklearn.model_selection import GridSearchCV"],
                    labels={k: Label("multi_test", "cv_selection_reported", "standard")})


# ------------------------------------------------------------------ group


def grp_holdout(base, meta, slots, variant, k):
    if variant == "tts":
        split = [L("X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)", k)]
        imps = ["from sklearn.model_selection import train_test_split"]
    elif variant == "tts_stratified":
        split = [L("X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, stratify=y, "
                   "random_state=0)", k)]
        imps = ["from sklearn.model_selection import train_test_split"]
    else:  # shufflesplit
        split = [L("splitter = ShuffleSplit(n_splits=1, test_size=0.25, random_state=0)", k),
                 L("train_idx, test_idx = next(splitter.split(X, y))", k),
                 "X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]",
                 "y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]"]
        imps = ["from sklearn.model_selection import ShuffleSplit"]
    return Mutation(overrides={"split": split}, imports=imps,
                    labels={k: Label("group", "row_split", "group")})


def grp_cv(base, meta, slots, variant, k):
    scoring = meta["scoring"]
    if variant == "default_cv":
        cv = [L(f'scores = cross_val_score(model, X, y, cv=5, scoring="{scoring}")', k)]
        imps, sub = [], "default_cv"
    else:
        cls = {"kfold": "KFold", "stratified": "StratifiedKFold"}[variant]
        cv = [L(f"cv = {cls}(n_splits=5, shuffle=True, random_state=0)", k),
              L(f'scores = cross_val_score(model, X, y, cv=cv, scoring="{scoring}")', k)]
        imps, sub = [f"from sklearn.model_selection import {cls}"], "row_cv"
    if meta.get("entity_source") == "file_path":
        sub += "+file_path_entity"
    return Mutation(overrides={"cv": cv}, imports=imps, labels={k: Label("group", sub, "group")})


# ------------------------------------------------------------------ temporal


def tmp_holdout(base, meta, slots, variant, k):
    if variant == "tts_default":
        split = [L("X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)", k)]
    elif variant == "tts_shuffle_true":
        split = [L("X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=True, "
                   "random_state=0)", k)]
    else:  # manual random sample
        split = [L("test_rows = X.sample(frac=0.2, random_state=0).index", k),
                 "X_train, X_test = X.drop(test_rows), X.loc[test_rows]",
                 "y_train, y_test = y.drop(test_rows), y.loc[test_rows]"]
    return Mutation(overrides={"split": split}, imports=["from sklearn.model_selection import train_test_split"],
                    labels={k: Label("temporal", "T1", "temporal_differentiating")})


def tmp_cv(base, meta, slots, variant, k):
    scoring = meta["scoring"]
    if variant == "default_cv":
        cv = [L(f'scores = cross_val_score(model, X, y, cv=5, scoring="{scoring}")', k)]
        cat = "temporal_differentiating"
        imps = []
    else:
        shuffle = variant == "kfold_shuffle"
        args = "n_splits=5, shuffle=True, random_state=0" if shuffle else "n_splits=5"
        cv = [L(f"cv = KFold({args})", k),
              L(f'scores = cross_val_score(model, X, y, cv=cv, scoring="{scoring}")', k)]
        cat = "temporal_common" if shuffle else "temporal_differentiating"
        imps = ["from sklearn.model_selection import KFold"]
    return Mutation(overrides={"cv": cv}, imports=imps, labels={k: Label("temporal", "T1", cat)})


def tmp_future_feature(base, meta, slots, variant, k):
    v, series = meta["value_col"], meta.get("series_col")
    src = f'g["{v}"]' if series else f'df["{v}"]'
    if variant == "neg_shift":
        name, expr, cat = f"{v}_in_2", f"{src}.shift(-2)", "temporal_common"
    elif variant == "centered_rolling":
        name = f"{v}_smooth"
        expr = (f'{src}.transform(lambda s: s.rolling(7, center=True).mean())' if series
                else f"{src}.rolling(7, center=True).mean()")
        cat = "temporal_common"
    else:  # reversed rolling window: forward-looking without shift(-k) or center=True
        name = f"{v}_ahead_mean"
        expr = (f'{src}.transform(lambda s: s[::-1].rolling(7).mean()[::-1])' if series
                else f"{src}[::-1].rolling(7).mean()[::-1]")
        cat = "temporal_hard"
    over = {"features": [L(f'df["{name}"] = {expr}', k)]}
    if base == "ts_sensor":
        over["features_list"] = [f'FEATURES = FEATURES + ["{name}"]']
    return Mutation(overrides=over, labels={k: Label("temporal", "T2", cat)})


def tmp_hidden_time(base, meta, slots, variant, k):
    """Random split on time-ordered data whose time column has a non-temporal name ("ref")."""
    mut = tmp_holdout(base, meta, slots, "tts_default", k)
    mut.rename_col = (meta["time_col"], "ref")
    mut.data_transform = {"rename": {meta["time_col"]: "ref"}}
    mut.fixed_overrides = None
    return mut


# ------------------------------------------------------------------ target-derived

PROXY = {  # base -> (feature name, expression using df[TARGET])
    "tab_credit": ("late_payments", "df[TARGET] * np.random.default_rng(7).integers(1, 4, len(df))"),
    "tab_fraud": ("chargeback_filed", "(df[TARGET] == 1) & (np.random.default_rng(7).random(len(df)) < 0.8)"),
    "tab_churn": ("cancellation_calls", "df[TARGET] * np.random.default_rng(7).poisson(2, len(df))"),
    "tab_housing": ("assessed_value", "df[TARGET] * 0.9 + np.random.default_rng(7).normal(0, 20, len(df))"),
    "grp_eeg": ("annotated_spikes", "df[TARGET] * np.random.default_rng(7).integers(1, 5, len(df))"),
    "grp_patients": ("icu_days", "df[TARGET] * np.random.default_rng(7).integers(1, 9, len(df))"),
    "grp_users": ("order_items", "df[TARGET] * np.random.default_rng(7).integers(1, 6, len(df))"),
    "grp_sites": ("treatment_started", "df[TARGET] * (np.random.default_rng(7).random(len(df)) < 0.9)"),
}


def tgt_proxy(base, meta, slots, variant, k):
    name, expr = PROXY[base]
    lines = [L(f'df["{name}"] = {expr}', k), f'FEATURES = FEATURES + ["{name}"]']
    if base == "tab_credit":
        lines.append(f'NUMERIC = NUMERIC + ["{name}"]')
    return Mutation(overrides={"features": lines}, labels={k: Label("target_derived", "post_outcome", "standard")})


# ------------------------------------------------------------------ traps (clean)


def trap_manual_scaler(base, meta, slots, variant, k):
    split = list(slots["split"]) + [
        'num_cols = X_train.select_dtypes("number").columns',
        "scaler = StandardScaler().fit(X_train[num_cols])",
        "X_train = X_train.copy()",
        "X_test = X_test.copy()",
        "X_train[num_cols] = scaler.transform(X_train[num_cols])",
        "X_test[num_cols] = scaler.transform(X_test[num_cols])",
    ]
    imps = ["from sklearn.preprocessing import StandardScaler"]
    # Nothing to fix: the reference version is the trap itself, so its true inflation is 0 by definition.
    return Mutation(overrides={"split": split}, imports=imps, fixed_overrides={"split": split}, fixed_imports=imps)


# ------------------------------------------------------------------ registry

# name -> (function, variants, applicability predicate on (base, meta))
OPERATORS = {
    "pre_scaler": (pre_scaler, ["standard", "minmax", "robust"], lambda b, m: b != "grp_eeg"),
    "pre_imputer": (pre_imputer, ["mean", "median"], lambda b, m: b in ("tab_credit", "tab_housing")),
    "pre_pandas_stats": (pre_pandas_stats, ["zscore", "minmax"], lambda b, m: b != "grp_eeg"),
    "pre_select": (pre_select, ["kbest"], lambda b, m: b in ("tab_churn", "tab_fraud")),
    "pre_target_encoding": (pre_target_encoding, ["groupby_mean"],
                            lambda b, m: "cat_col" in m and m["task"] == "clf"),
    "ovl_oversample_before_split": (ovl_oversample_before_split, ["resample", "duplicate"],
                                    lambda b, m: m.get("imbalanced", False)),
    "ovl_test_in_fit": (ovl_test_in_fit, ["concat", "refit_all"], lambda b, m: m["shape"] == "holdout"),
    "ovl_raw_duplicates": (ovl_raw_duplicates, ["frac30"], lambda b, m: m["family"] == "tabular"),
    "mul_holdout_loop": (mul_holdout_loop, ["loop"], lambda b, m: m["shape"] == "holdout"),
    "mul_cv_loop": (mul_cv_loop, ["loop"], lambda b, m: m["shape"] == "cv"),
    "grp_holdout": (grp_holdout, ["tts", "tts_stratified", "shufflesplit"],
                    lambda b, m: m["family"] == "grouped" and m["shape"] == "holdout"),
    "grp_cv": (grp_cv, ["kfold", "stratified", "default_cv"],
               lambda b, m: m["family"] == "grouped" and m["shape"] == "cv"),
    "tmp_holdout": (tmp_holdout, ["tts_default", "tts_shuffle_true", "manual_sample"],
                    lambda b, m: m["family"] == "timeseries" and m["shape"] == "holdout"),
    "tmp_cv": (tmp_cv, ["kfold_shuffle", "kfold_plain", "default_cv"],
               lambda b, m: m["family"] == "timeseries" and m["shape"] == "cv"),
    "tmp_future_feature": (tmp_future_feature, ["neg_shift", "centered_rolling", "reverse_rolling"],
                           lambda b, m: m["family"] == "timeseries"),
    "tmp_hidden_time": (tmp_hidden_time, ["renamed_time_col"],
                        lambda b, m: m["family"] == "timeseries" and m["shape"] == "holdout"),
    "tgt_proxy": (tgt_proxy, ["proxy"], lambda b, m: b in PROXY),
    "trap_manual_scaler": (trap_manual_scaler, ["fit_on_train"], lambda b, m: m["shape"] == "holdout"),
}

# Two-leak items: (base, [(operator, variant), (operator, variant)])
COMBOS = [
    ("grp_patients", [("pre_scaler", "standard"), ("grp_holdout", "tts")]),
    ("grp_users", [("tgt_proxy", "proxy"), ("grp_cv", "default_cv")]),
    ("ts_sales", [("pre_pandas_stats", "zscore"), ("tmp_holdout", "tts_default")]),
    ("ts_sensor", [("tmp_future_feature", "neg_shift"), ("tmp_cv", "kfold_shuffle")]),
    ("tab_credit", [("pre_imputer", "mean"), ("ovl_test_in_fit", "refit_all")]),
    ("tab_churn", [("pre_target_encoding", "groupby_mean"), ("mul_cv_loop", "loop")]),
]
