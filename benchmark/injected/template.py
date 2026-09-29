"""Minimal template engine for base pipelines.

A base is ordinary Python with named slots:

    #<split>
    X_train, X_test, y_train, y_test = train_test_split(X, y, ...)
    #</split>

The default slot content is the clean code. Operators replace slot content; a line they want recorded as a leak
ends with `#!LEAK<k>` (k = leak index within the item). Rendering drops the slot markers and the leak markers, so
the generated item contains no hint of the ground truth, and returns the 1-based line numbers of each leak.
`# %%` lines separate notebook cells.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SLOT_OPEN = re.compile(r"^#<(\w+)>$")
SLOT_CLOSE = re.compile(r"^#</(\w+)>$")
LEAK_MARK = re.compile(r"\s*#!LEAK(\d+)\s*$")
CELL = "# %%"


@dataclass
class Template:
    parts: list  # ("text", [lines]) or ("slot", name, [lines])

    @property
    def slots(self) -> dict[str, list[str]]:
        return {p[1]: p[2] for p in self.parts if p[0] == "slot"}


def parse(text: str) -> Template:
    parts, current, slot = [], [], None
    for line in text.splitlines():
        m_open, m_close = SLOT_OPEN.match(line), SLOT_CLOSE.match(line)
        if m_open:
            if slot is not None:
                raise ValueError(f"nested slot {m_open.group(1)} inside {slot}")
            parts.append(("text", current))
            current, slot = [], m_open.group(1)
        elif m_close:
            if m_close.group(1) != slot:
                raise ValueError(f"closing {m_close.group(1)} but open slot is {slot}")
            parts.append(("slot", slot, current))
            current, slot = [], None
        else:
            current.append(line)
    if slot is not None:
        raise ValueError(f"unclosed slot {slot}")
    parts.append(("text", current))
    return Template(parts)


@dataclass
class Rendered:
    lines: list[str]
    leaks: dict[int, list[int]] = field(default_factory=dict)  # leak index -> 1-based line numbers

    @property
    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def render(tpl: Template, overrides: dict[str, list[str]] | None = None) -> Rendered:
    overrides = overrides or {}
    unknown = set(overrides) - set(tpl.slots)
    if unknown:
        raise KeyError(f"operator writes unknown slots {sorted(unknown)}")
    out = Rendered([])
    for p in tpl.parts:
        lines = p[1] if p[0] == "text" else overrides.get(p[1], p[2])
        for line in lines:
            m = LEAK_MARK.search(line)
            if m:
                line = line[: m.start()]
                out.leaks.setdefault(int(m.group(1)), []).append(len(out.lines) + 1)
            out.lines.append(line)
    # Collapse runs of blank lines left by empty slots, keeping leak line numbers valid.
    return _squeeze_blank(out)


def _squeeze_blank(r: Rendered) -> Rendered:
    keep, new_no, prev_blank = [], {}, False
    for i, line in enumerate(r.lines, start=1):
        blank = line.strip() == ""
        if blank and prev_blank:
            continue
        keep.append(line)
        new_no[i] = len(keep)
        prev_blank = blank
    while keep and keep[-1].strip() == "":
        keep.pop()
    leaks = {k: [new_no[n] for n in v] for k, v in r.leaks.items()}
    return Rendered(keep, leaks)


def to_cells(r: Rendered) -> tuple[list[list[str]], dict[int, list[tuple[int, int]]]]:
    """Split rendered lines into notebook cells at `# %%`; map leak lines to (cell index, line in cell)."""
    cells, where = [], {}
    current, start = [], None
    for i, line in enumerate(r.lines, start=1):
        if line.strip() == CELL:
            if current or start is not None:
                cells.append(current)
            current, start = [], i
            continue
        where[i] = (len(cells), len(current) + 1)
        current.append(line)
    cells.append(current)
    # Drop leading/trailing blank lines inside cells, adjusting positions.
    clean_cells, remap = [], {}
    for ci, cell in enumerate(cells):
        lo = 0
        while lo < len(cell) and cell[lo].strip() == "":
            lo += 1
        hi = len(cell)
        while hi > lo and cell[hi - 1].strip() == "":
            hi -= 1
        remap[ci] = (len(clean_cells), lo)
        if hi > lo:
            clean_cells.append(cell[lo:hi])
    leaks = {}
    for k, nums in r.leaks.items():
        leaks[k] = []
        for n in nums:
            ci, li = where[n]
            new_ci, lo = remap[ci]
            leaks[k].append((new_ci, li - lo))
    return clean_cells, leaks
