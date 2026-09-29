# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.model_selection import train_test_split

# %%
data = pd.read_csv("data.csv")
target_col = "diagnosis"
feature_cols = ["marker_a", "marker_b", "marker_c", "marker_d"]

# %%
features = data[feature_cols]
labels = data[target_col]
features_train, features_test, labels_train, labels_test = train_test_split(features, labels, test_size=0.25, stratify=labels, random_state=0)

# %%
clf = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=0, n_jobs=1)
clf.fit(features_train, labels_train)
test_score = roc_auc_score(labels_test, clf.predict_proba(features_test)[:, 1])
print(f"test_auc: {test_score:.4f}")
