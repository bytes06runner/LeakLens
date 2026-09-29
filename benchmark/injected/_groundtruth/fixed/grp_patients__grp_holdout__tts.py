# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

# %%
df = pd.read_csv("data.csv")
TARGET = "complication"
FEATURES = ["visit", "age", "bp_sys", "height_cm", "resting_hr", "creatinine"]

# %%
X = df[FEATURES]
y = df[TARGET]
splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=0)
train_idx, test_idx = next(splitter.split(X, y, groups=df["patient_id"]))
X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

# %%
model = RandomForestClassifier(n_estimators=200, min_samples_leaf=2, random_state=0, n_jobs=1)
model.fit(X_train, y_train)
score = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
print(f"test_auc: {score:.4f}")
