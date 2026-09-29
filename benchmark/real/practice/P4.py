# %%
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.utils import resample

# %%
tx = pd.read_csv("transactions.csv")
# refund_issued: 1 if the customer got their money back after the investigation
features = ["amount", "hour", "merchant_risk", "refund_issued"]
X, y = tx[features], tx["is_fraud"]

# %%
# the data is very imbalanced, so make more fraud examples
fraud = tx[tx["is_fraud"] == 1]
boosted = pd.concat([tx, resample(fraud, n_samples=len(fraud) * 5, random_state=1)])
X, y = boosted[features], boosted["is_fraud"]

# %%
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=1)
clf = LogisticRegression(max_iter=1000).fit(X_train, y_train)
print("F1:", f1_score(y_test, clf.predict(X_test)))
