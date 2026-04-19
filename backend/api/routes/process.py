"""
POST /process
Runs the full synchronous fast pipeline and returns initial result.
Spawns AI refinement as a background task if needed.
Must return initial response in < 5 seconds.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from api.schemas import ProcessRequest, JobResult, JobStatus
from cache import job_store
from preprocessing.line_filter import filter_lines
from fast_extraction.field_extractor import extract_fields
from fast_extraction.confidence_scorer import score_confidence
from decision_engine.trigger import needs_ai_refinement
from rule_engine.profile_matcher import match_documents
from rule_engine.eligibility_checker import check_eligibility
from rule_engine.deadline_risk import assess_deadline_risks
from output_builder.checklist import build_checklist
from output_builder.alerts import build_alerts
from output_builder.timeline import build_timeline
from worker.background_job import run_ai_refinement

router = APIRouter()


@router.post("/process", response_model=JobResult)
async def process_document(
    body: ProcessRequest,
    background_tasks: BackgroundTasks,
):
    """
    Full hybrid pipeline:
    1. Filter lines (rule-based)
    2. Extract fields (rule-based regex)
    3. Score confidence (rule-based)
    4. Decide if AI is needed (rule-based)
    5. Run rule engine (rule-based)
    6. Build output
    7. Spawn AI background task if needed
    Returns fast result immediately.
    """
    job_id  = body.job_id
    profile = body.profile

    if not job_store.exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found. Upload a file first.")

    raw_text = job_store.get_raw_text(job_id)
    if not raw_text:
        raise HTTPException(status_code=422, detail="No text found for this job.")

    # Store profile so background worker can access it independently
    job_store.set_profile(job_id, profile)
    job_store.update_status(job_id, JobStatus.PENDING, stage="fast_processing")

    # ── Step 1: Filter lines ─────────────────────────────────────────────
    filtered_lines, ambiguous_phrases = filter_lines(raw_text)

    if not filtered_lines:
        raise HTTPException(
            status_code=422,
            detail="No relevant content found in the document.",
        )

    # ── Step 2: Fast regex extraction ────────────────────────────────────
    extracted = extract_fields(filtered_lines, ambiguous_phrases)

    # ── Step 3: Confidence scoring ───────────────────────────────────────
    confidence = score_confidence(extracted)

    # ── Step 4: Decision engine ──────────────────────────────────────────
    needs_ai, reasons = needs_ai_refinement(extracted, confidence)

    # ── Step 5: Rule engine ──────────────────────────────────────────────
    doc_results  = match_documents(extracted, profile)
    elig_results = check_eligibility(extracted, profile)
    dl_results   = assess_deadline_risks(extracted)

    # ── Step 6: Build output ─────────────────────────────────────────────
    checklist = build_checklist(doc_results, elig_results, dl_results)
    alerts    = build_alerts(
        doc_results, elig_results, dl_results,
        extracted, confidence,
        ai_was_used=False,
    )
    timeline  = build_timeline(dl_results)

    initial_status = JobStatus.AI_PENDING if needs_ai else JobStatus.FAST_COMPLETE

    fast_result = JobResult(
        job_id      = job_id,
        status      = initial_status,
        extracted   = extracted,
        confidence  = confidence,
        checklist   = checklist,
        alerts      = alerts,
        timeline    = timeline,
        ai_was_used = False,
    )
    job_store.set_result(job_id, fast_result)

    # ── Step 7: Spawn AI background task if needed ───────────────────────
    if needs_ai:
        background_tasks.add_task(
            run_ai_refinement,
            job_id    = job_id,
            extracted = extracted,
            confidence= confidence,
            profile   = profile,
            reasons   = reasons,
        )

    return fast_result
