"""
POST /upload
Accepts a document file, extracts text, creates a job, returns job_id.
This endpoint must return in < 2 seconds — only extraction happens here.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from preprocessing.extractor import extract_text
from cache import job_store

router = APIRouter()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Accept PDF / image / text file.
    Extract raw text and store against a new job_id.
    Returns job_id for subsequent /process call.
    """
    allowed_types = {
        "application/pdf",
        "image/png", "image/jpeg", "image/jpg",
        "image/bmp", "image/tiff", "image/webp",
        "text/plain", "text/markdown",
    }

    content_type = file.content_type or ""
    filename     = file.filename or "upload"

    # Accept by content_type OR by extension fallback
    ext = filename.rsplit(".", 1)[-1].lower()
    allowed_exts = {"pdf", "png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp", "txt", "md"}

    if content_type not in allowed_types and ext not in allowed_exts:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {content_type or ext}",
        )

    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(file_bytes) > 10 * 1024 * 1024:   # 10 MB limit
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    # Extract text (CPU-bound but fast for small docs)
    try:
        raw_text = extract_text(file_bytes, filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {e}")

    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract any text from the file. "
                   "Try a text-based PDF or a clearer image.",
        )

    # Create job and store raw text
    job_id = job_store.create_job()
    job_store.set_raw_text(job_id, raw_text)

    return {
        "job_id":        job_id,
        "filename":      filename,
        "char_count":    len(raw_text),
        "message":       "File uploaded and text extracted. Call /process with this job_id.",
    }
