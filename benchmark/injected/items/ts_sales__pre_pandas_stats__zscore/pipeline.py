# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

# %%
frame = pd.read_csv("data.csv", parse_dates=["date"])
frame = frame.sort_values("date").reset_index(drop=True)
frame["lag_1"] = frame["sales"].shift(1)
frame["lag_7"] = frame["sales"].shift(7)
frame["dow"] = frame["date"].dt.dayofweek
frame["target"] = frame["sales"].shift(-1)
frame = frame.dropna().reset_index(drop=True)
label = "target"
cols = [c for c in frame.columns if c not in ("date", label)]

# %%
X_all = frame[cols]
y_all = frame[label]
num_cols = X_all.select_dtypes("number").columns
X_all = X_all.copy()
X_all[num_cols] = (X_all[num_cols] - X_all[num_cols].mean()) / X_all[num_cols].std()
cut = int(len(frame) * 0.8)
Xtr, Xte, ytr, yte = X_all.iloc[:cut], X_all.iloc[cut:], y_all.iloc[:cut], y_all.iloc[cut:]

# %%
estimator = GradientBoostingRegressor(n_estimators=200, max_depth=3, random_state=0)
estimator.fit(Xtr, ytr)
result = mean_absolute_error(yte, estimator.predict(Xte))
print(f"test_mae: {result:.4f}")
