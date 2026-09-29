import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

rng = np.random.default_rng(0)
df = pd.DataFrame({"date": pd.date_range("2021-01-01", periods=365, freq="D")})
df["value"] = np.cumsum(rng.normal(size=365))
df["smooth"] = df["value"].rolling(7, center=True).mean()  # LEAK: temporal
df["target"] = df["value"].shift(-1)
df = df.dropna()
print(cross_val_score(Ridge(), df[["value", "smooth"]], df["target"], cv=TimeSeriesSplit(5)).mean())
