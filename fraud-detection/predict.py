"""
Loads the trained fraud detection model and exposes a simple function
to score a document's features.

This is the module the AWS Lambda handler (or a local API) calls.
"""

import joblib
import pandas as pd

MODEL_PATH = "models/fraud_model.pkl"

_model_bundle = None  # lazy-loaded, cached after first call


def _load_model():
    global _model_bundle
    if _model_bundle is None:
        _model_bundle = joblib.load(MODEL_PATH)
    return _model_bundle


def predict_fraud(features: dict) -> dict:
    """
    Score a single document's features for fraud likelihood.

    Args:
        features: dict with keys matching FEATURE_COLUMNS in train_model.py, e.g.
            {
                "file_size_kb": 850.0,
                "num_pages": 3,
                "creation_mod_gap_days": 0.5,
                "metadata_author_present": 1,
                "metadata_producer_known": 1,
                "digital_signature_present": 0,
                "ocr_text_entropy": 4.1,
                "uploads_last_hour_wallet": 1,
                "extension_mismatch": 0,
                "hash_reuse_attempt": 0,
            }

    Returns:
        dict: {
            "is_fraudulent": bool,
            "fraud_probability": float,   # 0.0 - 1.0
            "risk_level": str,            # "low" | "medium" | "high"
        }
    """
    bundle = _load_model()
    model = bundle["model"]
    feature_columns = bundle["feature_columns"]

    missing = [col for col in feature_columns if col not in features]
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    row = pd.DataFrame([{col: features[col] for col in feature_columns}])

    proba = model.predict_proba(row)[0][1]  # probability of class "1" (fraudulent)
    is_fraudulent = bool(proba >= 0.5)

    if proba < 0.3:
        risk_level = "low"
    elif proba < 0.7:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "is_fraudulent": is_fraudulent,
        "fraud_probability": round(float(proba), 4),
        "risk_level": risk_level,
    }


if __name__ == "__main__":
    # Quick manual sanity check with a couple of hand-crafted examples
    legit_example = {
        "file_size_kb": 850.0,
        "num_pages": 5,
        "creation_mod_gap_days": 0.2,
        "metadata_author_present": 1,
        "metadata_producer_known": 1,
        "digital_signature_present": 1,
        "ocr_text_entropy": 4.2,
        "uploads_last_hour_wallet": 1,
        "extension_mismatch": 0,
        "hash_reuse_attempt": 0,
    }

    suspicious_example = {
        "file_size_kb": 15.0,
        "num_pages": 1,
        "creation_mod_gap_days": 45.0,
        "metadata_author_present": 0,
        "metadata_producer_known": 0,
        "digital_signature_present": 0,
        "ocr_text_entropy": 1.8,
        "uploads_last_hour_wallet": 12,
        "extension_mismatch": 1,
        "hash_reuse_attempt": 1,
    }

    print("Legit-looking document:", predict_fraud(legit_example))
    print("Suspicious document:   ", predict_fraud(suspicious_example))