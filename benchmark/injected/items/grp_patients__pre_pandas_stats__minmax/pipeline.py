# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

# %%
frame = pd.read_csv("data.csv")
label = "complication"
cols = ["visit", "age", "bp_sys", "height_cm", "resting_hr", "creatinine"]

# %%
X_all = frame[cols]
y_all = frame[label]
num_cols = X_all.select_dtypes("number").columns
X_all = X_all.copy()
X_all[num_cols] = (X_all[num_cols] - X_all[num_cols].min()) / (X_all[num_cols].max() - X_all[num_cols].min())
splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=0)
train_idx, test_idx = next(splitter.split(X_all, y_all, groups=frame["patient_id"]))
Xtr, Xte = X_all.iloc[train_idx], X_all.iloc[test_idx]
ytr, yte = y_all.iloc[train_idx], y_all.iloc[test_idx]

# %%
estimator = RandomForestClassifier(n_estimators=200, min_samples_leaf=2, random_state=0, n_jobs=1)
estimator.fit(Xtr, ytr)
result = roc_auc_score(yte, estimator.predict_proba(Xte)[:, 1])
print(f"test_auc: {result:.4f}")
