"""
Output Builder — Timeline Plan Generator
Converts deadline risk results into a sorted, actionable timeline.
Adds buffer recommendations for critical deadlines.
"""
from api.schemas import TimelineEntry, DeadlineRiskResult, DeadlineRisk


def build_timeline(deadline_results: list[DeadlineRiskResult]) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []

    for dl in deadline_results:
        # Main deadline entry
        entries.append(TimelineEntry(
            date_str       = dl.date_str,
            task           = f"{dl.label.title()} — Submit application",
            days_remaining = dl.days_remaining,
            risk           = dl.risk,
        ))

        # Add a buffer reminder for non-past deadlines
        if dl.days_remaining is not None and dl.days_remaining > 0:
            buffer_days = _buffer_days(dl.risk, dl.days_remaining)
            if buffer_days > 0:
                buffer_remaining = dl.days_remaining - buffer_days
                entries.append(TimelineEntry(
                    date_str       = _subtract_days_str(dl.date_str, buffer_days),
                    task           = f"Start preparing for: {dl.label.title()}",
                    days_remaining = buffer_remaining if buffer_remaining > 0 else 0,
                    risk           = DeadlineRisk.WARNING,
                ))

    # Sort by days_remaining ascending (most urgent first)
    # None (unknown dates) go to end
    entries.sort(key=lambda e: (e.days_remaining is None, e.days_remaining or 9999))
    return entries


def _buffer_days(risk: DeadlineRisk, days_remaining: int) -> int:
    """How many days before deadline should preparation start."""
    if risk == DeadlineRisk.CRITICAL or days_remaining <= 3:
        return 0    # No time — just go
    elif risk == DeadlineRisk.WARNING or days_remaining <= 7:
        return 2
    elif days_remaining <= 14:
        return 5
    else:
        return 7


def _subtract_days_str(date_str: str, days: int) -> str:
    """Subtract N days from a DD/MM/YYYY string. Returns original on failure."""
    try:
        from datetime import datetime, timedelta
        d = datetime.strptime(date_str, "%d/%m/%Y")
        result = d - timedelta(days=days)
        return result.strftime("%d/%m/%Y")
    except Exception:
        return date_str
