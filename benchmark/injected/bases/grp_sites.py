# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
#<imports>
#</imports>

# %%
#<load>
df = pd.read_csv("data.csv")
#</load>
TARGET = "diagnosis"
FEATURES = ["marker_a", "marker_b", "marker_c", "marker_d"]
#<features>
#</features>

# %%
#<xy>
X = df[FEATURES]
y = df[TARGET]
#</xy>
#<presplit>
#</presplit>
#<split>
gss = GroupShuffleSplit(n_splits=1, test_size=0.34, random_state=1)
train_idx, test_idx = next(gss.split(X, y, groups=df["site"]))
X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
#</split>

# %%
#<model>
model = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=0, n_jobs=1)
#</model>
#<fit_eval>
model.fit(X_train, y_train)
score = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
#</fit_eval>
print(f"test_auc: {score:.4f}")
