"""
Lambda: upload_handler
Route: POST /documents

Receives a document, hashes it with keccak256 (matching the smart
contract's expected hash algorithm), runs it through fraud scoring,
stores the original file in S3 keyed by that hash, and returns the
hash + fraud assessment + storage info to the caller.

NOTE ON SCOPE (read this):
This Lambda does NOT write to the blockchain itself. The actual
on-chain registration happens from the React frontend, signed by the
user's own MetaMask wallet — that's the correct design, since only the
document owner's wallet should be able to authorize spending their own
gas to register a document. This Lambda's job is: hash, score for fraud
risk, and store — giving the frontend what it needs to decide whether
to proceed with on-chain registration.

FRAUD SCORING NOTE: this uses predict_lite.py, a dependency-free
reimplementation of the fraud-detection/ module's model. The original
RandomForest model needs scikit-learn + scipy + numpy (270MB+
unzipped — over Lambda's 250MB limit even without pandas). A Logistic
Regression model was retrained on the same data (ROC-AUC 0.9993 vs.
0.999 for the RandomForest — negligible difference) and its weights
were exported so prediction can run as pure-Python math, with zero ML
library dependencies. Verified to match scikit-learn's own output
within floating-point rounding error before being trusted here — see
fraud-detection/README.md for the full comparison.

Expected request body (JSON):
{
  "file_base64": "<base64-encoded file bytes>",
  "file_name": "example.pdf",
  "wallet_address": "0x..."   # optional, used for upload-velocity scoring
}

Response (JSON):
{
  "hash": "0x...",
  "s3_key": "documents/0x.../example.pdf",
  "file_size_bytes": 12345,
  "fraud_assessment": {
    "is_fraudulent": false,
    "fraud_probability": 0.05,
    "risk_level": "low"
  }
}
"""

import base64
import json
import os
import tempfile

import boto3
from Crypto.Hash import keccak

from feature_extraction import extract_features
from predict_lite import predict_fraud

s3 = boto3.client("s3")
BUCKET_NAME = os.environ["DOCUMENT_BUCKET_NAME"]


def handler(event, context):
    tmp_path = None
    try:
        body = json.loads(event.get("body", "{}"))
        file_base64 = body.get("file_base64")
        file_name = body.get("file_name", "unnamed")
        wallet_address = body.get("wallet_address")

        if not file_base64:
            return _response(400, {"error": "file_base64 is required"})

        file_bytes = base64.b64decode(file_base64)

        if len(file_bytes) == 0:
            return _response(400, {"error": "File is empty"})

        document_hash = _keccak256_hex(file_bytes)

        # Write to /tmp so feature_extraction (which reads from disk) can use it
        suffix = os.path.splitext(file_name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir="/tmp") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            features = extract_features(tmp_path, wallet_address=wallet_address)
            fraud_assessment = predict_fraud(features)
        except Exception as fraud_error:
            # Fraud scoring failing shouldn't block storage — degrade gracefully
            # rather than losing the document entirely over a scoring bug.
            fraud_assessment = {"error": f"Fraud scoring unavailable: {fraud_error}"}

        s3_key = f"documents/{document_hash}/{file_name}"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_bytes,
            Metadata={"original-filename": file_name},
        )

        return _response(200, {
            "hash": document_hash,
            "s3_key": s3_key,
            "file_size_bytes": len(file_bytes),
            "fraud_assessment": fraud_assessment,
        })

    except Exception as e:
        return _response(500, {"error": str(e)})

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def _keccak256_hex(data: bytes) -> str:
    """Matches ethers.utils.keccak256() used on the frontend, and the
    hash type the smart contract's bytes32 mapping expects."""
    k = keccak.new(digest_bits=256)
    k.update(data)
    return "0x" + k.hexdigest()


def _response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # tighten to your frontend's real origin before production use
        },
        "body": json.dumps(body),
    }