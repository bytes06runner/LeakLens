"""Syntactic evidence for hand-written splits in research code (EVAL_CHANGES.md #13).

Two pre-passes over the module, before the abstract interpretation:

- `attribute_entities`: collections whose items carry an entity attribute with a strong name, e.g. `r.subject`
  in `for r in recs`, `recs[k].subject`, `[r.patient for r in visits]`. The analyser then treats data derived
  from such a collection as carrying that entity (entity evidence by attribute, next to column names and file
  paths).
- `within_entity_splits`: a loop over the rows of one entity at a time (a dict keyed by an entity attribute or
  a `groupby` on an entity column) that sends one slice of each entity's rows to one list and the complementary
  slice to another, so that every entity is on both sides (within-entity evaluation).
"""

from __future__ import annotations

import ast
from collections.abc import Callable


def _base_name(node: ast.expr) -> str | None:
    while isinstance(node, ast.Subscript | ast.Attribute | ast.Call):
        node = node.value if not isinstance(node, ast.Call) else node.func
    return node.id if isinstance(node, ast.Name) else None


def attribute_entities(tree: ast.Module, strength: Callable[[str], str | None]) -> dict[str, str]:
    """{collection name: entity attribute} for strong-name attributes read on the collection's items."""
    out: dict[str, str] = {}
    loop_of: dict[str, str] = {}  # loop variable -> collection name, from for loops and comprehensions
    for node in ast.walk(tree):
        if isinstance(node, ast.For | ast.comprehension) and isinstance(node.target, ast.Name):
            coll = _base_name(node.iter)
            if coll:
                loop_of[node.target.id] = coll
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or strength(node.attr) != "strong":
            continue
        v = node.value
        if isinstance(v, ast.Subscript) and isinstance(v.value, ast.Name):  # recs[k].subject
            out.setdefault(v.value.id, node.attr)
        elif isinstance(v, ast.Name) and v.id in loop_of:  # for r in recs: r.subject
            out.setdefault(loop_of[v.id], node.attr)
    return out


def _entity_groupings(tree: ast.Module, strength: Callable[[str], str | None]) -> dict[str, str]:
    """{dict name: entity} for dicts filled per entity: D.setdefault(r.subject, ...), D[r.subject].append(...)."""
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        key, dname = None, None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "setdefault":
            dname = _base_name(node.func.value)
            key = node.args[0] if node.args else None
        elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            dname, key = node.value.id, node.slice
        if dname and isinstance(key, ast.Attribute) and strength(key.attr) == "strong":
            out.setdefault(dname, key.attr)
    return out


def _slice_kind(node: ast.expr) -> tuple[str, str] | None:
    """('head' | 'tail', alias) for G[:k] / G[k:] / G.iloc[:k] / G.iloc[k:]."""
    if not isinstance(node, ast.Subscript) or not isinstance(node.slice, ast.Slice):
        return None
    sl = node.slice
    base = node.value
    if isinstance(base, ast.Attribute) and base.attr in ("iloc", "loc"):
        base = base.value
    if not isinstance(base, ast.Name) or sl.step is not None:
        return None
    if sl.lower is None and sl.upper is not None:
        return "head", base.id
    if sl.lower is not None and sl.upper is None:
        return "tail", base.id
    return None


def within_entity_splits(tree: ast.Module, strength: Callable[[str], str | None]) -> list[dict]:
    """Loops that put a head slice of every entity's rows on one side and the tail slice on the other."""
    groupings = _entity_groupings(tree, strength)
    found = []
    for loop in ast.walk(tree):
        if not isinstance(loop, ast.For):
            continue
        entity, group_var = None, None
        it = loop.iter
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute):
            owner = _base_name(it.func.value)
            if it.func.attr in ("items", "values") and owner in groupings:
                entity = groupings[owner]
                tgt = loop.target
                group_var = (tgt.elts[-1] if isinstance(tgt, ast.Tuple) else tgt)
            elif it.func.attr == "groupby" and it.args and isinstance(it.args[0], ast.Constant) \
                    and isinstance(it.args[0].value, str) and strength(it.args[0].value) == "strong":
                entity = it.args[0].value
                tgt = loop.target
                group_var = tgt.elts[-1] if isinstance(tgt, ast.Tuple) else None
        if entity is None or not isinstance(group_var, ast.Name):
            continue
        aliases = {group_var.id}
        sides: dict[str, tuple[str, ast.stmt]] = {}  # target list -> (head/tail, statement)
        for st in ast.walk(ast.Module(body=loop.body, type_ignores=[])):
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                if _base_name(st.value) in aliases:  # rs = sorted(rs, ...), g = g.sort_values(...)
                    aliases.add(st.targets[0].id)
            target, value = None, None
            if isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name):
                target, value = st.target.id, st.value
            elif isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) \
                    and isinstance(st.value.func, ast.Attribute) and st.value.func.attr in ("append", "extend") \
                    and st.value.args:
                target, value = _base_name(st.value.func.value), st.value.args[0]
            if target is None:
                continue
            if isinstance(value, ast.List) and len(value.elts) == 1:
                value = value.elts[0]
            sk = _slice_kind(value)
            if sk and sk[1] in aliases and target not in sides:
                sides[target] = (sk[0], st)
        kinds = {k for k, _ in sides.values()}
        if {"head", "tail"} <= kinds:
            stmts = sorted((s for _, s in sides.values()), key=lambda s: s.lineno)
            head = next(t for t, (k, _) in sides.items() if k == "head")
            tail = next(t for t, (k, _) in sides.items() if k == "tail")
            found.append({"entity": entity, "line": stmts[0].lineno,
                          "end_line": stmts[-1].end_lineno or stmts[-1].lineno, "loop_line": loop.lineno,
                          "head": head, "tail": tail})
    return found
