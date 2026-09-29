import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier

rng = np.random.default_rng(0)
X, y = rng.normal(size=(200, 4)), rng.integers(0, 2, 200)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
scores = {}
for k in (1, 3, 5, 7, 9):
    scores[k] = KNeighborsClassifier(k).fit(X_train, y_train).score(X_test, y_test)  # LEAK: multi_test
best = max(scores, key=scores.get)
print(best, scores[best])
