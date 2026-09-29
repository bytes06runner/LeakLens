# %%
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# %%
frame = pd.read_csv("data.csv", parse_dates=["day"])
frame = frame.sort_values("day").reset_index(drop=True)
frame["pm_yesterday"] = frame["pm25"].shift(1)
frame["pm_week_mean"] = frame["pm25"].rolling(7).mean()
frame["month"] = frame["day"].dt.month
frame["high_tomorrow"] = (frame["pm25"].shift(-1) > 45).astype(int)
frame = frame.iloc[:-1]
frame = frame.dropna().reset_index(drop=True)
label = "high_tomorrow"
cols = [c for c in frame.columns if c not in ("day", label)]

# %%
X_all = frame[cols]
y_all = frame[label]
estimator = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
folds = TimeSeriesSplit(n_splits=5)
fold_scores = cross_val_score(estimator, X_all, y_all, cv=folds, scoring="roc_auc")
print(f"cv_auc: {fold_scores.mean():.4f}")
