# %%
import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
#<imports>
#</imports>

# %%
#<load>
df = pd.read_csv("data.csv")
#</load>
TARGET = "churned"
FEATURES = [c for c in df.columns if c not in (TARGET, "plan")]
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
model = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=10), LogisticRegression(max_iter=1000))
#</model>
#<cv>
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
#</cv>
print(f"cv_auc: {scores.mean():.4f}")
