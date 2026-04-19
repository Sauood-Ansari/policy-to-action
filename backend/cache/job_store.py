"""
In-memory Job Store
Maps job_id -> full job entry dict.

Additions over v1:
  - stores profile alongside raw_text (needed for AI re-run after restart)
  - stores ai_reasons (why AI was triggered, shown in status response)
  - stores stage  (preprocessing / extracting / ai_running / complete / failed)
  - stores timestamps (created_at, completed_at)
  - auto-expiry: jobs older than JOB_TTL_SECONDS are removed on next access
  - thread-safe via a simple lock (FastAPI runs in a single process with async)
"""
import uuid
import threading
import time
from typing import Optional
from api.schemas import JobResult, JobStatus, UserProfile

# Jobs expire after 2 hours (7200 seconds) — prevents memory leak
JOB_TTL_SECONDS = 7200

_store: dict[str, dict] = {}
_lock  = threading.Lock()


# ── Internal helpers ───────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _expired(entry: dict) -> bool:
    return (_now() - entry.get("created_at", 0)) > JOB_TTL_SECONDS


def _clean_if_expired(job_id: str) -> bool:
    """Returns True if the job was expired and removed."""
    with _lock:
        entry = _store.get(job_id)
        if entry and _expired(entry):
            del _store[job_id]
            return True
    return False


# ── Public API ─────────────────────────────────────────────────────────────

def create_job() -> str:
    job_id = str(uuid.uuid4())
    with _lock:
        _store[job_id] = {
            "status":       JobStatus.PENDING,
            "stage":        "uploaded",
            "raw_text":     "",
            "profile":      None,
            "result":       None,
            "ai_reasons":   [],
            "error":        None,
            "created_at":   _now(),
            "completed_at": None,
        }
    return job_id


def set_raw_text(job_id: str, text: str) -> None:
    with _lock:
        if job_id in _store:
            _store[job_id]["raw_text"] = text
            _store[job_id]["stage"]    = "text_extracted"


def get_raw_text(job_id: str) -> Optional[str]:
    if _clean_if_expired(job_id):
        return None
    return _store.get(job_id, {}).get("raw_text")


def set_profile(job_id: str, profile: UserProfile) -> None:
    with _lock:
        if job_id in _store:
            _store[job_id]["profile"] = profile


def get_profile(job_id: str) -> Optional[UserProfile]:
    return _store.get(job_id, {}).get("profile")


def set_result(job_id: str, result: JobResult) -> None:
    with _lock:
        if job_id in _store:
            _store[job_id]["result"]       = result
            _store[job_id]["status"]       = result.status
            _store[job_id]["completed_at"] = _now()
            if result.status in (JobStatus.FAST_COMPLETE, JobStatus.AI_COMPLETE):
                _store[job_id]["stage"]    = "complete"
            elif result.status == JobStatus.FAILED:
                _store[job_id]["stage"]    = "failed"


def get_result(job_id: str) -> Optional[JobResult]:
    if _clean_if_expired(job_id):
        return None
    return _store.get(job_id, {}).get("result")


def get_status(job_id: str) -> Optional[JobStatus]:
    if _clean_if_expired(job_id):
        return None
    entry = _store.get(job_id)
    return entry["status"] if entry else None


def update_status(job_id: str, status: JobStatus, stage: str = "") -> None:
    with _lock:
        if job_id in _store:
            _store[job_id]["status"] = status
            if stage:
                _store[job_id]["stage"] = stage


def set_ai_reasons(job_id: str, reasons: list[str]) -> None:
    with _lock:
        if job_id in _store:
            _store[job_id]["ai_reasons"] = reasons


def get_stage_info(job_id: str) -> Optional[dict]:
    """Returns status, stage, ai_reasons, elapsed_seconds for the status endpoint."""
    if _clean_if_expired(job_id):
        return None
    entry = _store.get(job_id)
    if not entry:
        return None
    elapsed = round(_now() - entry["created_at"], 1)
    return {
        "status":      entry["status"],
        "stage":       entry["stage"],
        "ai_reasons":  entry["ai_reasons"],
        "elapsed_sec": elapsed,
        "ai_complete": entry["status"] in (
            JobStatus.AI_COMPLETE, JobStatus.FAST_COMPLETE
        ),
    }


def set_error(job_id: str, error: str) -> None:
    with _lock:
        if job_id in _store:
            _store[job_id]["error"]  = error
            _store[job_id]["status"] = JobStatus.FAILED
            _store[job_id]["stage"]  = "failed"


def exists(job_id: str) -> bool:
    if _clean_if_expired(job_id):
        return False
    return job_id in _store


def get_store_stats() -> dict:
    """Health/debug endpoint helper."""
    with _lock:
        total   = len(_store)
        by_status = {}
        for entry in _store.values():
            s = str(entry["status"])
            by_status[s] = by_status.get(s, 0) + 1
    return {"total_jobs": total, "by_status": by_status, "ttl_seconds": JOB_TTL_SECONDS}
