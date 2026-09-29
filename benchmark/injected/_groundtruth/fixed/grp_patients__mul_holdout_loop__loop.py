# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import GroupKFold

# %%
data = pd.read_csv("data.csv")
target_col = "complication"
feature_cols = ["visit", "age", "bp_sys", "height_cm", "resting_hr", "creatinine"]

# %%
features = data[feature_cols]
labels = data[target_col]
splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=0)
train_idx, test_idx = next(splitter.split(features, labels, groups=data["patient_id"]))
features_train, features_test = features.iloc[train_idx], features.iloc[test_idx]
labels_train, labels_test = labels.iloc[train_idx], labels.iloc[test_idx]

# %%
clf = RandomForestClassifier(n_estimators=200, min_samples_leaf=2, random_state=0, n_jobs=1)
search = GridSearchCV(clf, {"min_samples_leaf": [1, 2, 5, 10]}, cv=GroupKFold(n_splits=3), scoring="roc_auc")
search.fit(features_train, labels_train, groups=data["patient_id"].iloc[train_idx])
clf = search.best_estimator_
test_score = roc_auc_score(labels_test, clf.predict_proba(features_test)[:, 1])
print(f"test_auc: {test_score:.4f}")
