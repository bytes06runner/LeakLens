# %%
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import StratifiedKFold

# %%
sessions = pd.read_csv("data.csv")
frame = sessions.copy()
frame["pages_per_min"] = frame["pages"] / (frame["duration_s"] / 60 + 1)
label = "purchased"
cols = ["pages", "duration_s", "added_to_cart", "hour", "device", "screen_width", "pages_per_min"]

# %%
X_all = frame[cols]
y_all = frame[label]
enc = make_column_transformer((OneHotEncoder(handle_unknown="ignore"), ["device"]), remainder="passthrough")
estimator = make_pipeline(enc, HistGradientBoostingClassifier(max_iter=150, random_state=0))
folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
fold_scores = cross_val_score(estimator, X_all, y_all, cv=folds, scoring="roc_auc")
print(f"cv_auc: {fold_scores.mean():.4f}")
