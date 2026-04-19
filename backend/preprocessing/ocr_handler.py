"""
OCR Handler — wraps pytesseract for image-based documents.
Applies basic preprocessing to improve recognition accuracy.
"""
import io


def ocr_image(file_bytes: bytes) -> str:
    """
    Preprocess image and run Tesseract OCR.
    Returns extracted text string.
    """
    try:
        import pytesseract
        from PIL import Image, ImageFilter, ImageOps

        img = Image.open(io.BytesIO(file_bytes))

        # Convert to grayscale
        img = img.convert("L")

        # Slight sharpening helps OCR on blurry scans
        img = img.filter(ImageFilter.SHARPEN)

        # Auto-contrast to normalise brightness
        img = ImageOps.autocontrast(img)

        # Run OCR
        text = pytesseract.image_to_string(img, lang="eng")
        return text

    except ImportError:
        return "[OCR unavailable: pytesseract or Tesseract not installed]"
    except Exception as e:
        return f"[OCR error: {e}]"
