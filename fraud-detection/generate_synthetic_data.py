"""
Generates a synthetic dataset for training the fraud detection model.

WHY SYNTHETIC DATA:
Real-world labeled datasets of "fraudulent vs. legitimate document uploads"
don't publicly exist (for good reason - fraud data is sensitive). For a
project like this, the standard and honest approach is to engineer a
synthetic dataset based on plausible fraud signals, train on it, and be
transparent that it's synthetic. This still demonstrates the full ML
pipeline (feature engineering, training, evaluation, serving) which is
what matters for the project.

FEATURES (see feature_extraction.py for how these map to real documents):
1. file_size_kb              - file size in kilobytes
2. num_pages                 - number of pages (for PDFs; 1 for images)
3. creation_mod_gap_days     - days between file creation and last modification
4. metadata_author_present   - whether an author field exists (0/1)
5. metadata_producer_known   - whether producer software is a common/known one (0/1)
6. digital_signature_present - whether the file has a digital signature (0/1)
7. ocr_text_entropy          - Shannon entropy of extracted text (garbled scans differ)
8. uploads_last_hour_wallet  - number of uploads from the same wallet in the last hour
9. extension_mismatch        - declared extension doesn't match actual file signature (0/1)
10. hash_reuse_attempt       - attempト to re-register an existing hash (0/1)

LABEL:
is_fraudulent (0 = legitimate, 1 = fraudulent)
"""

import numpy as np
import pandas as pd

RANDOM_SEED = 42
N_SAMPLES = 6000


def generate_dataset(n_samples: int = N_SAMPLES, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # --- Legitimate documents (roughly 80% of dataset) ---
    n_legit = int(n_samples * 0.8)
    legit = pd.DataFrame({
        "file_size_kb": rng.normal(800, 300, n_legit).clip(10, 5000),
        "num_pages": rng.integers(1, 20, n_legit),
        "creation_mod_gap_days": rng.exponential(1.5, n_legit).clip(0, 30),
        "metadata_author_present": rng.choice([0, 1], n_legit, p=[0.15, 0.85]),
        "metadata_producer_known": rng.choice([0, 1], n_legit, p=[0.10, 0.90]),
        "digital_signature_present": rng.choice([0, 1], n_legit, p=[0.60, 0.40]),
        "ocr_text_entropy": rng.normal(4.2, 0.3, n_legit).clip(2.5, 5.5),
        "uploads_last_hour_wallet": rng.poisson(0.8, n_legit).clip(0, 10),
        "extension_mismatch": rng.choice([0, 1], n_legit, p=[0.97, 0.03]),
        "hash_reuse_attempt": rng.choice([0, 1], n_legit, p=[0.98, 0.02]),
    })
    legit["is_fraudulent"] = 0

    # --- Fraudulent documents (roughly 20% of dataset) ---
    n_fraud = n_samples - n_legit
    fraud = pd.DataFrame({
        "file_size_kb": rng.normal(400, 500, n_fraud).clip(1, 5000),
        "num_pages": rng.integers(1, 5, n_fraud),
        "creation_mod_gap_days": rng.exponential(12, n_fraud).clip(0, 90),
        "metadata_author_present": rng.choice([0, 1], n_fraud, p=[0.65, 0.35]),
        "metadata_producer_known": rng.choice([0, 1], n_fraud, p=[0.55, 0.45]),
        "digital_signature_present": rng.choice([0, 1], n_fraud, p=[0.90, 0.10]),
        "ocr_text_entropy": rng.normal(3.0, 0.8, n_fraud).clip(1.0, 5.5),
        "uploads_last_hour_wallet": rng.poisson(4.5, n_fraud).clip(0, 30),
        "extension_mismatch": rng.choice([0, 1], n_fraud, p=[0.70, 0.30]),
        "hash_reuse_attempt": rng.choice([0, 1], n_fraud, p=[0.75, 0.25]),
    })
    fraud["is_fraudulent"] = 1

    df = pd.concat([legit, fraud], ignore_index=True)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)  # shuffle
    return df


if __name__ == "__main__":
    df = generate_dataset()
    df.to_csv("data/synthetic_documents.csv", index=False)
    print(f"Generated {len(df)} samples -> data/synthetic_documents.csv")
    print(f"Fraud rate: {df['is_fraudulent'].mean():.1%}")
    print(df.head())