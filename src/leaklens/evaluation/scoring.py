"""Matching, per-type precision/recall and bootstrap confidence intervals (EVAL_PROTOCOL.md sections 2 to 4).

A *prediction* is (item_id, type, cell, line_start, line_end, confidence). A *label* is one row of
`benchmark/injected/_groundtruth/labels.csv`. The same code scores LeakLens and every baseline, so no tool gets
its own matching rule.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass

TYPES = ("preprocessing", "overlap", "multi_test", "group", "temporal", "target_derived")
CONFIDENCE = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class Pred:
    item_id: str
    type: str
    cell: int | None
    line_start: int
    line_end: int
    confidence: str = "medium"


@dataclass(frozen=True)
class Label:
    item_id: str
    type: str
    alt_types: tuple[str, ...]
    cell: int | None
    line_start: int
    line_end: int
    category: str
    subtype: str = ""

    @property
    def types(self) -> set[str]:
        return {self.type, *self.alt_types}


def label_from_row(r: dict) -> Label:
    cell = int(float(r["cell"])) if r.get("cell") not in (None, "", "nan") else None
    alts = tuple(a for a in (r.get("alt_types") or "").split(";") if a and a != "nan")
    return Label(
        r["item_id"],
        r["type"],
        alts,
        cell,
        int(r["line_start"]),
        int(r["line_end"]),
        r["category"],
        r.get("subtype", ""),
    )


def overlaps(p: Pred, lab: Label) -> bool:
    """Same file, same notebook cell, overlapping line range, and a type the label accepts."""
    return (
        p.item_id == lab.item_id
        and p.type in lab.types
        and p.cell == lab.cell
        and p.line_start <= lab.line_end
        and p.line_end >= lab.line_start
    )


def match_item(preds: list[Pred], labels: list[Label]) -> tuple[list[tuple[Pred, Label]], list[Pred], list[Label]]:
    """One-to-one matching inside one item. Labels are taken in order; each takes the first unused prediction that
    overlaps it. Returns (matched pairs, unmatched predictions = false positives, unmatched labels = misses)."""
    used: set[int] = set()
    pairs, missed = [], []
    for lab in labels:
        hit = next((i for i, p in enumerate(preds) if i not in used and overlaps(p, lab)), None)
        if hit is None:
            missed.append(lab)
        else:
            used.add(hit)
            pairs.append((preds[hit], lab))
    return pairs, [p for i, p in enumerate(preds) if i not in used], missed


def counts(preds: list[Pred], labels: list[Label], items: list[str], min_confidence: str = "medium") -> dict:
    """Per-item (tp, fp, fn) per type. A true positive counts for the label's primary type; a false positive for
    the type the tool reported."""
    by_p, by_l = defaultdict(list), defaultdict(list)
    for p in preds:
        if CONFIDENCE[p.confidence] >= CONFIDENCE[min_confidence]:
            by_p[p.item_id].append(p)
    for lab in labels:
        by_l[lab.item_id].append(lab)
    out: dict[str, dict[str, list[int]]] = {}
    for it in items:
        pairs, fps, misses = match_item(sorted(by_p[it], key=lambda p: p.line_start), by_l[it])
        c = {t: [0, 0, 0] for t in TYPES}
        for _, lab in pairs:
            c[lab.type][0] += 1
        for p in fps:
            c[p.type][1] += 1
        for lab in misses:
            c[lab.type][2] += 1
        out[it] = c
    return out


def prf(tp: int, fp: int, fn: int) -> tuple[float | None, float | None, float | None]:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
    return p, r, f


def aggregate(per_item: dict, items: list[str]) -> dict[str, tuple[int, int, int]]:
    tot = {t: [0, 0, 0] for t in TYPES}
    for it in items:
        for t in TYPES:
            for k in range(3):
                tot[t][k] += per_item[it][t][k]
    return {t: tuple(v) for t, v in tot.items()}


def bootstrap(
    per_item: dict, units: dict[str, list[str]], n: int = 2000, seed: int = 20261112, alpha: float = 0.05
) -> dict[str, dict[str, tuple[float, float] | None]]:
    """Percentile bootstrap CIs for precision, recall and F1 per type. `units` maps a resampling unit (an item, or
    a base pipeline for the sensitivity analysis) to its items; units are drawn with replacement."""
    rng = random.Random(seed)
    keys = sorted(units)
    samples: dict[str, dict[str, list[float]]] = {t: {"precision": [], "recall": [], "f1": []} for t in TYPES}
    for _ in range(n):
        drawn = [units[keys[rng.randrange(len(keys))]] for _ in keys]
        items = [it for group in drawn for it in group]
        agg = aggregate(per_item, items)
        for t in TYPES:
            for name, v in zip(("precision", "recall", "f1"), prf(*agg[t]), strict=True):
                if v is not None:
                    samples[t][name].append(v)
    out: dict[str, dict[str, tuple[float, float] | None]] = {}
    for t in TYPES:
        out[t] = {}
        for name, vals in samples[t].items():
            if len(vals) < n / 2:  # undefined in most resamples (for example no finding of this type at all)
                out[t][name] = None
                continue
            vals.sort()
            lo = vals[int(alpha / 2 * (len(vals) - 1))]
            hi = vals[int((1 - alpha / 2) * (len(vals) - 1))]
            out[t][name] = (lo, hi)
    return out


def summarise(
    preds: list[Pred],
    labels: list[Label],
    items: list[str],
    bases: dict[str, str] | None = None,
    min_confidence: str = "medium",
    n_boot: int = 2000,
) -> list[dict]:
    """One row per leakage type: counts, precision/recall/F1 and 95% CIs (items resampled; bases if given)."""
    per_item = counts(preds, labels, items, min_confidence)
    agg = aggregate(per_item, items)
    ci = bootstrap(per_item, {it: [it] for it in items}, n_boot)
    ci_base = None
    if bases:
        groups: dict[str, list[str]] = defaultdict(list)
        for it in items:
            groups[bases[it]].append(it)
        ci_base = bootstrap(per_item, groups, n_boot)
    rows = []
    for t in TYPES:
        tp, fp, fn = agg[t]
        p, r, f = prf(tp, fp, fn)
        row = {"type": t, "labels": tp + fn, "tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f}
        for name in ("precision", "recall", "f1"):
            row[f"{name}_ci"] = ci[t][name]
            if ci_base is not None:
                row[f"{name}_ci_bases"] = ci_base[t][name]
        rows.append(row)
    return rows
