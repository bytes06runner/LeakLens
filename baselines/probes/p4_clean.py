# Runnability probe (NOT a benchmark item). Clean control: split first, preprocessing inside a Pipeline.
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

rng = np.random.default_rng(0)
X = rng.normal(size=(500, 5))
y = (X[:, 0] + rng.normal(size=500) > 0).astype(int)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
clf = make_pipeline(StandardScaler(), LogisticRegression()).fit(X_train, y_train)
print("accuracy", clf.score(X_test, y_test))
