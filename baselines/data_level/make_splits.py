"""Write leaky train/test CSVs from the group and temporal probes (random split, as the probes do).

Used only to check whether data-level baseline tools run and what they need from the user (Phase 0).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(0)

# Group probe: 40 patients x 25 rows, random split.
g = pd.DataFrame({"patient_id": np.repeat(np.arange(40), 25)})
offset = rng.normal(size=40)[g["patient_id"]]
g["f1"] = offset + rng.normal(scale=0.3, size=len(g))
g["f2"] = rng.normal(size=len(g))
g["label"] = (offset > 0).astype(int)
tr, te = train_test_split(g, test_size=0.2, random_state=0)
tr.to_csv(out / "group_train.csv", index=False)
te.to_csv(out / "group_test.csv", index=False)

# Temporal probe: daily random walk, lag feature before split, shuffled split.
t = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=730, freq="D")})
t["value"] = np.cumsum(rng.normal(size=len(t)))
t["lag1"] = t["value"].shift(1)
t["label"] = (t["value"].shift(-1) > t["value"]).astype(int)
t = t.dropna()
tr, te = train_test_split(t, test_size=0.2, shuffle=True, random_state=0)
tr.to_csv(out / "temporal_train.csv", index=False)
te.to_csv(out / "temporal_test.csv", index=False)
print("wrote", sorted(p.name for p in out.iterdir()))
