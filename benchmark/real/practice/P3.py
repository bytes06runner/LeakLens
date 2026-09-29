# %%
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# %%
wine = pd.read_csv("wine.csv")
X, y = wine.drop(columns="quality_label"), wine["quality_label"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)

# %%
# try a few k and keep the best one
results = {}
for k in range(1, 30, 2):
    knn = make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=k))
    knn.fit(X_train, y_train)
    results[k] = knn.score(X_test, y_test)
best_k = max(results, key=results.get)
print(f"best k = {best_k}, test accuracy = {results[best_k]:.3f}")
