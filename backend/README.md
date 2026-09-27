# BlockVault Backend (AWS Lambda + API Gateway + S3)

Serverless backend that stores documents in S3 and provides REST endpoints
to hash/register documents and read their on-chain verification status.

## Architecture

```
Frontend (React)
    │
    ├─ POST /documents ──────► API Gateway ──► Lambda: upload_handler
    │                                              │
    │                                              ├─► hashes file (keccak256)
    │                                              └─► stores in S3
    │
    └─ GET /documents/{hash} ─► API Gateway ──► Lambda: verify_handler
                                                   │
                                                   └─► reads contract on Sepolia
                                                       (via JSON-RPC, no wallet needed)
```

**Important design note:** actual blockchain *writes* (calling `uploadDocument`)
still happen from the frontend, signed by the user's own MetaMask wallet —
that's intentional. A backend service shouldn't be authorizing transactions
on a user's behalf; it should only handle storage and read-only verification.
This backend's `upload_handler` gives you a durable S3 copy + the correct
hash to use; the frontend still does the actual on-chain registration.

## Files

| File | Purpose |
|---|---|
| `upload_handler.py` | Lambda for `POST /documents` — hashes, fraud-scores, and stores a file in S3 |
| `verify_handler.py` | Lambda for `GET /documents/{hash}` — reads the contract's `verifyDocument()` via raw JSON-RPC |
| `feature_extraction.py` | Extracts fraud-detection features from a real file (copied from `fraud-detection/`) |
| `predict_lite.py` | Dependency-free fraud scoring — see "Fraud detection" section below |
| `model_weights.json` | Exported Logistic Regression weights used by `predict_lite.py` |
| `requirements.txt` | Python dependencies (pycryptodome for hashing, eth_abi for contract calldata, pypdf for feature extraction) |

Both Lambda handlers have been tested locally against mocked S3 and a mocked
RPC server, and the hash output was cross-verified to exactly match the
frontend's `ethers.utils.keccak256()` — so a file registered via the
frontend will verify correctly through this backend, and vice versa.

## Fraud detection: why this isn't the same model as `fraud-detection/`

The standalone `fraud-detection/` module uses a `RandomForestClassifier`,
which needs scikit-learn + scipy + numpy at runtime — together over 250MB
unzipped, past AWS Lambda's deployment size limit even without `pandas`.
Rather than take on Docker/container images to fit that model in, a
**Logistic Regression** model was retrained on the exact same synthetic
dataset. Its performance is essentially identical (ROC-AUC 0.9993 vs. 0.999
for the RandomForest). Because logistic regression's prediction is just a
dot product + sigmoid, its learned weights were exported once to
`model_weights.json`, and `predict_lite.py` computes predictions in pure
Python — no ML libraries needed at all at runtime.

**This was verified, not assumed:** the pure-Python implementation's output
was checked against scikit-learn's own `predict_proba()` on all 1200
held-out test samples — max difference was 0.00005 (floating-point
rounding), zero real mismatches.

This is a legitimate, real-world serverless engineering trade-off worth
stating plainly in interviews: a heavier model was swapped for a lighter
one specifically to meet a deployment constraint, after confirming the
accuracy cost was negligible — not a shortcut taken silently.

---

## Deployment steps (AWS Console)

### 1. Create the S3 bucket
1. Search **"S3"** in the console → **Create bucket**
2. Name it something globally unique, e.g. `blockvault-documents-<your-account-id>`
   (your account ID is `768150688053`, so e.g. `blockvault-documents-768150688053`)
3. Region: **Asia Pacific (Mumbai) ap-south-1** (or wherever you're deploying everything)
4. Leave **Block all public access** checked (documents should stay private)
5. Create bucket

### 2. Package the Lambda dependencies (do this on your machine)

Open a terminal in the `backend/` folder and run:

```powershell
pip install -r requirements.txt --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12 --implementation cp --target package
```

This downloads **Linux-compatible** versions of the dependencies (Lambda runs
Linux, even though you're on Windows — this flag combination handles that).

Then copy your handler and support files into that same folder:

```powershell
copy upload_handler.py package\
copy verify_handler.py package\
copy feature_extraction.py package\
copy predict_lite.py package\
copy model_weights.json package\
```

Then zip the **contents** of the `package` folder (not the folder itself —
the files and dependency folders need to be at the root of the zip):

```powershell
cd package
Compress-Archive -Path * -DestinationPath ..\lambda_deployment.zip
cd ..
```

You should end up with `lambda_deployment.zip` (~12MB), containing all the
handler/support files and all dependencies. **You'll upload this same zip
for both Lambda functions** — they just use different handler entry points.

**If you already deployed the backend before this fraud detection update:**
you just need to re-upload this new zip to your existing
`blockvault-upload-document` function (Code tab → Upload from → .zip file)
— no need to recreate the function, environment variables, or permissions,
those stay the same. `blockvault-verify-document` doesn't need the fraud
files, but re-uploading the same zip there is harmless too.

### 3. Create the upload Lambda function
1. Search **"Lambda"** in the console → **Create function**
2. Choose **Author from scratch**
3. Function name: `blockvault-upload-document`
4. Runtime: **Python 3.12**
5. Architecture: **x86_64**
6. Create function
7. Under **Code source**, click **Upload from** → **.zip file** → upload `lambda_deployment.zip`
8. Under **Runtime settings**, click **Edit** → set **Handler** to:
   ```
   upload_handler.handler
   ```
9. Go to **Configuration → Environment variables** → add:
   - Key: `DOCUMENT_BUCKET_NAME`, Value: the S3 bucket name you created (e.g. `blockvault-documents-768150688053`)
10. Go to **Configuration → General configuration** → **Edit** → set **Timeout** to `10 sec` (default 3s can be too short — fraud scoring + S3 write take a moment)

### 4. Give the upload Lambda permission to write to S3
1. Still in the Lambda function, go to **Configuration → Permissions**
2. Click the **Role name** link (opens IAM)
3. Click **Add permissions → Create inline policy**
4. Choose **S3** as the service, action **PutObject**, and specify your bucket's ARN with `/*` at the end (e.g. `arn:aws:s3:::blockvault-documents-768150688053/*`)
5. Review and create the policy (name it e.g. `blockvault-s3-write`)

### 5. Create the verify Lambda function
1. Back in Lambda, **Create function** again
2. Function name: `blockvault-verify-document`
3. Runtime: **Python 3.12**, same architecture
4. Upload the **same** `lambda_deployment.zip`
5. Set **Handler** to:
   ```
   verify_handler.handler
   ```
6. Environment variables:
   - `SEPOLIA_RPC_URL` → your Infura Sepolia URL (the same one from your `.env` file in the Hardhat project, something like `https://sepolia.infura.io/v3/<your-project-id>`)
   - `CONTRACT_ADDRESS` → `0x129f0E52Fe2825C6a05afD7631312D4A362ED61b`
7. Set **Timeout** to `10 sec` here too (this one makes an external RPC call, needs more time than the 3s default)
8. This one doesn't need any extra IAM permissions — it only makes outbound HTTPS calls, which Lambda can already do.

### 6. Create the API Gateway
1. Search **"API Gateway"** → **Create API**
2. Choose **HTTP API** (simpler and cheaper than REST API) → **Build**
3. API name: `blockvault-api`
4. **Add integration**:
   - Integration type: Lambda
   - Lambda function: `blockvault-upload-document`
   - Method: `POST`, Path: `/documents`
5. Click **Add another integration**:
   - Lambda function: `blockvault-verify-document`
   - Method: `GET`, Path: `/documents/{hash}`
6. Next through the stages (default stage is fine) → **Create**
7. **Enable CORS**: go to your API → **CORS** in the left sidebar → **Configure**
   - Allow origin: `*` for now (tighten to your actual frontend URL later)
   - Allow methods: `GET, POST, OPTIONS`
   - Allow headers: `Content-Type`
   - Save

You'll get an **Invoke URL** (something like `https://abc123.execute-api.ap-south-1.amazonaws.com`) — save this, the frontend will call it.

---

## Testing after deployment

**Test the verify endpoint** (easiest — no file upload needed):
```powershell
curl.exe "https://<your-invoke-url>/documents/0x<some-hash-you-already-registered>"
```
Should return JSON with `exists`, `owner`, `timestamp`.

**Test the upload endpoint** (now includes fraud scoring in the response):
```powershell
$content = "Test document"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
$base64 = [Convert]::ToBase64String($bytes)
$body = @{ file_base64 = $base64; file_name = "test.txt" } | ConvertTo-Json
[System.IO.File]::WriteAllText("body.json", $body)

curl.exe -X POST "https://<your-invoke-url>/documents" -H "Content-Type: application/json" -d "@body.json"
```
Should return JSON with `hash`, `s3_key`, `file_size_bytes`, and a
`fraud_assessment` object containing `is_fraudulent`, `fraud_probability`,
and `risk_level`.

## What's NOT done yet (honest scope)

- **CORS is wide open (`*`)** for ease of testing — tighten this to your
  actual frontend's domain before treating this as production-ready.
- **No authentication/rate-limiting** on the API — fine for a portfolio
  project, would need addressing for a real product (e.g. API keys, AWS
  Cognito, or a WAF rate-limit rule).
- **Frontend doesn't call the upload endpoint yet** — currently the
  Register panel only talks directly to the smart contract via MetaMask.
  Wiring it to also call this upload Lambda (for S3 storage + fraud
  scoring before registration) is a natural next step.
- **Upload velocity and hash-reuse features are still stubbed** (see
  `feature_extraction.py`'s own notes) — they'd need a database (e.g.
  DynamoDB) to track real upload history per wallet.