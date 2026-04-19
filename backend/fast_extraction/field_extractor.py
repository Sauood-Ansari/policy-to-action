"""
Layer 2 — Field Extractor (NO AI)
Runs regex patterns on filtered lines.
Returns a structured ExtractedData object.
"""
import re
from api.schemas import ExtractedData, ExtractedDeadline
from fast_extraction import regex_patterns as P


def extract_fields(filtered_lines: list[str],
                   ambiguous_phrases: list[str]) -> ExtractedData:
    """
    Run all pattern banks on the filtered lines.
    Returns structured ExtractedData.
    """
    deadlines       = _extract_deadlines(filtered_lines)
    required_docs   = _extract_documents(filtered_lines)
    eligibility     = _extract_eligibility(filtered_lines)
    instructions    = _extract_instructions(filtered_lines)
    stipend         = _extract_stipend(filtered_lines)

    return ExtractedData(
        deadlines         = deadlines,
        required_docs     = required_docs,
        eligibility       = eligibility,
        instructions      = instructions,
        stipend           = stipend,
        ambiguous_phrases = ambiguous_phrases,
        source_lines      = filtered_lines,
    )


# ── Deadline extraction ────────────────────────────────────────────────────

def _extract_deadlines(lines: list[str]) -> list[ExtractedDeadline]:
    results: list[ExtractedDeadline] = []
    seen_dates: set[str] = set()

    for line in lines:
        has_signal  = bool(P.DEADLINE_SIGNAL.search(line))
        date_str    = _find_date(line)

        if date_str and date_str not in seen_dates:
            seen_dates.add(date_str)
            label = _extract_deadline_label(line)
            results.append(ExtractedDeadline(
                raw_text   = line,
                date_str   = date_str,
                label      = label,
                confidence = 0.0,  # scored separately
            ))
        elif has_signal and not date_str:
            # Line mentions a deadline keyword but no parseable date
            results.append(ExtractedDeadline(
                raw_text   = line,
                date_str   = None,
                label      = _extract_deadline_label(line),
                confidence = 0.0,
            ))

    return results


def _find_date(text: str) -> str | None:
    """Try all date patterns, return first match as string."""
    m = P.DATE_DMY.search(text)
    if m:
        return m.group(0)

    m = P.DATE_MONTH_NAME.search(text)
    if m:
        return m.group(0)

    m = P.DATE_MONTH_NAME_REV.search(text)
    if m:
        return m.group(0)

    return None


def _extract_deadline_label(line: str) -> str:
    m = P.DEADLINE_SIGNAL.search(line)
    if m:
        return m.group(0).lower()
    return "deadline"


# ── Document extraction ────────────────────────────────────────────────────

def _extract_documents(lines: list[str]) -> list[str]:
    docs: set[str] = set()

    # Canonical aliases — if both sop and statement of purpose appear, keep only sop
    SOP_ALIASES = {"statement of purpose", "sop"}

    for line in lines:
        for match in P.KNOWN_DOCS.finditer(line):
            doc = match.group(0).strip().lower()
            doc = re.sub(r"\s+", " ", doc)
            if doc in SOP_ALIASES:
                doc = "sop"
            docs.add(doc)

    return sorted(docs)


# ── Eligibility extraction ─────────────────────────────────────────────────

def _extract_eligibility(lines: list[str]) -> list[str]:
    rules: list[str] = []
    seen: set[str] = set()

    full_text = "\n".join(lines)

    # Numeric criteria
    for m in P.NUMERIC_CRITERION.finditer(full_text):
        rule = m.group(0).strip()
        key = rule.lower()
        if key not in seen:
            seen.add(key)
            rules.append(rule)

    # Backlog
    for m in P.BACKLOG_CRITERION.finditer(full_text):
        key = "no backlog"
        if key not in seen:
            seen.add(key)
            rules.append(m.group(0).strip())

    # Age
    for m in P.AGE_CRITERION.finditer(full_text):
        rule = m.group(0).strip()
        key = rule.lower()
        if key not in seen:
            seen.add(key)
            rules.append(rule)

    # Branch — require explicit separator to avoid "Department of X" false positives
    for m in re.finditer(
        r"\b(?:branch|stream)\s*[:\-]\s*([A-Za-z,/\s&]+?)(?:\.|,|\n|$)",
        full_text, re.IGNORECASE
    ):
        rule = m.group(0).strip().rstrip(",.")
        key = rule.lower()
        if key not in seen:
            seen.add(key)
            rules.append(rule)

    return rules


# ── Instruction extraction ─────────────────────────────────────────────────

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z]+")
INSTRUCTION_SIGNAL = re.compile(
    r"\b(apply|register|visit|click|download|fill|submit|contact|email|portal|"
    r"login|mode of application|how to apply)\b",
    re.IGNORECASE,
)

def _extract_instructions(lines: list[str]) -> list[str]:
    instructions: list[str] = []

    for line in lines:
        if (INSTRUCTION_SIGNAL.search(line)
                or URL_RE.search(line)
                or EMAIL_RE.search(line)):
            instructions.append(line.strip())

    return instructions[:10]   # cap for readability


# ── Stipend extraction ─────────────────────────────────────────────────────

def _extract_stipend(lines: list[str]) -> str | None:
    full_text = "\n".join(lines)
    m = P.STIPEND_AMOUNT.search(full_text)
    if m:
        return m.group(0).strip()
    return None
