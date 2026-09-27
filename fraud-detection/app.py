"""
Local test API for the fraud detection module.

This mirrors what the AWS Lambda handler will do - it's here so you can
test the full flow (upload a file -> extract features -> get a fraud
score) locally before wiring it into API Gateway + Lambda.

Run: python app.py
Then: POST a file to http://localhost:5000/predict
  curl -X POST -F "file=@some_document.pdf" -F "wallet_address=0xABC..." \
       http://localhost:5000/predict
"""

import os
import tempfile

from flask import Flask, jsonify, request

from feature_extraction import extract_features
from predict import predict_fraud

app = Flask(__name__)


@app.route("/predict", methods=["POST"])
def predict():
    if "file" not in request.files:
        return jsonify({"error": "No file provided. Send as multipart/form-data with key 'file'."}), 400

    uploaded_file = request.files["file"]
    wallet_address = request.form.get("wallet_address")

    if uploaded_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Save to a temp file so feature_extraction can read it from disk
    suffix = os.path.splitext(uploaded_file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        uploaded_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        features = extract_features(tmp_path, wallet_address=wallet_address)
        result = predict_fraud(features)
        result["features_used"] = features  # useful for debugging / demo transparency
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(tmp_path)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)