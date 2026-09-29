"""Print Markdown count tables for the injected benchmark (used to write benchmark/SPLIT.md)."""

import hashlib
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
m = pd.read_csv(HERE / "manifest.csv")
lab = pd.read_csv(HERE / "_groundtruth" / "labels.csv")


def md(df: pd.DataFrame) -> str:
    df = df.reset_index()
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "---|" * len(df.columns)
    rows = ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


def with_total(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t["total"] = t.sum(axis=1)
    t.loc["total"] = t.sum()
    return t


print("### Items per split\n")
m["kind"] = m["categories"].where(m["categories"].isin(["clean", "trap"]), "leaky")
print(md(with_total(pd.crosstab(m["kind"], m["split"]))))
print("\n### Leaks per type and split\n")
print(md(with_total(pd.crosstab(lab["type"], lab["split"]))))
print("\n### Leaks per category and split\n")
print(md(with_total(pd.crosstab(lab["category"], lab["split"]))))
print("\n### Bases\n")
print(md(m.groupby(["split", "family", "base"]).size().rename("items").to_frame()))
print("\n### Formats\n")
print(md(with_total(pd.crosstab(m["format"], m["split"]))))
for f in ("split.csv", "manifest.csv", "_groundtruth/labels.csv"):
    print(f"\n`{f}` sha256: `{hashlib.sha256((HERE / f).read_bytes()).hexdigest()}`")
