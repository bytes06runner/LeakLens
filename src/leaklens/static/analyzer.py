"""Static analyser: one pass of abstract interpretation over a flat module (docs/TAXONOMY.md, docs/SPEC.md).

The analysed code is never imported or run. Every variable gets an abstract value (`values.py`); rules fire at
*sinks*, the places where rows are partitioned or a model is fitted and evaluated:

- a split point (train_test_split, a splitter's `.split`, a CV helper, a search object's `.fit`, a manual random
  sample with its complement) checks group and temporal (T1) leakage and reports every statistic or copied row
  that reached the data being split;
- a model `fit` on training rows reports statistics that were computed on rows including the evaluation side;
- a `predict` / `score` on evaluation rows checks whether the model was fitted on rows that include them;
- a selection (`max`, `sorted`, `if score > best`) over scores computed in a loop reports multi-test leakage.

Unknown calls are opaque: their result depends on all their inputs. Anything unresolved produces no finding
rather than a guess, so the analyser prefers missing a leak to inventing one.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import replace

from leaklens.config import load_config
from leaklens.ingest import Source
from leaklens.report.findings import CONFIDENCE_ORDER, Finding

from . import handwritten
from .values import (
    UNKNOWN,
    AVal,
    Bound,
    ColFact,
    Cols,
    Const,
    Data,
    DrawV,
    Est,
    EvalEvent,
    FitRec,
    FuncV,
    Indexer,
    Iter,
    ListV,
    MaskV,
    Num,
    Origin,
    PathV,
    Ref,
    RngV,
    Rows,
    Score,
    Split,
    SplitIter,
    SplitterV,
    Str,
    Taint,
    covers,
)

CFG = load_config("static")
_T = CFG["transformers"]
STATISTICAL = set(_T["statistical"])
VOCABULARY = set(_T["vocabulary"])
SUPERVISED = set(_T["supervised"])
COMPOSITE = set(_T["composite"])
RESAMPLERS = set(CFG["resamplers"])
UNDERSAMPLERS = set(CFG["undersamplers"])
ROW_SPLITTERS = set(CFG["splitters"]["row_level"])
GROUP_SPLITTERS = set(CFG["splitters"]["group_aware"])
TIME_SPLITTERS = set(CFG["splitters"]["time_aware"])
ALWAYS_SHUFFLED = set(CFG["splitters"]["always_shuffled"])
CV_HELPERS = set(CFG["cv_helpers"])
SEARCH = set(CFG["search_estimators"])
MODEL_SUFFIXES = tuple(CFG["model_suffixes"])
READERS = set(CFG["readers"])
REDUCTIONS = set(CFG["reductions"])
GROUPBY_STATS = set(CFG["groupby_stat_functions"])
FWD_FILL = set(CFG["forward_fill_methods"])
LOW_FWD = set(CFG["low_confidence_forward"])
ORDERED_OPS = set(CFG["ordered_ops"])
METRIC_SUFFIXES = tuple(CFG["metric_suffixes"])
METRIC_NAMES = set(CFG["metric_names"])
NON_SCALAR_METRICS = set(CFG["non_scalar_metrics"])
SELECT_FUNCS = set(CFG["selection_functions"])
SELECT_METHODS = set(CFG["selection_methods"])
ENT_STRONG = set(CFG["entity_tokens"]["strong"])
ENT_WEAK = set(CFG["entity_tokens"]["weak"])
ENT_NEEDS_ID = set(CFG["entity_tokens"]["strong_only_with_id_suffix"])
ID_SUFFIXES = set(CFG["entity_tokens"]["id_suffixes"])
TIME_TOKENS = set(CFG["time_tokens"])
HINT_TRAIN = set(CFG["role_hints"]["train"])
HINT_TEST = set(CFG["role_hints"]["test"])
HINT_VAL = set(CFG["role_hints"]["validation"])
PATH_NAMES = set(CFG["path_name_tokens"])
MAX_DEPTH = CFG["limits"]["max_inline_depth"]
DRAW_FUNCS = set(CFG["random_draws"])  # uniform draws in [0, 1) used for hand-written random splits
MAX_STATEMENTS = CFG["limits"]["max_statements"]
TRIM_MAX = CFG["limits"]["positional_trim_max_rows"]
STATELESS = set(_T["stateless"])
DEBUG = bool(os.environ.get("LEAKLENS_DEBUG"))

_TOKEN = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
_SUPPRESS = re.compile(r"#\s*leaklens:\s*ignore(?:\[([\w,\s]+)\])?(?:\s*--\s*(.*))?")
_STRONG_TIME = {"date", "datetime", "timestamp"}
_PASSTHROUGH_FUNCS = {
    "Series",
    "array",
    "asarray",
    "asanyarray",
    "ascontiguousarray",
    "from_numpy",
    "tensor",
    "as_tensor",
    "Tensor",
    "FloatTensor",
    "LongTensor",
    "squeeze",
    "ravel",
    "copy",
    "deepcopy",
    "nan_to_num",
    "log",
    "log1p",
    "log2",
    "log10",
    "exp",
    "expm1",
    "sqrt",
    "square",
    "absolute",
    "sign",
    "rint",
    "float32",
    "float64",
    "int32",
    "int64",
    "to_numeric",
    "DMatrix",
    "Dataset",
    "Pool",
    "TensorDataset",
    "atleast_2d",
    "atleast_1d",
    "reshape",
    "where",
    "clip",
    "isnan",
    "isfinite",
    "to_categorical",
    "csr_matrix",
    "csc_matrix",
    "factorize",
    "cut",
    "qcut",
}
_CONCAT_FUNCS = {
    "concat",
    "vstack",
    "hstack",
    "concatenate",
    "column_stack",
    "row_stack",
    "c_",
    "r_",
    "stack",
    "append",
}
_PATH_FUNCS = {"glob", "iglob", "listdir", "scandir", "walk", "rglob", "iterdir"}
_SEQ_FUNCS = {"list", "tuple", "set", "reversed", "iter", "frozenset"}
_SCORE_KEEP = {"mean", "median", "sum", "std", "round", "abs", "average", "nanmean", "float", "sqrt", "var"}
_PREDICT = {"predict", "predict_proba", "decision_function", "predict_log_proba", "predict_classes"}
_FRAME_PROPS_UNKNOWN = {
    "shape",
    "dtypes",
    "size",
    "ndim",
    "empty",
    "dtype",
    "name",
    "names",
    "nbytes",
    "axes",
    "attrs",
    "flags",
}
_COMPARE_METHODS = {"eq", "ne", "lt", "gt", "le", "ge", "between"}
_COMBINE_METHODS = {
    "map",
    "replace",
    "fillna",
    "clip",
    "where",
    "mask",
    "sub",
    "add",
    "div",
    "mul",
    "subtract",
    "divide",
    "multiply",
    "truediv",
    "floordiv",
    "mod",
    "pow",
    "combine_first",
    "corrwith",
    "dot",
    "update",
    "isin",
    "reindex_like",
    "align",
} | _COMPARE_METHODS
_FUNC_METHODS = {"apply", "transform", "pipe", "map", "applymap", "agg", "aggregate", "progress_apply"}
_CUM = {"cumsum", "cumprod", "cummax", "cummin"}
_DATASET_MAKERS = {
    "make_classification",
    "make_regression",
    "make_blobs",
    "make_moons",
    "make_circles",
    "load_iris",
    "load_wine",
    "load_breast_cancer",
    "load_diabetes",
    "load_digits",
    "fetch_california_housing",
    "fetch_openml",
}


class Budget(Exception):
    """Raised when an input exceeds the statement budget; findings so far are kept."""


def tokens(name: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(name)]


def entity_strength(name: str) -> str | None:
    """`strong`, `weak` or None for a column or variable name (TAXONOMY section 5, name evidence)."""
    toks = [t for t in tokens(name) if not t.isdigit()]
    if not toks:
        return None
    strong = [t for t in toks if t in ENT_STRONG]
    weak = [t for t in toks if t in ENT_WEAK]
    rest = [t for t in toks if t not in ENT_STRONG and t not in ENT_WEAK and t not in ID_SUFFIXES]
    if rest:  # descriptive name such as patient_age or device_type: a feature, not an identifier
        return None
    if strong:
        if all(t in ENT_NEEDS_ID for t in strong) and not any(t in ID_SUFFIXES for t in toks):
            return "weak"  # `device` alone is usually a device type; `device_id` is an identifier
        return "strong"
    return "weak" if weak else None


def time_name(name: str) -> bool:
    toks = [t for t in tokens(name) if not t.isdigit()]
    return bool(toks) and (bool(set(toks) & _STRONG_TIME) or all(t in TIME_TOKENS for t in toks))


def is_metric(name: str) -> bool:
    return (
        (name.endswith(METRIC_SUFFIXES) or name in METRIC_NAMES)
        and name not in CV_HELPERS
        and name not in NON_SCALAR_METRICS
        and name != "make_scorer"
    )


def is_model_name(name: str) -> bool:
    return bool(name) and name[0].isupper() and any(s in name for s in MODEL_SUFFIXES)


def join(vals: list[AVal]) -> AVal:
    vals = [v for v in vals if v is not UNKNOWN]
    if not vals:
        return UNKNOWN
    scores = [v for v in vals if isinstance(v, Score)]
    if scores:
        return Score(frozenset().union(*(s.events for s in scores)))
    for cls in (Data, Est, SplitterV, PathV):
        for v in vals:
            if isinstance(v, cls):
                return v
    first = vals[0]
    if isinstance(first, Str | Num | Const):
        return first if all(v == first for v in vals) else UNKNOWN
    return first


def str_list(v: AVal) -> list[str] | None:
    if isinstance(v, Str):
        return [v.value]
    if isinstance(v, ListV) and v.kind != "dict" and v.items and all(isinstance(i, Str) for i in v.items):
        return [i.value for i in v.items]
    if isinstance(v, Cols) and v.names is not None:
        return list(v.names)
    return None


def num(v: AVal | None) -> float | int | None:
    return v.value if isinstance(v, Num) else None


def is_true(v: AVal | None) -> bool:
    return isinstance(v, Const) and v.value is True


def is_false(v: AVal | None) -> bool:
    return isinstance(v, Const) and v.value is False


def collect_events(v: AVal, depth: int = 0) -> set[EvalEvent]:
    if depth > 6:
        return set()
    if isinstance(v, Score):
        return set(v.events)
    if isinstance(v, ListV):
        out: set[EvalEvent] = set()
        for i in v.items + v.keys:
            out |= collect_events(i, depth + 1)
        return out
    if isinstance(v, Iter):
        return collect_events(v.elem, depth + 1)
    if isinstance(v, Bound):
        return collect_events(v.recv, depth + 1)
    return set()


class Analyzer:
    def __init__(self, src: Source):
        self.src = src
        self.scopes: list[dict[str, AVal]] = [{}]
        self.findings: dict[tuple[str, int], Finding] = {}
        self.loops: list[int] = []
        self.path_loops: set[int] = set()
        self.loop_origins: dict[int, Origin] = {}
        self.rets: list[list[AVal]] = []
        self.call_stack: list[ast.AST] = []
        self.stmt_line = (1, 1)
        self.n_origin = 0
        self.n_split = 0
        self.steps = 0
        self.manual: dict[tuple, Split] = {}
        self.cat_names: set[str] = set()
        self.origins: list[Origin] = []
        self.truncated = False
        self.attr_coll: dict[str, str] = {}  # collection name -> entity attribute of its items (handwritten.py)
        self.attr_data: dict[str, Data] = {}
        self.called: set[ast.AST] = set()

    # ------------------------------------------------------------------ driver

    def run(self) -> list[Finding]:
        if self.src.tree is None:
            return []
        tree = self.src.tree
        self.attr_coll = handwritten.attribute_entities(tree, entity_strength)
        try:
            self.block(tree.body)
            self.uncalled_functions(tree)
        except (Budget, RecursionError):
            self.truncated = True
        self.within_entity(tree)
        return self.finish()

    def uncalled_functions(self, tree: ast.Module) -> None:
        """Module-level functions the file never calls are analysed once with unknown arguments (research code
        often defines its experiment in functions driven from another file)."""
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node not in self.called:
                self.stmt_line = (node.lineno, node.end_lineno or node.lineno)
                self.call_func(FuncV(node), [])

    def within_entity(self, tree: ast.Module) -> None:
        for w in handwritten.within_entity_splits(tree, entity_strength):
            ent = w["entity"]
            self.emit(
                "group",
                "LL-GRP-005",
                (w["line"], w["end_line"]),
                "within_entity_split",
                "medium",
                f"Each `{ent}` contributes rows to both sides: the loop from line {w['loop_line']} sends a first part "
                f"of every {ent}'s rows to `{w['head']}` and the rest to `{w['tail']}`. The score "
                f"measures performance on {ent}s seen in training; this is legitimate only if the model is meant "
                f"for those same {ent}s.",
                [{"kind": "split_call", "detail": f"per-{ent} split in a loop (line {w['loop_line']})"},
                 {"kind": "entity_column", "detail": f"`{ent}` (grouping key, name evidence)"}],
                f"Hold out whole {ent}s (GroupShuffleSplit, or leave-one-{ent}-out) if the claim is about new {ent}s.",
                "replace_splitter:GroupShuffleSplit",
                {"entity_columns": [ent], "entity_strengths": {ent: "strong"}},
            )

    # ------------------------------------------------------------------ hand-written random splits

    def attr_collection(self, name: str) -> Data:
        d = self.attr_data.get(name)
        if d is None:
            attr = self.attr_coll[name]
            o = self.new_origin(f"items of `{name}`")
            o.entity[attr] = (f"`{attr}` attribute of the items of `{name}`", "strong")
            d = self.attr_data[name] = Data(o, Rows("all", None, o.id), "array")
        return d

    def new_draw(self, node: ast.Call, call: str) -> DrawV:
        data = None
        kws = {k.arg: k.value for k in node.keywords}
        if call.endswith("uniform"):  # uniform(low, high, size)
            size = kws.get("size", node.args[2] if len(node.args) > 2 else None)
        else:
            size = kws.get("size", node.args[0] if node.args else None)
        if isinstance(size, ast.Call) and isinstance(size.func, ast.Name) and size.func.id == "len" and size.args:
            data = self.to_data(self.ev(size.args[0]))
        elif isinstance(size, ast.Subscript) and isinstance(size.value, ast.Attribute) and size.value.attr == "shape":
            data = self.to_data(self.ev(size.value.value))
        return DrawV(self.stmt_line[0], self.stmt_line[1], call, data)

    def mask_select(self, d: Data, mask: MaskV) -> Data:
        draw = mask.draw
        sp = draw.split
        if sp is None:
            sp = draw.split = self.new_split(
                f"random mask ({draw.call})", d.rows, d.origin, row_level=True, checked=False,
                info={"manual": True, "mask": True, "roles": set()},
            )
            sp.line, sp.end_line = mask.line, mask.end_line
        role = mask.role or {"low": "train", "high": "test", "mid": "test"}[mask.side]
        sp.info["roles"].add(role)
        if {"train", "test"} <= sp.info["roles"] and not sp.info.get("confirmed"):
            sp.info["confirmed"] = True
            self.check_split(sp, d, None)
        return replace(d, rows=Rows(role, sp, d.origin.id), subset=False)

    def finish(self) -> list[Finding]:
        out = sorted(self.findings.values(), key=lambda f: (f.flat_line_start, f.type))
        lines = self.src.flat.splitlines()
        by_line: dict[int, list[Finding]] = {}
        for f in out:
            cell, line = self.src.locate(f.flat_line_start)
            cell_end, line_end = self.src.locate(f.flat_line_end)
            if cell_end != cell:  # a finding never spans cells
                f.flat_line_end, line_end = f.flat_line_start, line
            f.cell, f.line_start, f.line_end = cell, line, line_end
            text = "\n".join(" ".join(ln.split()) for ln in lines[f.flat_line_start - 1 : f.flat_line_end])
            f.set_id(text)
            for ln in lines[f.flat_line_start - 1 : f.flat_line_end]:
                m = _SUPPRESS.search(ln)
                if m:
                    kinds = {k.strip() for k in m.group(1).split(",")} if m.group(1) else None
                    if kinds is None or f.type in kinds:
                        f.suppressed = {"by": "inline", "reason": (m.group(2) or "").strip() or None}
            by_line.setdefault(f.flat_line_start, []).append(f)
        for group in by_line.values():
            for f in group:
                f.related = sorted(g.id for g in group if g is not f)
        return out

    # ------------------------------------------------------------------ environment

    def get(self, name: str) -> AVal | None:
        if name in self.scopes[-1]:
            return self.scopes[-1][name]
        return self.scopes[0].get(name)

    def set(self, name: str, val: AVal) -> None:
        self.scopes[-1][name] = val

    def new_origin(self, source: str) -> Origin:
        self.n_origin += 1
        o = Origin(self.n_origin, self.stmt_line[0], source)
        self.origins.append(o)
        return o

    def fresh(self, source: str, kind: str = "frame") -> Data:
        o = self.new_origin(source)
        return Data(o, Rows("all", None, o.id), kind)

    def new_split(self, call: str, parent: Rows, origin: Origin | None, **kw) -> Split:
        self.n_split += 1
        return Split(self.n_split, self.stmt_line[0], self.stmt_line[1], call, parent, origin, **kw)

    # ------------------------------------------------------------------ evidence bookkeeping

    def note_col(self, o: Origin, name: str) -> ColFact:
        fact = o.cols.get(name)
        if fact is None:
            fact = o.cols[name] = ColFact(name)
            s = entity_strength(name)
            if s and name not in o.entity:
                o.entity[name] = (f"column `{name}` (name evidence)", s)
            if time_name(name) and name not in o.time_cols:
                o.time_cols[name] = "name"
        return fact

    def note_time(self, o: Origin, name: str | None) -> None:
        if name:
            self.note_col(o, name)
            o.time_cols[name] = "parsed"
        else:
            o.time_index = "parsed"

    def note_path_entity(self, o: Origin, name: str, pv: PathV, multi_rows: bool) -> None:
        if not (multi_rows or pv.part == "group"):
            return  # one row per file and the whole file name: unique per row, not a repeated entity
        strong = entity_strength(name) == "strong" or multi_rows
        o.entity[name] = (f"`{name}` is derived from file or folder names", "strong" if strong else "weak")
        o.file_entities.add(name)

    # ------------------------------------------------------------------ statements

    def block(self, stmts: list[ast.stmt]) -> None:
        for s in stmts:
            self.stmt(s)

    def stmt(self, s: ast.stmt) -> None:
        self.steps += 1
        if self.steps > MAX_STATEMENTS:
            raise Budget
        prev = self.stmt_line
        self.stmt_line = (s.lineno, s.end_lineno or s.lineno)
        try:
            self._stmt(s)
        except (Budget, RecursionError):
            raise
        except Exception:  # keep going with the next statement
            if DEBUG:
                raise
        finally:
            self.stmt_line = prev

    def _stmt(self, s: ast.stmt) -> None:
        if isinstance(s, ast.Import):
            for a in s.names:
                self.set(a.asname or a.name.split(".")[0], Ref(a.name if a.asname else a.name.split(".")[0]))
        elif isinstance(s, ast.ImportFrom):
            for a in s.names:
                if a.name != "*":
                    self.set(a.asname or a.name, Ref(f"{s.module or ''}.{a.name}"))
        elif isinstance(s, ast.FunctionDef | ast.AsyncFunctionDef):
            self.set(s.name, FuncV(s))
        elif isinstance(s, ast.ClassDef):
            self.set(s.name, Ref(f"<class>.{s.name}"))
        elif isinstance(s, ast.Assign):
            v = self.ev(s.value)
            for t in s.targets:
                self.assign(t, v)
        elif isinstance(s, ast.AugAssign):
            cur = self.ev(s.target) if isinstance(s.target, ast.Name | ast.Subscript | ast.Attribute) else UNKNOWN
            self.assign(s.target, self.binop(cur, self.ev(s.value), s.op))
        elif isinstance(s, ast.AnnAssign):
            if s.value is not None:
                self.assign(s.target, self.ev(s.value))
        elif isinstance(s, ast.Expr):
            self.ev(s.value)
        elif isinstance(s, ast.For | ast.AsyncFor):
            self.stmt_line = (s.lineno, s.iter.end_lineno or s.lineno)
            elem = self.elem_of(self.ev(s.iter))
            self.loops.append(id(s))
            try:
                elem = self.path_hint(s.target, elem)
                if isinstance(elem, PathV) or (
                    isinstance(elem, ListV) and any(isinstance(i, PathV) for i in elem.items)
                ):
                    self.path_loops.add(id(s))
                self.assign(s.target, elem)
                self.block(s.body)
            finally:
                self.loops.pop()
            self.block(s.orelse)
        elif isinstance(s, ast.While):
            self.stmt_line = (s.lineno, s.test.end_lineno or s.lineno)
            self.loops.append(id(s))
            try:
                self.test(s.test)
                self.block(s.body)
            finally:
                self.loops.pop()
            self.block(s.orelse)
        elif isinstance(s, ast.If):
            self.stmt_line = (s.lineno, s.test.end_lineno or s.lineno)
            self.test(s.test)
            self.block(s.body)
            self.block(s.orelse)
        elif isinstance(s, ast.With | ast.AsyncWith):
            for item in s.items:
                v = self.ev(item.context_expr)
                if item.optional_vars is not None:
                    self.assign(item.optional_vars, v)
            self.block(s.body)
        elif isinstance(s, ast.Try):
            self.block(s.body)
            for h in s.handlers:
                self.block(h.body)
            self.block(s.orelse)
            self.block(s.finalbody)
        elif isinstance(s, ast.Return):
            if self.rets:
                self.rets[-1].append(self.ev(s.value) if s.value is not None else Const(None))
        elif isinstance(s, ast.Match):
            for case in s.cases:
                self.block(case.body)
        elif isinstance(s, ast.Assert):
            self.ev(s.test)

    def test(self, node: ast.expr) -> None:
        """A comparison of a score computed in the enclosing loop selects among candidates."""
        if self.loops:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare):
                    vals = [self.ev(sub.left)] + [self.ev(c) for c in sub.comparators]
                    events = set().union(*(collect_events(v) for v in vals))
                    if events:
                        self.select(events, "comparison with the best score so far")
                    return
        self.ev(node)

    def path_hint(self, target: ast.expr, elem: AVal) -> AVal:
        """A loop variable named like a file name is treated as file-derived when nothing better is known."""

        def hinted(t: ast.expr, v: AVal) -> AVal:
            if (
                isinstance(t, ast.Name)
                and not isinstance(v, Data | PathV | Est | Score)
                and set(tokens(t.id)) & PATH_NAMES
            ):
                return PathV("whole", True)
            return v

        if isinstance(target, ast.Name):
            return hinted(target, elem)
        if isinstance(target, ast.Tuple | ast.List):
            items = self.unpack(elem, len(target.elts))
            return ListV([hinted(t, v) for t, v in zip(target.elts, items, strict=False)], "tuple")
        return elem

    # ------------------------------------------------------------------ assignment

    def unpack(self, value: AVal, n: int) -> list[AVal]:
        if isinstance(value, ListV) and value.kind != "dict":
            items = list(value.items[:n])
            return items + [UNKNOWN] * (n - len(items))
        if isinstance(value, Iter):
            return self.unpack(value.elem, n) if isinstance(value.elem, ListV) else [value.elem] * n
        if isinstance(value, Data | Score):
            return [value] * n
        return [UNKNOWN] * n

    def assign(self, target: ast.expr, value: AVal) -> None:
        if isinstance(target, ast.Name):
            self.set(target.id, self.hint_role(target.id, value))
        elif isinstance(target, ast.Tuple | ast.List):
            items = self.unpack(value, len(target.elts))
            for t, v in zip(target.elts, items, strict=False):
                self.assign(t.value if isinstance(t, ast.Starred) else t, v)
        elif isinstance(target, ast.Subscript):
            self.assign_subscript(target, value)
        elif isinstance(target, ast.Attribute):
            base = self.ev(target.value)
            if isinstance(base, Data):
                if target.attr == "index":
                    if isinstance(value, Data) and value.is_time:
                        base.origin.time_index = "parsed"
                elif target.attr != "columns" and base.kind == "frame":
                    self.assign_col(base, target.attr, value, target.value)

    def hint_role(self, name: str, value: AVal) -> AVal:
        """A row subset stored under a name like `test_df` or `X_val` is one side of a manual split."""
        if isinstance(value, MaskV):
            toks = set(tokens(name))
            role = "train" if toks & HINT_TRAIN else "test" if toks & (HINT_TEST | HINT_VAL) else None
            return replace(value, role=role) if role else value
        if not isinstance(value, Data):
            return value
        toks = set(tokens(name))
        role = "train" if toks & HINT_TRAIN else "test" if toks & (HINT_TEST | HINT_VAL) else None
        if role is None:
            return value
        sp = value.rows.split
        if sp is not None and (sp.info.get("positional") or sp.info.get("manual")) and value.rows.role != role:
            if value.rows.role in ("train", "test"):
                return replace(value, rows=Rows(role, sp, value.rows.oid))
        if value.subset and value.rows.role == "all" and not value.is_stat:
            key = (value.origin.id, value.rows, "hint")
            sp = self.manual.get(key)
            if sp is None:
                sp = self.manual[key] = self.new_split(
                    "manual subset", value.rows, value.origin, row_level=False, checked=True, info={"hint": True}
                )
            return replace(value, rows=Rows(role, sp, value.origin.id), subset=False)
        return value

    def assign_subscript(self, target: ast.Subscript, value: AVal) -> None:
        base = self.ev(target.value)
        if isinstance(base, Indexer):
            sl = target.slice
            col = self.ev(sl.elts[1]) if isinstance(sl, ast.Tuple) and len(sl.elts) == 2 else None
            node = target.value.value if isinstance(target.value, ast.Attribute) else None
            if isinstance(col, Str):
                self.assign_col(base.data, col.value, value, node, partial=True)
            elif node is not None:
                self.taint_frame(node, base.data, value)
            return
        if isinstance(base, Data):
            key = UNKNOWN if isinstance(target.slice, ast.Slice) else self.ev(target.slice)
            if isinstance(key, Str) and base.kind == "frame":
                self.assign_col(base, key.value, value, target.value)
            else:
                self.taint_frame(target.value, base, value)
            return
        if isinstance(base, ListV):
            base.items.append(value)
            if base.kind == "dict" and not isinstance(target.slice, ast.Slice):
                base.keys.append(self.ev(target.slice))

    def assign_col(self, data: Data, c: str, value: AVal, node: ast.expr | None, partial: bool = False) -> None:
        o = data.origin
        old = o.cols.get(c)
        self.note_col(o, c)
        new = ColFact(c, True, self.stmt_line[0], self.stmt_line[1])
        if isinstance(value, Data):
            selfdep = c in value.deps
            new.deps = set(value.deps) - {c}
            new.fwd = list(value.fwd)
            new.taints = set(value.taints)
            new.thresholded, new.shifted = value.thresholded, value.shifted
            if value.shifted:
                o.ordered_ops.add(f"lag, window or fill feature `{c}`")
            if value.is_stat:
                t = self.stat_taint(value)
                if t is not None:
                    new.taints.add(t)
            if value.is_time:
                self.note_time(o, c)
            if (selfdep or partial) and old is not None:
                new.deps |= old.deps
                new.fwd = old.fwd + [f for f in new.fwd if f not in old.fwd]
                new.taints |= old.taints
                new.shifted = new.shifted or old.shifted
                if old.assigned:
                    new.line, new.end_line = old.line, old.end_line
        elif isinstance(value, PathV):
            self.note_path_entity(o, c, value, multi_rows=True)
        elif partial and old is not None:
            new = old
        o.cols[c] = new
        if isinstance(node, ast.Name):
            cur = self.get(node.id)
            if isinstance(cur, Data) and cur.cols is not None:
                cols = cur.cols
                cols = (
                    replace(cols, names=cols.names + (c,))
                    if cols.names is not None and c not in cols.names
                    else replace(cols, base=cols.base | {c}, minus=cols.minus - {c})
                )
                self.set(node.id, replace(cur, cols=cols))

    def taint_frame(self, node: ast.expr, data: Data, value: AVal) -> None:
        if not isinstance(value, Data):
            return
        taints = data.taints | value.taints
        if value.is_stat:
            t = self.stat_taint(value)
            if t is not None:
                taints |= {t}
        if taints == data.taints and not value.fwd:
            return
        new = replace(data, taints=taints, fwd=tuple(dict.fromkeys(data.fwd + value.fwd)))
        if isinstance(node, ast.Name):
            self.set(node.id, new)
        elif isinstance(node, ast.Subscript | ast.Attribute):  # df[cols][...] = v or df.loc[...]: taint the root
            self.taint_frame(node.value, new, value)

    # ------------------------------------------------------------------ expressions

    def ev(self, node: ast.expr | None) -> AVal:
        if node is None:
            return UNKNOWN
        try:
            return self._ev(node)
        except (Budget, RecursionError):
            raise
        except Exception:  # an unmodelled construct must never abort the scan
            if DEBUG:
                raise
            return UNKNOWN

    def _ev(self, node: ast.expr) -> AVal:
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, str):
                return Str(v)
            if isinstance(v, bool) or v is None:
                return Const(v)
            if isinstance(v, int | float):
                return Num(v)
            return UNKNOWN
        if isinstance(node, ast.Name):
            v = self.get(node.id)
            if node.id in self.attr_coll and not isinstance(v, Data | FuncV | Ref):
                return self.attr_collection(node.id)
            return Ref(node.id) if v is None else v
        if isinstance(node, ast.Attribute):
            return self.ev_attribute(node)
        if isinstance(node, ast.Subscript):
            return self.ev_subscript(node)
        if isinstance(node, ast.Call):
            return self.ev_call(node)
        if isinstance(node, ast.BinOp):
            return self.binop(self.ev(node.left), self.ev(node.right), node.op)
        if isinstance(node, ast.UnaryOp):
            v = self.ev(node.operand)
            if isinstance(v, MaskV) and isinstance(node.op, ast.Invert):
                return replace(v, side={"low": "high", "high": "low", "mid": "mid"}[v.side], role=None)
            if isinstance(v, Num) and isinstance(node.op, ast.USub) and v.value is not None:
                return Num(-v.value)
            return v if isinstance(v, Data | Score) else UNKNOWN
        if isinstance(node, ast.Compare):
            vals = [self.ev(node.left)] + [self.ev(c) for c in node.comparators]
            if len(node.ops) == 1 and any(isinstance(v, DrawV) for v in vals):
                op = node.ops[0]
                lower = isinstance(op, ast.Lt | ast.LtE) == isinstance(vals[0], DrawV)
                draw = vals[0] if isinstance(vals[0], DrawV) else vals[1]
                if isinstance(op, ast.Lt | ast.LtE | ast.Gt | ast.GtE):
                    return MaskV(draw, "low" if lower else "high", *self.stmt_line)
            datas = [v for v in vals if isinstance(v, Data)]
            if datas:
                out = datas[0]
                for d in datas[1:]:
                    out = self.combine(out, d)
                return replace(out, thresholded=True, kind="series" if out.kind == "frame" and out.col else out.kind)
            return UNKNOWN
        if isinstance(node, ast.BoolOp):
            vals = [self.ev(v) for v in node.values]
            datas = [v for v in vals if isinstance(v, Data)]
            if datas:
                out = datas[0]
                for d in datas[1:]:
                    out = self.combine(out, d)
                return out
            return join(vals)
        if isinstance(node, ast.IfExp):
            self.ev(node.test)
            return join([self.ev(node.body), self.ev(node.orelse)])
        if isinstance(node, ast.List | ast.Tuple | ast.Set):
            items = [self.ev(e.value if isinstance(e, ast.Starred) else e) for e in node.elts]
            return ListV(items, {ast.List: "list", ast.Tuple: "tuple", ast.Set: "set"}[type(node)])
        if isinstance(node, ast.Dict):
            keys = [self.ev(k) if k is not None else UNKNOWN for k in node.keys]
            return ListV([self.ev(v) for v in node.values], "dict", keys)
        if isinstance(node, ast.ListComp | ast.GeneratorExp | ast.SetComp | ast.DictComp):
            return self.ev_comp(node)
        if isinstance(node, ast.Lambda):
            return FuncV(node)
        if isinstance(node, ast.JoinedStr):
            parts = [self.ev(v.value) for v in node.values if isinstance(v, ast.FormattedValue)]
            pv = [p for p in parts if isinstance(p, PathV)]
            return pv[0] if pv else UNKNOWN
        if isinstance(node, ast.NamedExpr):
            v = self.ev(node.value)
            self.assign(node.target, v)
            return v
        if isinstance(node, ast.Starred | ast.Await):
            return self.ev(node.value)
        return UNKNOWN

    def binop(self, left: AVal, right: AVal, op: ast.operator) -> AVal:
        if isinstance(left, MaskV) and isinstance(right, MaskV) and left.draw is right.draw:
            if isinstance(op, ast.BitAnd) and left.side != right.side:
                return replace(left, side="mid", role=None)
            return left
        if isinstance(left, Data) and isinstance(right, Data):
            return self.combine(left, right)
        if isinstance(left, Data):
            return left
        if isinstance(right, Data):
            return right
        if isinstance(left, Score) or isinstance(right, Score):
            return join([left, right])
        if isinstance(op, ast.Add):
            if isinstance(left, ListV) and isinstance(right, ListV) and "dict" not in (left.kind, right.kind):
                return ListV(left.items + right.items, left.kind)
            if isinstance(left, Cols) or isinstance(right, Cols):
                cols, other = (left, right) if isinstance(left, Cols) else (right, left)
                extra = str_list(other)
                if extra is None:
                    return replace(cols, uncertain=True)
                if cols.names is not None:
                    return replace(cols, names=cols.names + tuple(e for e in extra if e not in cols.names))
                return replace(
                    cols, base=cols.base | set(extra), minus=cols.minus - set(extra), sure=cols.sure | set(extra)
                )
            if isinstance(left, Str) and isinstance(right, Str):
                return Str(left.value + right.value)
        if isinstance(op, ast.Mult):
            lst, k = (left, right) if isinstance(left, ListV) else (right, left)
            if isinstance(lst, ListV) and lst.kind != "dict" and isinstance(k, Num):
                reps = 2 if k.value is None or k.value >= 2 else int(k.value)
                return ListV(lst.items * max(reps, 0), lst.kind)
        if isinstance(op, ast.Sub) and isinstance(left, ListV | Cols):
            return left
        if isinstance(left, PathV) or isinstance(right, PathV):
            return left if isinstance(left, PathV) else right
        if isinstance(left, Num) and isinstance(right, Num):
            return Num(None)
        return UNKNOWN

    def stat_taint(self, s: Data) -> Taint | None:
        if s.stat_src is None:
            return None
        return Taint(
            "pre",
            self.stmt_line[0],
            self.stmt_line[1],
            "a statistic computed over rows is applied to the data",
            s.stat_src,
            confidence="medium",
            stat_cols=s.stat_cols,
            subtype="pandas_stats",
        )

    def combine(self, a: Data, b: Data) -> Data:
        """Result of an operation on two data values: `a`'s rows unless `a` is only a statistic."""
        taints = a.taints | b.taints
        primary = a
        if b.is_stat and not a.is_stat:
            t = self.stat_taint(b)
            taints |= {t} if t else set()
        elif a.is_stat and not b.is_stat:
            primary = b
            t = self.stat_taint(a)
            taints |= {t} if t else set()
        return replace(
            primary,
            taints=taints,
            deps=a.deps | b.deps,
            fwd=tuple(dict.fromkeys(a.fwd + b.fwd)),
            shifted=a.shifted or b.shifted,
            thresholded=a.thresholded or b.thresholded,
            is_stat=a.is_stat and b.is_stat,
        )

    def combine_args(self, d: Data, args: list[AVal], kw: dict[str, AVal]) -> Data:
        out = d
        for a in list(args) + list(kw.values()):
            if isinstance(a, Data):
                out = self.combine(out, a)
        return out

    # -- attributes ------------------------------------------------------------

    def ev_attribute(self, node: ast.Attribute) -> AVal:
        base = self.ev(node.value)
        attr = node.attr
        if isinstance(base, Ref):
            return Ref(f"{base.qual}.{attr}")
        if isinstance(base, Data):
            return self.data_attr(base, attr)
        if isinstance(base, Est):
            if attr == "best_estimator_":
                return base.inner or base
            if attr == "best_score_" and base.fit is not None:
                return Score(
                    frozenset(
                        {
                            EvalEvent(
                                base.fit.line,
                                base.fit.end_line,
                                "cv",
                                base.fit.rows,
                                (),
                                False,
                                f"{base.cls}.best_score_",
                            )
                        }
                    )
                )
            return Bound(base, attr)
        if isinstance(base, PathV):
            return PathV("group" if attr in ("parent", "parents", "parts") else base.part, base.multi)
        if isinstance(base, Score):
            return base
        if isinstance(base, ListV | SplitterV | Indexer | Cols | Iter):
            return Bound(base, attr)
        return UNKNOWN

    def data_attr(self, d: Data, attr: str) -> AVal:
        o = d.origin
        if attr in ("iloc", "loc", "at", "iat"):
            return Indexer(d, attr)
        if attr == "columns":
            return self.cols_of(d)
        if attr == "index":
            return replace(d, kind="index", cols=None, col=None, is_time=o.time_index == "parsed", deps=frozenset())
        if attr in ("values", "array", "T"):
            return replace(d, kind="array")
        if attr == "dt":
            if d.col:
                self.note_time(o, d.col)
            return replace(d, is_time=False)
        if attr in _FRAME_PROPS_UNKNOWN:
            return UNKNOWN
        if d.kind == "bunch":
            if attr in ("data", "frame", "images"):
                return replace(d, kind="frame")
            if attr == "target":
                return replace(d, kind="series", col="target")
            return UNKNOWN
        if (
            d.kind == "frame"
            and attr.isidentifier()
            and not attr.startswith("_")
            and attr not in ("str", "cat", "plot")
        ):
            return self.read_col(d, attr)
        return d

    def cols_of(self, d: Data) -> Cols:
        if d.cols is not None:
            return d.cols
        return Cols(None, frozenset(d.origin.cols), frozenset())

    def read_col(self, d: Data, c: str) -> Data:
        o = d.origin
        self.note_col(o, c)
        return replace(
            d,
            kind="series",
            col=c,
            cols=None,
            deps=frozenset({c}),
            fwd=(),
            is_time=o.time_cols.get(c) == "parsed",
            is_stat=False,
            thresholded=False,
            shifted=False,
        )

    # -- subscripts ------------------------------------------------------------

    def ev_subscript(self, node: ast.Subscript) -> AVal:
        base = self.ev(node.value)
        sl = node.slice
        if isinstance(sl, ast.Name | ast.Compare | ast.UnaryOp | ast.BinOp):
            key = self.ev(sl)
            if isinstance(key, MaskV):
                return self.mask_select(base, key) if isinstance(base, Data) else base
        if isinstance(base, Data):
            return self.data_index(base, sl)
        if isinstance(base, Indexer):
            return self.indexer_get(base, sl)
        if isinstance(base, ListV):
            if isinstance(sl, ast.Slice):
                return base
            key = self.ev(sl)
            if base.kind == "dict" and isinstance(key, Str):
                for k, v in zip(base.keys, base.items, strict=False):
                    if k == key:
                        return v
            if base.kind != "dict" and isinstance(key, Num) and isinstance(key.value, int):
                if -len(base.items) <= key.value < len(base.items):
                    return base.items[key.value]
            return join(base.items)
        if isinstance(base, PathV):
            return PathV("group", base.multi)
        if isinstance(base, Score):
            return base
        if isinstance(base, Cols):
            return replace(base, uncertain=True)
        if isinstance(base, Iter):
            return base.elem
        return UNKNOWN

    def data_index(self, d: Data, sl: ast.expr) -> AVal:
        if isinstance(sl, ast.Slice):
            return self.row_slice(d, sl)
        if isinstance(sl, ast.Tuple) and sl.elts:
            first = sl.elts[0]
            out = self.row_slice(d, first) if isinstance(first, ast.Slice) else self.row_select(d, self.ev(first))
            if d.cols is not None and len(sl.elts) > 1:
                out = replace(out, cols=replace(d.cols, uncertain=True))
            return out
        key = self.ev(sl)
        if d.kind in ("frame", "bunch") or d.window == "groupby":
            if isinstance(key, Str):
                return self.read_col(d, key.value)
            names = str_list(key)
            if names is not None:
                for n in names:
                    self.note_col(d.origin, n)
                return replace(d, kind="frame", cols=Cols(tuple(names)), col=None, deps=d.deps | set(names))
            if isinstance(key, Cols):
                return replace(d, kind="frame", cols=key, col=None)
        return self.row_select(d, key)

    def positional(self, d: Data) -> Split:
        key = (d.origin.id, d.rows, "pos")
        sp = self.manual.get(key)
        if sp is None:
            chrono = d.origin.shuffled_line is None
            sp = self.manual[key] = self.new_split(
                "positional slice",
                d.rows,
                d.origin,
                row_level=True,
                chronological=chrono,
                checked=True,
                info={"positional": True},
            )
        return sp

    def row_slice(self, d: Data, sl: ast.Slice) -> Data:
        step = num(self.ev(sl.step)) if sl.step is not None else None
        if step is not None and step < 0:
            return replace(d, reversed=not d.reversed)
        if (sl.lower is None and sl.upper is None) or d.window is not None or d.is_stat:
            return d
        if sl.lower is not None and sl.upper is not None:
            return replace(d, subset=True)
        k = num(self.ev(sl.upper if sl.lower is None else sl.lower))
        if k is not None and abs(k) <= TRIM_MAX:
            return replace(d, subset=True)  # dropping a few first or last rows is a trim, not a split
        side = "train" if sl.lower is None else "test"
        return replace(d, rows=Rows(side, self.positional(d), d.origin.id), subset=False)

    def row_select(self, d: Data, key: AVal) -> Data:
        if isinstance(key, Data):
            kr = key.rows
            if key.kind == "index" and kr.split is not None and kr.role in ("train", "test") and kr != d.rows:
                return replace(d, rows=Rows(kr.role, kr.split, d.origin.id), subset=False)
            return replace(d, subset=True)
        if key is UNKNOWN or isinstance(key, Cols):
            return d
        return replace(d, subset=True)

    def indexer_get(self, ix: Indexer, sl: ast.expr) -> AVal:
        d = ix.data
        rsel, csel = (sl.elts[0], sl.elts[1]) if isinstance(sl, ast.Tuple) and len(sl.elts) == 2 else (sl, None)
        out = self.row_slice(d, rsel) if isinstance(rsel, ast.Slice) else self.row_select(d, self.ev(rsel))
        if csel is not None:
            if isinstance(csel, ast.Slice):
                if not (csel.lower is None and csel.upper is None):
                    out = replace(out, cols=replace(self.cols_of(out), uncertain=True))
            else:
                ck = self.ev(csel)
                names = str_list(ck)
                if isinstance(ck, Str):
                    return self.read_col(out, ck.value)
                if names is not None:
                    for n in names:
                        self.note_col(d.origin, n)
                    return replace(out, kind="frame", cols=Cols(tuple(names)), col=None)
                if isinstance(ck, Cols):
                    return replace(out, kind="frame", cols=ck, col=None)
                if isinstance(ck, Num):
                    return replace(out, kind="series", cols=None, col=None)
                out = replace(out, cols=replace(self.cols_of(out), uncertain=True))
        return out

    # -- comprehensions --------------------------------------------------------

    def ev_comp(self, node: ast.ListComp | ast.GeneratorExp | ast.SetComp | ast.DictComp) -> AVal:
        gen = node.generators[0]
        it = self.ev(gen.iter)
        if (
            not isinstance(node, ast.DictComp)
            and len(node.generators) == 1
            and isinstance(node.elt, ast.Name)
            and isinstance(gen.target, ast.Name)
            and node.elt.id == gen.target.id
        ):
            t = gen.target.id
            if isinstance(it, Cols) and it.names is None:
                minus, uncertain, sure = set(), it.uncertain, set(it.sure)
                for cond in gen.ifs:
                    ex = self.excluded_by(cond, t)
                    if ex is None:
                        uncertain = True
                    else:
                        minus |= ex
                if uncertain:  # the filter is not resolved in general; decide the columns we do know
                    sure = set()
                    for c in it.base - it.minus - minus:
                        verdicts = [self.truth(cond, t, c) for cond in gen.ifs]
                        if False in verdicts:
                            minus.add(c)
                        elif None not in verdicts:
                            sure.add(c)
                return replace(it, minus=it.minus | minus, uncertain=uncertain, sure=frozenset(sure))
            names = str_list(it)
            if names is not None:
                kept = [n for n in names if all(self.truth(c, t, n) is not False for c in gen.ifs)]
                return ListV([Str(n) for n in kept], "list")
        self.loops.append(id(node))
        try:
            for g in node.generators:
                elem = self.path_hint(g.target, self.elem_of(self.ev(g.iter)))
                if isinstance(elem, PathV):
                    self.path_loops.add(id(node))
                self.assign(g.target, elem)
                for cond in g.ifs:
                    self.ev(cond)
            if isinstance(node, ast.DictComp):
                return ListV([self.ev(node.value)], "dict", [self.ev(node.key)])
            return ListV([self.ev(node.elt)], "list")
        finally:
            self.loops.pop()

    def excluded_by(self, cond: ast.expr, t: str) -> set[str] | None:
        """Names a column filter such as `c not in (a, b)` or `c != a` removes; None when unknown."""
        if isinstance(cond, ast.BoolOp) and isinstance(cond.op, ast.And):
            out: set[str] = set()
            for v in cond.values:
                ex = self.excluded_by(v, t)
                if ex is None:
                    return None
                out |= ex
            return out
        if isinstance(cond, ast.UnaryOp) and isinstance(cond.op, ast.Not):
            inner = cond.operand
            if isinstance(inner, ast.Compare) and len(inner.ops) == 1 and isinstance(inner.ops[0], ast.In | ast.Eq):
                return self._cmp_names(inner, t)
            return None
        if isinstance(cond, ast.Compare) and len(cond.ops) == 1 and isinstance(cond.ops[0], ast.NotIn | ast.NotEq):
            return self._cmp_names(cond, t)
        return None

    def _cmp_names(self, cmp: ast.Compare, t: str) -> set[str] | None:
        if not (isinstance(cmp.left, ast.Name) and cmp.left.id == t):
            return None
        names = str_list(self.ev(cmp.comparators[0]))
        return set(names) if names is not None else None

    def truth(self, cond: ast.expr, t: str, value: str) -> bool | None:
        if isinstance(cond, ast.BoolOp):
            vals = [self.truth(v, t, value) for v in cond.values]
            if isinstance(cond.op, ast.And):
                return False if False in vals else (None if None in vals else True)
            return True if True in vals else (None if None in vals else False)
        if isinstance(cond, ast.UnaryOp) and isinstance(cond.op, ast.Not):
            r = self.truth(cond.operand, t, value)
            return None if r is None else not r
        if (
            isinstance(cond, ast.Compare)
            and len(cond.ops) == 1
            and isinstance(cond.left, ast.Name)
            and cond.left.id == t
        ):
            names = str_list(self.ev(cond.comparators[0]))
            if names is None:
                return None
            op = cond.ops[0]
            if isinstance(op, ast.In | ast.Eq):
                return value in names
            if isinstance(op, ast.NotIn | ast.NotEq):
                return value not in names
        if (
            isinstance(cond, ast.Call)
            and isinstance(cond.func, ast.Attribute)
            and isinstance(cond.func.value, ast.Name)
            and cond.func.value.id == t
            and cond.args
            and cond.func.attr in ("startswith", "endswith")
        ):
            affixes = str_list(self.ev(cond.args[0]))
            if affixes is not None:
                fn = value.startswith if cond.func.attr == "startswith" else value.endswith
                return fn(tuple(affixes))
        return None

    def elem_of(self, v: AVal) -> AVal:
        if isinstance(v, SplitIter):
            return self.fold(v.split)
        if isinstance(v, Iter):
            return v.elem
        if isinstance(v, ListV):
            return join(v.keys if v.kind == "dict" else v.items)
        if isinstance(v, Data):
            return v if v.kind != "frame" else UNKNOWN
        if isinstance(v, PathV | Score):
            return v
        return UNKNOWN

    def fold(self, split: Split) -> ListV:
        o = split.origin or self.new_origin("split indices")
        return ListV(
            [Data(o, Rows("train", split, o.id), "index"), Data(o, Rows("test", split, o.id), "index")], "tuple"
        )

    # -- calls -----------------------------------------------------------------

    def ev_args(self, node: ast.Call) -> tuple[list[AVal], dict[str, AVal]]:
        args = [self.ev(a.value if isinstance(a, ast.Starred) else a) for a in node.args]
        kw = {k.arg: self.ev(k.value) for k in node.keywords if k.arg}
        return args, kw

    def to_data(self, v: AVal | None, name: str | None = None) -> Data | None:
        if isinstance(v, Data):
            return v
        if isinstance(v, ListV) and v.acc is not None:
            return Data(v.acc, Rows("all", None, v.acc.id), "array", col=name)
        return None

    def as_data(self, n: ast.expr | None, v: AVal | None) -> Data | None:
        """`v` as data. An unresolved variable in a data position is bound to fresh data, so that what happens to
        it later (fit, split, evaluation) is still connected."""
        d = self.to_data(v, n.id if isinstance(n, ast.Name) else None)
        if d is not None or n is None or not (v is UNKNOWN or isinstance(v, Ref)):
            return d
        root = n
        while isinstance(root, ast.Subscript | ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name) and self.get(root.id) in (None, UNKNOWN):
            self.set(root.id, self.fresh("unresolved variable", "array"))
            return self.to_data(self.ev(n))
        return None

    def arg_data(self, node: ast.Call, args: list[AVal], i: int, kw: dict[str, AVal], key: str) -> Data | None:
        """Positional argument i (or keyword `key`) as data; a row-accumulating list keeps its variable name."""
        if i < len(args):
            n = node.args[i]
            return self.as_data(n.value if isinstance(n, ast.Starred) else n, args[i])
        n = next((k.value for k in node.keywords if k.arg == key), None)
        return self.as_data(n, kw.get(key))

    def ev_call(self, node: ast.Call) -> AVal:
        func = node.func
        if isinstance(func, ast.Attribute):
            recv = self.ev(func.value)
            m = func.attr
            if isinstance(recv, Ref):
                return self.call_ref(Ref(f"{recv.qual}.{m}"), node)
            return self.call_method(recv, m, node, func.value)
        f = self.ev(func)
        if isinstance(f, Ref):
            return self.call_ref(f, node)
        if isinstance(f, FuncV):
            return self.call_user(f, node)
        if isinstance(f, Bound):
            return self.call_method(f.recv, f.name, node, None)
        args, kw = self.ev_args(node)
        return self.opaque(args, kw)

    def call_method(self, recv: AVal, m: str, node: ast.Call, recv_node: ast.expr | None) -> AVal:
        args, kw = self.ev_args(node)
        if isinstance(recv, RngV):
            if m in DRAW_FUNCS and (node.args or any(k.arg == "size" for k in node.keywords)):
                return self.new_draw(node, f"rng.{m}")
            return self.opaque(args, kw)
        if isinstance(recv, Data):
            res = self.data_method(recv, m, args, kw, node, recv_node)
            if is_true(kw.get("inplace")) and isinstance(res, Data) and recv_node is not None:
                self.assign(recv_node, res)
            return res
        if isinstance(recv, Est):
            return self.est_method(recv, m, args, kw, node)
        if isinstance(recv, SplitterV):
            return self.splitter_method(recv, m, args, kw, node)
        if isinstance(recv, ListV):
            return self.list_method(recv, m, args, node, recv_node)
        if isinstance(recv, Score):
            if m in SELECT_METHODS:
                self.select(set(recv.events), f".{m}()")
            return recv
        if isinstance(recv, PathV):
            if m in ("glob", "rglob", "iterdir"):
                return Iter(PathV("whole", True))
            return PathV("group" if m in ("split", "rsplit", "partition", "rpartition") else recv.part, recv.multi)
        if isinstance(recv, Cols):
            if m in ("drop", "difference"):
                names = str_list(args[0]) if args else None
                if names is None:
                    return replace(recv, uncertain=True)
                if recv.names is not None:
                    return replace(recv, names=tuple(n for n in recv.names if n not in names))
                return replace(recv, minus=recv.minus | set(names))
            if m in ("tolist", "to_list", "copy", "to_numpy", "unique", "sort_values"):
                return recv
            return replace(recv, uncertain=True)
        if isinstance(recv, Iter):
            return recv
        if isinstance(recv, Indexer):
            return UNKNOWN
        if m in ("glob", "rglob", "iterdir"):
            return Iter(PathV("whole", True))
        if m in ("fit_transform", "fit_resample", "fit_sample") and any(isinstance(a, Data) for a in args):
            return self.est_method(
                Est(
                    "an unrecognised resampler" if "sample" in m else "an unrecognised transformer",
                    "resampler" if "sample" in m else "transformer",
                    self.stmt_line[0],
                    "generic",
                ),
                m,
                args,
                kw,
                node,
            )
        if isinstance(recv, Str) or recv is UNKNOWN:
            pv = [a for a in args if isinstance(a, PathV)]
            if pv and m in ("join", "format", "basename", "dirname"):
                return pv[0]
        return self.opaque(args, kw)

    def opaque(self, args: list[AVal], kw: dict[str, AVal]) -> AVal:
        """An unmodelled call: its result depends on all its data inputs (SPEC section 1)."""
        vals = list(args) + list(kw.values())
        datas = [v for v in vals if isinstance(v, Data)]
        if datas:
            out = datas[0]
            for d in datas[1:]:
                out = self.combine(out, d)
            return out
        events = set().union(*(collect_events(v) for v in vals)) if vals else set()
        return Score(frozenset(events)) if events else UNKNOWN

    def call_user(self, f: FuncV, node: ast.Call) -> AVal:
        args, kw = self.ev_args(node)
        if len(self.call_stack) >= MAX_DEPTH or f.node in self.call_stack:
            return self.opaque(args, kw)
        return self.call_func(f, args, kw)

    def call_func(self, f: FuncV, args: list[AVal], kw: dict[str, AVal] | None = None) -> AVal:
        if len(self.call_stack) >= MAX_DEPTH or f.node in self.call_stack:
            return self.opaque(args, kw or {})
        a = f.node.args
        params = [p.arg for p in a.posonlyargs + a.args]
        scope: dict[str, AVal] = {}
        defaults = [None] * (len(params) - len(a.defaults)) + list(a.defaults)
        for i, p in enumerate(params):
            if i < len(args):
                scope[p] = args[i]
            elif kw and p in kw:
                scope[p] = kw[p]
            else:
                scope[p] = self.ev(defaults[i]) if defaults[i] is not None else UNKNOWN
        for p, dflt in zip(a.kwonlyargs, a.kw_defaults, strict=False):
            scope[p.arg] = kw[p.arg] if kw and p.arg in kw else (self.ev(dflt) if dflt is not None else UNKNOWN)
        if a.vararg:
            scope[a.vararg.arg] = ListV(list(args[len(params) :]), "tuple")
        self.scopes.append(scope)
        self.rets.append([])
        self.call_stack.append(f.node)
        self.called.add(f.node)
        saved = self.stmt_line
        try:
            if isinstance(f.node, ast.Lambda):
                return self.ev(f.node.body)
            self.block(f.node.body)
            rets = self.rets[-1]
            if rets and all(isinstance(r, ListV) and r.kind != "dict" for r in rets):
                n = max(len(r.items) for r in rets)
                return ListV([join([r.items[i] for r in rets if i < len(r.items)]) for i in range(n)], "tuple")
            return join(rets)
        finally:
            self.stmt_line = saved
            self.call_stack.pop()
            self.rets.pop()
            self.scopes.pop()

    def call_ref(self, ref: Ref, node: ast.Call) -> AVal:
        name = ref.name
        args, kw = self.ev_args(node)
        if ref.root in ("numpy", "np") and ".random." in f".{ref.qual}.":
            if name in ("default_rng", "RandomState", "Generator"):
                return RngV()
            if name in DRAW_FUNCS and (node.args or any(k.arg == "size" for k in node.keywords)):
                return self.new_draw(node, f"np.random.{name}")
        if ref.qual.startswith("<class>."):
            return self.opaque(args, kw)
        if name == "train_test_split":
            return self.do_tts(args, kw, node)
        if name in CV_HELPERS:
            return self.do_cv_helper(name, args, kw, node)
        if name in READERS or (name == "load" and ref.root in ("numpy", "np")):
            return self.new_frame(name, args, kw)
        if name.startswith(("load_", "fetch_", "make_")) and ("datasets" in ref.qual or name in _DATASET_MAKERS):
            o = self.new_origin(name)
            d = Data(o, Rows("all", None, o.id), "bunch")
            if is_true(kw.get("return_X_y")) or name.startswith("make_"):
                return ListV([replace(d, kind="array"), replace(d, kind="series", col="target")], "tuple")
            return d
        if name == "DataFrame":
            return self.make_frame(args, kw, node)
        if name in _CONCAT_FUNCS:
            return self.do_concat(name, args, kw)
        if name in ("merge", "merge_asof", "merge_ordered"):
            datas = [a for a in args if isinstance(a, Data)]
            return self.merge(datas[0], datas[1:], kw) if datas else UNKNOWN
        if name == "get_dummies":
            for n in str_list(kw.get("columns", UNKNOWN)) or []:
                self.cat_names.add(n)
            d = self.to_data(args[0]) if args else None
            if d is not None and d.col:
                self.cat_names.add(d.col)
            return d if d is not None else UNKNOWN
        if name == "to_datetime":
            d = self.to_data(args[0]) if args else None
            return replace(d, is_time=True) if d is not None else UNKNOWN
        if name in ("date_range", "bdate_range", "period_range", "timedelta_range"):
            return replace(self.fresh(name, "series"), is_time=True)
        if name == "resample" and "sklearn" in ref.qual or name == "resample" and ref.qual == "resample":
            args = [self.as_data(n, a) or a for n, a in zip(node.args, args, strict=False)]
            return self.do_resample(args, kw)
        if name == "shuffle" and ref.root != "random":
            for a in args:
                if isinstance(a, Data):
                    a.origin.shuffled_line = self.stmt_line[0]
            return args[0] if len(args) == 1 else ListV(list(args), "tuple")
        if name in _PATH_FUNCS:
            return Iter(PathV("whole", True))
        if name in ("basename", "splitext", "stem", "normpath", "abspath", "fspath", "Path", "PurePath"):
            pv = [a for a in args if isinstance(a, PathV)]
            return pv[0] if pv else UNKNOWN
        if name == "dirname":
            pv = [a for a in args if isinstance(a, PathV)]
            return PathV("group", pv[0].multi) if pv else UNKNOWN
        if name in SELECT_FUNCS or name == "sorted":
            vals = list(args) + list(kw.values())
            events = set().union(*(collect_events(v) for v in vals)) if vals else set()
            if events:
                self.select(events, f"{name}()")
                return Score(frozenset(events))
            if name == "sorted" and args:
                return args[0]
        if name in _SEQ_FUNCS:
            return args[0] if args else ListV([], "list" if name == "list" else name)
        if name == "next":
            return self.elem_of(args[0]) if args else UNKNOWN
        if name == "enumerate":
            return Iter(ListV([Num(None), self.elem_of(args[0]) if args else UNKNOWN], "tuple"))
        if name == "zip":
            return Iter(ListV([self.elem_of(a) for a in args], "tuple"))
        if name == "range":
            return Iter(Num(None))
        if name == "len":
            return Num(None)
        if name == "dict":
            return ListV(list(kw.values()), "dict", [Str(k) for k in kw])
        if name in ("int", "float", "str", "bool", "repr"):
            return args[0] if args and isinstance(args[0], PathV | Score | Data) else UNKNOWN
        if name in _SCORE_KEEP and any(collect_events(a) for a in args):
            return Score(frozenset(set().union(*(collect_events(a) for a in args))))
        if name == "unique" and args and isinstance(args[0], Data):
            return replace(args[0], unique_of=args[0].col or "?", kind="array")
        if name in REDUCTIONS and args and isinstance(args[0], Data):
            return self.reduce(
                args[0],
                kw.get(
                    "axis",
                    args[1] if len(args) > 1 and name not in ("quantile", "percentile", "nanpercentile") else None,
                ),
            )
        if name == "clone" and args and isinstance(args[0], Est):
            e = args[0]
            return Est(e.cls, e.kind, self.stmt_line[0], e.flavour, list(e.steps), None, e.inner, e.cv, set(e.params))
        if name in ROW_SPLITTERS | GROUP_SPLITTERS | TIME_SPLITTERS:
            kind = "row" if name in ROW_SPLITTERS else "group" if name in GROUP_SPLITTERS else "time"
            shuffle = True if name in ALWAYS_SHUFFLED or is_true(kw.get("shuffle")) else False
            return SplitterV(name, kind, self.stmt_line[0], self.stmt_line[1], shuffle)
        est = self.make_est(name, args, kw)
        if est is not None:
            return est
        if is_metric(name):
            return self.do_metric(name, args, kw, node)
        if name in _PASSTHROUGH_FUNCS:
            d = next(
                (
                    self.to_data(a, n.id if isinstance(n, ast.Name) else None)
                    for a, n in zip(args, node.args, strict=False)
                    if self.to_data(a) is not None
                ),
                None,
            )
            if d is not None:
                return self.combine_args(d, [a for a in args if a is not d], kw)
        return self.opaque(args, kw)

    # -- constructors ----------------------------------------------------------

    def new_frame(self, name: str, args: list[AVal], kw: dict[str, AVal]) -> AVal:
        o = self.new_origin(name)
        if args and isinstance(args[0], Str):
            o.path = args[0].value
        pd_ = kw.get("parse_dates")
        for n in str_list(pd_) or []:
            self.note_time(o, n)
        ic = kw.get("index_col")
        if is_true(pd_) or (isinstance(ic, Str) and time_name(ic.value)):
            o.time_index = "parsed" if is_true(pd_) else "name"
        for key in ("usecols", "names"):
            for n in str_list(kw.get(key, UNKNOWN)) or []:
                self.note_col(o, n)
        kind = "array" if name in ("load", "genfromtxt", "loadtxt") else "frame"
        return Data(o, Rows("all", None, o.id), kind)

    def make_frame(self, args: list[AVal], kw: dict[str, AVal], node: ast.Call) -> AVal:
        first = args[0] if args else kw.get("data", UNKNOWN)
        if isinstance(first, Data):
            cols = kw.get("columns")
            out = replace(first, kind="frame")
            if isinstance(cols, Cols):
                out = replace(out, cols=cols)
            return out
        if collect_events(first):
            return Score(frozenset(collect_events(first)))
        if isinstance(first, ListV) and first.acc is not None:
            return Data(first.acc, Rows("all", None, first.acc.id), "frame")
        if isinstance(first, ListV) and first.kind == "dict":
            datas = [v for v in first.items if isinstance(v, Data)]
            accs = [v for v in first.items if isinstance(v, ListV) and v.acc is not None]
            o = self.new_origin("DataFrame")
            if datas:
                base = replace(
                    datas[0],
                    origin=o,
                    kind="frame",
                    cols=None,
                    col=None,
                    deps=frozenset(),
                    fwd=(),
                    is_stat=False,
                    pred_of=None,
                    shifted=False,
                    thresholded=False,
                )
            elif accs:
                base = Data(accs[0].acc, Rows("all", None, accs[0].acc.id), "frame")
            else:
                base = Data(o, Rows("all", None, o.id), "frame")
            taints = base.taints
            for k, v in zip(first.keys, first.items, strict=False):
                if isinstance(k, Str):
                    fact = self.note_col(base.origin, k.value)
                    if isinstance(v, Data):
                        fact.fwd += [f for f in v.fwd if f not in fact.fwd]
                        fact.shifted = fact.shifted or v.shifted
                        if v.shifted:
                            base.origin.ordered_ops.add(f"lag, window or fill feature `{k.value}`")
                        if v.is_time or (v.col and v.origin.time_cols.get(v.col) == "parsed"):
                            self.note_time(base.origin, k.value)
                    elif isinstance(v, PathV):
                        self.note_path_entity(base.origin, k.value, v, multi_rows=False)
                elif isinstance(v, Data):
                    taints |= v.taints
            return replace(base, taints=taints)
        return self.fresh("DataFrame")

    def make_est(self, name: str, args: list[AVal], kw: dict[str, AVal]) -> Est | None:
        line = self.stmt_line[0]
        params = set(kw)

        def found(vals: list[AVal], depth: int = 0) -> list[Est]:
            out: list[Est] = []
            for v in vals:
                if isinstance(v, Est):
                    out.append(v)
                elif isinstance(v, ListV) and depth < 4:
                    if v.kind == "tuple" and any(isinstance(i, Est) and i.flavour == "vocabulary" for i in v.items):
                        for i in v.items:
                            for n in str_list(i) or []:
                                self.cat_names.add(n)
                    out += found(v.items, depth + 1)
            return out

        if name in COMPOSITE:
            steps = found(list(args) + list(kw.values()))
            flav = (
                "supervised"
                if any(s.flavour == "supervised" and s.kind == "transformer" for s in steps)
                else "statistical"
                if any(s.flavour == "statistical" and s.kind == "transformer" for s in steps)
                else "vocabulary"
            )
            is_model = (
                bool(steps) and steps[-1].kind in ("model", "search") and "olumn" not in name and "nion" not in name
            )
            return Est(name, "model" if is_model else "transformer", line, flav, steps, params=params)
        if name in SEARCH:
            inner = next((a for a in list(args) + list(kw.values()) if isinstance(a, Est)), None)
            return Est(name, "search", line, inner=inner, cv=kw.get("cv"), params=params)
        if name in RESAMPLERS:
            return Est(name, "resampler", line, params=params)
        if name in UNDERSAMPLERS:
            return Est(name, "resampler", line, "undersampler", params=params)
        if name in STATELESS:
            return Est(name, "transformer", line, "stateless", params=params)
        if name in SUPERVISED:
            return Est(name, "transformer", line, "supervised", params=params)
        if name in STATISTICAL:
            return Est(name, "transformer", line, "statistical", params=params)
        if name in VOCABULARY:
            return Est(name, "transformer", line, "vocabulary", params=params)
        if is_model_name(name):
            return Est(name, "model", line, params=params)
        return None

    # -- pandas / numpy data methods -------------------------------------------

    def reduce(self, d: Data, axis: AVal | None) -> AVal:
        if num(axis) == 1 or (isinstance(axis, Str) and axis.value == "columns"):
            return replace(d, kind="series", cols=None)
        if d.is_stat or d.pred_of is not None:
            return d
        return replace(
            d,
            is_stat=True,
            stat_src=d.rows,
            stat_cols=d.deps | ({d.col} if d.col else set()),
            kind="array",
            subset=False,
        )

    def add_fwd(self, d: Data, op: str, confidence: str) -> Data:
        f = (self.stmt_line[0], self.stmt_line[1], op, confidence)
        return d if f in d.fwd else replace(d, fwd=d.fwd + (f,))

    def aggregated(self, d: Data) -> Data:
        """A per-group aggregate is a new table with one row per group; as a value it is a statistic of `d`."""
        o = self.new_origin("groupby aggregate")
        o.aggregated_by = set(d.gkeys)
        o.time_cols, o.time_index = dict(d.origin.time_cols), d.origin.time_index
        return Data(
            o,
            Rows("all", None, o.id),
            "frame",
            is_stat=True,
            stat_src=d.rows,
            stat_cols=d.deps | set(d.gkeys) | ({d.col} if d.col else set()),
            taints=d.taints,
        )

    def group_stat(self, d: Data, what: str) -> Data:
        t = Taint(
            "pre",
            self.stmt_line[0],
            self.stmt_line[1],
            f"{what}: a per-group statistic over rows",
            d.rows,
            confidence="medium",
            stat_cols=frozenset(d.deps | set(d.gkeys) | ({d.col} if d.col else set())),
            subtype="pandas_stats",
        )
        return replace(d, window=None, gkeys=(), taints=d.taints | {t}, is_stat=False)

    def merge(self, d: Data, others: list[Data], kw: dict[str, AVal]) -> Data:
        taints = d.taints
        for other in others:
            taints |= other.taints
            if other.is_stat:
                t = self.stat_taint(other)
                taints |= {t} if t else set()
        for n in str_list(kw.get("on", UNKNOWN)) or []:
            self.note_col(d.origin, n)
        return replace(d, taints=taints, cols=None if others else d.cols)

    def data_method(
        self, d: Data, m: str, args: list[AVal], kw: dict[str, AVal], node: ast.Call, recv_node: ast.expr | None
    ) -> AVal:
        o = d.origin
        if m in ORDERED_OPS and d.gkeys:
            o.panel_keys |= set(d.gkeys)
        if m in ("shift", "diff", "pct_change"):
            k = num(args[0]) if args else num(kw.get("periods"))
            k = 1 if k is None and not args and "periods" not in kw else k
            out = replace(d, shifted=True, is_stat=False, window=None, gkeys=())
            if k is not None and ((k < 0) != d.reversed) and k != 0:
                out = self.add_fwd(out, f"{m}({k})" + (" on a reversed series" if d.reversed else ""), "medium")
            return out
        if m == "rolling":
            return replace(d, window="rolling", centered=is_true(kw.get("center")), shifted=True)
        if m in ("expanding", "ewm"):
            return replace(d, window=m, shifted=True)
        if m == "groupby":
            keys = str_list(args[0] if args else kw.get("by", UNKNOWN)) or []
            for k in keys:
                self.note_col(o, k)
            return replace(d, window="groupby", gkeys=tuple(keys))
        if m == "resample" and d.kind in ("frame", "series"):
            o.time_index = o.time_index or "parsed"
            return replace(d, window="groupby", gkeys=())
        if d.window in ("rolling", "expanding", "ewm"):
            out = replace(d, window=None, centered=False, shifted=True, gkeys=())
            if d.centered:
                out = self.add_fwd(out, "rolling(center=True)", "medium")
            if d.reversed:
                out = self.add_fwd(out, f"{d.window} window over a reversed series", "medium")
            return out
        if d.window == "groupby":
            return self.groupby_method(d, m, args, kw)
        if m in REDUCTIONS:
            return self.reduce(d, kw.get("axis", args[0] if args and m not in ("quantile", "percentile") else None))
        if m in FWD_FILL:
            return self.add_fwd(replace(d, shifted=True), m, "medium")
        if m == "fillna":
            method = kw.get("method")
            if isinstance(method, Str) and method.value in FWD_FILL:
                return self.add_fwd(replace(d, shifted=True), f"fillna(method='{method.value}')", "medium")
            return self.combine_args(d, args, kw)
        if m in LOW_FWD:
            return self.add_fwd(d, m, "low")
        if m in _CUM:
            out = replace(d, shifted=True)
            return self.add_fwd(out, f"{m} over a reversed series", "medium") if d.reversed else out
        if m == "sort_values":
            by = str_list(args[0] if args else kw.get("by", UNKNOWN)) or []
            if any(b in o.time_cols or time_name(b) for b in by):
                for b in by:
                    self.note_col(o, b)
                o.sorted_by_time, o.shuffled_line = True, None
            elif not by and d.is_time:
                o.sorted_by_time = True
            return d
        if m == "sort_index":
            if o.time_index:
                o.sorted_by_time, o.shuffled_line = True, None
            return d
        if m == "set_index":
            for k in str_list(args[0] if args else kw.get("keys", UNKNOWN)) or []:
                self.note_col(o, k)
                if k in o.time_cols:
                    o.time_index = o.time_cols[k]
            return d
        if m == "sample":
            return self.sample(d, args, kw)
        if m == "drop":
            return self.drop(d, args, kw)
        if m == "pop" and args and isinstance(args[0], Str):
            c = args[0].value
            if isinstance(recv_node, ast.Name):
                cols = self.cols_of(d)
                cols = (
                    replace(cols, names=tuple(n for n in cols.names if n != c))
                    if cols.names is not None
                    else replace(cols, minus=cols.minus | {c})
                )
                self.set(recv_node.id, replace(d, cols=cols))
            return self.read_col(d, c)
        if m in ("unique", "drop_duplicates"):
            if d.kind == "series" or d.col:
                return replace(d, unique_of=d.col or "?", kind="array")
            for n in str_list(kw.get("subset", args[0] if args else UNKNOWN)) or []:
                o.aggregated_by.add(n)
            return d
        if m in ("head", "tail", "query", "nlargest", "nsmallest", "take", "filter", "between_time", "truncate"):
            return replace(d, subset=True) if m != "filter" else d
        if m in ("merge", "join"):
            return self.merge(d, [a for a in args if isinstance(a, Data)], kw)
        if m == "rename":
            mapping = kw.get("columns", args[0] if args else UNKNOWN)
            if isinstance(mapping, ListV) and mapping.kind == "dict":
                for k, v in zip(mapping.keys, mapping.items, strict=False):
                    if isinstance(k, Str) and isinstance(v, Str) and k.value in o.cols:
                        self.note_col(o, v.value)
                        old = o.cols[k.value]
                        o.cols[v.value] = replace(old, name=v.value)
                        if k.value in o.time_cols:
                            o.time_cols[v.value] = o.time_cols[k.value]
            return d
        if m == "assign":
            for k, v in kw.items():
                self.assign_col(d, k, self.call_func(v, [d]) if isinstance(v, FuncV) else v, None)
            return (
                d
                if d.cols is None
                else replace(
                    d,
                    cols=replace(
                        d.cols,
                        base=d.cols.base | set(kw),
                        names=None
                        if d.cols.names is None
                        else d.cols.names + tuple(k for k in kw if k not in d.cols.names),
                    ),
                )
            )
        if m in _FUNC_METHODS:
            f = args[0] if args else kw.get("func", UNKNOWN)
            if isinstance(f, FuncV):
                r = self.call_func(f, [replace(d, subset=False)])
                if isinstance(r, Data):
                    return replace(
                        d,
                        taints=d.taints | r.taints,
                        fwd=tuple(dict.fromkeys(d.fwd + r.fwd)),
                        deps=d.deps | r.deps,
                        shifted=d.shifted or r.shifted,
                        thresholded=d.thresholded or r.thresholded,
                    )
                return d
            if m in ("agg", "aggregate"):
                return self.reduce(d, kw.get("axis"))
            return self.combine_args(d, args, kw)
        if m in _COMBINE_METHODS:
            out = self.combine_args(d, args, kw)
            return replace(out, thresholded=True) if m in _COMPARE_METHODS else out
        if m in ("items", "iterrows", "itertuples", "iteritems"):
            return Iter(ListV([UNKNOWN, d], "tuple"))
        if m in ("to_numpy", "to_frame", "flatten", "ravel", "squeeze", "reshape", "todense", "toarray", "numpy"):
            return replace(d, kind="array" if m != "to_frame" else "frame")
        if m in (
            "to_csv",
            "to_pickle",
            "to_parquet",
            "to_excel",
            "plot",
            "hist",
            "info",
            "boxplot",
            "to_json",
            "to_string",
            "to_markdown",
            "to_latex",
        ):
            return UNKNOWN
        if m in ("tolist", "to_list", "to_dict", "keys"):
            return d
        return self.combine_args(d, [a for a in args if isinstance(a, Data) and a.is_stat], {})

    def groupby_method(self, d: Data, m: str, args: list[AVal], kw: dict[str, AVal]) -> AVal:
        keys = ", ".join(d.gkeys) or "..."
        if m in ("transform", "apply", "agg", "aggregate"):
            f = args[0] if args else kw.get("func", UNKNOWN)
            if isinstance(f, FuncV):
                r = self.call_func(f, [replace(d, window=None, gkeys=())])
                if not isinstance(r, Data):
                    return replace(d, window=None, gkeys=())
                if r.is_stat:
                    return self.group_stat(d, f"groupby({keys}).{m}(...)") if m == "transform" else self.aggregated(d)
                return replace(
                    d,
                    window=None,
                    gkeys=(),
                    taints=d.taints | r.taints,
                    deps=d.deps | r.deps,
                    fwd=tuple(dict.fromkeys(d.fwd + r.fwd)),
                    shifted=d.shifted or r.shifted,
                )
            fname = f.value if isinstance(f, Str) else f.name if isinstance(f, Ref) else None
            if m == "transform":
                if fname in FWD_FILL:
                    return self.add_fwd(
                        replace(d, window=None, gkeys=(), shifted=True), f"transform('{fname}')", "medium"
                    )
                if fname is None or fname in GROUPBY_STATS or fname in REDUCTIONS:
                    return self.group_stat(d, f"groupby({keys}).transform({fname or '...'})")
                return replace(d, window=None, gkeys=(), shifted=True)
            return self.aggregated(d)
        if m in GROUPBY_STATS or m in REDUCTIONS or m in ("describe", "ohlc"):
            return self.aggregated(d)
        if m in FWD_FILL:
            return self.add_fwd(replace(d, window=None, gkeys=(), shifted=True), m, "medium")
        if m in _CUM or m in ("cumcount", "rank", "ffill", "pad", "ngroup", "fillna"):
            return replace(d, window=None, gkeys=(), shifted=m in _CUM or m in ("ffill", "pad"))
        if m in ("head", "tail", "nth", "sample", "filter", "get_group"):
            return replace(d, window=None, gkeys=(), subset=True)
        return d

    def sample(self, d: Data, args: list[AVal], kw: dict[str, AVal]) -> Data:
        o = d.origin
        frac = num(kw.get("frac"))
        if is_true(kw.get("replace")):
            t = Taint(
                "dup",
                self.stmt_line[0],
                self.stmt_line[1],
                "sample(replace=True) copies rows",
                d.rows,
                subtype="resample_before_split",
            )
            return replace(d, taints=d.taints | {t}, subset=True)
        if frac == 1:
            o.shuffled_line, o.sorted_by_time = self.stmt_line[0], False
            return d
        if d.window is not None or d.is_stat:
            return d
        side = "train" if frac is not None and frac >= 0.5 else "test"
        sp = self.new_split(
            "DataFrame.sample (random rows)", d.rows, o, row_level=True, checked=False, info={"manual": True, "X": d}
        )
        return replace(d, rows=Rows(side, sp, o.id), subset=False)

    def drop(self, d: Data, args: list[AVal], kw: dict[str, AVal]) -> Data:
        axis = kw.get("axis", args[1] if len(args) > 1 else None)
        by_col = num(axis) == 1 or (isinstance(axis, Str) and axis.value == "columns")
        cols = kw.get(
            "columns", args[0] if args and (by_col or str_list(args[0]) is not None) and "index" not in kw else None
        )
        if cols is not None and not isinstance(cols, Data):
            names = str_list(cols)
            cur = self.cols_of(d)
            if names is None:
                return replace(d, cols=replace(cur, uncertain=True))
            for n in names:
                self.note_col(d.origin, n)
            cur = (
                replace(cur, names=tuple(n for n in cur.names if n not in names))
                if cur.names is not None
                else replace(cur, minus=cur.minus | set(names))
            )
            return replace(d, cols=cur)
        idx = kw.get("index", args[0] if args else None)
        if (
            isinstance(idx, Data)
            and idx.rows.split is not None
            and idx.rows.role in ("train", "test")
            and idx.rows != d.rows
        ):
            sp = idx.rows.split
            if sp.info.get("manual") and not sp.info.get("confirmed"):
                sp.info["confirmed"] = True  # the complement of a random sample makes it a real split
                x = sp.info.get("X", d)
                self.check_split(sp, x, None)
                self.sink(x, None, sp)
            return replace(d, rows=Rows(idx.rows.other().role, sp, d.origin.id), subset=False)
        return replace(d, subset=True)

    # -- lists -----------------------------------------------------------------

    def list_method(self, lv: ListV, m: str, args: list[AVal], node: ast.Call, recv_node: ast.expr | None) -> AVal:
        if m in ("append", "add", "insert", "extend", "update", "setdefault"):
            v = args[-1] if args else UNKNOWN
            lv.items.append(v)
            if lv.kind == "dict":
                lv.keys.append(args[0] if len(args) > 1 else UNKNOWN)
            if m == "append" and self.loops:
                loop = self.loops[-1]
                o = self.loop_origins.get(loop)
                if o is None:
                    o = self.loop_origins[loop] = self.new_origin("rows built in a loop")
                if lv.acc is None:
                    lv.acc = o
                multi = loop not in self.path_loops and any(lp in self.path_loops for lp in self.loops)
                name = recv_node.id if isinstance(recv_node, ast.Name) else None
                if isinstance(v, ListV) and v.kind == "dict":
                    for k, val in zip(v.keys, v.items, strict=False):
                        if isinstance(k, Str):
                            self.note_col(lv.acc, k.value)
                            if isinstance(val, PathV):
                                self.note_path_entity(lv.acc, k.value, val, multi)
                elif isinstance(v, PathV) and name:
                    self.note_path_entity(lv.acc, name, v, multi)
            return Const(None)
        if m == "items":
            return Iter(ListV([join(lv.keys), join(lv.items)], "tuple"))
        if m == "values":
            return Iter(join(lv.items))
        if m == "keys":
            return Iter(join(lv.keys))
        if m in ("get", "pop"):
            return join(lv.items)
        if m == "copy":
            return lv
        if m == "sort":
            events = collect_events(lv)
            if events:
                self.select(events, ".sort()")
            return Const(None)
        if m in ("index", "count"):
            return Num(None)
        return UNKNOWN

    # -- estimators ------------------------------------------------------------

    def est_method(self, est: Est, m: str, args: list[AVal], kw: dict[str, AVal], node: ast.Call) -> AVal:
        X = self.arg_data(node, args, 0, kw, "X")
        y = args[1] if len(args) > 1 else kw.get("y")
        if m in ("fit", "partial_fit"):
            if X is not None:
                self.do_fit(est, X, y, kw, node)
            return est
        if m == "fit_transform":
            if X is None:
                return UNKNOWN
            self.fit_transformer(est, X)
            return self.transformed(est, X)
        if m == "transform":
            return self.transformed(est, X) if X is not None else UNKNOWN
        if m == "inverse_transform":
            return X if X is not None else UNKNOWN
        if m in ("fit_resample", "fit_sample"):
            if X is None:
                return UNKNOWN
            yd = self.to_data(y)
            if est.flavour == "undersampler":
                return ListV(
                    [
                        replace(X, subset=True),
                        replace(yd, subset=True) if yd is not None else replace(X, kind="series", subset=True),
                    ],
                    "tuple",
                )
            t = Taint(
                "dup",
                self.stmt_line[0],
                self.stmt_line[1],
                f"{est.cls} creates copied or synthetic rows",
                X.rows,
                subtype="resample_before_split",
                confidence="low" if est.flavour == "generic" else "high",
            )
            return ListV(
                [
                    replace(X, taints=X.taints | {t}),
                    replace(yd, taints=yd.taints | {t}) if yd is not None else replace(X, kind="series"),
                ],
                "tuple",
            )
        if m in _PREDICT:
            if X is None:
                return UNKNOWN
            self.check_overlap(est, X)
            return replace(
                X, kind="array", pred_of=est, cols=None, col=None, taints=frozenset(), deps=frozenset(), is_stat=False
            )
        if m in ("score", "evaluate"):
            if X is None:
                return UNKNOWN
            self.check_overlap(est, X)
            return self.event("holdout", X.rows, node, f"{est.cls}.{m}")
        if m in ("set_params", "set_output", "compile"):
            return est
        return UNKNOWN

    def fit_transformer(self, est: Est, X: Data) -> None:
        est.fit = FitRec(X.rows, X.origin, self.stmt_line[0], self.stmt_line[1], est.flavour == "supervised")
        if est.flavour == "vocabulary":
            if X.col:
                self.cat_names.add(X.col)
            if X.cols is not None and X.cols.names:
                self.cat_names |= set(X.cols.names)

    def transformed(self, est: Est, X: Data) -> Data:
        fit = est.fit
        if fit is None or est.kind == "model" or est.flavour == "stateless":
            return X
        conf = {"statistical": "high", "supervised": "high", "vocabulary": "low", "generic": "low"}[est.flavour]
        t = Taint(
            "pre",
            fit.line,
            fit.end_line,
            f"{est.cls} is fitted here",
            fit.rows,
            supervised=fit.supervised,
            confidence=conf,
            subtype="supervised" if fit.supervised else "scaler",
        )
        return replace(X, taints=X.taints | {t})

    def do_fit(self, est: Est, X: Data, y: AVal | None, kw: dict[str, AVal], node: ast.Call) -> None:
        rec = FitRec(X.rows, X.origin, self.stmt_line[0], self.stmt_line[1], est.flavour == "supervised")
        if est.kind == "transformer":
            self.fit_transformer(est, X)
            return
        est.fit = rec
        if est.kind == "search":
            if est.inner is not None:
                est.inner.fit = rec
            split = self.cv_split(est.cv, kw.get("groups"), X, f"{est.cls}.fit")
            self.check_split(split, X, y, helper=True)
            self.sink(X, y, split)
            return
        self.sink(X, y, None)
        stops = bool({"early_stopping_rounds", "callbacks"} & (set(kw) | est.params))
        for key in ("eval_set", "validation_data"):
            v = kw.get(key)
            if v is None:
                continue
            knode = next((k.value for k in node.keywords if k.arg == key), None)
            named_val = knode is not None and any(
                isinstance(n, ast.Name) and set(tokens(n.id)) & HINT_VAL for n in ast.walk(knode)
            )
            for d in self.datas_in(v):
                if self.final_test(d.rows):
                    self.emit(
                        "multi_test",
                        "LL-MUL-002",
                        self.stmt_line,
                        "early_stopping",
                        "medium" if stops and not named_val else "low",
                        f"Evaluation rows are passed as `{key}` while fitting; if they stop or select the "
                        "training run, the score reported on the same rows is optimistic.",
                        [{"kind": "fit_call", "detail": f"{est.cls}.fit({key}=...) receives evaluation rows"}],
                        "Use a separate validation split for early stopping and score once on the test rows.",
                        "holdout_validation_split",
                    )
                    break

    def datas_in(self, v: AVal, depth: int = 0) -> list[Data]:
        if isinstance(v, Data):
            return [v]
        if isinstance(v, ListV) and depth < 4:
            return [d for i in v.items for d in self.datas_in(i, depth + 1)]
        return []

    def final_test(self, rows: Rows) -> bool:
        """Rows that are the evaluation side of a real, outermost split (not a validation split inside training)."""
        sp = rows.split
        if rows.role != "test" or sp is None:
            return False
        if sp.info.get("manual") and not sp.info.get("confirmed"):
            return False
        return sp.parent.role != "train"

    def check_overlap(self, est: Est, E: Data) -> None:
        fit = est.fit
        if fit is None or E.rows.role != "test" or E.rows.split is None:
            return
        sp = E.rows.split
        if sp.info.get("manual") and not sp.info.get("confirmed"):
            return
        if covers(fit.rows, E.rows) and fit.rows != E.rows:  # same rows fitted and scored: a training score
            how = (
                "train and evaluation rows concatenated"
                if fit.rows.role == "mixed"
                else "the evaluation rows themselves"
                if fit.rows.role == "test"
                else "all rows, before or regardless of the split"
            )
            self.emit(
                "overlap",
                "LL-OVL-003" if fit.rows.role == "mixed" else "LL-OVL-001",
                (fit.line, fit.end_line),
                "test_in_fit",
                "high",
                f"The model is fitted on {how}, then scored on evaluation rows it has already seen.",
                [
                    {"kind": "fit_call", "detail": f"{est.cls}.fit on rows that include the evaluation rows"},
                    {
                        "kind": "data_flow",
                        "detail": f"evaluated at line {self.stmt_line[0]} on the test side of "
                        f"the split at line {sp.line}",
                    },
                ],
                "Fit on the training rows only.",
                "fit_on_train_only",
                {"eval_lines": [self.stmt_line[0]]},
            )

    # -- splits ----------------------------------------------------------------

    def do_tts(self, args: list[AVal], kw: dict[str, AVal], node: ast.Call) -> AVal:
        datas = [self.arg_data(node, args, i, {}, "") for i in range(len(args))]
        first = next((d for d in datas if d is not None), None)
        if first is None:
            first = self.fresh("unknown data", "array")
        second = next((d for d in datas if d is not None and d is not first), None)
        entity_level = first.unique_of is not None
        chrono = is_false(kw.get("shuffle")) and first.origin.shuffled_line is None
        split = self.new_split(
            "train_test_split" + ("(shuffle=False)" if is_false(kw.get("shuffle")) else ""),
            first.rows,
            first.origin,
            row_level=not entity_level,
            chronological=chrono,
            info={"stratify": "stratify" in kw},
        )
        self.check_split(split, first, second)
        self.sink(first, second, split)
        out: list[AVal] = []
        for d in datas:
            d = d if d is not None else replace(first, kind="array", cols=None, col=None, taints=frozenset())
            out += [
                replace(d, rows=Rows("train", split, d.origin.id), subset=False),
                replace(d, rows=Rows("test", split, d.origin.id), subset=False),
            ]
        return ListV(out, "tuple")

    def cv_split(self, cv: AVal | None, groups: AVal | None, X: Data, call: str) -> Split:
        given = groups is not None and not (isinstance(groups, Const) and groups.value is None)
        if cv is None or isinstance(cv, Num | Const):
            return self.new_split(
                f"{call} (default or integer cv)",
                X.rows,
                X.origin,
                row_level=True,
                group_aware=given,
                is_cv=True,
                info={"default_cv": True},
            )
        if isinstance(cv, SplitterV):
            return self.new_split(
                f"{call} with {cv.cls}",
                X.rows,
                X.origin,
                row_level=cv.kind != "group",
                group_aware=cv.kind == "group" or given,
                chronological=cv.kind == "time",
                is_cv=True,
                info={"splitter": cv.cls, "shuffle": cv.shuffle},
            )
        return self.new_split(f"{call} (unresolved cv)", X.rows, X.origin, row_level=False, is_cv=True, checked=True)

    def do_cv_helper(self, name: str, args: list[AVal], kw: dict[str, AVal], node: ast.Call) -> AVal:
        est = args[0] if args else kw.get("estimator")
        X = self.arg_data(node, args, 1, kw, "X")
        if X is None:
            X = self.fresh("unknown data", "array")
        y = args[2] if len(args) > 2 else kw.get("y")
        groups = kw.get("groups", args[3] if len(args) > 3 else None)
        cv = kw["cv"] if "cv" in kw else None
        split = self.cv_split(cv, groups, X, name)
        self.check_split(split, X, y, helper=True)
        self.sink(X, y, split)
        if name == "cross_val_predict":
            return replace(X, kind="array", pred_of=("cv", est), cols=None, col=None, taints=frozenset())
        return self.event("cv", X.rows, node, name)

    def splitter_method(self, sp: SplitterV, m: str, args: list[AVal], kw: dict[str, AVal], node: ast.Call) -> AVal:
        if m != "split":
            return Num(None) if m == "get_n_splits" else UNKNOWN
        X = self.arg_data(node, args, 0, kw, "X")
        if X is None:
            X = self.fresh("unknown data", "array")
        y = args[1] if len(args) > 1 else kw.get("y")
        split = self.new_split(
            f"{sp.cls}.split",
            X.rows,
            X.origin,
            row_level=sp.kind != "group" and X.unique_of is None,
            group_aware=sp.kind == "group",
            chronological=sp.kind == "time",
            is_cv=True,
            info={"splitter": sp.cls, "shuffle": sp.shuffle},
        )
        self.check_split(split, X, y)
        self.sink(X, y, split)
        return SplitIter(split)

    def entity_candidates(self, o: Origin, ycols: set[str], X: Data) -> list[tuple[str, str, str]]:
        out = []
        panel = o.time_strength() is not None
        features = set(X.cols.names) if X.cols is not None and X.cols.names is not None else set()
        for col, (evidence, strength) in o.entity.items():
            if col in ycols or col in self.cat_names or col in o.aggregated_by:
                continue
            if panel and col in o.panel_keys:
                continue  # per-entity lag features on time-ordered data: a panel forecast for the same entities
            if col in features and col not in o.file_entities:
                strength = "weak"  # listed among the model's features: more likely a categorical feature than an id
            out.append((col, evidence, strength))
        out.sort(key=lambda c: (c[2] != "strong", c[0] not in o.file_entities, c[0]))
        return out

    def check_split(self, split: Split, X: Data, y: AVal | None, helper: bool = False) -> None:
        if split.checked:
            return
        split.checked = True
        o = X.origin
        ycols = self.ycols(y)
        loc = (split.line, split.end_line)
        if split.row_level and not split.group_aware:
            cands = self.entity_candidates(o, ycols, X)
            if cands:
                col, evidence, strength = cands[0]
                is_file = col in o.file_entities
                conf = "medium" if strength == "strong" and not split.chronological else "low"
                base = "default_cv" if split.info.get("default_cv") else "row_cv" if split.is_cv else "row_split"
                rule = "LL-GRP-003" if is_file else "LL-GRP-002" if split.info.get("default_cv") else "LL-GRP-001"
                fix = "GroupKFold" if split.is_cv else "GroupShuffleSplit"
                self.emit(
                    "group",
                    rule,
                    loc,
                    base + ("+file_path_entity" if is_file else ""),
                    conf,
                    f"Rows are split without regard to `{col}`; the same {col} can be in training and "
                    "evaluation rows, so the score does not measure performance on new entities.",
                    [{"kind": "split_call", "detail": f"{split.call}: row-level, not group-aware"}]
                    + [{"kind": "entity_column", "detail": e} for _, e, _ in cands[:3]],
                    f"Split by entity: use {fix} with groups=`{col}` (same folds, test size and seed).",
                    f"replace_splitter:{fix}",
                    {"entity_columns": [c for c, _, _ in cands], "entity_strengths": {c: s for c, _, s in cands}},
                )
        if split.row_level and not split.chronological and not split.group_aware:
            if X.shifted:
                o.ordered_ops.add("lag or window values in the split data")
            strength = o.time_strength()
            if strength is not None:
                how = split.info.get("splitter") or split.call
                self.emit(
                    "temporal",
                    "LL-TMP-001",
                    loc,
                    "T1",
                    "medium" if strength == "strong" else "low",
                    "Time-ordered rows are split without respecting time; the model trains on rows that are "
                    "later than rows it is evaluated on.",
                    [
                        {"kind": "split_call", "detail": f"{how}: not a forward-chaining split"},
                        {"kind": "time_column", "detail": o.time_evidence()},
                    ],
                    "Sort by time and split without shuffling (shuffle=False), or use TimeSeriesSplit with the "
                    "same number of folds.",
                    "replace_splitter:TimeSeriesSplit" if split.is_cv else "replace_splitter:chronological",
                    {"time_columns": sorted(o.time_cols)},
                )

    # -- sinks -----------------------------------------------------------------

    def ycols(self, y: AVal | None) -> set[str]:
        if isinstance(y, Data):
            if y.col:
                return {y.col}
            if y.cols is not None and y.cols.names:
                return set(y.cols.names)
        return set()

    def frame_has(self, X: Data, c: str) -> bool:
        if X.kind == "series" and X.col:
            return X.col == c
        cols = X.cols
        if cols is None:
            return True
        if cols.names is not None:
            return c in cols.names
        if c in cols.minus:
            return False
        if c in cols.base:
            return True
        fact = X.origin.cols.get(c)
        return not (fact is not None and fact.assigned)

    def effective(self, o: Origin, c: str) -> tuple[set[Taint], list, set[str]]:
        """Taints and forward-looking operations of column c and everything it is computed from; plus the columns
        it depends on through value-preserving steps (a lag is not a copy of its source)."""
        taints: set[Taint] = set()
        fwd: list = []
        seen: set[str] = set()
        pure: set[str] = set()
        stack = [(c, True)]
        while stack:
            name, is_pure = stack.pop()
            if name in seen:
                continue
            seen.add(name)
            fact = o.cols.get(name)
            if fact is None:
                continue
            taints |= fact.taints
            fwd += [f for f in fact.fwd if f not in fwd]
            step_pure = is_pure and not fact.shifted
            for dep in fact.deps:
                if step_pure:
                    pure.add(dep)
                stack.append((dep, step_pure))
        return taints, fwd, pure

    def sink(self, X: Data, y: AVal | None, split: Split | None) -> None:
        """Report what leaked into X, given that X is being split (split is set) or is fitted as training rows."""
        r = X.rows
        if split is None and (r.role != "train" or r.split is None):
            return
        ycols = self.ycols(y)
        o = X.origin
        nested = (
            split is not None
            and split.parent.role == "train"
            and split.parent.split is not None
            and not split.parent.split.info.get("hint")
        )

        def leaks(t: Taint) -> bool:
            if split is not None:
                return covers(t.src, split.parent)
            return covers(t.src, r.split.parent) or (t.src.role in ("mixed", "test") and t.src.split is r.split)

        at = split.line if split is not None else r.split.line
        for t in X.taints:
            if leaks(t):
                self.emit_taint(t, o, ycols, nested, at)
        for f in X.fwd:
            self.emit_fwd(f, None)
        partial = X.cols is not None and X.cols.names is None and X.cols.uncertain
        resolved = bool(ycols) if X.cols is None else (not partial or bool(X.cols.sure))
        if not resolved:
            return
        for c in list(o.cols):
            if c in ycols or not self.frame_has(X, c):
                continue
            if partial and c not in X.cols.sure:
                continue  # an unresolved column filter: only columns known to be included are judged
            fact = o.cols[c]
            taints, fwd, pure = self.effective(o, c)
            for t in taints:
                if leaks(t):
                    self.emit_taint(t, o, ycols, nested, at)
            for f in fwd:
                self.emit_fwd(f, c)
            hit = ycols & pure
            if hit and fact.assigned and not any(t.kind == "pre" and t.stat_cols & ycols for t in taints):
                tgt = sorted(hit)[0]
                self.emit(
                    "target_derived",
                    "LL-TGT-001",
                    (fact.line, fact.end_line),
                    "computed_from_target",
                    "medium",
                    f"Feature `{c}` is computed from the target `{tgt}`; it will not be available, or will not "
                    "mean the same, at prediction time.",
                    [{"kind": "data_flow", "detail": f"`{c}` depends on `{tgt}` and is among the model's features"}],
                    f"Remove `{c}` from the features.",
                    f"drop_feature:{c}",
                    {"feature": c, "target": tgt},
                )
        for tgt in ycols:
            tf = o.cols.get(tgt)
            if tf is None or not tf.assigned or tf.shifted or tf.fwd:
                continue
            _, _, pure = self.effective(o, tgt)
            explicit = X.cols is not None
            for dcol in sorted(pure - ycols):
                if partial and dcol not in X.cols.sure:
                    continue
                if explicit and self.frame_has(X, dcol):
                    conf = "medium" if tf.thresholded and len(pure - ycols) == 1 else "low"
                    self.emit(
                        "target_derived",
                        "LL-TGT-001",
                        (tf.line, tf.end_line),
                        "target_from_feature",
                        conf,
                        f"The target `{tgt}` is computed from `{dcol}`, which is also among the features.",
                        [
                            {
                                "kind": "data_flow",
                                "detail": f"`{tgt}` depends on `{dcol}`; `{dcol}` stays in the features",
                            }
                        ],
                        f"Remove `{dcol}` from the features.",
                        f"drop_feature:{dcol}",
                        {"feature": dcol, "target": tgt},
                    )

    def emit_fwd(self, f: tuple[int, int, str, str], col: str | None) -> None:
        line, end, op, conf = f
        what = f"Feature `{col}`" if col else "A feature"
        self.emit(
            "temporal",
            "LL-TMP-002",
            (line, end),
            "T2",
            conf,
            f"{what} is computed from values later in time ({op}); at prediction time those values do not exist yet.",
            [
                {"kind": "forward_op", "detail": op},
                {"kind": "data_flow", "detail": "the result is among the features of an evaluated model"},
            ],
            "Use the backward-looking counterpart (positive shift, center=False, ffill), computed on past rows only.",
            "replace_forward_op",
            {"feature": col},
        )

    def emit_taint(self, t: Taint, o: Origin, ycols: set[str], nested: bool, at: int) -> None:
        ctx = {"split_lines": [at]}
        conf = "low" if nested else t.confidence
        loc = (t.line, t.end_line)
        if t.kind == "dup":
            self.emit(
                "overlap",
                "LL-OVL-002",
                loc,
                t.subtype or "resample_before_split",
                conf,
                "Rows are copied or synthesised before the split, so copies of the same row can land in both "
                "training and evaluation rows.",
                [
                    {"kind": "data_flow", "detail": t.detail},
                    {"kind": "split_call", "detail": "the resampled rows are split afterwards"},
                ],
                "Split first, then resample the training rows only.",
                "resample_after_split",
                ctx,
            )
            return
        supervised = t.supervised or bool(t.stat_cols & ycols)
        if o.time_strength() == "strong" and not supervised:
            self.emit(
                "temporal",
                "LL-TMP-002",
                loc,
                "T2_whole_series",
                conf,
                "A statistic is computed over the whole time series, including rows later than the training "
                "period, and applied to the features.",
                [{"kind": "fit_call", "detail": t.detail}, {"kind": "time_column", "detail": o.time_evidence()}],
                "Fit the transformation on the training period only (for example inside a Pipeline).",
                "fit_on_train_only",
                {**ctx, "instrumented": t.subtype != "pandas_stats"},
            )
            return
        rule = "LL-PRE-003" if supervised else "LL-PRE-002" if t.subtype == "pandas_stats" else "LL-PRE-001"
        msg = (
            "A target-dependent transformation is fitted on rows that include the evaluation rows."
            if supervised
            else "A data-dependent transformation is fitted on rows that include the evaluation rows."
        )
        self.emit(
            "preprocessing",
            rule,
            loc,
            "supervised" if supervised else t.subtype,
            conf,
            msg,
            [
                {"kind": "fit_call", "detail": t.detail},
                {"kind": "data_flow", "detail": "the transformed data is split or cross-validated afterwards"},
            ],
            "Split first and fit on the training rows only, or put the step in a Pipeline that is fitted "
            "inside each fold.",
            "fit_on_train_only",
            {**ctx, "instrumented": t.subtype != "pandas_stats"},
        )

    # -- scores and selection --------------------------------------------------

    def event(self, kind: str, rows: Rows, node: ast.AST, what: str) -> Score:
        hint = any(isinstance(n, ast.Name) and set(tokens(n.id)) & HINT_VAL for n in ast.walk(node))
        return Score(
            frozenset({EvalEvent(self.stmt_line[0], self.stmt_line[1], kind, rows, tuple(self.loops), hint, what)})
        )

    def do_metric(self, name: str, args: list[AVal], kw: dict[str, AVal], node: ast.Call) -> AVal:
        datas = [a for a in list(args) + list(kw.values()) if isinstance(a, Data)]
        if not datas:
            return UNKNOWN
        cv = next((d for d in datas if isinstance(d.pred_of, tuple)), None)
        if cv is not None:
            return self.event("cv", cv.rows, node, name)
        test = next((d for d in datas if d.rows.role == "test"), datas[0])
        return self.event("holdout", test.rows, node, name)

    def select(self, events: set[EvalEvent], how: str) -> None:
        cands = [e for e in events if e.loops]
        if not cands and len({e.line for e in events}) >= 2:
            cands = list(events)
        first: dict[tuple, EvalEvent] = {}
        for e in sorted(cands, key=lambda e: e.line):  # several metrics of one evaluation: report the first line
            first.setdefault((e.loops, e.rows, e.kind), e)
        for e in first.values():
            if e.kind == "holdout":
                if not self.final_test(e.rows) or e.val_hint:
                    continue
                sub = "cv_selection_reported" if e.rows.split.is_cv else "test_set_tuning"
                msg = (
                    "Several candidates are scored on the same evaluation rows and the best one is selected; its "
                    "score on those rows is an optimistic estimate."
                )
            else:
                if e.rows.role != "all":
                    continue
                sub = "cv_selection_reported"
                msg = (
                    "Several candidates are compared by cross-validation on all rows and the best score is kept; "
                    "no rows remain that were not used for the selection."
                )
            self.emit(
                "multi_test",
                "LL-MUL-001",
                (e.line, e.end_line),
                sub,
                "medium",
                msg,
                [
                    {"kind": "selection", "detail": f"scores from this line are compared by {how}"},
                    {"kind": "data_flow", "detail": f"{e.what} on evaluation rows, repeated for several candidates"},
                ],
                "Select with a separate validation split or nested cross-validation, then score the chosen "
                "candidate once on untouched rows.",
                "nested_validation",
            )

    # -- resampling and concatenation ------------------------------------------

    def do_resample(self, args: list[AVal], kw: dict[str, AVal]) -> AVal:
        out: list[AVal] = []
        for a in args:
            if isinstance(a, Data) and not is_false(kw.get("replace")):
                t = Taint(
                    "dup",
                    self.stmt_line[0],
                    self.stmt_line[1],
                    "resample() draws rows with replacement",
                    a.rows,
                    subtype="resample_before_split",
                )
                out.append(replace(a, taints=a.taints | {t}, subset=True))
            else:
                out.append(replace(a, subset=True) if isinstance(a, Data) else a)
        return out[0] if len(out) == 1 else ListV(out, "tuple")

    def do_concat(self, name: str, args: list[AVal], kw: dict[str, AVal]) -> AVal:
        axis = kw.get("axis", args[1] if len(args) > 1 and isinstance(args[1], Num) else None)
        by_col = (
            num(axis) == 1
            or (isinstance(axis, Str) and axis.value == "columns")
            or name in ("hstack", "column_stack", "c_")
        )
        items = args[0].items if args and isinstance(args[0], ListV) else list(args)
        datas = [d for d in (self.to_data(i) for i in items) if d is not None]
        if not datas:
            events = set().union(*(collect_events(i) for i in items)) if items else set()
            return Score(frozenset(events)) if events else UNKNOWN
        first = datas[0]
        taints = frozenset().union(*(d.taints for d in datas))
        fwd = tuple(dict.fromkeys(f for d in datas for f in d.fwd))
        deps = frozenset().union(*(d.deps for d in datas))
        if by_col:
            names = None
            if all(d.cols is not None and d.cols.names is not None or d.col for d in datas):
                names = tuple(
                    n for d in datas for n in (d.cols.names if d.cols is not None and d.cols.names else (d.col,))
                )
            for d in datas:
                if d.is_stat and not first.is_stat:
                    t = self.stat_taint(d)
                    taints |= {t} if t else set()
            return replace(
                first,
                taints=taints,
                fwd=fwd,
                deps=deps,
                col=None,
                kind="frame" if first.kind != "array" else "array",
                cols=Cols(names) if names else None,
            )
        rows = first.rows
        splits = {d.rows.split for d in datas}
        if len(splits) == 1 and None not in splits and {"train", "test"} <= {d.rows.role for d in datas}:
            rows = Rows("mixed", first.rows.split, first.origin.id)
        same = [d for d in datas if d.origin is first.origin and d.rows == first.rows]
        if (
            len(same) >= 2
            and any(not d.subset for d in same)
            and not any(t.kind == "dup" for t in taints)
            and first.rows.role != "mixed"
            and not first.is_stat
        ):
            taints |= {
                Taint(
                    "dup",
                    self.stmt_line[0],
                    self.stmt_line[1],
                    "rows are concatenated with a copy or subset of themselves",
                    first.rows,
                    confidence="medium",
                    subtype="resample_before_split",
                )
            }
        return replace(first, rows=rows, taints=taints, fwd=fwd, deps=deps, subset=False)

    # ------------------------------------------------------------------ findings

    def emit(
        self,
        type_: str,
        rule: str,
        loc: tuple[int, int],
        subtype: str | None,
        confidence: str,
        message: str,
        evidence: list[dict],
        fix: str,
        canonical: str | None,
        context: dict | None = None,
    ) -> None:
        key = (type_, loc[0])
        cur = self.findings.get(key)
        if cur is not None:
            if CONFIDENCE_ORDER[confidence] > CONFIDENCE_ORDER[cur.confidence]:
                cur.confidence = confidence
            for e in evidence:
                if e not in cur.evidence:
                    cur.evidence.append(e)
            for k, v in (context or {}).items():
                if isinstance(v, list):
                    cur.context[k] = list(dict.fromkeys(cur.context.get(k, []) + v))
                else:
                    cur.context.setdefault(k, v)
            return
        self.findings[key] = Finding(
            rule,
            type_,
            subtype,
            confidence,
            self.src.path,
            loc[0],
            max(loc[1], loc[0]),
            message,
            list(evidence),
            fix,
            canonical,
            context=dict(context or {}),
        )


def analyze(src: Source) -> tuple[list[Finding], bool]:
    """Findings for one loaded source, and whether the analysis stopped early on the statement budget."""
    a = Analyzer(src)
    findings = a.run()
    return findings, a.truncated


def analyze_with_hints(src: Source) -> tuple[list[Finding], dict]:
    """Findings plus what the static pass learned that the instrumented run can use: the columns it nominated
    as entity or time columns, and the columns it knows are not entities (one-hot encoded, or the key of
    per-entity lag features in a panel forecast)."""
    a = Analyzer(src)
    findings = a.run()
    not_entities = set(a.cat_names)
    for o in a.origins:
        if o.time_strength() is not None:
            not_entities |= o.panel_keys
        not_entities |= o.aggregated_by
    hints = {
        "entity_columns": {
            c: s for f in findings if f.type == "group" for c, s in f.context.get("entity_strengths", {}).items()
        },
        "time_columns": sorted(
            {c for f in findings if f.type == "temporal" for c in f.context.get("time_columns", [])}
        ),
        "not_entities": sorted(not_entities),
        "features": sorted(
            {f.context["feature"] for f in findings if f.type == "target_derived" and f.context.get("feature")}
        ),
        "target": next(
            (f.context["target"] for f in findings if f.type == "target_derived" and f.context.get("target")), None
        ),
    }
    return findings, hints
