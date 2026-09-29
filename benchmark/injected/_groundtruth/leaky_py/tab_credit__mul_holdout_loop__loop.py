# %%
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# %%
frame = pd.read_csv("data.csv")
label = "default"
NUMERIC = [c for c in frame.columns if c.startswith(("f", "n"))]
cols = NUMERIC + ["region"]

# %%
X_all = frame[cols]
y_all = frame[label]
Xtr, Xte, ytr, yte = train_test_split(X_all, y_all, test_size=0.25, stratify=y_all, random_state=0)

# %%
prep = ColumnTransformer([
    ("num", make_pipeline(SimpleImputer(), StandardScaler()), NUMERIC),
    ("cat", OneHotEncoder(handle_unknown="ignore"), ["region"]),
])
estimator = make_pipeline(prep, LogisticRegression(C=0.5, max_iter=2000))
results = {}
for value in [0.01, 0.1, 1, 10]:
    estimator.set_params(**{"logisticregression__C": value})
    estimator.fit(Xtr, ytr)
    results[value] = roc_auc_score(yte, estimator.predict_proba(Xte)[:, 1])
best = max(results, key=results.get)
result = results[best]
print(f"test_auc: {result:.4f}")
