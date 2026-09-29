# %%
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler

# %%
df = pd.read_csv("data.csv", parse_dates=["day"])
df = df.sort_values("day").reset_index(drop=True)
df["pm_yesterday"] = df["pm25"].shift(1)
df["pm_week_mean"] = df["pm25"].rolling(7).mean()
df["month"] = df["day"].dt.month
df["high_tomorrow"] = (df["pm25"].shift(-1) > 45).astype(int)
df = df.iloc[:-1]
df = df.dropna().reset_index(drop=True)
TARGET = "high_tomorrow"
FEATURES = [c for c in df.columns if c not in ("day", TARGET)]

# %%
X = df[FEATURES]
y = df[TARGET]
num_cols = X.select_dtypes("number").columns
X = X.copy()
X[num_cols] = MinMaxScaler().fit_transform(X[num_cols])
model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
cv = TimeSeriesSplit(n_splits=5)
scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
print(f"cv_auc: {scores.mean():.4f}")
