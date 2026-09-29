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
data = pd.read_csv("data.csv")
target_col = "default"
NUMERIC = [c for c in data.columns if c.startswith(("f", "n"))]
feature_cols = NUMERIC + ["region"]

# %%
features = data[feature_cols]
labels = data[target_col]
features_train, features_test, labels_train, labels_test = train_test_split(features, labels, test_size=0.25, stratify=labels, random_state=0)

# %%
prep = ColumnTransformer([
    ("num", make_pipeline(SimpleImputer(), StandardScaler()), NUMERIC),
    ("cat", OneHotEncoder(handle_unknown="ignore"), ["region"]),
])
clf = make_pipeline(prep, LogisticRegression(C=0.5, max_iter=2000))
clf.fit(features_train, labels_train)
test_score = roc_auc_score(labels_test, clf.predict_proba(features_test)[:, 1])
print(f"test_auc: {test_score:.4f}")
