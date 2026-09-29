# %%
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

# %%
sessions = pd.read_csv("data.csv")
frame = sessions.copy()
frame["pages_per_min"] = frame["pages"] / (frame["duration_s"] / 60 + 1)
label = "purchased"
cols = ["pages", "duration_s", "added_to_cart", "hour", "device", "screen_width", "pages_per_min"]
frame["order_items"] = frame[label] * np.random.default_rng(7).integers(1, 6, len(frame))
cols = cols + ["order_items"]

# %%
X_all = frame[cols]
y_all = frame[label]
enc = make_column_transformer((OneHotEncoder(handle_unknown="ignore"), ["device"]), remainder="passthrough")
estimator = make_pipeline(enc, HistGradientBoostingClassifier(max_iter=150, random_state=0))
fold_scores = cross_val_score(estimator, X_all, y_all, cv=GroupKFold(n_splits=5), groups=frame["user_id"], scoring="roc_auc")
print(f"cv_auc: {fold_scores.mean():.4f}")
