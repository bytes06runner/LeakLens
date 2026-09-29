# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.model_selection import ShuffleSplit

# %%
frame = pd.read_csv("data.csv")
label = "diagnosis"
cols = ["marker_a", "marker_b", "marker_c", "marker_d"]

# %%
X_all = frame[cols]
y_all = frame[label]
splitter = ShuffleSplit(n_splits=1, test_size=0.25, random_state=0)
train_idx, test_idx = next(splitter.split(X_all, y_all))
Xtr, Xte = X_all.iloc[train_idx], X_all.iloc[test_idx]
ytr, yte = y_all.iloc[train_idx], y_all.iloc[test_idx]

# %%
estimator = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=0, n_jobs=1)
estimator.fit(Xtr, ytr)
result = roc_auc_score(yte, estimator.predict_proba(Xte)[:, 1])
print(f"test_auc: {result:.4f}")
