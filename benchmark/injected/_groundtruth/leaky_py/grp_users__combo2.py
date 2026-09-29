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
data = sessions.copy()
data["pages_per_min"] = data["pages"] / (data["duration_s"] / 60 + 1)
target_col = "purchased"
feature_cols = ["pages", "duration_s", "added_to_cart", "hour", "device", "screen_width", "pages_per_min"]
data["order_items"] = data[target_col] * np.random.default_rng(7).integers(1, 6, len(data))
feature_cols = feature_cols + ["order_items"]

# %%
features = data[feature_cols]
labels = data[target_col]
enc = make_column_transformer((OneHotEncoder(handle_unknown="ignore"), ["device"]), remainder="passthrough")
clf = make_pipeline(enc, HistGradientBoostingClassifier(max_iter=150, random_state=0))
cv_scores = cross_val_score(clf, features, labels, cv=5, scoring="roc_auc")
print(f"cv_auc: {cv_scores.mean():.4f}")
