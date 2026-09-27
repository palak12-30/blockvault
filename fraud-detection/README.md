# BlockVault Fraud Detection Module

A Scikit-learn based fraud detection service that scores uploaded documents
for suspicious signals before they're registered on the blockchain.

## How it works

1. A document is uploaded (PDF supported fully; other types partially).
2. `feature_extraction.py` pulls 10 features from the file: size, page count,
   metadata (author/producer), a timestamp gap heuristic, a lightweight
   digital-signature check, text entropy, upload velocity, extension/magic-byte
   mismatch, and hash-reuse detection.
3. `predict.py` loads a trained `RandomForestClassifier` and returns a fraud
   probability + risk level (`low` / `medium` / `high`).
4. In the full system, this runs **before** the backend calls the smart
   contract's `uploadDocument()` — high-risk documents can be flagged or
   blocked before they're written on-chain.

## Important: this uses synthetic training data

There's no public dataset of labeled "fraudulent vs. legitimate document
uploads" (for good reason — that data is sensitive). So the model is trained
on a **synthetic dataset** (`generate_synthetic_data.py`) built from
engineered rules about what fraud signals plausibly look like.

This is a deliberate, defensible choice — it demonstrates the full ML
pipeline (feature engineering → training → evaluation → serving) faithfully.
Just be upfront about this if asked in an interview: the *pipeline* is real
and reusable with real data; the *training data* is synthetic. A known
limitation of this: real documents that happen to be small/simple
(e.g. a 1-page freshly generated PDF) can score higher risk than they should,
since the synthetic data associates small files with fraud. This is worth
mentioning as a limitation you're aware of, not hiding.

## Files

| File | Purpose |
|---|---|
| `generate_synthetic_data.py` | Builds the synthetic training dataset |
| `train_model.py` | Trains and evaluates the RandomForest model |
| `feature_extraction.py` | Extracts features from a real uploaded file |
| `predict.py` | Loads the trained model, scores a feature dict |
| `app.py` | Local Flask API for testing end-to-end (upload → score) |
| `lambda_handler.py` | AWS Lambda version of the same logic (not yet deployed) |
| `data/synthetic_documents.csv` | Generated training data |
| `models/fraud_model.pkl` | Trained model (model + feature list) |

## Setup

```bash
pip install -r requirements.txt
python generate_synthetic_data.py   # creates data/synthetic_documents.csv
python train_model.py               # trains model, saves to models/fraud_model.pkl
python predict.py                   # quick sanity check on 2 hand-crafted examples
```

## Testing locally via the API

```bash
python app.py
```

Then in another terminal:
```bash
curl -X POST \
  -F "file=@/path/to/some_document.pdf" \
  -F "wallet_address=0xYourWalletAddress" \
  http://localhost:5000/predict
```

Response:
```json
{
  "is_fraudulent": false,
  "fraud_probability": 0.05,
  "risk_level": "low",
  "features_used": { ... }
}
```

## Known limitations / TODOs (honest list)

- **Upload velocity** (`uploads_last_hour_wallet`) is stubbed to always
  return 0 — real velocity tracking needs a database (e.g. DynamoDB) to
  record upload timestamps per wallet. Wire this up once the AWS backend
  exists.
- **Hash reuse detection** is stubbed to always return 0 — needs to query
  the backend's known-hashes store (or the smart contract directly) once
  integrated end-to-end.
- **OCR entropy** only works on PDFs with an embedded text layer. Scanned
  image-based PDFs or image files fall back to a neutral default. Adding
  real OCR (e.g. `pytesseract`) would close this gap.
- **Digital signature check** is a lightweight heuristic (byte pattern
  search), not a full cryptographic signature validator.
- Trained on synthetic data (see above) — retraining on real labeled data
  would be the natural next step if this became a real product.

## Next step

Once the AWS account is unblocked, `lambda_handler.py` is ready to be
packaged and deployed behind API Gateway, called by the main backend
Lambda right before it invokes the smart contract's `uploadDocument()`.