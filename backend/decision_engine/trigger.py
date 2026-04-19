"""
Layer 3 — Decision Engine (NO AI)
Pure rule-based logic that decides whether an AI API call is warranted.
Returns True if AI refinement is needed, False otherwise.

This is the cost-control gate of the entire system.
"""
from api.schemas import ExtractedData, ConfidenceScores
from config import CONFIDENCE_THRESHOLD_FOR_AI, DEADLINE_CONFIDENCE_MIN


def needs_ai_refinement(
    extracted: ExtractedData,
    confidence: ConfidenceScores,
) -> tuple[bool, list[str]]:
    """
    Returns:
        (should_call_ai: bool, reasons: list[str])
    reasons is populated when should_call_ai is True.
    """
    reasons: list[str] = []

    # Rule 1: Overall confidence below threshold
    if confidence.overall < CONFIDENCE_THRESHOLD_FOR_AI:
        reasons.append(
            f"Low overall confidence ({confidence.overall:.2f} < {CONFIDENCE_THRESHOLD_FOR_AI})"
        )

    # Rule 2: No deadlines found at all
    if not extracted.deadlines:
        reasons.append("No deadlines extracted")

    # Rule 3: Deadline confidence too low (even if overall is OK)
    elif confidence.deadline_score < DEADLINE_CONFIDENCE_MIN:
        reasons.append(
            f"Deadline confidence low ({confidence.deadline_score:.2f} < {DEADLINE_CONFIDENCE_MIN})"
        )

    # Rule 4: Any deadline found without a parseable date
    unparsed = [d for d in extracted.deadlines if not d.date_str]
    if unparsed:
        reasons.append(
            f"{len(unparsed)} deadline(s) mention without a parseable date"
        )

    # Rule 5: Document list is empty
    if not extracted.required_docs:
        reasons.append("No required documents found")

    # Rule 6: Eligibility list is empty
    if not extracted.eligibility:
        reasons.append("No eligibility criteria found")

    # Rule 7: Ambiguous / vague phrases detected in the document
    if extracted.ambiguous_phrases:
        reasons.append(
            f"Ambiguous language detected: {', '.join(extracted.ambiguous_phrases[:3])}"
        )

    return bool(reasons), reasons


def build_ai_prompt(extracted: ExtractedData,
                    reasons: list[str]) -> str:
    """
    Build a tight, focused prompt for the AI call.
    Only sends filtered lines — NOT the full document.
    Asks only for what is missing/uncertain.
    """
    lines_block = "\n".join(extracted.source_lines)
    missing_fields = _identify_missing(extracted)

    prompt = (
        "You are extracting structured information from a college/scholarship notice.\n"
        "Return ONLY a valid JSON object, no extra text, no markdown.\n\n"
        f"DOCUMENT LINES:\n{lines_block}\n\n"
        f"MISSING OR UNCERTAIN FIELDS: {', '.join(missing_fields)}\n\n"
        "Extract and return:\n"
        "{\n"
        '  "deadlines": [{"raw_text": "...", "date_str": "DD/MM/YYYY or null", "label": "..."}],\n'
        '  "required_docs": ["..."],\n'
        '  "eligibility": ["..."],\n'
        '  "instructions": ["..."],\n'
        '  "stipend": "... or null"\n'
        "}\n"
        "Rules:\n"
        "- date_str must be DD/MM/YYYY format if you can determine it, else null\n"
        "- required_docs: list document names only, lowercase\n"
        "- eligibility: each rule as a short readable string\n"
        "- Return ONLY the JSON object, nothing else\n"
    )
    return prompt


def _identify_missing(extracted: ExtractedData) -> list[str]:
    missing = []
    if not extracted.deadlines or any(not d.date_str for d in extracted.deadlines):
        missing.append("deadlines with exact dates")
    if not extracted.required_docs:
        missing.append("required documents")
    if not extracted.eligibility:
        missing.append("eligibility criteria")
    if not missing:
        missing.append("verify and complete all fields")
    return missing
