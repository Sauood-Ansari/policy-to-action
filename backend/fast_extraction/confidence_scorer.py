"""
Layer 2b — Confidence Scorer (NO AI)
Scores each extracted field 0.0–1.0.
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

    overall = (
        deadline_score    * 0.45 +
        doc_score         * 0.30 +
        eligibility_score * 0.25
    )

    return ConfidenceScores(
        deadline_score    = round(deadline_score, 3),
        doc_score         = round(doc_score, 3),
        eligibility_score = round(eligibility_score, 3),
        overall           = round(overall, 3),
    )


def _score_deadlines(extracted: ExtractedData) -> float:
    if not extracted.deadlines:
        return 0.0

    scores = []
    for d in extracted.deadlines:
        s = 0.0
        if d.date_str:
            s += 0.5
            year_match = re.search(r"\b(20\d{2})\b", d.date_str)
            if year_match:
                year = int(year_match.group(1))
                if CURRENT_YEAR - 1 <= year <= CURRENT_YEAR + 3:
                    s += 0.2
        if d.label and d.label not in ("deadline", "before"):
            s += 0.3
        scores.append(min(s, 1.0))

    return sum(scores) / len(scores)


def _score_documents(extracted: ExtractedData) -> float:
    if not extracted.required_docs:
        return 0.2

    full_text = "\n".join(extracted.source_lines).lower()
    bonus = 0.3 if P.MANDATORY_SIGNAL.search(full_text) else 0.0
    count_score = min(len(extracted.required_docs) * 0.08, 0.5)
    return min(0.2 + count_score + bonus, 1.0)


def _score_eligibility(extracted: ExtractedData) -> float:
    if not extracted.eligibility:
        return 0.2

    concrete = sum(
        1 for r in extracted.eligibility
        if re.search(r"\d+(?:\.\d+)?", r)
    )
    concrete_ratio = concrete / len(extracted.eligibility)
    base = 0.3 + concrete_ratio * 0.5

    # Bonus for variety of rule types
    combined = "\n".join(extracted.eligibility).lower()
    types = sum([
        bool(re.search(r"\b(cgpa|gpa|percentage)\b", combined)),
        bool(re.search(r"\b(branch|stream|programme)\b", combined)),
        bool(re.search(r"\b(year|semester)\b", combined)),
        bool(re.search(r"\b(backlog|arrear)\b", combined)),
    ])
    base += min(types * 0.05, 0.2)
    return min(base, 1.0)
