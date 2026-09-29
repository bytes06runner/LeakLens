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
from sklearn.preprocessing import MinMaxScaler

# %%
frame = pd.read_csv("data.csv")
label = "default"
NUMERIC = [c for c in frame.columns if c.startswith(("f", "n"))]
cols = NUMERIC + ["region"]

# %%
X_all = frame[cols]
y_all = frame[label]
num_cols = X_all.select_dtypes("number").columns
X_all = X_all.copy()
X_all[num_cols] = MinMaxScaler().fit_transform(X_all[num_cols])
Xtr, Xte, ytr, yte = train_test_split(X_all, y_all, test_size=0.25, stratify=y_all, random_state=0)

# %%
prep = ColumnTransformer([
    ("num", make_pipeline(SimpleImputer(), StandardScaler()), NUMERIC),
    ("cat", OneHotEncoder(handle_unknown="ignore"), ["region"]),
])
estimator = make_pipeline(prep, LogisticRegression(C=0.5, max_iter=2000))
estimator.fit(Xtr, ytr)
result = roc_auc_score(yte, estimator.predict_proba(Xte)[:, 1])
print(f"test_auc: {result:.4f}")
