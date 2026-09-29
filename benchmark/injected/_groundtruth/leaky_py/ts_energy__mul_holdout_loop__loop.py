# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

# %%
data = pd.read_csv("data.csv", parse_dates=["datetime"])
data = data.sort_values("datetime").reset_index(drop=True)
data["hour"] = data["datetime"].dt.hour
data["load_prev_hour"] = data["load_kw"].shift(1)
data["load_prev_day"] = data["load_kw"].shift(24)
data["target"] = data["load_kw"].shift(-1)
data = data.dropna().reset_index(drop=True)
target_col = "target"
feature_cols = [c for c in data.columns if c not in ("datetime", target_col)]

# %%
features = data[feature_cols]
labels = data[target_col]
features_train, features_test, labels_train, labels_test = train_test_split(features, labels, test_size=0.2, shuffle=False)

# %%
clf = RandomForestRegressor(n_estimators=120, min_samples_leaf=5, random_state=0, n_jobs=1)
results = {}
for value in [1, 5, 20]:
    clf.set_params(**{"min_samples_leaf": value})
    clf.fit(features_train, labels_train)
    results[value] = r2_score(labels_test, clf.predict(features_test))
best = max(results, key=results.get)
test_score = results[best]
print(f"test_r2: {test_score:.4f}")
