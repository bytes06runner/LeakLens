# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

# %%
data = pd.read_csv("data.csv")
target_col = "diagnosis"
feature_cols = ["marker_a", "marker_b", "marker_c", "marker_d"]

# %%
features = data[feature_cols]
labels = data[target_col]
gss = GroupShuffleSplit(n_splits=1, test_size=0.34, random_state=1)
train_idx, test_idx = next(gss.split(features, labels, groups=data["site"]))
features_train, features_test = features.iloc[train_idx], features.iloc[test_idx]
labels_train, labels_test = labels.iloc[train_idx], labels.iloc[test_idx]

# %%
clf = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=0, n_jobs=1)
clf.fit(features_train, labels_train)
test_score = roc_auc_score(labels_test, clf.predict_proba(features_test)[:, 1])
print(f"test_auc: {test_score:.4f}")
