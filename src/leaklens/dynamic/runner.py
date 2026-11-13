"""Run one script with scikit-learn instrumented, and write what happened to a JSON file.

    python -m leaklens.dynamic.runner SCRIPT --out events.json [--hints hints.json] [--fix fix.json]

This module is the child process of the dynamic pass. It executes SCRIPT (so it must only be used on trusted code,
or inside `leaklens.sandbox` in an offline Kaggle session, CLAUDE.md Rule 7). It patches library entry points
before the script imports them:

- `train_test_split`, every splitter's `split` and the CV helpers: at each split it records, fold by fold, the
  duplicate rows across the split, the entity columns whose values are on both sides, and whether training rows
  are dated after evaluation rows. Entity and time columns are looked up in the data frames of the script's own
  namespace that are row-aligned with the data being split, so the user declares nothing.
- estimator `fit` / `predict` / `score`: which rows a model was fitted on, and what share of the rows it is later
  scored on were among them.
- `sklearn.metrics` functions: which evaluation rows are scored repeatedly with different predictions.

With `--fix`, one call site is changed and nothing else (impact estimation, Phase 6): a row-level split becomes
its group-aware or chronological counterpart, a model fit drops the evaluation rows, a transformer is fitted on
the training rows only, or one feature is removed. The script's own printed metric is then compared by the parent.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import runpy
import sys
import traceback
import warnings

EVENTS: list[dict] = []
STATE = {
    "depth": 0,
    "script": "",
    "hints": {},
    "fix": None,
    "fix_applied": [],
    "test_hashes": {},
    "fits": {},
    "split_positions": {},
    "cfg": {},
    "dump": None,
    "dump_index": [],
}


# ---------------------------------------------------------------------------------------------- helpers


def user_frame():
    """Innermost frame that belongs to the analysed script, and its line."""
    f = sys._getframe(1)
    while f is not None:
        if f.f_code.co_filename == STATE["script"]:
            return f, f.f_lineno
        f = f.f_back
    return None, None


def row_hashes(X):
    """One 64-bit hash per row of X (values only, no index), or None if X cannot be hashed."""
    import numpy as np
    import pandas as pd

    try:
        if hasattr(X, "toarray") and not isinstance(X, pd.DataFrame | pd.Series):
            X = X.toarray()
        if isinstance(X, pd.Series):
            X = X.to_frame()
        if not isinstance(X, pd.DataFrame):
            a = np.asarray(X)
            a = a.reshape(len(a), -1)
            X = pd.DataFrame(a)
        if len(X) > STATE["cfg"].get("max_rows_hashed", 2_000_000):
            return None
        num_cols = X.select_dtypes("number").columns
        if len(num_cols):
            X = X.copy()
            X[num_cols] = X[num_cols].round(STATE["cfg"].get("duplicates", {}).get("round_decimals", 6))
        return pd.util.hash_pandas_object(X, index=False).to_numpy()
    except Exception:
        return None


def signature(a) -> str | None:
    h = row_hashes(a)
    return None if h is None else hashlib.sha1(h.tobytes()).hexdigest()[:16]


def n_rows(X) -> int | None:
    try:
        return X.shape[0] if hasattr(X, "shape") else len(X)
    except Exception:
        return None


def aligned_columns(frame, X, n: int) -> dict:
    """Columns of data frames (and named 1-D arrays) in the script's namespace that have one value per row of X."""
    import numpy as np
    import pandas as pd

    out: dict[str, object] = {}
    xi = X.index if isinstance(X, pd.DataFrame | pd.Series) else None
    spaces = [frame.f_locals] if frame is not None else []
    if frame is not None and frame.f_globals is not frame.f_locals:
        spaces.append(frame.f_globals)
    if isinstance(X, pd.DataFrame):
        for c in X.columns:
            out[str(c)] = X[c].to_numpy()
    if xi is not None and isinstance(xi, pd.DatetimeIndex):
        out["<index>"] = xi.to_numpy()
    for ns in spaces:
        for name, v in list(ns.items()):
            if name.startswith("_"):
                continue
            try:
                if isinstance(v, pd.DataFrame):
                    if len(v) == n and (xi is None or v.index.equals(xi)):
                        sub = v
                    elif xi is not None and v.index.is_unique and len(v) >= n and xi.isin(v.index).all():
                        sub = v.loc[xi]
                    else:
                        continue
                    for c in sub.columns:
                        out.setdefault(str(c), sub[c].to_numpy())
                    if isinstance(sub.index, pd.DatetimeIndex):
                        out.setdefault("<index>", sub.index.to_numpy())
                elif isinstance(v, pd.Series):
                    if len(v) == n and (xi is None or v.index.equals(xi)):
                        out.setdefault(str(v.name) if v.name is not None else name, v.to_numpy())
                        out.setdefault(name, v.to_numpy())
                elif isinstance(v, np.ndarray | list) and len(v) == n:
                    a = np.asarray(v)
                    if a.ndim == 1:
                        out.setdefault(name, a)
            except Exception:
                continue
    return out


def entity_columns(cols: dict, x_names: set[str]) -> dict[str, str]:
    """Aligned columns with entity evidence by name (or named by the static pass): name -> strength."""
    from leaklens.static.analyzer import entity_strength

    hinted = dict(STATE["hints"].get("entity_columns", {}))
    excluded = set(STATE["hints"].get("not_entities", []))
    out = {}
    for name in cols:
        if name in excluded:
            continue
        s = hinted.get(name) or entity_strength(name)
        if s is None:
            continue
        if name in x_names and name not in hinted and s == "strong":
            s = "weak"  # used as a model feature: more likely a categorical feature than an identifier
        out[name] = s
    limit = STATE["cfg"].get("entities", {}).get("max_columns_checked", 25)
    return dict(sorted(out.items(), key=lambda kv: (kv[1] != "strong", kv[0]))[:limit])


def time_columns(cols: dict) -> dict:
    """Aligned columns that hold timestamps: datetime dtype, a datetime index, or a date-named text column."""
    import numpy as np
    import pandas as pd

    from leaklens.static.analyzer import tokens

    hinted = set(STATE["hints"].get("time_columns", []))
    out = {}
    for name, a in cols.items():
        a = np.asarray(a)
        if a.dtype.kind == "M":
            out[name] = a
        elif a.dtype.kind in "OU" and (name in hinted or set(tokens(name)) & {"date", "datetime", "timestamp"}):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                t = pd.to_datetime(pd.Series(a), errors="coerce")
            if t.notna().mean() >= 0.9:
                out[name] = t.to_numpy()
    return out


def dump_fold(site: dict, fold: int, cols: dict, y, train, test) -> None:
    """Write the train and evaluation tables of one fold (every row-aligned column plus `__target__`) as CSV.

    Opt-in (`--dump-splits DIR`), used only to give data-level baseline tools exactly the splits the script made.
    """
    import numpy as np
    import pandas as pd

    data = {}
    for name, a in cols.items():
        a = np.asarray(a)
        if a.ndim == 1 and a.dtype.kind in "biufcMmOUS":
            data[name] = a
    if y is not None and n_rows(y) == len(next(iter(data.values()), [])):
        data["__target__"] = np.asarray(y).ravel()
    if not data:
        return
    df = pd.DataFrame(data)
    base = f"L{site['line']}_F{fold}"
    df.iloc[np.asarray(train)].to_csv(os.path.join(STATE["dump"], base + "_train.csv"), index=False)
    df.iloc[np.asarray(test)].to_csv(os.path.join(STATE["dump"], base + "_test.csv"), index=False)
    STATE["dump_index"].append({"line": site["line"], "call": site["call"], "fold": fold, "base": base,
                                "has_target": "__target__" in data, "columns": list(data)[:400]})


def record_fold(site: dict, fold: int, X, train, test, frame, y=None) -> None:
    """Everything the dynamic checks need about one train/evaluation partition, computed in the child."""
    import numpy as np
    import pandas as pd

    if fold >= STATE["cfg"].get("max_folds_recorded", 10):
        return
    train, test = np.asarray(train), np.asarray(test)
    n = n_rows(X)
    ev = {
        "kind": "split",
        "line": site["line"],
        "call": site["call"],
        "fold": fold,
        "n": n,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "entities": {},
        "times": {},
        "dup": None,
    }
    h = row_hashes(X)
    if h is not None and n:
        htr, hte = h[train], h[test]
        ev["dup"] = {
            "test_in_train": float(np.isin(hte, htr).mean()) if len(hte) else 0.0,
            "distinct_frac": float(len(np.unique(h)) / n),
            "train_dup": float(1 - len(np.unique(htr)) / max(len(htr), 1)),
        }
        STATE["test_hashes"].setdefault(site["line"], set()).update(hte.tolist())
    STATE["split_positions"].setdefault(
        site["line"], {"n": n, "test": test.tolist() if fold == 0 else None, "folds": 0}
    )["folds"] += 1
    cols = aligned_columns(frame, X, n) if n else {}
    if STATE["dump"] and cols and fold < STATE["cfg"].get("max_folds_dumped", 5):
        try:
            dump_fold(site, fold, cols, y, train, test)
        except Exception as e:  # never let the baseline export change the analysed run
            STATE["dump_index"].append({"line": site["line"], "fold": fold, "error": f"{type(e).__name__}: {e}"})
    x_names = {str(c) for c in X.columns} if isinstance(X, pd.DataFrame) else set()
    ev["x_cols"] = sorted(x_names)[:200]
    for name, strength in entity_columns(cols, x_names).items():
        try:
            v = pd.Series(cols[name])
            tr, te = v.iloc[train], v.iloc[test]
            shared = set(tr.dropna().unique()) & set(te.dropna().unique())
            ev["entities"][name] = {
                "strength": strength,
                "n_unique": int(v.nunique()),
                "n": int(len(v)),
                "shared": len(shared),
                "n_test_entities": int(te.nunique()),
                "test_rows_shared": float(te.isin(shared).mean()) if len(te) else 0.0,
            }
        except Exception:
            continue
    for name, a in time_columns(cols).items():
        try:
            t = pd.Series(a)
            ttr, tte = t.iloc[train].dropna(), t.iloc[test].dropna()
            if len(ttr) and len(tte):
                ev["times"][name] = {
                    "train_after_test": float((ttr > tte.min()).mean()),
                    "train_max": str(ttr.max()),
                    "test_min": str(tte.min()),
                }
        except Exception:
            continue
    EVENTS.append(ev)


# ---------------------------------------------------------------------------------------------- fixes


def dedupe(arrays: tuple, what: str) -> tuple:
    """Drop rows whose values repeat an earlier row of the first array (the canonical fix for duplicated records)."""
    import numpy as np
    from sklearn.utils import _safe_indexing

    h = row_hashes(arrays[0])
    if h is None:
        raise RuntimeError("fix failed: rows cannot be compared")
    _, first = np.unique(h, return_index=True)
    keep = np.sort(first)
    STATE["fix_applied"].append(f"{what}: {len(h) - len(keep)} duplicated rows removed before the split")
    n = len(h)
    return tuple(_safe_indexing(a, keep) if a is not None and n_rows(a) == n else a for a in arrays)


def fix_for(line: int | None, kinds: tuple[str, ...]) -> dict | None:
    fix = STATE["fix"]
    if fix and fix["kind"] in kinds and (fix.get("line") is None or fix.get("line") == line):
        return fix
    return None


def find_column(frame, X, name: str):
    cols = aligned_columns(frame, X, n_rows(X))
    return cols.get(name)


def time_order(frame, X, name: str | None):
    """Row positions sorted by time (stable), from the named time column or the first one found."""
    import numpy as np

    cols = aligned_columns(frame, X, n_rows(X))
    times = time_columns(cols)
    key = name if name in times else next(iter(sorted(times)), None)
    if key is None:
        return None
    return np.argsort(times[key], kind="stable")


def fixed_folds(fix: dict, splitter, X, y, frame):
    """The folds the fixed splitter would produce: group-aware or forward-chaining, same number of folds."""
    import numpy as np
    from sklearn import model_selection as ms

    n = n_rows(X)
    try:
        k = splitter.get_n_splits(X, y, None)
    except Exception:
        k = 5
    seed = getattr(splitter, "random_state", None)
    name = type(splitter).__name__
    if fix["kind"] == "group_split":
        groups = find_column(frame, X, fix["column"])
        if groups is None:
            raise RuntimeError(f"fix failed: column {fix['column']!r} is not row-aligned with the split data")
        if "ShuffleSplit" in name:
            new = ms.GroupShuffleSplit(n_splits=k, test_size=getattr(splitter, "test_size", None), random_state=seed)
        elif "Stratified" in name and y is not None:
            new = ms.StratifiedGroupKFold(
                n_splits=k,
                shuffle=bool(getattr(splitter, "shuffle", False)),
                random_state=seed if getattr(splitter, "shuffle", False) else None,
            )
        else:
            new = ms.GroupKFold(n_splits=k)
        STATE["fix_applied"].append(f"{name} -> {type(new).__name__}(groups={fix['column']})")
        return list(new.split(X, y, groups))
    order = time_order(frame, X, fix.get("column"))
    if order is None:
        order = np.arange(n)
    STATE["fix_applied"].append(f"{name} -> TimeSeriesSplit({k}) in time order")
    return [(order[tr], order[te]) for tr, te in ms.TimeSeriesSplit(n_splits=k).split(np.arange(n))]


# ---------------------------------------------------------------------------------------------- patches


def patch_train_test_split(ms, split_mod) -> None:
    import numpy as np
    from sklearn.utils import _safe_indexing

    orig = ms.train_test_split

    @functools.wraps(orig)
    def train_test_split(*arrays, **options):
        frame, line = user_frame()
        if STATE["depth"] or line is None or not arrays:
            return orig(*arrays, **options)
        if fix_for(line, ("dedupe_split",)) is not None:
            if options.get("stratify") is not None and n_rows(options["stratify"]) == n_rows(arrays[0]):
                *arrays, strat = dedupe((*arrays, options["stratify"]), "train_test_split")
                options = {**options, "stratify": strat}
            else:
                arrays = dedupe(arrays, "train_test_split")
        n = n_rows(arrays[0])
        STATE["depth"] += 1
        try:
            fix = fix_for(line, ("group_split", "time_split"))
            idx = np.arange(n)
            if fix is not None and fix["kind"] == "group_split":
                groups = find_column(frame, arrays[0], fix["column"])
                if groups is None:
                    raise RuntimeError(f"fix failed: column {fix['column']!r} is not row-aligned with the split data")
                gss = ms.GroupShuffleSplit(
                    n_splits=1,
                    test_size=options.get("test_size"),
                    train_size=options.get("train_size"),
                    random_state=options.get("random_state"),
                )
                tr, te = next(gss.split(arrays[0], groups=groups))
                STATE["fix_applied"].append(f"train_test_split -> GroupShuffleSplit(groups={fix['column']})")
                out = [part for a in arrays for part in (_safe_indexing(a, tr), _safe_indexing(a, te))]
            elif fix is not None:
                order = time_order(frame, arrays[0], fix.get("column"))
                if order is None:
                    raise RuntimeError("fix failed: no time column is row-aligned with the split data")
                opts = {k: v for k, v in options.items() if k not in ("shuffle", "stratify", "random_state")}
                parts = orig(order, shuffle=False, **opts)
                tr, te = parts[0], parts[1]
                STATE["fix_applied"].append("train_test_split -> chronological split in time order")
                out = [part for a in arrays for part in (_safe_indexing(a, tr), _safe_indexing(a, te))]
            else:
                res = orig(*arrays, idx, **options)
                tr, te = res[-2], res[-1]
                out = res[:-2]
            site = {"line": line, "call": "train_test_split"}
            record_fold(site, 0, arrays[0], tr, te, frame, arrays[1] if len(arrays) > 1 else None)
            return out
        finally:
            STATE["depth"] -= 1

    ms.train_test_split = train_test_split
    split_mod.train_test_split = train_test_split


def patch_splitters(split_mod) -> None:
    import inspect

    def make(cls, orig):
        @functools.wraps(orig)
        def split(self, X, y=None, groups=None):
            frame, line = user_frame()
            if STATE["depth"] or line is None:
                yield from orig(self, X, y, groups)
                return
            fix = fix_for(line, ("group_split", "time_split"))
            STATE["depth"] += 1
            try:
                folds = fixed_folds(fix, self, X, y, frame) if fix is not None else list(orig(self, X, y, groups))
            finally:
                STATE["depth"] -= 1
            site = {"line": line, "call": f"{type(self).__name__}.split"}
            for i, (tr, te) in enumerate(folds):
                record_fold(site, i, X, tr, te, frame, y)
                yield tr, te

        return split

    for _, cls in inspect.getmembers(split_mod, inspect.isclass):
        if (
            "split" in cls.__dict__
            and inspect.isfunction(cls.__dict__["split"])
            and cls.__module__ == split_mod.__name__
        ):
            cls.split = make(cls, cls.__dict__["split"])


class _Method:
    """Wraps a method (plain function or scikit-learn's `available_if` descriptor) without changing its signature."""

    def __init__(self, orig, name: str):
        self.orig, self.name = orig, name
        functools.update_wrapper(self, orig, updated=())

    def __get__(self, obj, owner=None):
        bound = self.orig.__get__(obj, owner)
        if obj is None:
            return bound
        name = self.name

        @functools.wraps(bound)
        def call(*args, **kwargs):
            return invoke(bound, obj, name, args, kwargs)

        return call


def params_hash(est) -> str:
    try:
        return hashlib.sha1(repr(sorted(est.get_params(deep=True).items(), key=lambda kv: kv[0])).encode()).hexdigest()[
            :12
        ]
    except Exception:
        return "?"


def invoke(bound, est, name: str, args: tuple, kwargs: dict):
    frame, line = user_frame()
    if STATE["depth"] or line is None:
        return bound(*args, **kwargs)
    X = args[0] if args else kwargs.get("X")
    cls = type(est).__name__
    is_transformer = hasattr(est, "transform") and not hasattr(est, "predict")
    STATE["depth"] += 1
    try:
        if name in ("fit", "fit_transform", "fit_predict") and X is not None:
            import pandas as pd

            fix = STATE["fix"]
            if fix and fix["kind"] == "drop_feature" and isinstance(X, pd.DataFrame) and fix["column"] in X.columns:
                X = X.drop(columns=[fix["column"]])
                args = (X, *args[1:]) if args else args
                kwargs = kwargs if args else {**kwargs, "X": X}
                STATE["fix_applied"].append(f"{cls}.{name}: feature {fix['column']} removed")
            fix = fix_for(line, ("fit_drop_test_rows",))
            if fix is not None and not is_transformer:
                import numpy as np
                from sklearn.utils import _safe_indexing

                seen = set().union(*STATE["test_hashes"].values()) if STATE["test_hashes"] else set()
                h = row_hashes(X)
                if h is None or not seen:
                    raise RuntimeError("fix failed: evaluation rows of the split are not known at this fit")
                keep = np.flatnonzero(~np.isin(h, np.fromiter(seen, dtype=h.dtype, count=len(seen))))
                X = _safe_indexing(X, keep)
                rest = tuple(_safe_indexing(a, keep) if n_rows(a) == len(h) else a for a in args[1:])
                args = (X, *rest)
                kwargs = {
                    k: (_safe_indexing(v, keep) if k in ("y", "sample_weight") and n_rows(v) == len(h) else v)
                    for k, v in kwargs.items()
                }
                STATE["fix_applied"].append(f"{cls}.fit: {len(h) - len(keep)} evaluation rows removed from the fit")
            fix = fix_for(line, ("fit_on_train_rows",))
            if fix is not None and is_transformer and name == "fit_transform":
                import numpy as np
                from sklearn.utils import _safe_indexing

                n = n_rows(X)
                test = np.asarray(fix["test_positions"])
                if fix["n"] != n:
                    raise RuntimeError("fix failed: the fitted data and the split data do not have the same rows")
                keep = np.setdiff1d(np.arange(n), test)
                rest = tuple(_safe_indexing(a, keep) if n_rows(a) == n else a for a in args[1:])
                est.fit(_safe_indexing(X, keep), *rest)
                STATE["fix_applied"].append(
                    f"{cls}: fitted on {len(keep)} training rows only, then applied to all rows"
                )
                EVENTS.append({"kind": "tfit", "line": line, "cls": cls, "method": name, "n": int(len(keep))})
                return est.transform(X)
            h = row_hashes(X)
            if is_transformer:
                EVENTS.append({"kind": "tfit", "line": line, "cls": cls, "method": name, "n": n_rows(X)})
            else:
                import numpy as np

                STATE["fits"][id(est)] = (line, np.unique(h) if h is not None else None)
                EVENTS.append({"kind": "fit", "line": line, "cls": cls, "n": n_rows(X), "params": params_hash(est)})
        elif name in ("predict", "predict_proba", "decision_function", "score", "predict_log_proba") and X is not None:
            import numpy as np
            import pandas as pd

            fix = STATE["fix"]
            if fix and fix["kind"] == "drop_feature" and isinstance(X, pd.DataFrame) and fix["column"] in X.columns:
                X = X.drop(columns=[fix["column"]])
                args = (X, *args[1:]) if args else args
                kwargs = kwargs if args else {**kwargs, "X": X}
            fit = STATE["fits"].get(id(est))
            h = row_hashes(X)
            frac = None
            if fit is not None and fit[1] is not None and h is not None and len(h):
                frac = float(np.isin(h, fit[1]).mean())
            EVENTS.append(
                {
                    "kind": "eval",
                    "line": line,
                    "method": name,
                    "cls": cls,
                    "n": n_rows(X),
                    "fit_line": fit[0] if fit else None,
                    "in_fit": frac,
                    "params": params_hash(est),
                    "x_sig": hashlib.sha1(h.tobytes()).hexdigest()[:16] if h is not None else None,
                }
            )
        return bound(*args, **kwargs)
    finally:
        STATE["depth"] -= 1


def patch_estimators() -> None:
    import inspect

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from sklearn.utils import all_estimators

        classes = [c for _, c in all_estimators()]
    from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
    from sklearn.pipeline import Pipeline

    names = ("fit", "fit_transform", "predict", "predict_proba", "decision_function", "score")
    seen = set()
    for cls in classes + [Pipeline, GridSearchCV, RandomizedSearchCV]:
        for klass in inspect.getmro(cls):
            if klass in seen or not klass.__module__.startswith("sklearn"):
                continue
            seen.add(klass)
            for name in names:
                orig = klass.__dict__.get(name)
                if orig is None or isinstance(orig, _Method | staticmethod | classmethod | property):
                    continue
                if hasattr(orig, "__get__"):
                    setattr(klass, name, _Method(orig, name))


def patch_cv_helpers(ms, val_mod) -> None:
    def make(name, orig):
        @functools.wraps(orig)
        def helper(estimator, X, y=None, **kw):
            frame, line = user_frame()
            if STATE["depth"] or line is None:
                return orig(estimator, X, y, **kw)
            import pandas as pd

            fix = STATE["fix"]
            if fix and fix["kind"] == "drop_feature" and isinstance(X, pd.DataFrame) and fix["column"] in X.columns:
                X = X.drop(columns=[fix["column"]])
                STATE["fix_applied"].append(f"{name}: feature {fix['column']} removed")
            if fix_for(line, ("dedupe_split",)) is not None:
                X, y = dedupe((X, y), name)
            fix = fix_for(line, ("group_split", "time_split"))
            if fix is not None:
                from sklearn.base import is_classifier
                from sklearn.model_selection import check_cv

                cv = check_cv(kw.get("cv"), y, classifier=is_classifier(estimator))
                STATE["depth"] += 1
                try:
                    kw["cv"] = fixed_folds(fix, cv, X, y, frame)
                finally:
                    STATE["depth"] -= 1
                kw.pop("groups", None)
                site = {"line": line, "call": f"{name} (fixed)"}
                for i, (tr, te) in enumerate(kw["cv"]):
                    record_fold(site, i, X, tr, te, frame, y)
            EVENTS.append(
                {
                    "kind": "cv",
                    "line": line,
                    "name": name,
                    "n": n_rows(X),
                    "params": params_hash(estimator),
                    "x_sig": signature(X),
                }
            )
            return orig(estimator, X, y, **kw)

        return helper

    for name in ("cross_val_score", "cross_validate", "cross_val_predict"):
        new = make(name, getattr(ms, name))
        setattr(ms, name, new)
        setattr(val_mod, name, new)


def patch_metrics() -> None:
    import inspect

    import sklearn.metrics as metrics

    def make(name, orig):
        @functools.wraps(orig)
        def metric(*args, **kw):
            frame, line = user_frame()
            if not STATE["depth"] and line is not None and len(args) >= 2:
                EVENTS.append(
                    {
                        "kind": "metric",
                        "line": line,
                        "name": name,
                        "n": n_rows(args[0]),
                        "y_sig": signature(args[0]),
                        "p_sig": signature(args[1]),
                    }
                )
            return orig(*args, **kw)

        return metric

    for name, fn in inspect.getmembers(metrics, inspect.isfunction):
        if name.endswith(("_score", "_error", "_loss")) and not name.startswith("_"):
            setattr(metrics, name, make(name, fn))


def single_feature_scores() -> None:
    """Evidence for target-derived findings: how well each hinted feature alone predicts the target."""
    feats = STATE["hints"].get("features", [])
    target = STATE["hints"].get("target")
    if not feats or not target:
        return
    import pandas as pd
    from sklearn.metrics import r2_score, roc_auc_score
    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

    ns = STATE.get("namespace") or {}
    for v in list(ns.values()):
        if isinstance(v, pd.DataFrame) and target in v.columns:
            for f in feats:
                if f not in v.columns:
                    continue
                try:
                    d = v[[f, target]].dropna()
                    x, y = d[[f]].apply(pd.to_numeric, errors="coerce").fillna(0), d[target]
                    if y.nunique() == 2:
                        m = DecisionTreeClassifier(max_depth=2, random_state=0).fit(x, y)
                        s, what = roc_auc_score(y, m.predict_proba(x)[:, 1]), "auc"
                    elif y.nunique() > 20 and y.dtype.kind in "fi":
                        m = DecisionTreeRegressor(max_depth=2, random_state=0).fit(x, y)
                        s, what = r2_score(y, m.predict(x)), "r2"
                    else:
                        continue
                    EVENTS.append(
                        {
                            "kind": "single_feature",
                            "feature": f,
                            "target": target,
                            "score": float(s),
                            "metric": what,
                            "n": int(len(d)),
                        }
                    )
                except Exception:
                    continue
            return


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", required=True)
    ap.add_argument("--hints")
    ap.add_argument("--fix")
    ap.add_argument("--dump-splits", help="directory: write each fold's train/evaluation tables (baselines only)")
    a = ap.parse_args(argv)
    if a.dump_splits:
        os.makedirs(a.dump_splits, exist_ok=True)
        STATE["dump"] = os.path.abspath(a.dump_splits)
    script = os.path.abspath(a.script)
    STATE["script"] = script
    if a.hints:
        STATE["hints"] = json.load(open(a.hints))
    if a.fix:
        STATE["fix"] = json.load(open(a.fix))
    from leaklens.config import load_config

    STATE["cfg"] = load_config("dynamic")
    status, error = "ok", None
    try:
        import sklearn.model_selection as ms
        import sklearn.model_selection._split as split_mod
        import sklearn.model_selection._validation as val_mod

        patch_train_test_split(ms, split_mod)
        patch_splitters(split_mod)
        patch_cv_helpers(ms, val_mod)
        patch_estimators()
        patch_metrics()
        sys.argv = [script]
        sys.path.insert(0, os.path.dirname(script))
        STATE["namespace"] = runpy.run_path(script, run_name="__main__")
        STATE["depth"] += 1
        single_feature_scores()
    except SystemExit as e:
        if e.code not in (None, 0):
            status, error = "error", f"SystemExit({e.code})"
    except BaseException as e:  # the analysed script failed: report it, the parent decides what that means
        status = "error"
        error = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    finally:
        with open(a.out, "w") as f:
            json.dump(
                {
                    "status": status,
                    "error": error,
                    "events": EVENTS,
                    "fix": STATE["fix"],
                    "fix_applied": STATE["fix_applied"],
                    "split_positions": {str(k): v for k, v in STATE["split_positions"].items()},
                    "dump_index": STATE["dump_index"],
                },
                f,
            )
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
