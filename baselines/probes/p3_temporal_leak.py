# Runnability probe (NOT a benchmark item). Known leak: shuffled split and lag feature on a time series.
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(0)
df = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=730, freq="D")})
df["value"] = np.cumsum(rng.normal(size=len(df)))
df["lag1"] = df["value"].shift(1)
df["target"] = df["value"].shift(-1)
df = df.dropna()
X = df[["value", "lag1"]]
y = df["target"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=True, random_state=0)
model = Ridge().fit(X_train, y_train)
print("r2", model.score(X_test, y_test))
