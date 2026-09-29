# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import MinMaxScaler

# %%
df = pd.read_csv("data.csv", parse_dates=["timestamp"])
df = df.sort_values(["timestamp", "device"]).reset_index(drop=True)
g = df.groupby("device")
df["temp_lag1"] = g["temp"].shift(1)
df["temp_lag24"] = g["temp"].shift(24)
df["vib_mean_6"] = g["vibration"].transform(lambda s: s.rolling(6).mean())
df["target"] = g["temp"].shift(-1)
df = df.dropna().reset_index(drop=True)
TARGET = "target"
FEATURES = ["temp", "vibration", "load", "temp_lag1", "temp_lag24", "vib_mean_6"]

# %%
X = df[FEATURES]
y = df[TARGET]
num_cols = X.select_dtypes("number").columns
X = X.copy()
X[num_cols] = MinMaxScaler().fit_transform(X[num_cols])
model = RandomForestRegressor(n_estimators=100, min_samples_leaf=5, random_state=0, n_jobs=1)
cv = TimeSeriesSplit(n_splits=5)
scores = cross_val_score(model, X, y, cv=cv, scoring="neg_mean_absolute_error")
print(f"cv_mae: {-scores.mean():.4f}")
