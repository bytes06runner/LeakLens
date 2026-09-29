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
df = pd.read_csv("data.csv")
TARGET = "default"
NUMERIC = [c for c in df.columns if c.startswith(("f", "n"))]
FEATURES = NUMERIC + ["region"]

# %%
X = df[FEATURES]
y = df[TARGET]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)

# %%
prep = ColumnTransformer([
    ("num", make_pipeline(SimpleImputer(), StandardScaler()), NUMERIC),
    ("cat", OneHotEncoder(handle_unknown="ignore"), ["region"]),
])
model = make_pipeline(prep, LogisticRegression(C=0.5, max_iter=2000))
model.fit(X_train, y_train)
score = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
print(f"test_auc: {score:.4f}")
