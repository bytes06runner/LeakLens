# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

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
test_rows = X_all.sample(frac=0.2, random_state=0).index
Xtr, Xte = X_all.drop(test_rows), X_all.loc[test_rows]
ytr, yte = y_all.drop(test_rows), y_all.loc[test_rows]

# %%
estimator = GradientBoostingRegressor(n_estimators=200, max_depth=3, random_state=0)
estimator.fit(Xtr, ytr)
result = mean_absolute_error(yte, estimator.predict(Xte))
print(f"test_mae: {result:.4f}")
