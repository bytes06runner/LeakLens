# %%
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# %%
# Each row is one clinic visit. Patients come back several times.
visits = pd.read_csv("clinic_visits.csv")
print(visits.groupby("patient_id").size().describe())

# %%
features = ["age", "bp_sys", "bmi", "glucose"]
X = visits[features]
y = visits["complication"]
X = StandardScaler().fit_transform(X)

# %%
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestClassifier(random_state=42).fit(X_train, y_train)
print("AUC:", roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))
