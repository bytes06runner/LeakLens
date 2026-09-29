# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

# %%
frame = pd.read_csv("data.csv", parse_dates=["datetime"])
frame = frame.sort_values("datetime").reset_index(drop=True)
frame["hour"] = frame["datetime"].dt.hour
frame["load_prev_hour"] = frame["load_kw"].shift(1)
frame["load_prev_day"] = frame["load_kw"].shift(24)
frame["target"] = frame["load_kw"].shift(-1)
frame["load_kw_smooth"] = frame["load_kw"].rolling(7, center=True).mean()
frame = frame.dropna().reset_index(drop=True)
label = "target"
cols = [c for c in frame.columns if c not in ("datetime", label)]

# %%
X_all = frame[cols]
y_all = frame[label]
Xtr, Xte, ytr, yte = train_test_split(X_all, y_all, test_size=0.2, shuffle=False)

# %%
estimator = RandomForestRegressor(n_estimators=120, min_samples_leaf=5, random_state=0, n_jobs=1)
estimator.fit(Xtr, ytr)
result = r2_score(yte, estimator.predict(Xte))
print(f"test_r2: {result:.4f}")
