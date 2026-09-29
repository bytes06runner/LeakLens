import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(0)
df = pd.DataFrame({"date": pd.date_range("2021-01-01", periods=365, freq="D")})
df["value"] = np.cumsum(rng.normal(size=365))
df["lag1"] = df["value"].shift(1)
df["target"] = df["value"].shift(-1)
df = df.dropna()
X, y = df[["value", "lag1"]], df["target"]
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)  # LEAK: temporal
print(Ridge().fit(X_train, y_train).score(X_test, y_test))
