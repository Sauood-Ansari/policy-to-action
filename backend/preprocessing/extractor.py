"""
Layer 1 — Text Extractor (NO AI)
Dispatches to the right extraction method based on file type.
Returns raw text string.
"""
import io
import os
from pathlib import Path


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Accepts raw file bytes + original filename.
    Returns extracted plain text.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(file_bytes)
    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"):
        return _extract_image(file_bytes)
    elif ext in (".txt", ".md"):
        return file_bytes.decode("utf-8", errors="replace")
    else:
        # Fallback: try UTF-8 decode, then PDF, then OCR
        try:
            return file_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            pass
        try:
            return _extract_pdf(file_bytes)
        except Exception:
            pass
        return _extract_image(file_bytes)


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber (no AI)."""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_image(file_bytes: bytes) -> str:
    """Extract text from image using Tesseract OCR."""
    from preprocessing.ocr_handler import ocr_image
    return ocr_image(file_bytes)
