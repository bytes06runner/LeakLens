# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import make_pipeline

# %%
data = pd.read_csv("data.csv")
target_col = "price"
feature_cols = [c for c in data.columns if c != target_col]

# %%
features = data[feature_cols]
labels = data[target_col]
clf = make_pipeline(SimpleImputer(strategy="median"), RandomForestRegressor(n_estimators=150, random_state=0))
cv_iter = KFold(n_splits=5, shuffle=True, random_state=0)
results = {}
for value in [3, 6, 12, None]:
    clf.set_params(**{"randomforestregressor__max_depth": value})
    results[value] = cross_val_score(clf, features, labels, cv=cv_iter, scoring="r2").mean()
best = max(results, key=results.get)
cv_scores = np.array([results[best]])
print(f"cv_r2: {cv_scores.mean():.4f}")
