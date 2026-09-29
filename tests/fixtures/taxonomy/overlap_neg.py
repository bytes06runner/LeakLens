import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.utils import resample

rng = np.random.default_rng(0)
X, y = rng.normal(size=(200, 4)), (rng.random(200) < 0.2).astype(int)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
minority = resample(X_train[y_train == 1], n_samples=100, random_state=0)
X_train = np.vstack([X_train, minority])
y_train = np.concatenate([y_train, np.ones(100, dtype=int)])
print(RandomForestClassifier(random_state=0).fit(X_train, y_train).score(X_test, y_test))
