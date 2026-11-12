"""Load `.py` and `.ipynb` files into one flat module with a line map (docs/SPEC.md section 1).

A notebook's code cells are concatenated in **execution order** when every non-empty code cell has a unique
`execution_count`, otherwise in **cell order**; the order used is recorded. IPython lines (`%magic`, `!cmd`) are
replaced by `pass` so the line count is unchanged. Cells in another language or that do not parse are skipped
and listed. Nothing is imported or executed.
"""

from __future__ import annotations

import ast
import json
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path

_MAGIC = re.compile(r"^(\s*)(%|!)")
_OTHER_LANGUAGE = re.compile(
    r"^\s*%%(bash|sh|sql|html|javascript|js|latex|perl|ruby|R|writefile|script|cmd|svg|markdown)\b"
)
_SKIP_DIRS = {".venv", "venv", "site-packages", ".ipynb_checkpoints", "__pycache__", "node_modules", ".git"}


@dataclass
class Source:
    """One analysable file. `flat` is the module text; `line_map[i]` is (cell index or None, line in cell or file)
    for flat line i + 1."""

    path: str
    kind: str  # "py" or "ipynb"
    flat: str = ""
    line_map: list[tuple[int | None, int]] = field(default_factory=list)
    status: str = "ok"  # "ok" or "unanalysable"
    reason: str | None = None
    order_used: str | None = None  # "execution" or "cell" for notebooks
    skipped_cells: list[dict] = field(default_factory=list)
    tree: ast.Module | None = None

    def locate(self, flat_line: int) -> tuple[int | None, int]:
        if 1 <= flat_line <= len(self.line_map):
            return self.line_map[flat_line - 1]
        return (None, flat_line)

    def line_text(self, flat_line: int) -> str:
        lines = self.flat.splitlines()
        return lines[flat_line - 1] if 1 <= flat_line <= len(lines) else ""

    def ingest_info(self) -> dict:
        return {"order_used": self.order_used, "skipped_cells": self.skipped_cells}


def _neutralise(src: str) -> str:
    """Replace IPython lines by `pass`, keeping indentation and the number of lines."""
    out = []
    for line in src.splitlines():
        m = _MAGIC.match(line)
        out.append(f"{m.group(1)}pass" if m else line)
    return "\n".join(out)


def _parse(src: str) -> ast.Module:
    with warnings.catch_warnings():  # invalid escape sequences in analysed code are not our warnings
        warnings.simplefilter("ignore")
        return ast.parse(src)


def _parses(src: str) -> bool:
    try:
        _parse(src)
        return True
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return False


def load_py(path: Path, display: str | None = None) -> Source:
    s = Source(path=display or str(path), kind="py")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        s.status, s.reason = "unanalysable", f"cannot read file: {e.__class__.__name__}"
        return s
    s.flat = _neutralise(text)
    s.line_map = [(None, i) for i in range(1, s.flat.count("\n") + 2)]
    try:
        s.tree = _parse(s.flat)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as e:
        s.status = "unanalysable"
        s.reason = f"does not parse as Python 3.12: {e.__class__.__name__} at line {getattr(e, 'lineno', '?')}"
    return s


def load_ipynb(path: Path, display: str | None = None) -> Source:
    s = Source(path=display or str(path), kind="ipynb")
    try:
        nb = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        cells = nb["cells"] if "cells" in nb else [c for ws in nb.get("worksheets", []) for c in ws.get("cells", [])]
    except (OSError, ValueError, KeyError, TypeError) as e:
        s.status, s.reason = "unanalysable", f"not a readable notebook: {e.__class__.__name__}"
        return s
    code = []
    for idx, cell in enumerate(cells):
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        raw = cell.get("source", cell.get("input", ""))
        src = "".join(raw) if isinstance(raw, list) else str(raw)
        if not src.strip():
            continue
        ec = cell.get("execution_count", cell.get("prompt_number"))
        code.append((idx, src, ec if isinstance(ec, int) else None))
    counts = [ec for _, _, ec in code]
    if code and all(c is not None for c in counts) and len(set(counts)) == len(counts):
        s.order_used = "execution"
        code.sort(key=lambda c: c[2])
    else:
        s.order_used = "cell"
    parts: list[str] = []
    for idx, src, _ in code:
        if _OTHER_LANGUAGE.match(src):
            s.skipped_cells.append({"cell": idx, "reason": "cell magic changes the language"})
            continue
        body = _neutralise(src)
        if not _parses(body):
            s.skipped_cells.append({"cell": idx, "reason": "cell does not parse as Python 3.12"})
            continue
        n = body.count("\n") + 1
        parts.append(body)
        s.line_map.extend((idx, i) for i in range(1, n + 1))
    if not parts:
        s.status = "unanalysable"
        s.reason = "no code cell could be parsed" if code else "notebook has no code cells"
        return s
    s.flat = "\n".join(parts)
    try:
        s.tree = _parse(s.flat)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as e:  # cells parse alone but not together
        s.status, s.reason = "unanalysable", f"cells do not parse together: {e.__class__.__name__}"
    return s


def load(path: str | Path, display: str | None = None) -> Source:
    p = Path(path)
    return load_ipynb(p, display) if p.suffix == ".ipynb" else load_py(p, display)


def collect(paths: list[str | Path], exclude: list[str] | None = None) -> list[Path]:
    """Expand files and directories into the list of `.py` / `.ipynb` files to analyse (SPEC section 1)."""
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for q in sorted(p.rglob("*")):
                rel = q.relative_to(p)
                if q.suffix not in (".py", ".ipynb") or not q.is_file():
                    continue
                if any(part.startswith(".") or part in _SKIP_DIRS for part in rel.parts[:-1]):
                    continue
                if exclude and any(rel.match(pat) for pat in exclude):
                    continue
                out.append(q)
        else:
            out.append(p)
    return out


__all__ = ["Source", "collect", "load", "load_ipynb", "load_py"]
