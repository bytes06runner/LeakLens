"""Abstract values used by the static analyser.

The analyser never runs the analysed code. It walks the syntax tree once, in statement order, and keeps for every
variable an abstract value: which table the rows came from (`Origin`), which side of which split they are on
(`Rows`), which columns they have (`Cols`), and what leaked into them (`Taint`).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


class AVal:
    """Base class of abstract values."""


class _Unknown(AVal):
    def __repr__(self) -> str:
        return "UNKNOWN"


UNKNOWN = _Unknown()


@dataclass(frozen=True)
class Str(AVal):
    value: str


@dataclass(frozen=True)
class Num(AVal):
    value: float | int | None


@dataclass(frozen=True)
class Const(AVal):
    value: object  # None, True or False


@dataclass(frozen=True)
class Ref(AVal):
    """A module, function or class referred to by its qualified name."""

    qual: str

    @property
    def name(self) -> str:
        return self.qual.rsplit(".", 1)[-1]

    @property
    def root(self) -> str:
        return self.qual.split(".", 1)[0]


@dataclass(eq=False)
class FuncV(AVal):
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda


@dataclass(frozen=True)
class PathV(AVal):
    """A value derived from a file or directory name. `part` records how much of the name it keeps."""

    part: str = "whole"  # "whole" (unique per file) or "group" (shared by several files: parent folder, name part)
    multi: bool = False  # True when it is the loop variable itself (one value per file)


@dataclass(eq=False)
class ListV(AVal):
    """A list, tuple, set or dict whose items are known abstractly. Mutable: `append` in a loop adds items."""

    items: list[AVal] = field(default_factory=list)
    kind: str = "list"
    keys: list[AVal] = field(default_factory=list)  # for dicts, parallel to items
    acc: Origin | None = None  # set when rows are appended to it in a loop
    acc_entity: tuple[str, str] | None = None  # (evidence, strength) when it accumulates file-derived values


@dataclass(frozen=True)
class Iter(AVal):
    """An iterable whose elements all look like `elem` (enumerate, zip, dict.items, ...)."""

    elem: AVal


@dataclass(frozen=True)
class Cols(AVal):
    """A set of column names: an explicit list, or all columns known at some point minus some."""

    names: tuple[str, ...] | None = None
    base: frozenset[str] = frozenset()
    minus: frozenset[str] = frozenset()
    uncertain: bool = False
    sure: frozenset[str] = frozenset()  # names known to be included even when the filter is unresolved


@dataclass(eq=False)
class ColFact:
    name: str
    assigned: bool = False  # created or overwritten by the analysed code (not only read from the file)
    line: int = 0
    end_line: int = 0
    deps: set[str] = field(default_factory=set)
    fwd: list[tuple[int, int, str, str]] = field(default_factory=list)  # (line, end_line, operation, confidence)
    taints: set[Taint] = field(default_factory=set)
    thresholded: bool = False
    shifted: bool = False


@dataclass(eq=False)
class Origin:
    """One table lineage: every value derived from the same loaded or constructed table shares it."""

    id: int
    line: int
    source: str
    cols: dict[str, ColFact] = field(default_factory=dict)
    time_cols: dict[str, str] = field(default_factory=dict)  # column -> "parsed" or "name"
    time_index: str | None = None
    sorted_by_time: bool = False
    shuffled_line: int | None = None
    ordered_ops: set[str] = field(default_factory=set)
    entity: dict[str, tuple[str, str]] = field(default_factory=dict)  # column -> (evidence text, strength)
    cat_cols: set[str] = field(default_factory=set)
    panel_keys: set[str] = field(default_factory=set)
    aggregated_by: set[str] = field(default_factory=set)
    file_entities: set[str] = field(default_factory=set)
    path: str | None = None

    def time_strength(self) -> str | None:
        """strong: a time column and evidence that row order matters. weak: only one of the two."""
        has_col = bool(self.time_cols) or self.time_index is not None
        parsed = "parsed" in self.time_cols.values() or self.time_index == "parsed"
        ordered = self.sorted_by_time or bool(self.ordered_ops)
        if has_col and ordered:
            return "strong"
        if parsed or ordered:
            return "weak"
        return None

    def time_evidence(self) -> str:
        bits = []
        for c, how in sorted(self.time_cols.items()):
            bits.append(f"column `{c}` ({'parsed as datetime' if how == 'parsed' else 'date-like name'})")
        if self.time_index:
            bits.append("datetime index")
        if self.sorted_by_time:
            bits.append("rows sorted by time")
        if self.ordered_ops:
            bits.append("order-dependent operations: " + ", ".join(sorted(self.ordered_ops)))
        return "; ".join(bits)


@dataclass(eq=False)
class Split:
    id: int
    line: int
    end_line: int
    call: str  # e.g. "train_test_split", "KFold.split", "cross_val_score(cv=5)"
    parent: Rows
    origin: Origin | None
    row_level: bool = True  # partitions individual rows without regard to entity
    group_aware: bool = False
    chronological: bool = False
    is_cv: bool = False
    checked: bool = False
    info: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Rows:
    """Which rows a value holds: all rows of an origin, or one side of a split."""

    role: str  # "all", "train", "test", "mixed"
    split: Split | None = None
    oid: int = 0

    def other(self) -> Rows:
        return Rows({"train": "test", "test": "train"}.get(self.role, self.role), self.split, self.oid)


def covers(a: Rows, b: Rows) -> bool:
    """True when row set `a` includes every row of `b` (b is a, or a side of a split of something a covers)."""
    seen = 0
    while seen < 50:
        if a == b:
            return True
        if a.role == "mixed" and b.split is not None and b.split is a.split:
            return True
        if b.split is None:
            return False
        b = b.split.parent
        seen += 1
    return False


@dataclass(frozen=True)
class Taint:
    kind: str  # "pre" (statistic of rows) or "dup" (copied or synthetic rows)
    line: int
    end_line: int
    detail: str
    src: Rows
    supervised: bool = False
    confidence: str = "high"
    stat_cols: frozenset[str] = frozenset()
    subtype: str | None = None


@dataclass(frozen=True)
class Data(AVal):
    origin: Origin
    rows: Rows
    kind: str = "frame"  # frame, series, array, index, bunch
    cols: Cols | None = None
    col: str | None = None
    taints: frozenset[Taint] = frozenset()
    deps: frozenset[str] = frozenset()
    fwd: tuple[tuple[int, int, str, str], ...] = ()
    is_stat: bool = False
    stat_src: Rows | None = None
    stat_cols: frozenset[str] = frozenset()
    window: str | None = None  # rolling, expanding, ewm, groupby
    gkeys: tuple[str, ...] = ()
    centered: bool = False
    reversed: bool = False
    is_time: bool = False
    subset: bool = False
    thresholded: bool = False
    shifted: bool = False
    pred_of: object = None
    unique_of: str | None = None


@dataclass(frozen=True)
class Indexer(AVal):
    data: Data
    how: str  # "iloc", "loc", "at", "iat"


@dataclass(frozen=True)
class Bound(AVal):
    recv: AVal
    name: str


@dataclass(frozen=True)
class SplitIter(AVal):
    split: Split


@dataclass(frozen=True)
class EvalEvent:
    line: int
    end_line: int
    kind: str  # "holdout" or "cv"
    rows: Rows
    loops: tuple[int, ...]
    val_hint: bool = False
    what: str = ""


@dataclass(frozen=True)
class Score(AVal):
    events: frozenset[EvalEvent]


@dataclass(eq=False)
class FitRec:
    rows: Rows
    origin: Origin
    line: int
    end_line: int
    supervised: bool = False


@dataclass(eq=False)
class Est(AVal):
    cls: str
    kind: str  # transformer, model, resampler, search
    line: int = 0
    flavour: str = "statistical"  # statistical, vocabulary, supervised, generic (transformers only)
    steps: list[Est] = field(default_factory=list)
    fit: FitRec | None = None
    inner: Est | None = None  # estimator wrapped by a search object
    cv: AVal = UNKNOWN
    params: set[str] = field(default_factory=set)


@dataclass(eq=False)
class SplitterV(AVal):
    cls: str
    kind: str  # row, group, time
    line: int = 0
    end_line: int = 0
    shuffle: bool | None = None
