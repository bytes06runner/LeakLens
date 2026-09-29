# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.model_selection import train_test_split

# %%
df = pd.read_csv("data.csv")
TARGET = "complication"
FEATURES = ["visit", "age", "bp_sys", "height_cm", "resting_hr", "creatinine"]

# %%
X = df[FEATURES]
y = df[TARGET]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)

# %%
model = RandomForestClassifier(n_estimators=200, min_samples_leaf=2, random_state=0, n_jobs=1)
model.fit(X_train, y_train)
score = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
print(f"test_auc: {score:.4f}")
