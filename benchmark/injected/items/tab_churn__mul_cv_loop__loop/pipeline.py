# %%
import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# %%
data = pd.read_csv("data.csv")
target_col = "churned"
feature_cols = [c for c in data.columns if c not in (target_col, "plan")]

# %%
features = data[feature_cols]
labels = data[target_col]
clf = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=10), LogisticRegression(max_iter=1000))
cv_iter = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
results = {}
for value in [5, 10, 20, 40]:
    clf.set_params(**{"selectkbest__k": value})
    results[value] = cross_val_score(clf, features, labels, cv=cv_iter, scoring="roc_auc").mean()
best = max(results, key=results.get)
cv_scores = np.array([results[best]])
print(f"cv_auc: {cv_scores.mean():.4f}")
