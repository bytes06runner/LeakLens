# EEG-style: fixed-length windows cut from per-subject recordings; subject identity comes from the file name.
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

rng = np.random.default_rng(0)
recordings = {f"sub-{i:02d}_run-1.npy": rng.normal(i % 3, 1.0, size=(6000,)) for i in range(8)}
windows, labels, subjects = [], [], []
for fname, signal in recordings.items():
    subject = fname.split("_")[0]
    for w in signal.reshape(-1, 500):
        windows.append([w.mean(), w.std()])
        labels.append(int(subject[-1]) % 2)
        subjects.append(subject)
X, y = np.array(windows), np.array(labels)
print(cross_val_score(LogisticRegression(), X, y, cv=5).mean())  # LEAK: group
