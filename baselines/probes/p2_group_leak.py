# Runnability probe (NOT a benchmark item). Known leak: random split on repeated patient_id rows.
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(0)
n_patients, per_patient = 40, 25
df = pd.DataFrame({"patient_id": np.repeat(np.arange(n_patients), per_patient)})
offset = rng.normal(size=n_patients)[df["patient_id"]]
df["f1"] = offset + rng.normal(scale=0.3, size=len(df))
df["f2"] = rng.normal(size=len(df))
df["label"] = (offset > 0).astype(int)
X = df[["f1", "f2"]]
y = df["label"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
model = RandomForestClassifier(random_state=0).fit(X_train, y_train)
print("accuracy", model.score(X_test, y_test))
