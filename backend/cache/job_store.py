"""
In-memory job store.
Maps job_id -> JobResult dict.
Thread-safe enough for single-worker hackathon use.
Swap with Redis for production.
"""
import uuid
from typing import Optional
from api.schemas import JobResult, JobStatus

_store: dict[str, dict] = {}


def create_job() -> str:
    job_id = str(uuid.uuid4())
    _store[job_id] = {
        "status": JobStatus.PENDING,
        "raw_text": "",
        "result": None,
    }
    return job_id


def set_raw_text(job_id: str, text: str) -> None:
    if job_id in _store:
        _store[job_id]["raw_text"] = text


def get_raw_text(job_id: str) -> Optional[str]:
    return _store.get(job_id, {}).get("raw_text")


def set_result(job_id: str, result: JobResult) -> None:
    if job_id in _store:
        _store[job_id]["result"] = result
        _store[job_id]["status"] = result.status


def get_result(job_id: str) -> Optional[JobResult]:
    return _store.get(job_id, {}).get("result")


def get_status(job_id: str) -> Optional[JobStatus]:
    entry = _store.get(job_id)
    if not entry:
        return None
    return entry["status"]


def update_status(job_id: str, status: JobStatus) -> None:
    if job_id in _store:
        _store[job_id]["status"] = status


def exists(job_id: str) -> bool:
    return job_id in _store
