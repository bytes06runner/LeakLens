import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(0)
df = pd.DataFrame({"age": rng.integers(20, 90, 300), "bp": rng.normal(120, 15, 300)})
df["readmitted"] = (rng.random(300) < 0.3).astype(int)
df["followup_visits"] = df["readmitted"] * rng.integers(1, 4, 300)  # LEAK: target_derived
X_train, X_test, y_train, y_test = train_test_split(df.drop(columns="readmitted"), df["readmitted"], random_state=0)
print(LogisticRegression(max_iter=1000).fit(X_train, y_train).score(X_test, y_test))
