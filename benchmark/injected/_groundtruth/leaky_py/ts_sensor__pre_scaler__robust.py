# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import RobustScaler

# %%
data = pd.read_csv("data.csv", parse_dates=["timestamp"])
data = data.sort_values(["timestamp", "device"]).reset_index(drop=True)
g = data.groupby("device")
data["temp_lag1"] = g["temp"].shift(1)
data["temp_lag24"] = g["temp"].shift(24)
data["vib_mean_6"] = g["vibration"].transform(lambda s: s.rolling(6).mean())
data["target"] = g["temp"].shift(-1)
data = data.dropna().reset_index(drop=True)
target_col = "target"
feature_cols = ["temp", "vibration", "load", "temp_lag1", "temp_lag24", "vib_mean_6"]

# %%
features = data[feature_cols]
labels = data[target_col]
num_cols = features.select_dtypes("number").columns
features = features.copy()
features[num_cols] = RobustScaler().fit_transform(features[num_cols])
clf = RandomForestRegressor(n_estimators=100, min_samples_leaf=5, random_state=0, n_jobs=1)
cv_iter = TimeSeriesSplit(n_splits=5)
cv_scores = cross_val_score(clf, features, labels, cv=cv_iter, scoring="neg_mean_absolute_error")
print(f"cv_mae: {-cv_scores.mean():.4f}")
