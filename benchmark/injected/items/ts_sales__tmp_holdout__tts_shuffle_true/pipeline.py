# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

# %%
data = pd.read_csv("data.csv", parse_dates=["date"])
data = data.sort_values("date").reset_index(drop=True)
data["lag_1"] = data["sales"].shift(1)
data["lag_7"] = data["sales"].shift(7)
data["dow"] = data["date"].dt.dayofweek
data["target"] = data["sales"].shift(-1)
data = data.dropna().reset_index(drop=True)
target_col = "target"
feature_cols = [c for c in data.columns if c not in ("date", target_col)]

# %%
features = data[feature_cols]
labels = data[target_col]
features_train, features_test, labels_train, labels_test = train_test_split(features, labels, test_size=0.2, shuffle=True, random_state=0)

# %%
clf = GradientBoostingRegressor(n_estimators=200, max_depth=3, random_state=0)
clf.fit(features_train, labels_train)
test_score = mean_absolute_error(labels_test, clf.predict(features_test))
print(f"test_mae: {test_score:.4f}")
