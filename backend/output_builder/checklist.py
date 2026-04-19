"""
Output Builder — Checklist Generator
Combines document match results and eligibility results
into a unified, categorised checklist.
"""
from api.schemas import (
    ChecklistItem, ChecklistStatus,
    DocMatchResult, EligibilityResult, DeadlineRiskResult, DeadlineRisk,
)


def build_checklist(
    doc_results:         list[DocMatchResult],
    eligibility_results: list[EligibilityResult],
    deadline_results:    list[DeadlineRiskResult],
) -> list[ChecklistItem]:

    items: list[ChecklistItem] = []

    # ── Documents ────────────────────────────────────────────────────────
    for doc in doc_results:
        items.append(ChecklistItem(
            task     = f"Prepare: {doc.doc_name.title()}",
            status   = doc.status,
            category = "documents",
        ))

    # ── Eligibility ──────────────────────────────────────────────────────
    for elig in eligibility_results:
        if elig.eligible:
            status = ChecklistStatus.DONE
        elif "cannot verify" in elig.reason.lower() or "please verify" in elig.reason.lower():
            status = ChecklistStatus.PENDING
        else:
            status = ChecklistStatus.MISSING

        items.append(ChecklistItem(
            task     = f"Eligibility: {elig.rule}",
            status   = status,
            category = "eligibility",
        ))

    # ── Submission / Deadlines ───────────────────────────────────────────
    for dl in deadline_results:
        if dl.days_remaining is not None and dl.days_remaining < 0:
            status = ChecklistStatus.MISSING   # past deadline
        elif dl.risk == DeadlineRisk.SAFE:
            status = ChecklistStatus.PENDING
        else:
            status = ChecklistStatus.PENDING   # needs action

        days_label = (
            f" ({dl.days_remaining} days left)" if dl.days_remaining is not None
            else " (date unclear)"
        )
        items.append(ChecklistItem(
            task     = f"Submit by {dl.date_str}{days_label} — {dl.label}",
            status   = status,
            category = "submission",
        ))

    return items
