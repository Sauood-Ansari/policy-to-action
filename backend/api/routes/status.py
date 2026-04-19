"""
GET /status/{job_id}
Lightweight polling endpoint.
Returns current job status so frontend knows when AI is done.
"""
from fastapi import APIRouter, HTTPException
from cache import job_store

router = APIRouter()


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    if not job_store.exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    status = job_store.get_status(job_id)
    return {
        "job_id": job_id,
        "status": status,
        "ai_complete": status in ("ai_complete", "fast_complete"),
    }
