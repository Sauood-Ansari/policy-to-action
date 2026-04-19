"""
Layer 2b — Confidence Scorer (NO AI)
Scores each extracted field on a 0.0–1.0 scale.
Lower score → more likely to trigger AI refinement.
"""
import re
from datetime import datetime
from api.schemas import ExtractedData, ConfidenceScores
from fast_extraction import regex_patterns as P

CURRENT_YEAR = datetime.now().year


def score_confidence(extracted: ExtractedData) -> ConfidenceScores:
    deadline_score    = _score_deadlines(extracted)
    doc_score         = _score_documents(extracted)
    eligibility_score = _score_eligibility(extracted)

    # Weighted average: deadlines are most critical
    weights = {"deadline": 0.45, "doc": 0.30, "eligibility": 0.25}
    overall = (
        deadline_score    * weights["deadline"] +
        doc_score         * weights["doc"] +
        eligibility_score * weights["eligibility"]
    )

    return ConfidenceScores(
        deadline_score    = round(deadline_score, 3),
        doc_score         = round(doc_score, 3),
        eligibility_score = round(eligibility_score, 3),
        overall           = round(overall, 3),
    )


# ── Deadline scoring ──────────────────────────────────────────────────────

def _score_deadlines(extracted: ExtractedData) -> float:
    if not extracted.deadlines:
        return 0.0      # No deadlines found at all

    scores = []
    for d in extracted.deadlines:
        s = 0.0

        # Date was found by regex
        if d.date_str:
            s += 0.5

            # Year looks plausible
            year_match = re.search(r"\b(20\d{2})\b", d.date_str)
            if year_match:
                year = int(year_match.group(1))
                if CURRENT_YEAR - 1 <= year <= CURRENT_YEAR + 3:
                    s += 0.2

        # Temporal keyword was present ("last date", "deadline", etc.)
        if d.label and d.label != "deadline":
            s += 0.3

        scores.append(min(s, 1.0))

    return sum(scores) / len(scores)


# ── Document scoring ──────────────────────────────────────────────────────

def _score_documents(extracted: ExtractedData) -> float:
    if not extracted.required_docs:
        return 0.2      # Low confidence (none found, might be missing)

    full_text = "\n".join(extracted.source_lines).lower()
    bonus = 0.0

    # Check if mandatory/required signals appear near document mentions
    if P.MANDATORY_SIGNAL.search(full_text):
        bonus = 0.3

    # More docs = probably more complete extraction
    count_score = min(len(extracted.required_docs) * 0.1, 0.4)

    return min(0.3 + count_score + bonus, 1.0)


# ── Eligibility scoring ───────────────────────────────────────────────────

def _score_eligibility(extracted: ExtractedData) -> float:
    if not extracted.eligibility:
        return 0.2

    # Check how many rules have numeric thresholds (concrete rules)
    concrete = 0
    for rule in extracted.eligibility:
        if re.search(r"\d+(?:\.\d+)?", rule):
            concrete += 1

    concrete_ratio = concrete / len(extracted.eligibility)
    base = 0.3 + concrete_ratio * 0.5

    # Bonus for multiple distinct rule types
    rule_types = _count_rule_types(extracted.eligibility)
    base += min(rule_types * 0.05, 0.2)

    return min(base, 1.0)


def _count_rule_types(rules: list[str]) -> int:
    types = 0
    combined = "\n".join(rules).lower()
    if re.search(r"\b(cgpa|gpa|percentage)\b", combined):
        types += 1
    if re.search(r"\b(branch|department|stream)\b", combined):
        types += 1
    if re.search(r"\b(year|semester)\b", combined):
        types += 1
    if re.search(r"\b(backlog|arrear)\b", combined):
        types += 1
    if re.search(r"\bage\b", combined):
        types += 1
    return types
