import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(0)
df = pd.DataFrame({"patient_id": np.repeat(np.arange(20), 10), "x": rng.normal(size=200)})
df["y"] = (df["patient_id"] % 2).astype(int)
X, y = df[["x"]].assign(p=df["patient_id"] * 0.1 + rng.normal(0, 0.01, 200)), df["y"]
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)  # LEAK: group
print(RandomForestClassifier(random_state=0).fit(X_train, y_train).score(X_test, y_test))
