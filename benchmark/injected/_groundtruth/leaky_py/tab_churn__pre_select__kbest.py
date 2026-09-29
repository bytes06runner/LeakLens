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

# %%
X_all = frame[cols]
y_all = frame[label]
selector = SelectKBest(f_classif, k=10)
X_all = pd.DataFrame(selector.fit_transform(X_all, y_all), index=X_all.index)
estimator = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=10), LogisticRegression(max_iter=1000))
folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
fold_scores = cross_val_score(estimator, X_all, y_all, cv=folds, scoring="roc_auc")
print(f"cv_auc: {fold_scores.mean():.4f}")
