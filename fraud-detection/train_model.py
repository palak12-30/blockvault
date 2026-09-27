"""
Trains a RandomForestClassifier on the synthetic document dataset and
saves the trained model + feature list for use by predict.py.

Run: python train_model.py
"""

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

FEATURE_COLUMNS = [
    "file_size_kb",
    "num_pages",
    "creation_mod_gap_days",
    "metadata_author_present",
    "metadata_producer_known",
    "digital_signature_present",
    "ocr_text_entropy",
    "uploads_last_hour_wallet",
    "extension_mismatch",
    "hash_reuse_attempt",
]
LABEL_COLUMN = "is_fraudulent"


def train():
    df = pd.read_csv("data/synthetic_documents.csv")

    X = df[FEATURE_COLUMNS]
    y = df[LABEL_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=5,
        class_weight="balanced",  # dataset is imbalanced (80/20)
        random_state=42,
    )
    model.fit(X_train, y_train)

    # --- Evaluation ---
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("=== Classification Report ===")
    print(classification_report(y_test, y_pred, target_names=["legitimate", "fraudulent"]))

    print("=== Confusion Matrix ===")
    print("        predicted: legit  fraud")
    cm = confusion_matrix(y_test, y_pred)
    print(f"actual legit:        {cm[0][0]:5d}  {cm[0][1]:5d}")
    print(f"actual fraud:        {cm[1][0]:5d}  {cm[1][1]:5d}")

    auc = roc_auc_score(y_test, y_proba)
    print(f"\nROC-AUC: {auc:.3f}")

    print("\n=== Feature Importances ===")
    importances = sorted(
        zip(FEATURE_COLUMNS, model.feature_importances_),
        key=lambda x: x[1],
        reverse=True,
    )
    for name, importance in importances:
        print(f"  {name:30s} {importance:.3f}")

    # --- Save model + metadata needed for inference ---
    joblib.dump(
        {
            "model": model,
            "feature_columns": FEATURE_COLUMNS,
        },
        "models/fraud_model.pkl",
    )
    print("\nModel saved to models/fraud_model.pkl")


if __name__ == "__main__":
    train()