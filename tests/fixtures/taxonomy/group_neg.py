import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit

rng = np.random.default_rng(0)
df = pd.DataFrame({"patient_id": np.repeat(np.arange(20), 10), "x": rng.normal(size=200)})
df["y"] = (df["patient_id"] % 2).astype(int)
X, y = df[["x"]].assign(p=df["patient_id"] * 0.1 + rng.normal(0, 0.01, 200)), df["y"]
train_idx, test_idx = next(GroupShuffleSplit(test_size=0.25, random_state=0).split(X, y, groups=df["patient_id"]))
model = RandomForestClassifier(random_state=0).fit(X.iloc[train_idx], y.iloc[train_idx])
print(model.score(X.iloc[test_idx], y.iloc[test_idx]))
