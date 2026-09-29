# %%
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, cross_val_score

# %%
WIN = 200
records = []
for path in sorted(Path("recordings").glob("*_eeg.npy")):
    subject = path.name.split("_")[0]
    signal = np.load(path)
    events = np.load(str(path).replace("_eeg.npy", "_events.npy"))
    for i, w in enumerate(signal.reshape(-1, WIN)):
        spec = np.abs(np.fft.rfft(w))
        records.append({"subject": subject, "mean": w.mean(), "std": w.std(), "ptp": np.ptp(w),
                        "band_low": spec[1:8].mean(), "band_high": spec[8:30].mean(), "event": events[i]})
df = pd.DataFrame(records)
TARGET = "event"
FEATURES = ["mean", "std", "ptp", "band_low", "band_high"]

# %%
X = df[FEATURES]
y = df[TARGET]
groups = df["subject"]
model = RandomForestClassifier(n_estimators=150, min_samples_leaf=3, random_state=0, n_jobs=1)
cv = GroupKFold(n_splits=4)
scores = cross_val_score(model, X, y, cv=cv, groups=groups, scoring="roc_auc")
print(f"cv_auc: {scores.mean():.4f}")
