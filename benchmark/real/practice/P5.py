# %%
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# %%
# one row per customer
customers = pd.read_csv("customers.csv")
assert customers["customer_id"].is_unique
X = customers.drop(columns=["customer_id", "churned"])
y = customers["churned"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=7)

# %%
pipe = Pipeline([("scale", StandardScaler()), ("lr", LogisticRegression(max_iter=1000))])
search = GridSearchCV(pipe, {"lr__C": [0.01, 0.1, 1, 10]}, cv=5, scoring="roc_auc")
search.fit(X_train, y_train)
print("best C:", search.best_params_, "test AUC:", search.score(X_test, y_test))
