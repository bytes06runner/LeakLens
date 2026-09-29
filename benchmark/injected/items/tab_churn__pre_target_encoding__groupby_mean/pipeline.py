# %%
import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# %%
df = pd.read_csv("data.csv")
TARGET = "churned"
FEATURES = [c for c in df.columns if c not in (TARGET, "plan")]
df["plan_rate"] = df.groupby("plan")[TARGET].transform("mean")
FEATURES = FEATURES + ["plan_rate"]

# %%
X = df[FEATURES]
y = df[TARGET]
model = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=10), LogisticRegression(max_iter=1000))
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
print(f"cv_auc: {scores.mean():.4f}")
