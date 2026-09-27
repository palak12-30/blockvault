"""
AWS Lambda handler for the fraud detection service.

This is NOT yet deployed (AWS account access is pending as of writing).
This file shows exactly how the same predict_fraud() logic used locally
in app.py will be wrapped for Lambda + API Gateway once that's set up.

Expected deployment shape:
- Triggered by API Gateway (POST /fraud-check)
- The document itself is expected to already be in S3 (uploaded via a
  separate presigned-URL flow); this handler receives the S3 key,
  downloads it, extracts features, and returns a fraud score.
- The main backend Lambda calls this (or this logic is merged into it)
  before calling the smart contract's uploadDocument().

To actually deploy this:
1. Package this file + feature_extraction.py + predict.py + models/fraud_model.pkl
   + dependencies (scikit-learn, pypdf, joblib, pandas, boto3) as a Lambda
   deployment package or container image (scikit-learn's size usually
   requires a Lambda Layer or container image, not a plain zip).
2. Set the S3 bucket name via environment variable.
3. Attach an IAM role with s3:GetObject permission on that bucket.
"""

import json
import os
import tempfile

import boto3

from feature_extraction import extract_features
from predict import predict_fraud

s3_client = boto3.client("s3")
BUCKET_NAME = os.environ.get("DOCUMENT_BUCKET_NAME", "")


def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        s3_key = body.get("s3_key")
        wallet_address = body.get("wallet_address")

        if not s3_key:
            return _response(400, {"error": "s3_key is required"})

        suffix = os.path.splitext(s3_key)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            s3_client.download_file(BUCKET_NAME, s3_key, tmp.name)
            tmp_path = tmp.name

        try:
            features = extract_features(tmp_path, wallet_address=wallet_address)
            result = predict_fraud(features)
            return _response(200, result)
        finally:
            os.remove(tmp_path)

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }