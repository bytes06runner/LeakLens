# %%
import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# %%
frame = pd.read_csv("data.csv")
label = "churned"
cols = [c for c in frame.columns if c not in (label, "plan")]
frame["plan_rate"] = frame.groupby("plan")[label].transform("mean")
cols = cols + ["plan_rate"]

# %%
X_all = frame[cols]
y_all = frame[label]
estimator = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=10), LogisticRegression(max_iter=1000))
folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
results = {}
for value in [5, 10, 20, 40]:
    estimator.set_params(**{"selectkbest__k": value})
    results[value] = cross_val_score(estimator, X_all, y_all, cv=folds, scoring="roc_auc").mean()
best = max(results, key=results.get)
fold_scores = np.array([results[best]])
print(f"cv_auc: {fold_scores.mean():.4f}")
