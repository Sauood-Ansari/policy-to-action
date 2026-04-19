"""
Background Worker
Runs AI refinement asynchronously after the initial fast response
has already been sent to the client.
Updates job_store when complete so the frontend can poll for updates.
"""
from api.schemas import (
    JobStatus, JobResult, UserProfile,
    ExtractedData, ConfidenceScores,
)
from cache import job_store
from ai_refinement.gemini_client import refine_with_ai
from decision_engine.trigger import build_ai_prompt
from rule_engine.profile_matcher import match_documents
from rule_engine.eligibility_checker import check_eligibility
from rule_engine.deadline_risk import assess_deadline_risks
from output_builder.checklist import build_checklist
from output_builder.alerts import build_alerts
from output_builder.timeline import build_timeline


def run_ai_refinement(
    job_id:     str,
    extracted:  ExtractedData,
    confidence: ConfidenceScores,
    profile:    UserProfile,
    reasons:    list[str],
) -> None:
    """
    Called as a FastAPI BackgroundTask.
    1. Calls Claude API with focused prompt
    2. Re-runs rule engine on refined data
    3. Updates job store with improved result
    """
    try:
        job_store.update_status(job_id, JobStatus.AI_PENDING)

        # Build focused prompt (only filtered lines)
        prompt = build_ai_prompt(extracted, reasons)

        # Call AI
        refined_extracted = refine_with_ai(extracted, prompt)

        # Re-run rule engine on refined data
        doc_results   = match_documents(refined_extracted, profile)
        elig_results  = check_eligibility(refined_extracted, profile)
        dl_results    = assess_deadline_risks(refined_extracted)

        checklist = build_checklist(doc_results, elig_results, dl_results)
        alerts    = build_alerts(
            doc_results, elig_results, dl_results,
            refined_extracted, confidence,
            ai_was_used=True,
        )
        timeline  = build_timeline(dl_results)

        refined_result = JobResult(
            job_id      = job_id,
            status      = JobStatus.AI_COMPLETE,
            extracted   = refined_extracted,
            confidence  = confidence,
            checklist   = checklist,
            alerts      = alerts,
            timeline    = timeline,
            ai_was_used = True,
        )
        job_store.set_result(job_id, refined_result)

    except Exception as e:
        print(f"[Background Worker] Error for job {job_id}: {e}")
        # Mark as failed but keep the fast result if it exists
        job_store.update_status(job_id, JobStatus.FAILED)
