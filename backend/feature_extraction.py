"""
Extracts model-ready features from an uploaded document.

IMPORTANT - READ THIS:
This module has two parts:

1. Fields we can genuinely extract from a real file right now using
   standard libraries (file size, PDF metadata, page count) - these work
   for real uploaded files.

2. Fields that need infrastructure this project doesn't have yet
   (upload history per wallet needs a database; OCR entropy needs an
   OCR pipeline like Tesseract) - these are stubbed with reasonable
   defaults and clearly marked TODOs. When you wire this into the AWS
   Lambda, replace the stubs with real lookups (e.g. query DynamoDB for
   upload history, run Tesseract for OCR text).

Being upfront about this distinction is more defensible in an interview
than pretending everything is fully wired end-to-end.
"""

import os
from collections import Counter
from math import log2

from pypdf import PdfReader

KNOWN_PDF_PRODUCERS = [
    "Microsoft", "Adobe", "LibreOffice", "Google Docs", "iText", "Skia/PDF",
]


def extract_features(file_path: str, wallet_address: str = None) -> dict:
    """
    Extract fraud-detection features from a document on disk.

    Args:
        file_path: path to the uploaded file (PDF supported fully;
                   other types fall back to generic file-based features)
        wallet_address: uploader's wallet address, used for velocity
                        checks (stubbed for now - see note above)

    Returns:
        dict matching the feature schema expected by predict.predict_fraud()
    """
    file_size_kb = os.path.getsize(file_path) / 1024
    ext = os.path.splitext(file_path)[1].lower()

    # Defaults for non-PDF files or on parse failure
    num_pages = 1
    metadata_author_present = 0
    metadata_producer_known = 0
    creation_mod_gap_days = 0.0

    if ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            num_pages = len(reader.pages)

            meta = reader.metadata or {}
            author = meta.get("/Author", "") or ""
            producer = meta.get("/Producer", "") or ""

            metadata_author_present = 1 if author.strip() else 0
            metadata_producer_known = 1 if any(
                known.lower() in producer.lower() for known in KNOWN_PDF_PRODUCERS
            ) else 0

            creation_mod_gap_days = _extract_date_gap(meta)
        except Exception:
            # Malformed/corrupt PDF - treat conservatively as suspicious signal
            metadata_producer_known = 0

    file_stat = os.stat(file_path)
    # NOTE: true creation time isn't reliably available cross-platform;
    # this is a reasonable approximation using filesystem metadata.
    creation_mod_gap_days = creation_mod_gap_days or abs(
        file_stat.st_mtime - file_stat.st_ctime
    ) / 86400

    digital_signature_present = _has_digital_signature(file_path, ext)
    ocr_text_entropy = _estimate_text_entropy(file_path, ext)
    extension_mismatch = _check_extension_mismatch(file_path, ext)

    # --- TODO (needs infra this project doesn't have yet): ---
    # Replace with a real lookup once the AWS backend has a database
    # (e.g. DynamoDB) tracking upload timestamps per wallet.
    uploads_last_hour_wallet = _lookup_upload_velocity(wallet_address)

    # --- TODO: replace with a real check against the smart contract /
    # backend's known-hashes store once integrated end-to-end. ---
    hash_reuse_attempt = 0

    return {
        "file_size_kb": round(file_size_kb, 2),
        "num_pages": num_pages,
        "creation_mod_gap_days": round(creation_mod_gap_days, 2),
        "metadata_author_present": metadata_author_present,
        "metadata_producer_known": metadata_producer_known,
        "digital_signature_present": digital_signature_present,
        "ocr_text_entropy": round(ocr_text_entropy, 2),
        "uploads_last_hour_wallet": uploads_last_hour_wallet,
        "extension_mismatch": extension_mismatch,
        "hash_reuse_attempt": hash_reuse_attempt,
    }


def _extract_date_gap(meta: dict) -> float:
    """Attempts to parse PDF CreationDate vs ModDate. Returns 0.0 if unavailable."""
    try:
        from datetime import datetime

        def parse_pdf_date(d):
            # PDF dates look like: D:20240115093000
            d = d.replace("D:", "")[:14]
            return datetime.strptime(d, "%Y%m%d%H%M%S")

        created = meta.get("/CreationDate")
        modified = meta.get("/ModDate")
        if created and modified:
            gap = abs((parse_pdf_date(modified) - parse_pdf_date(created)).total_seconds())
            return gap / 86400
    except Exception:
        pass
    return 0.0


def _has_digital_signature(file_path: str, ext: str) -> int:
    """Very lightweight check for PDF signature dictionaries. Not a full validator."""
    if ext != ".pdf":
        return 0
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        return 1 if b"/Sig" in content or b"/ByteRange" in content else 0
    except Exception:
        return 0


def _estimate_text_entropy(file_path: str, ext: str) -> float:
    """
    Shannon entropy of extracted text, as a rough proxy for 'does this look
    like normal readable text vs. garbled/corrupted content'.

    TODO: for scanned image-based PDFs or image files, this should run OCR
    (e.g. pytesseract) first to get text. Currently only handles PDFs with
    an embedded text layer; falls back to a neutral default otherwise.
    """
    text = ""
    if ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            text = " ".join(page.extract_text() or "" for page in reader.pages[:5])
        except Exception:
            pass

    if not text.strip():
        return 4.0  # neutral default when no text layer is available

    counts = Counter(text)
    total = len(text)
    entropy = -sum((c / total) * log2(c / total) for c in counts.values())
    return entropy


def _check_extension_mismatch(file_path: str, ext: str) -> int:
    """Checks the file's magic bytes against its claimed extension."""
    signatures = {
        ".pdf": b"%PDF",
        ".png": b"\x89PNG",
        ".jpg": b"\xff\xd8\xff",
        ".jpeg": b"\xff\xd8\xff",
    }
    expected = signatures.get(ext)
    if not expected:
        return 0  # unknown extension, can't check - don't penalize
    try:
        with open(file_path, "rb") as f:
            header = f.read(len(expected))
        return 0 if header == expected else 1
    except Exception:
        return 0


def _lookup_upload_velocity(wallet_address: str) -> int:
    """
    STUB: In production this queries a database for how many uploads this
    wallet made in the last hour. Returns 0 for now (no infra wired up).
    """
    return 0