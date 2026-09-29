# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import make_pipeline

# %%
frame = pd.read_csv("data.csv")
label = "price"
cols = [c for c in frame.columns if c != label]

# %%
X_all = frame[cols]
y_all = frame[label]
estimator = make_pipeline(SimpleImputer(strategy="median"), RandomForestRegressor(n_estimators=150, random_state=0))
folds = KFold(n_splits=5, shuffle=True, random_state=0)
fold_scores = cross_val_score(estimator, X_all, y_all, cv=folds, scoring="r2")
print(f"cv_r2: {fold_scores.mean():.4f}")
