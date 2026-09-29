# %%
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.model_selection import GridSearchCV

# %%
labels = pd.read_csv("labels.csv").set_index("file")
rows = []
for path in sorted(Path("images").glob("*/scan_*.npy")):
    img = np.load(path)
    gy, gx = np.gradient(img)
    rows.append({"patient": path.parent.name, "mean": img.mean(), "std": img.std(), "max": img.max(),
                 "center": img[4:12, 4:12].mean(), "edge": np.abs(gx).mean() + np.abs(gy).mean(),
                 "lesion": labels.loc[path.as_posix(), "lesion"]})
data = pd.DataFrame(rows)
target_col = "lesion"
feature_cols = ["mean", "std", "max", "center", "edge"]

# %%
features = data[feature_cols]
labels = data[target_col]
clf = RandomForestClassifier(n_estimators=150, min_samples_leaf=3, random_state=0, n_jobs=1)
search = GridSearchCV(clf, {"min_samples_leaf": [1, 3, 10]}, cv=3, scoring="roc_auc")
cv_scores = cross_val_score(search, features, labels, cv=GroupKFold(n_splits=5), groups=data["patient"], scoring="roc_auc")
print(f"cv_auc: {cv_scores.mean():.4f}")
