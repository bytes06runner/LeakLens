# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.model_selection import train_test_split

# %%
frame = pd.read_csv("data.csv")
label = "complication"
cols = ["visit", "age", "bp_sys", "height_cm", "resting_hr", "creatinine"]

# %%
X_all = frame[cols]
y_all = frame[label]
Xtr, Xte, ytr, yte = train_test_split(X_all, y_all, test_size=0.25, stratify=y_all, random_state=0)

# %%
estimator = RandomForestClassifier(n_estimators=200, min_samples_leaf=2, random_state=0, n_jobs=1)
estimator.fit(Xtr, ytr)
result = roc_auc_score(yte, estimator.predict_proba(Xte)[:, 1])
print(f"test_auc: {result:.4f}")
