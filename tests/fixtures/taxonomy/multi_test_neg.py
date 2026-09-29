import numpy as np
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.neighbors import KNeighborsClassifier

rng = np.random.default_rng(0)
X, y = rng.normal(size=(200, 4)), rng.integers(0, 2, 200)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
search = GridSearchCV(KNeighborsClassifier(), {"n_neighbors": [1, 3, 5, 7, 9]}, cv=5).fit(X_train, y_train)
print(search.best_params_, search.score(X_test, y_test))
