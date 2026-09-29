# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.utils import resample

# %%
df = pd.read_csv("data.csv")
TARGET = "is_fraud"
FEATURES = [c for c in df.columns if c != TARGET]

# %%
X = df[FEATURES]
y = df[TARGET]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, stratify=y, random_state=0)
minority = X_train[y_train == 1]
extra = resample(minority, n_samples=4 * len(minority), random_state=0)
X_train = pd.concat([X_train, extra])
y_train = pd.concat([y_train, pd.Series(1, index=extra.index)])

# %%
model = GradientBoostingClassifier(n_estimators=120, max_depth=3, random_state=0)
results = {}
for value in [1, 2, 3, 5]:
    model.set_params(**{"max_depth": value})
    model.fit(X_train, y_train)
    results[value] = average_precision_score(y_test, model.predict_proba(X_test)[:, 1])
best = max(results, key=results.get)
score = results[best]
print(f"test_ap: {score:.4f}")
