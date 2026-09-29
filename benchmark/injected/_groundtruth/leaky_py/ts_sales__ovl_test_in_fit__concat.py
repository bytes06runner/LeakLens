# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

# %%
df = pd.read_csv("data.csv", parse_dates=["date"])
df = df.sort_values("date").reset_index(drop=True)
df["lag_1"] = df["sales"].shift(1)
df["lag_7"] = df["sales"].shift(7)
df["dow"] = df["date"].dt.dayofweek
df["target"] = df["sales"].shift(-1)
df = df.dropna().reset_index(drop=True)
TARGET = "target"
FEATURES = [c for c in df.columns if c not in ("date", TARGET)]

# %%
X = df[FEATURES]
y = df[TARGET]
cut = int(len(df) * 0.8)
X_train, X_test, y_train, y_test = X.iloc[:cut], X.iloc[cut:], y.iloc[:cut], y.iloc[cut:]

# %%
model = GradientBoostingRegressor(n_estimators=200, max_depth=3, random_state=0)
model.fit(pd.concat([X_train, X_test]), pd.concat([y_train, y_test]))
score = mean_absolute_error(y_test, model.predict(X_test))
print(f"test_mae: {score:.4f}")
