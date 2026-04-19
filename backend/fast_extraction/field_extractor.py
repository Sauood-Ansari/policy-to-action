"""
Layer 2 — Field Extractor (NO AI)
Runs regex patterns on filtered lines.
Returns a structured ExtractedData object.
"""
import re
from api.schemas import ExtractedData, ExtractedDeadline
from fast_extraction import regex_patterns as P

SOP_ALIASES = {"statement of purpose", "sop"}

def extract_fields(filtered_lines: list[str],
                   ambiguous_phrases: list[str]) -> ExtractedData:
    deadlines     = _extract_deadlines(filtered_lines)
    required_docs = _extract_documents(filtered_lines)
    eligibility   = _extract_eligibility(filtered_lines)
    instructions  = _extract_instructions(filtered_lines)
    stipend       = _extract_stipend(filtered_lines)

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
        has_signal = bool(P.DEADLINE_SIGNAL.search(line))
        date_str   = _find_date(line)

        if date_str and date_str not in seen_dates:
            seen_dates.add(date_str)
            label = _extract_deadline_label(line)
            results.append(ExtractedDeadline(
                raw_text   = line,
                date_str   = date_str,
                label      = label,
                confidence = 0.0,
            ))
        elif has_signal and not date_str:
            results.append(ExtractedDeadline(
                raw_text   = line,
                date_str   = None,
                label      = _extract_deadline_label(line),
                confidence = 0.0,
            ))

    return results


def _find_date(text: str) -> str | None:
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
        return m.group(0).lower().strip()
    return "deadline"


# ── Document extraction ────────────────────────────────────────────────────

def _extract_documents(lines: list[str]) -> list[str]:
    docs: set[str] = set()

    for line in lines:
        for match in P.KNOWN_DOCS.finditer(line):
            doc = match.group(0).strip().lower()
            doc = re.sub(r"\s+", " ", doc)
            # Normalise SOP variants
            if doc in SOP_ALIASES:
                doc = "sop"
            # Normalise photo variants
            if doc in {"photo", "photo copy"}:
                doc = "photograph"
            # Normalise ID variants
            if doc in {"id card", "id proof", "student id card", "college id"}:
                doc = "college id card"
            # Normalise NOC variants
            if doc in {"no objection certificate", "no objection"}:
                doc = "noc"
            # Normalise bonafide
            if doc == "bonafide":
                doc = "bonafide certificate"
            docs.add(doc)

    return sorted(docs)


# ── Eligibility extraction ─────────────────────────────────────────────────

def _extract_eligibility(lines: list[str]) -> list[str]:
    rules: list[str] = []
    seen: set[str] = set()
    full_text = "\n".join(lines)

    # 1. CGPA
    for m in P.CGPA_PATTERN.finditer(full_text):
        val = m.group(1) or m.group(2)
        if val:
            rule = f"Minimum CGPA: {val}"
            if rule not in seen:
                seen.add(rule)
                rules.append(rule)

    # 2. Percentage
    for m in P.PCT_PATTERN.finditer(full_text):
        val = m.group(1) or m.group(2) or m.group(3) if m.lastindex and m.lastindex >= 3 else (m.group(1) or m.group(2))
        if val:
            rule = f"Minimum percentage: {val}%"
            if rule not in seen:
                seen.add(rule)
                rules.append(rule)

    # 3. Fallback generic numeric (covers edge cases)
    for m in P.NUMERIC_CRITERION.finditer(full_text):
        rule = m.group(0).strip()
        key  = rule.lower()
        # skip if already captured by CGPA/PCT patterns
        cgpa_dup  = ("cgpa" in key or "gpa" in key) and any("cgpa" in s.lower() or "gpa" in s.lower() for s in seen)
        pct_dup   = ("percent" in key or "aggregate" in key) and any("percent" in s.lower() for s in seen)
        if not cgpa_dup and not pct_dup and key not in seen:
            seen.add(key)
            rules.append(rule)

    # 4. Backlog
    for m in P.BACKLOG_CRITERION.finditer(full_text):
        key = "no backlog"
        if key not in seen:
            seen.add(key)
            rules.append("No active backlog/arrear")

    # 5. Age
    for m in P.AGE_CRITERION.finditer(full_text):
        rule = m.group(0).strip()
        key  = rule.lower()
        if key not in seen:
            seen.add(key)
            rules.append(rule)

    # 6. Branch (require explicit separator)
    for m in re.finditer(
        r"\b(?:branch|stream)\s*[:\-]\s*([A-Za-z,/\s&]+?)(?:\.|,|\n|$)",
        full_text, re.IGNORECASE
    ):
        rule = m.group(0).strip().rstrip(",.")
        key  = rule.lower()
        if key not in seen:
            seen.add(key)
            rules.append(rule)

    # 7. Programme eligibility (B.Tech / M.Tech / MCA etc.)
    prog_match = re.search(
        r"\b(b\.?tech|m\.?tech|mca|mba|b\.?sc|m\.?sc|b\.?e\.?|m\.?e\.?|ph\.?d)"
        r"(?:[,/\s]+(?:b\.?tech|m\.?tech|mca|mba|b\.?sc|m\.?sc|b\.?e\.?|m\.?e\.?))*",
        full_text, re.IGNORECASE
    )
    if prog_match:
        prog_str = prog_match.group(0).strip()
        # Standardise capitalisation: btech→B.Tech, mtech→M.Tech etc.
        prog_str = re.sub(r"\bb\.?tech\b",  "B.Tech",  prog_str, flags=re.IGNORECASE)
        prog_str = re.sub(r"\bm\.?tech\b",  "M.Tech",  prog_str, flags=re.IGNORECASE)
        prog_str = re.sub(r"\bmca\b",       "MCA",     prog_str, flags=re.IGNORECASE)
        prog_str = re.sub(r"\bmba\b",       "MBA",     prog_str, flags=re.IGNORECASE)
        prog_str = re.sub(r"\bb\.?sc\b",    "B.Sc",    prog_str, flags=re.IGNORECASE)
        prog_str = re.sub(r"\bm\.?sc\b",    "M.Sc",    prog_str, flags=re.IGNORECASE)
        prog_str = re.sub(r"\bb\.?e\.?\b",  "B.E",     prog_str, flags=re.IGNORECASE)
        prog_str = re.sub(r"\bm\.?e\.?\b",  "M.E",     prog_str, flags=re.IGNORECASE)
        prog_str = re.sub(r"\bph\.?d\b",    "Ph.D",    prog_str, flags=re.IGNORECASE)
        rule = f"Programme: {prog_str}"
        if rule not in seen:
            seen.add(rule)
            rules.append(rule)

    # 8. Year of study
    year_matches = re.findall(
        r"(\d)(?:st|nd|rd|th)?\s*year", full_text, re.IGNORECASE
    )
    if year_matches:
        years = sorted(set(year_matches), key=int)
        rule  = f"Year of study: {', '.join(years)}"
        if rule not in seen:
            seen.add(rule)
            rules.append(rule)

    return rules


# ── Instruction extraction ─────────────────────────────────────────────────

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z]+")
INSTRUCTION_SIGNAL = re.compile(
    r"\b(apply|register|visit|click|download|fill|submit|contact|email|portal|"
    r"login|mode of application|how to apply|google form|online form)\b",
    re.IGNORECASE,
)

def _extract_instructions(lines: list[str]) -> list[str]:
    instructions: list[str] = []
    for line in lines:
        if (INSTRUCTION_SIGNAL.search(line)
                or URL_RE.search(line)
                or EMAIL_RE.search(line)):
            instructions.append(line.strip())
    return instructions[:10]


# ── Stipend / Prize extraction ─────────────────────────────────────────────

PRIZE_LINE_RE = re.compile(
    r"(?:\d+(?:st|nd|rd|th)?\s*prize|prize\s*money|stipend|scholarship|award|"
    r"fellowship|grant|reward)[^\n]*"
    r"(?:rs\.?\s*|₹\s*|inr\s*)(\d[\d,]*)",
    re.IGNORECASE,
)

def _extract_stipend(lines: list[str]) -> str | None:
    full_text = "\n".join(lines)

    # Try prize/stipend labelled lines first
    m = PRIZE_LINE_RE.search(full_text)
    if m:
        # Return the whole matching line, trimmed
        start = full_text.rfind("\n", 0, m.start()) + 1
        end   = full_text.find("\n", m.end())
        line  = full_text[start: end if end != -1 else len(full_text)].strip()
        return line[:120]

    # Fallback to any money amount on a stipend line
    m = P.STIPEND_AMOUNT.search(full_text)
    if m:
        return m.group(0).strip()[:120]

    return None
