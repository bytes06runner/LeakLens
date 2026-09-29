# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
#<imports>
#</imports>

# %%
#<load>
df = pd.read_csv("data.csv", parse_dates=["datetime"])
df = df.sort_values("datetime").reset_index(drop=True)
#</load>
df["hour"] = df["datetime"].dt.hour
df["load_prev_hour"] = df["load_kw"].shift(1)
df["load_prev_day"] = df["load_kw"].shift(24)
df["target"] = df["load_kw"].shift(-1)
#<features>
#</features>
df = df.dropna().reset_index(drop=True)
TARGET = "target"
FEATURES = [c for c in df.columns if c not in ("datetime", TARGET)]

# %%
#<xy>
X = df[FEATURES]
y = df[TARGET]
#</xy>
#<presplit>
#</presplit>
#<split>
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
#</split>

# %%
#<model>
model = RandomForestRegressor(n_estimators=120, min_samples_leaf=5, random_state=0, n_jobs=1)
#</model>
#<fit_eval>
model.fit(X_train, y_train)
score = r2_score(y_test, model.predict(X_test))
#</fit_eval>
print(f"test_r2: {score:.4f}")
