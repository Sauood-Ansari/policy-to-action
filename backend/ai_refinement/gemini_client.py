"""
Layer 4 — AI Refinement using Google Gemini (CONDITIONAL, runs async in background)
Only called when the decision engine flags it as necessary.
Sends ONLY filtered lines to minimise token usage.
Merges Gemini output back into the existing ExtractedData object.

Free-tier model: gemini-2.0-flash
Get your API key free at: https://aistudio.google.com/apikey
"""
import json
import re
from api.schemas import ExtractedData, ExtractedDeadline
from config import GEMINI_API_KEY, AI_MODEL


def refine_with_ai(extracted: ExtractedData,
                   prompt: str) -> ExtractedData:
    """
    Call the Gemini API with the focused prompt.
    Returns an updated ExtractedData merging AI output with existing data.
    If API key is missing or call fails, returns the original extracted data.
    """
    if not GEMINI_API_KEY:
        print("[AI Refinement] No GEMINI_API_KEY set — skipping AI refinement.")
        return extracted

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)

        model = genai.GenerativeModel(
            model_name=AI_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=0.1,          # low temp → deterministic JSON output
                max_output_tokens=1024,
            ),
        )

        response     = model.generate_content(prompt)
        raw_response = response.text
        ai_data      = _parse_ai_response(raw_response)

        if ai_data:
            return _merge(extracted, ai_data)
        return extracted

    except Exception as e:
        print(f"[AI Refinement] Gemini API call failed: {e}")
        return extracted


def _parse_ai_response(raw: str) -> dict | None:
    """Strip markdown fences and parse JSON from Gemini response."""
    # Remove ```json ... ``` or ``` ... ``` wrappers
    clean = re.sub(r"```(?:json)?", "", raw).strip()
    clean = clean.strip("`").strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Try to extract just the JSON object from the response
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    print(f"[AI Refinement] Could not parse Gemini response as JSON: {raw[:200]}")
    return None


def _merge(original: ExtractedData, ai_data: dict) -> ExtractedData:
    """
    Merge Gemini-extracted data into the existing ExtractedData.
    AI data wins for empty/missing fields only.
    Existing confident data is always preserved.
    """

    # Deadlines: only override if original has no parseable date
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
                confidence = 0.85,   # Gemini-sourced, trust moderately
            )
            for d in ai_deadlines_raw
            if isinstance(d, dict)
        ]
        original_with_dates = [d for d in original.deadlines if d.date_str]
        merged_deadlines    = original_with_dates + [
            d for d in ai_deadlines
            if d.date_str not in {x.date_str for x in original_with_dates}
        ]
        original = original.model_copy(
            update={"deadlines": merged_deadlines or ai_deadlines}
        )

    # Required docs: union of original + AI (no duplicates)
    ai_docs = [str(d).lower().strip() for d in ai_data.get("required_docs", [])]
    if ai_docs:
        merged_docs = list(dict.fromkeys(original.required_docs + ai_docs))
        original = original.model_copy(update={"required_docs": merged_docs})

    # Eligibility rules: union (no duplicates)
    ai_elig = [str(e).strip() for e in ai_data.get("eligibility", [])]
    if ai_elig:
        merged_elig = list(dict.fromkeys(original.eligibility + ai_elig))
        original = original.model_copy(update={"eligibility": merged_elig})

    # Instructions: union (no duplicates)
    ai_instr = [str(i).strip() for i in ai_data.get("instructions", [])]
    if ai_instr:
        merged_instr = list(dict.fromkeys(original.instructions + ai_instr))
        original = original.model_copy(update={"instructions": merged_instr})

    # Stipend: only fill in if original is empty
    if not original.stipend and ai_data.get("stipend"):
        original = original.model_copy(update={"stipend": ai_data["stipend"]})

    return original
