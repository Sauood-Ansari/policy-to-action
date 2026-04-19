"""
Layer 4 — AI Refinement (CONDITIONAL, runs async in background)
Only called when the decision engine flags it as necessary.
Sends ONLY filtered lines to minimise token usage.
Merges AI output back into the existing ExtractedData object.
"""
import json
import re
from api.schemas import ExtractedData, ExtractedDeadline
from config import ANTHROPIC_API_KEY, AI_MODEL


def refine_with_ai(extracted: ExtractedData,
                   prompt: str) -> ExtractedData:
    """
    Call the Anthropic API with the focused prompt.
    Returns an updated ExtractedData merging AI output with existing data.
    If API key is missing or call fails, returns the original extracted data.
    """
    if not ANTHROPIC_API_KEY:
        return extracted

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        message = client.messages.create(
            model      = AI_MODEL,
            max_tokens = 1024,
            messages   = [{"role": "user", "content": prompt}],
        )

        raw_response = message.content[0].text
        ai_data      = _parse_ai_response(raw_response)

        if ai_data:
            return _merge(extracted, ai_data)
        return extracted

    except Exception as e:
        print(f"[AI Refinement] API call failed: {e}")
        return extracted


def _parse_ai_response(raw: str) -> dict | None:
    """Strip markdown fences and parse JSON."""
    # Remove ```json ... ``` wrappers if present
    clean = re.sub(r"```(?:json)?", "", raw).strip()
    clean = clean.strip("`").strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Try to extract just the JSON object
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return None


def _merge(original: ExtractedData, ai_data: dict) -> ExtractedData:
    """
    Merge AI-extracted data into the existing ExtractedData.
    AI data wins for empty/missing fields.
    Existing data is preserved where it already has values.
    """

    # Deadlines: if original has no date_str, replace with AI versions
    ai_deadlines_raw = ai_data.get("deadlines", [])
    if ai_deadlines_raw and (
        not original.deadlines
        or any(not d.date_str for d in original.deadlines)
    ):
        ai_deadlines = [
            ExtractedDeadline(
                raw_text   = d.get("raw_text", ""),
                date_str   = d.get("date_str"),
                label      = d.get("label", "deadline"),
                confidence = 0.85,   # AI-sourced, trust moderately
            )
            for d in ai_deadlines_raw
            if isinstance(d, dict)
        ]
        # Keep originals that had dates, add AI ones that fill gaps
        original_with_dates = [d for d in original.deadlines if d.date_str]
        merged_deadlines    = original_with_dates + [
            d for d in ai_deadlines
            if d.date_str not in {x.date_str for x in original_with_dates}
        ]
        original = original.model_copy(update={"deadlines": merged_deadlines or ai_deadlines})

    # Required docs: union of both
    ai_docs = [str(d).lower().strip() for d in ai_data.get("required_docs", [])]
    if ai_docs:
        merged_docs = list(dict.fromkeys(original.required_docs + ai_docs))
        original = original.model_copy(update={"required_docs": merged_docs})

    # Eligibility: union of both
    ai_elig = [str(e).strip() for e in ai_data.get("eligibility", [])]
    if ai_elig:
        merged_elig = list(dict.fromkeys(original.eligibility + ai_elig))
        original = original.model_copy(update={"eligibility": merged_elig})

    # Instructions: union of both
    ai_instr = [str(i).strip() for i in ai_data.get("instructions", [])]
    if ai_instr:
        merged_instr = list(dict.fromkeys(original.instructions + ai_instr))
        original = original.model_copy(update={"instructions": merged_instr})

    # Stipend: only override if original is None
    if not original.stipend and ai_data.get("stipend"):
        original = original.model_copy(update={"stipend": ai_data["stipend"]})

    return original
