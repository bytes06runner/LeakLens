# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

# %%
frame = pd.read_csv("data.csv")
label = "diagnosis"
cols = ["marker_a", "marker_b", "marker_c", "marker_d"]

# %%
X_all = frame[cols]
y_all = frame[label]
gss = GroupShuffleSplit(n_splits=1, test_size=0.34, random_state=1)
train_idx, test_idx = next(gss.split(X_all, y_all, groups=frame["site"]))
Xtr, Xte = X_all.iloc[train_idx], X_all.iloc[test_idx]
ytr, yte = y_all.iloc[train_idx], y_all.iloc[test_idx]

# %%
estimator = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=0, n_jobs=1)
estimator.fit(Xtr, ytr)
result = roc_auc_score(yte, estimator.predict_proba(Xte)[:, 1])
print(f"test_auc: {result:.4f}")
