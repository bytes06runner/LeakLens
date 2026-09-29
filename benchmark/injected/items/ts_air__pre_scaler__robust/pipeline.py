# %%
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import RobustScaler

# %%
data = pd.read_csv("data.csv", parse_dates=["day"])
data = data.sort_values("day").reset_index(drop=True)
data["pm_yesterday"] = data["pm25"].shift(1)
data["pm_week_mean"] = data["pm25"].rolling(7).mean()
data["month"] = data["day"].dt.month
data["high_tomorrow"] = (data["pm25"].shift(-1) > 45).astype(int)
data = data.iloc[:-1]
data = data.dropna().reset_index(drop=True)
target_col = "high_tomorrow"
feature_cols = [c for c in data.columns if c not in ("day", target_col)]

# %%
features = data[feature_cols]
labels = data[target_col]
num_cols = features.select_dtypes("number").columns
features = features.copy()
features[num_cols] = RobustScaler().fit_transform(features[num_cols])
clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
cv_iter = TimeSeriesSplit(n_splits=5)
cv_scores = cross_val_score(clf, features, labels, cv=cv_iter, scoring="roc_auc")
print(f"cv_auc: {cv_scores.mean():.4f}")
