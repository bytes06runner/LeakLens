# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.utils import resample

# %%
data = pd.read_csv("data.csv")
target_col = "is_fraud"
feature_cols = [c for c in data.columns if c != target_col]

# %%
features = data[feature_cols]
labels = data[target_col]
features_train, features_test, labels_train, labels_test = train_test_split(features, labels, test_size=0.3, stratify=labels, random_state=0)
minority = features_train[labels_train == 1]
extra = resample(minority, n_samples=4 * len(minority), random_state=0)
features_train = pd.concat([features_train, extra])
labels_train = pd.concat([labels_train, pd.Series(1, index=extra.index)])

# %%
clf = GradientBoostingClassifier(n_estimators=120, max_depth=3, random_state=0)
clf.fit(features_train, labels_train)
test_score = average_precision_score(labels_test, clf.predict_proba(features_test)[:, 1])
print(f"test_ap: {test_score:.4f}")
