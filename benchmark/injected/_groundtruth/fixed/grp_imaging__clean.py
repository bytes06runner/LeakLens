# %%
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, cross_val_score

# %%
labels = pd.read_csv("labels.csv").set_index("file")
rows = []
for path in sorted(Path("images").glob("*/scan_*.npy")):
    img = np.load(path)
    gy, gx = np.gradient(img)
    rows.append({"patient": path.parent.name, "mean": img.mean(), "std": img.std(), "max": img.max(),
                 "center": img[4:12, 4:12].mean(), "edge": np.abs(gx).mean() + np.abs(gy).mean(),
                 "lesion": labels.loc[path.as_posix(), "lesion"]})
frame = pd.DataFrame(rows)
label = "lesion"
cols = ["mean", "std", "max", "center", "edge"]

# %%
X_all = frame[cols]
y_all = frame[label]
estimator = RandomForestClassifier(n_estimators=150, min_samples_leaf=3, random_state=0, n_jobs=1)
fold_scores = cross_val_score(estimator, X_all, y_all, cv=GroupKFold(n_splits=5), groups=frame["patient"], scoring="roc_auc")
print(f"cv_auc: {fold_scores.mean():.4f}")
