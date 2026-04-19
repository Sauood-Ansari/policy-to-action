"""
Rule Engine — Deadline Risk Assessor (NO AI)
Parses all extracted deadline dates and computes
days remaining from today, then categorises risk level.
"""
import re
from datetime import datetime, date
from api.schemas import ExtractedData, DeadlineRiskResult, DeadlineRisk
from config import CRITICAL_DAYS, WARNING_DAYS

_MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def assess_deadline_risks(extracted: ExtractedData) -> list[DeadlineRiskResult]:
    today   = date.today()
    results = []

    for deadline in extracted.deadlines:
        parsed = _parse_date(deadline.date_str or deadline.raw_text)
        if parsed is None:
            results.append(DeadlineRiskResult(
                label          = deadline.label or "deadline",
                date_str       = deadline.raw_text,
                days_remaining = None,
                risk           = DeadlineRisk.WARNING,  # unknown → treat as warning
            ))
            continue

        days_remaining = (parsed - today).days

        if days_remaining < 0:
            risk = DeadlineRisk.CRITICAL   # already past
        elif days_remaining <= CRITICAL_DAYS:
            risk = DeadlineRisk.CRITICAL
        elif days_remaining <= WARNING_DAYS:
            risk = DeadlineRisk.WARNING
        else:
            risk = DeadlineRisk.SAFE

        results.append(DeadlineRiskResult(
            label          = deadline.label or "deadline",
            date_str       = parsed.strftime("%d/%m/%Y"),
            days_remaining = days_remaining,
            risk           = risk,
        ))

    # Sort: most urgent first
    results.sort(key=lambda r: (r.days_remaining is None, r.days_remaining or 9999))
    return results


def _parse_date(text: str) -> date | None:
    """Try multiple formats; return date or None."""
    if not text:
        return None

    text = text.strip()

    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = re.search(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})", text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        return _safe_date(year, month, day)

    # "15 January 2025" or "15 Jan 2025"
    m = re.search(
        r"(\d{1,2})\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
        r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
        r"nov(?:ember)?|dec(?:ember)?)[,\s]+(\d{2,4})",
        text, re.IGNORECASE,
    )
    if m:
        day   = int(m.group(1))
        month = _MONTH_MAP.get(m.group(2).lower()[:3], 0)
        year  = int(m.group(3))
        if year < 100:
            year += 2000
        return _safe_date(year, month, day)

    # "January 15, 2025"
    m = re.search(
        r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
        r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
        r"nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})[,\s]+(\d{2,4})",
        text, re.IGNORECASE,
    )
    if m:
        month = _MONTH_MAP.get(m.group(1).lower()[:3], 0)
        day   = int(m.group(2))
        year  = int(m.group(3))
        if year < 100:
            year += 2000
        return _safe_date(year, month, day)

    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None
