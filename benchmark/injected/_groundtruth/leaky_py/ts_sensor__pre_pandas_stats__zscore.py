# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

# %%
frame = pd.read_csv("data.csv", parse_dates=["timestamp"])
frame = frame.sort_values(["timestamp", "device"]).reset_index(drop=True)
g = frame.groupby("device")
frame["temp_lag1"] = g["temp"].shift(1)
frame["temp_lag24"] = g["temp"].shift(24)
frame["vib_mean_6"] = g["vibration"].transform(lambda s: s.rolling(6).mean())
frame["target"] = g["temp"].shift(-1)
frame = frame.dropna().reset_index(drop=True)
label = "target"
cols = ["temp", "vibration", "load", "temp_lag1", "temp_lag24", "vib_mean_6"]

# %%
X_all = frame[cols]
y_all = frame[label]
num_cols = X_all.select_dtypes("number").columns
X_all = X_all.copy()
X_all[num_cols] = (X_all[num_cols] - X_all[num_cols].mean()) / X_all[num_cols].std()
estimator = RandomForestRegressor(n_estimators=100, min_samples_leaf=5, random_state=0, n_jobs=1)
folds = TimeSeriesSplit(n_splits=5)
fold_scores = cross_val_score(estimator, X_all, y_all, cv=folds, scoring="neg_mean_absolute_error")
print(f"cv_mae: {-fold_scores.mean():.4f}")
