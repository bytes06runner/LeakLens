"""Generate the injected benchmark: items, ground-truth labels, fixed versions, manifest.

Outputs (all deterministic):
  items/<item_id>/pipeline.py | pipeline.ipynb     what tools analyse (no ground-truth hints inside)
  _groundtruth/labels.csv                          one row per injected leak, exact lines
  _groundtruth/fixed/<item_id>.py                  canonically fixed version (Phase 6 reference)
  _groundtruth/leaky_py/<item_id>.py               leaky version as a script (for inflation runs)
  manifest.csv                                     one row per item, incl. DEV/TEST split and file hash

Per item, a stable hash picks the file format (.py or .ipynb), whether notebook cells carry execution counts,
and a naming style (three consistent renamings of the shared variables), so items differ in surface form.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import tokenize
from pathlib import Path

import nbformat
import yaml

import operators as ops
import template

HERE = Path(__file__).resolve().parent
ITEMS, GT = HERE / "items", HERE / "_groundtruth"

STYLES = [
    {},
    {"df": "data", "X": "features", "y": "labels", "X_train": "features_train", "X_test": "features_test",
     "y_train": "labels_train", "y_test": "labels_test", "model": "clf", "FEATURES": "feature_cols",
     "TARGET": "target_col", "score": "test_score", "scores": "cv_scores", "cv": "cv_iter"},
    {"df": "frame", "X": "X_all", "y": "y_all", "X_train": "Xtr", "X_test": "Xte", "y_train": "ytr",
     "y_test": "yte", "model": "estimator", "FEATURES": "cols", "TARGET": "label", "score": "result",
     "scores": "fold_scores", "cv": "folds"},
]


def stable_int(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest()[:12], 16)


def rename_identifiers(text: str, mapping: dict[str, str]) -> str:
    """Rename variables via the tokenizer: skip attributes (`a.name`) and keyword arguments (`f(name=...)`)."""
    if not mapping:
        return text
    toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    edits, depth = [], 0
    for i, t in enumerate(toks):
        if t.type == tokenize.OP and t.string in "([{":
            depth += 1
        elif t.type == tokenize.OP and t.string in ")]}":
            depth -= 1
        if t.type != tokenize.NAME or t.string not in mapping:
            continue
        prev = toks[i - 1] if i else None
        nxt = next((u for u in toks[i + 1:] if u.type not in (tokenize.NL, tokenize.COMMENT)), None)
        if prev is not None and prev.type == tokenize.OP and prev.string == ".":
            continue
        if depth > 0 and nxt is not None and nxt.type == tokenize.OP and nxt.string == "=":
            continue
        edits.append((t.start, t.end, mapping[t.string]))
    lines = text.splitlines(keepends=True)
    for (r0, c0), (r1, c1), new in sorted(edits, reverse=True):
        assert r0 == r1
        line = lines[r0 - 1]
        lines[r0 - 1] = line[:c0] + new + line[c1:]
    return "".join(lines)


def merge(muts: list[ops.Mutation]) -> ops.Mutation:
    out = ops.Mutation()
    fixed: dict[str, list[str]] = {}
    for m in muts:
        clash = set(out.overrides) & set(m.overrides)
        if clash:
            raise ValueError(f"operators write the same slots {clash}")
        out.overrides.update(m.overrides)
        out.imports += m.imports
        fixed.update(m.fixed_overrides or {})
        out.fixed_imports += m.fixed_imports
        out.labels.update(m.labels)
        if m.data_transform:
            out.data_transform = {**(out.data_transform or {}), **m.data_transform}
        out.rename_col = m.rename_col or out.rename_col
    out.fixed_overrides = fixed or None
    return out


def build(tpl: template.Template, overrides: dict, imports: list[str], rename_col) -> template.Rendered:
    base_text = "\n".join("\n".join(p[1] if p[0] == "text" else p[2]) for p in tpl.parts)
    new_imports = [i for i in dict.fromkeys(imports) if i not in base_text]
    r = template.render(tpl, {**overrides, "imports": new_imports})
    if rename_col:
        old, new = rename_col
        r = template.Rendered([ln.replace(f'"{old}"', f'"{new}"') for ln in r.lines], r.leaks)
    return r


def items():
    meta = yaml.safe_load((HERE / "bases.yaml").read_text())
    split = {row["base"]: row["split"] for row in csv.DictReader((HERE / "split.csv").open())}
    for base in sorted(meta):
        m = meta[base]
        tpl = template.parse((HERE / "bases" / f"{base}.py").read_text())
        yield base, m, split[base], tpl, f"{base}__clean", ops.Mutation()
        for name, (fn, variants, applies) in ops.OPERATORS.items():
            if not applies(base, m):
                continue
            for v in variants:
                yield base, m, split[base], tpl, f"{base}__{name}__{v}", fn(base, m, tpl.slots, v, 1)
        for n, (cb, pairs) in enumerate(ops.COMBOS, start=1):
            if cb == base:
                muts = [ops.OPERATORS[o][0](base, m, tpl.slots, v, k) for k, (o, v) in enumerate(pairs, start=1)]
                yield base, m, split[base], tpl, f"{base}__combo{n}", merge(muts)


def main() -> None:
    for d in (ITEMS, GT):
        if d.exists():
            shutil.rmtree(d)
    (GT / "fixed").mkdir(parents=True)
    (GT / "leaky_py").mkdir(parents=True)
    manifest, labels = [], []

    for base, m, split, tpl, item_id, mut in items():
        h = stable_int(item_id)
        style = STYLES[h % 3]
        fmt = "ipynb" if (h >> 4) % 2 else "py"
        with_counts = (h >> 8) % 10 < 7

        leaky = build(tpl, mut.overrides, mut.imports, mut.rename_col)
        leaky_text = rename_identifiers(leaky.text, style)
        leaky_lines = leaky_text.splitlines()
        assert len(leaky_lines) == len(leaky.lines)
        fixed = build(tpl, mut.fixed_overrides or {}, mut.fixed_imports, mut.rename_col)
        fixed_text = rename_identifiers(fixed.text, style)
        compile(leaky_text, item_id, "exec")
        compile(fixed_text, item_id, "exec")
        (GT / "leaky_py" / f"{item_id}.py").write_text(leaky_text)
        (GT / "fixed" / f"{item_id}.py").write_text(fixed_text)

        d = ITEMS / item_id
        d.mkdir(parents=True)
        renamed = template.Rendered(leaky_lines, leaky.leaks)
        if fmt == "py":
            path = d / "pipeline.py"
            path.write_text(leaky_text)
            loc = {k: [(None, n) for n in v] for k, v in leaky.leaks.items()}
            flat = {k: list(v) for k, v in leaky.leaks.items()}
        else:
            cells, loc = template.to_cells(renamed)
            nb = nbformat.v4.new_notebook()
            nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
            for i, c in enumerate(cells):
                cell = nbformat.v4.new_code_cell("\n".join(c))
                cell.execution_count = i + 1 if with_counts else None
                cell.id = hashlib.sha256(f"{item_id}:{i}".encode()).hexdigest()[:8]  # nbformat's default is random
                nb.cells.append(cell)
            path = d / "pipeline.ipynb"
            nbformat.write(nb, path)
            offsets, acc = [], 0
            for c in cells:
                offsets.append(acc)
                acc += len(c)
            flat = {k: [offsets[ci] + li for ci, li in v] for k, v in loc.items()}

        cats = sorted({lab.category for lab in mut.labels.values()}) or (
            ["trap"] if "__trap_" in item_id else ["clean"])
        manifest.append({
            "item_id": item_id, "base": base, "family": m["family"], "shape": m["shape"], "split": split,
            "format": fmt, "exec_counts": with_counts if fmt == "ipynb" else "", "style": STYLES.index(style),
            "operators": item_id.split("__", 1)[1], "n_leaks": len(mut.labels), "categories": ";".join(cats),
            "data_transform": json.dumps(mut.data_transform or {}, sort_keys=True),
            "metric": m["metric"], "higher_is_better": m["higher_is_better"],
            "file": path.relative_to(HERE).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
        for k, lab in sorted(mut.labels.items()):
            cell_lines = [li for _, li in loc[k]]
            cell = loc[k][0][0]
            labels.append({
                "item_id": item_id, "leak": k, "type": lab.type, "alt_types": ";".join(lab.alt_types),
                "subtype": lab.subtype or "", "category": lab.category, "split": split,
                "file": path.relative_to(HERE).as_posix(), "cell": "" if cell is None else cell,
                "line_start": min(cell_lines), "line_end": max(cell_lines),
                "flat_line_start": min(flat[k]), "flat_line_end": max(flat[k]),
                "lines": ";".join(map(str, cell_lines)),
            })

    with (HERE / "manifest.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0]))
        w.writeheader()
        w.writerows(manifest)
    with (GT / "labels.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(labels[0]))
        w.writeheader()
        w.writerows(labels)
    print(f"{len(manifest)} items, {len(labels)} leaks")


if __name__ == "__main__":
    main()
