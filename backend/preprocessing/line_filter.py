"""
Layer 1b — Line Filter (NO AI)
Splits raw text into lines and keeps only those that are likely
to contain actionable information (deadlines, documents, eligibility, etc.)
This drastically reduces token count before any AI call.
"""
import re
from config import MAX_FILTERED_LINES

# ── Keyword banks ─────────────────────────────────────────────────────────

DEADLINE_KEYWORDS = {
    "deadline", "last date", "due date", "due by", "submit by",
    "submission", "apply before", "apply by", "closing date",
    "last day", "expires", "expiry", "valid till", "end date",
    "open till", "before", "by date", "application date",
}

DOCUMENT_KEYWORDS = {
    "document", "certificate", "marksheet", "transcript", "aadhar",
    "aadhaar", "pan card", "passport", "photo", "photograph",
    "id proof", "identity", "noc", "no objection", "letter",
    "recommendation", "sop", "statement of purpose", "resume", "cv",
    "biodata", "bank", "passbook", "income proof", "caste certificate",
    "domicile", "bonafide", "character certificate", "migration",
    "degree certificate", "provisional", "admit card", "hall ticket",
    "signature", "upload", "attach", "enclose", "submit",
}

ELIGIBILITY_KEYWORDS = {
    "eligible", "eligibility", "criteria", "cgpa", "gpa", "percentage",
    "aggregate", "marks", "score", "branch", "department", "stream",
    "year", "semester", "student", "undergraduate", "postgraduate",
    "ug", "pg", "btech", "mtech", "mca", "mba", "bsc", "msc",
    "nationality", "indian", "citizen", "age limit", "age", "gender",
    "minimum", "maximum", "required", "must have", "should have",
    "not eligible", "backlog", "arrear", "active backlog",
}

INSTRUCTION_KEYWORDS = {
    "apply", "register", "link", "url", "portal", "website", "form",
    "online", "offline", "mode", "procedure", "process", "step",
    "click", "visit", "download", "fill", "complete", "payment",
    "fee", "amount", "stipend", "scholarship", "fellowship",
    "selection", "interview", "test", "exam", "shortlist",
    "contact", "email", "helpdesk", "queries",
}

ALL_KEYWORDS = (DEADLINE_KEYWORDS | DOCUMENT_KEYWORDS |
                ELIGIBILITY_KEYWORDS | INSTRUCTION_KEYWORDS)

# Ambiguity markers — vague temporal/conditional language
AMBIGUITY_PHRASES = [
    r"\bshortly\b", r"\bsoon\b", r"\bas soon as possible\b",
    r"\btba\b", r"\bto be announced\b", r"\bwill be notified\b",
    r"\bwill be informed\b", r"\bcontact office\b",
    r"\bas per requirement\b", r"\bmay vary\b", r"\bsubject to change\b",
    r"\bapproximate\b", r"\btentative\b",
]
_AMBIGUITY_RE = re.compile("|".join(AMBIGUITY_PHRASES), re.IGNORECASE)


def filter_lines(raw_text: str) -> tuple[list[str], list[str]]:
    """
    Returns:
        filtered_lines  — relevant lines (capped at MAX_FILTERED_LINES)
        ambiguous_phrases — list of vague phrases detected in full text
    """
    lines = raw_text.splitlines()
    scored: list[tuple[int, str]] = []

    for line in lines:
        line_stripped = line.strip()
        if len(line_stripped) < 6:       # skip near-empty lines
            continue
        score = _score_line(line_stripped.lower())
        if score > 0:
            scored.append((score, line_stripped))

    # Sort by score descending, take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    filtered = [line for _, line in scored[:MAX_FILTERED_LINES]]

    # Detect ambiguity in the full text (not just filtered lines)
    ambiguous = _detect_ambiguity(raw_text)

    return filtered, ambiguous


def _score_line(line_lower: str) -> int:
    """Score a line by keyword hit count."""
    score = 0
    for kw in ALL_KEYWORDS:
        if kw in line_lower:
            score += 1
    # Bonus: line contains a date-like pattern
    if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", line_lower):
        score += 3
    if re.search(r"\d{4}", line_lower):   # year mention
        score += 1
    return score


def _detect_ambiguity(text: str) -> list[str]:
    """Find vague phrases in the document text."""
    matches = _AMBIGUITY_RE.findall(text)
    return list(set(m.lower() for m in matches))
