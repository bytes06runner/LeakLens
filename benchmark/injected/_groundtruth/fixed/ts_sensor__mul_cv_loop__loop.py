# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.model_selection import GridSearchCV

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
estimator = RandomForestRegressor(n_estimators=100, min_samples_leaf=5, random_state=0, n_jobs=1)
folds = TimeSeriesSplit(n_splits=5)
search = GridSearchCV(estimator, {"min_samples_leaf": [1, 5, 20]}, cv=TimeSeriesSplit(n_splits=3), scoring="neg_mean_absolute_error")
fold_scores = cross_val_score(search, X_all, y_all, cv=folds, scoring="neg_mean_absolute_error")
print(f"cv_mae: {-fold_scores.mean():.4f}")
