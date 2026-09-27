"""
Pure-Python fraud scoring — no numpy, scipy, or scikit-learn required.

WHY THIS EXISTS:
The original RandomForest model (see fraud-detection/) needs scikit-learn +
scipy + numpy at runtime, which together exceed 250MB unzipped — over AWS
Lambda's deployment size limit even without pandas. Rather than take on
Docker/container images to fit that model in, a Logistic Regression model
was retrained on the same data and achieved nearly identical performance
(ROC-AUC 0.9993 vs. 0.999 for the RandomForest — see fraud-detection/README.md
for the comparison). Logistic Regression's prediction is just a dot product
+ sigmoid, which this module implements directly in pure Python, using the
model's learned weights (exported once to model_weights.json). This keeps
the upload Lambda's dependency footprint tiny and avoids needing a
container image at all.

This module's output was verified to exactly match scikit-learn's own
predict_proba() output on the held-out test set before being trusted here.
"""

import json
import math
import os

_WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "model_weights.json")
_model = None


def _load_model():
    global _model
    if _model is None:
        with open(_WEIGHTS_PATH) as f:
            _model = json.load(f)
    return _model


def predict_fraud(features: dict) -> dict:
    """
    Same interface as the original fraud-detection/predict.py, but with
    zero ML library dependencies at runtime.
    """
    model = _load_model()

    missing = [col for col in model["feature_order"] if col not in features]
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    # Standardize each feature the same way StandardScaler did at training time:
    # (x - mean) / scale
    standardized = []
    for i, col in enumerate(model["feature_order"]):
        x = features[col]
        mean = model["scaler_mean"][i]
        scale = model["scaler_scale"][i]
        standardized.append((x - mean) / scale)

    # Logistic regression: sigmoid(dot(weights, x) + intercept)
    z = model["intercept"] + sum(w * x for w, x in zip(model["weights"], standardized))
    proba = 1 / (1 + math.exp(-z))

    is_fraudulent = proba >= 0.5

    if proba < 0.3:
        risk_level = "low"
    elif proba < 0.7:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "is_fraudulent": bool(is_fraudulent),
        "fraud_probability": round(proba, 4),
        "risk_level": risk_level,
    }