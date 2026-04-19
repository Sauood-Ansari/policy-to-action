"""
GET /result/{job_id}
Returns the current best result for a job.
Works at any stage — fast result or AI-refined result.
"""
from fastapi import APIRouter, HTTPException
from api.schemas import JobResult
from cache import job_store

router = APIRouter()


@router.get("/result/{job_id}", response_model=JobResult)
async def get_result(job_id: str):
    if not job_store.exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    result = job_store.get_result(job_id)
    if result is None:
        raise HTTPException(
            status_code=202,
            detail="Result not ready yet. Processing in progress.",
        )
    return result
