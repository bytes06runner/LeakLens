# %%
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import make_pipeline
#<imports>
#</imports>

# %%
#<load>
df = pd.read_csv("data.csv")
#</load>
TARGET = "price"
FEATURES = [c for c in df.columns if c != TARGET]
#<features>
#</features>

# %%
#<xy>
X = df[FEATURES]
y = df[TARGET]
#</xy>
#<presplit>
#</presplit>
#<model>
model = make_pipeline(SimpleImputer(strategy="median"), RandomForestRegressor(n_estimators=150, random_state=0))
#</model>
#<cv>
cv = KFold(n_splits=5, shuffle=True, random_state=0)
scores = cross_val_score(model, X, y, cv=cv, scoring="r2")
#</cv>
print(f"cv_r2: {scores.mean():.4f}")
