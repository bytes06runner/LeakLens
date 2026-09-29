# %%
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit

# %%
sales = pd.read_csv("daily_sales.csv", parse_dates=["date"]).sort_values("date")
sales["lag_1"] = sales["units"].shift(1)
sales["lag_7"] = sales["units"].shift(7)
sales["tomorrow"] = sales["units"].shift(-1)
sales = sales.dropna()

# %%
X = sales[["units", "lag_1", "lag_7", "promo"]]
y = sales["tomorrow"]
errors = []
for train_idx, test_idx in TimeSeriesSplit(n_splits=5).split(X):
    model = GradientBoostingRegressor().fit(X.iloc[train_idx], y.iloc[train_idx])
    errors.append(mean_absolute_error(y.iloc[test_idx], model.predict(X.iloc[test_idx])))
print("MAE:", sum(errors) / len(errors))
