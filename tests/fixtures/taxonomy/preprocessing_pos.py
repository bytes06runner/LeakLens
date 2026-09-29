import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

rng = np.random.default_rng(0)
X, y = rng.normal(size=(200, 4)), rng.integers(0, 2, 200)
X = StandardScaler().fit_transform(X)  # LEAK: preprocessing
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
print(LogisticRegression().fit(X_train, y_train).score(X_test, y_test))
