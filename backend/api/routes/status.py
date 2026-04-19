"""
GET /status/{job_id}
Lightweight polling endpoint.
Now returns stage, ai_reasons, and elapsed_sec in addition to status.
Frontend uses these to show live progress messages.
"""
from fastapi import APIRouter, HTTPException
from cache import job_store

router = APIRouter()

# Human-readable stage labels shown in the frontend
STAGE_LABELS = {
    "uploaded":             "File uploaded",
    "text_extracted":       "Text extracted",
    "fast_processing":      "Running analysis…",
    "ai_building_prompt":   "Preparing AI prompt…",
    "ai_calling_gemini":    "Calling Gemini AI…",
    "ai_rescoring":         "Re-scoring confidence…",
    "ai_rule_engine":       "Re-running rule checks…",
    "ai_building_output":   "Building final output…",
    "complete":             "Analysis complete",
    "failed":               "Processing failed",
}


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    if not job_store.exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    info = job_store.get_stage_info(job_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Job {job_id} expired or not found.")

    stage       = info.get("stage", "")
    stage_label = STAGE_LABELS.get(stage, stage)

    return {
        "job_id":      job_id,
        "status":      info["status"],
        "stage":       stage,
        "stage_label": stage_label,
        "ai_complete": info["ai_complete"],
        "ai_reasons":  info.get("ai_reasons", []),
        "elapsed_sec": info.get("elapsed_sec", 0),
    }
