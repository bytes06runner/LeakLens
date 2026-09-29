# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.utils import resample

# %%
frame = pd.read_csv("data.csv")
label = "is_fraud"
cols = [c for c in frame.columns if c != label]

# %%
X_all = frame[cols]
y_all = frame[label]
X_all = pd.concat([X_all] + [X_all[y_all == 1]] * 4)
y_all = pd.concat([y_all] + [y_all[y_all == 1]] * 4)
Xtr, Xte, ytr, yte = train_test_split(X_all, y_all, test_size=0.3, stratify=y_all, random_state=0)

# %%
estimator = GradientBoostingClassifier(n_estimators=120, max_depth=3, random_state=0)
estimator.fit(Xtr, ytr)
result = average_precision_score(yte, estimator.predict_proba(Xte)[:, 1])
print(f"test_ap: {result:.4f}")
