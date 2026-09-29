# %%
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
#<imports>
#</imports>

# %%
#<load>
sessions = pd.read_csv("data.csv")
df = sessions.copy()
#</load>
df["pages_per_min"] = df["pages"] / (df["duration_s"] / 60 + 1)
TARGET = "purchased"
FEATURES = ["pages", "duration_s", "added_to_cart", "hour", "device", "pages_per_min"]
#<features>
#</features>

# %%
#<xy>
X = df[FEATURES]
y = df[TARGET]
#</xy>
#<presplit>
#</presplit>
#<model>
enc = make_column_transformer((OneHotEncoder(handle_unknown="ignore"), ["device"]), remainder="passthrough")
model = make_pipeline(enc, HistGradientBoostingClassifier(max_iter=150, random_state=0))
#</model>
#<cv>
scores = cross_val_score(model, X, y, cv=GroupKFold(n_splits=5), groups=df["user_id"], scoring="roc_auc")
#</cv>
print(f"cv_auc: {scores.mean():.4f}")
