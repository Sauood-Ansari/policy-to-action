"""
Background Worker — AI Refinement
Runs after the fast synchronous response has already been sent.
Updates job_store at each stage so the frontend polling can show progress.

Fixes over v1:
  1. Per-stage status updates  — frontend shows live progress
  2. Timeout guard             — Gemini call capped at 30 seconds
  3. Retry with backoff        — up to 2 retries on transient errors
  4. Graceful degradation      — on any failure, fast result is preserved
                                 and status set to FAST_COMPLETE (not FAILED)
  5. Re-score confidence       — after AI merge, re-run scorer so output
                                 reflects improved extraction
  6. Structured logging        — timestamps + job_id on every log line
  7. Error detail stored       — job_store.set_error() captures the message
"""
import time
import logging
import threading

from api.schemas import (
    JobStatus, JobResult, UserProfile,
    ExtractedData, ConfidenceScores,
)
from cache import job_store
from ai_refinement.gemini_client import refine_with_ai
from decision_engine.trigger import build_ai_prompt
from fast_extraction.confidence_scorer import score_confidence
from rule_engine.profile_matcher import match_documents
from rule_engine.eligibility_checker import check_eligibility
from rule_engine.deadline_risk import assess_deadline_risks
from output_builder.checklist import build_checklist
from output_builder.alerts import build_alerts
from output_builder.timeline import build_timeline

# ── Config ─────────────────────────────────────────────────────────────────
AI_TIMEOUT_SECONDS = 30     # max time for a single Gemini call
MAX_RETRIES        = 2      # how many times to retry on transient error
RETRY_DELAY        = 2.0    # seconds to wait between retries

log = logging.getLogger("background_worker")
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt = "%H:%M:%S",
)


# ── Main entry point ────────────────────────────────────────────────────────

def run_ai_refinement(
    job_id:     str,
    extracted:  ExtractedData,
    confidence: ConfidenceScores,
    profile:    UserProfile,
    reasons:    list[str],
) -> None:
    """
    Called as a FastAPI BackgroundTask.
    Runs entirely after the HTTP response has been sent.
    Never raises — all exceptions are caught and stored.
    """
    t_start = time.time()
    log.info("[%s] Background job started. Reasons: %s", job_id, reasons)

    # Store AI trigger reasons so status endpoint can report them
    job_store.set_ai_reasons(job_id, reasons)
    job_store.update_status(job_id, JobStatus.AI_PENDING, stage="ai_calling")

    try:
        # ── Stage 1: Build prompt ───────────────────────────────────────
        job_store.update_status(job_id, JobStatus.AI_PENDING, stage="ai_building_prompt")
        prompt = build_ai_prompt(extracted, reasons)
        log.info("[%s] Prompt built (%d chars, %d source lines)",
                 job_id, len(prompt), len(extracted.source_lines))

        # ── Stage 2: Call Gemini with timeout + retry ───────────────────
        job_store.update_status(job_id, JobStatus.AI_PENDING, stage="ai_calling_gemini")
        refined_extracted = _call_with_retry(job_id, extracted, prompt)

        # ── Stage 3: Re-score confidence on refined data ────────────────
        job_store.update_status(job_id, JobStatus.AI_PENDING, stage="ai_rescoring")
        refined_confidence = score_confidence(refined_extracted)
        log.info("[%s] Confidence: %.2f → %.2f after AI",
                 job_id, confidence.overall, refined_confidence.overall)

        # ── Stage 4: Re-run rule engine on refined data ─────────────────
        job_store.update_status(job_id, JobStatus.AI_PENDING, stage="ai_rule_engine")
        doc_results  = match_documents(refined_extracted, profile)
        elig_results = check_eligibility(refined_extracted, profile)
        dl_results   = assess_deadline_risks(refined_extracted)

        # ── Stage 5: Build output ────────────────────────────────────────
        job_store.update_status(job_id, JobStatus.AI_PENDING, stage="ai_building_output")
        checklist = build_checklist(doc_results, elig_results, dl_results)
        alerts    = build_alerts(
            doc_results, elig_results, dl_results,
            refined_extracted, refined_confidence,
            ai_was_used=True,
        )
        timeline  = build_timeline(dl_results)

        # ── Stage 6: Save final result ───────────────────────────────────
        refined_result = JobResult(
            job_id      = job_id,
            status      = JobStatus.AI_COMPLETE,
            extracted   = refined_extracted,
            confidence  = refined_confidence,
            checklist   = checklist,
            alerts      = alerts,
            timeline    = timeline,
            ai_was_used = True,
        )
        job_store.set_result(job_id, refined_result)

        elapsed = round(time.time() - t_start, 2)
        log.info("[%s] Background job complete in %.2fs", job_id, elapsed)

    except _AICallFailed as e:
        # Gemini call failed even after retries — keep fast result, don't mark FAILED
        _preserve_fast_result(job_id, str(e))
        log.warning("[%s] AI call failed after retries: %s. Fast result preserved.", job_id, e)

    except Exception as e:
        # Unexpected error — preserve fast result, log details
        _preserve_fast_result(job_id, str(e))
        log.error("[%s] Unexpected error in background job: %s", job_id, e, exc_info=True)


# ── Helpers ─────────────────────────────────────────────────────────────────

class _AICallFailed(Exception):
    """Raised when all retries are exhausted."""


def _call_with_retry(
    job_id:    str,
    extracted: ExtractedData,
    prompt:    str,
) -> ExtractedData:
    """
    Calls refine_with_ai() with a timeout thread.
    Retries up to MAX_RETRIES times on transient errors.
    Raises _AICallFailed if all attempts fail.
    """
    last_error = ""
    for attempt in range(1, MAX_RETRIES + 2):    # 1, 2, 3
        log.info("[%s] Gemini call attempt %d/%d", job_id, attempt, MAX_RETRIES + 1)

        result_holder: list = []
        error_holder:  list = []

        def _call():
            try:
                result_holder.append(refine_with_ai(extracted, prompt))
            except Exception as e:
                error_holder.append(str(e))

        t = threading.Thread(target=_call, daemon=True)
        t.start()
        t.join(timeout=AI_TIMEOUT_SECONDS)

        if t.is_alive():
            # Thread still running after timeout — treat as transient failure
            last_error = f"Gemini call timed out after {AI_TIMEOUT_SECONDS}s"
            log.warning("[%s] %s (attempt %d)", job_id, last_error, attempt)
        elif error_holder:
            last_error = error_holder[0]
            log.warning("[%s] Gemini call error: %s (attempt %d)", job_id, last_error, attempt)
        elif result_holder:
            return result_holder[0]   # success

        if attempt <= MAX_RETRIES:
            log.info("[%s] Retrying in %.1fs...", job_id, RETRY_DELAY)
            time.sleep(RETRY_DELAY)

    raise _AICallFailed(last_error)


def _preserve_fast_result(job_id: str, error_msg: str) -> None:
    """
    On AI failure, keep whatever fast result exists and mark as
    FAST_COMPLETE (not FAILED) so the frontend still shows results.
    Stores the error message for the status endpoint to report.
    """
    existing = job_store.get_result(job_id)
    if existing:
        # Patch status to FAST_COMPLETE so polling stops
        patched = existing.model_copy(update={
            "status": JobStatus.FAST_COMPLETE,
            "error":  f"AI refinement failed: {error_msg}. Showing rule-based result.",
        })
        job_store.set_result(job_id, patched)
    else:
        # No fast result either — now it really is a failure
        job_store.set_error(job_id, error_msg)
