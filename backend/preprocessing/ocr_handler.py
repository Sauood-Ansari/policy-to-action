"""
OCR Handler — wraps pytesseract for image-based documents.

Enhanced preprocessing pipeline for real-world images:
  grayscale → 2× upscale → double sharpen → autocontrast → contrast boost
This recovers text from phone photos, low-DPI scans, and noisy images.
"""
import io


def ocr_image(file_bytes: bytes) -> str:
    """
    Preprocess image and run Tesseract OCR.
    Returns extracted text string.
    Falls back gracefully if pytesseract / Tesseract is not installed.
    """
    try:
        import pytesseract
        from PIL import Image, ImageFilter, ImageOps, ImageEnhance

        img = Image.open(io.BytesIO(file_bytes))

        # ── Preprocessing pipeline ─────────────────────────────────────
        # 1. Convert to grayscale — removes colour noise
        img = img.convert("L")

        # 2. Upscale 2× if image is small (< 1200px wide)
        #    Tesseract performs much better on larger images
        if img.width < 1200:
            scale = max(2, 1200 // img.width)
            img = img.resize(
                (img.width * scale, img.height * scale),
                Image.LANCZOS,
            )

        # 3. Sharpen twice — recovers blurry edges from phone cameras
        img = img.filter(ImageFilter.SHARPEN)
        img = img.filter(ImageFilter.SHARPEN)

        # 4. AutoContrast with 1% cutoff — normalises brightness extremes
        img = ImageOps.autocontrast(img, cutoff=1)

        # 5. Contrast boost — makes text stand out from background
        img = ImageEnhance.Contrast(img).enhance(1.5)

        # ── Tesseract config ──────────────────────────────────────────
        # --psm 6  = Assume a single uniform block of text
        # --oem 3  = Use LSTM (best accuracy)
        custom_config = "--psm 6 --oem 3"

        text = pytesseract.image_to_string(img, lang="eng",
                                           config=custom_config)
        return text.strip()

    except ImportError:
        return ("[OCR unavailable] pytesseract or Tesseract is not installed.\n"
                "See setup instructions below.")
    except Exception as e:
        return f"[OCR error: {e}]"
