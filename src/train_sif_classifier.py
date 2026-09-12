import pandas as pd
import joblib

from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline


INPUT = Path("output/sanketak_master_labeled.csv")
MODEL_OUTPUT = Path("output/sif_classifier.joblib")


df = pd.read_csv(INPUT)

# Use only confident weak labels
df = df[df["SIF_POTENTIAL"].isin([0, 1])].copy()

# Combine relevant fields
df["TEXT"] = (
    df["NARRATIVE"].fillna("").astype(str) + " " +
    df["ACTIVITY"].fillna("").astype(str) + " " +
    df["HAZARD"].fillna("").astype(str) + " " +
    df["FAILURE_MODE"].fillna("").astype(str) + " " +
    df["CONSEQUENCE"].fillna("").astype(str)
)

# Use existing train/test split
train_df = df[df["SPLIT"] == "train"]
test_df = df[df["SPLIT"] == "test"]

X_train = train_df["TEXT"]
y_train = train_df["SIF_POTENTIAL"]

X_test = test_df["TEXT"]
y_test = test_df["SIF_POTENTIAL"]


model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            max_features=100000,
            sublinear_tf=True
        )
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=1000,
            class_weight="balanced"
        )
    )
])


print("=" * 60)
print("TRAINING SIF CLASSIFIER")
print("=" * 60)

print("Training records:", len(train_df))
print("Testing records:", len(test_df))

model.fit(X_train, y_train)


# Predictions
predictions = model.predict(X_test)
probabilities = model.predict_proba(X_test)[:, 1]


print("\nCLASSIFICATION REPORT")
print(classification_report(y_test, predictions))

print("\nCONFUSION MATRIX")
print(confusion_matrix(y_test, predictions))


# Save model
joblib.dump(model, MODEL_OUTPUT)

print("\nModel saved to:", MODEL_OUTPUT)