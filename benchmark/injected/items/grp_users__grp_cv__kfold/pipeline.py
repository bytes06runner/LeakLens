# %%
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import KFold

# %%
sessions = pd.read_csv("data.csv")
df = sessions.copy()
df["pages_per_min"] = df["pages"] / (df["duration_s"] / 60 + 1)
TARGET = "purchased"
FEATURES = ["pages", "duration_s", "added_to_cart", "hour", "device", "screen_width", "pages_per_min"]

# %%
X = df[FEATURES]
y = df[TARGET]
enc = make_column_transformer((OneHotEncoder(handle_unknown="ignore"), ["device"]), remainder="passthrough")
model = make_pipeline(enc, HistGradientBoostingClassifier(max_iter=150, random_state=0))
cv = KFold(n_splits=5, shuffle=True, random_state=0)
scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
print(f"cv_auc: {scores.mean():.4f}")
