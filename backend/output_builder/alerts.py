"""
Output Builder — Alert Generator
Produces typed, severity-tagged alerts from rule engine results.
"""
from api.schemas import (
    Alert, AlertSeverity,
    DocMatchResult, EligibilityResult, DeadlineRiskResult,
    ChecklistStatus, DeadlineRisk,
    ExtractedData, ConfidenceScores,
)


def build_alerts(
    doc_results:         list[DocMatchResult],
    eligibility_results: list[EligibilityResult],
    deadline_results:    list[DeadlineRiskResult],
    extracted:           ExtractedData,
    confidence:          ConfidenceScores,
    ai_was_used:         bool,
) -> list[Alert]:

    alerts: list[Alert] = []

    # ── Missing documents ────────────────────────────────────────────────
    missing_docs = [d for d in doc_results if d.status == ChecklistStatus.MISSING]
    for doc in missing_docs:
        alerts.append(Alert(
            message  = f"Missing document: {doc.doc_name.title()}",
            severity = AlertSeverity.WARNING,
            category = "documents",
        ))

    # ── Ineligibility ────────────────────────────────────────────────────
    for elig in eligibility_results:
        if not elig.eligible and "cannot verify" not in elig.reason.lower():
            alerts.append(Alert(
                message  = f"Ineligible: {elig.reason}",
                severity = AlertSeverity.CRITICAL,
                category = "eligibility",
            ))

    # ── Deadline risk ────────────────────────────────────────────────────
    for dl in deadline_results:
        if dl.days_remaining is not None and dl.days_remaining < 0:
            alerts.append(Alert(
                message  = f"PAST DEADLINE: {dl.label} was on {dl.date_str}",
                severity = AlertSeverity.CRITICAL,
                category = "deadline",
            ))
        elif dl.risk == DeadlineRisk.CRITICAL:
            alerts.append(Alert(
                message  = (
                    f"URGENT: {dl.label.title()} in {dl.days_remaining} day(s) — {dl.date_str}"
                ),
                severity = AlertSeverity.CRITICAL,
                category = "deadline",
            ))
        elif dl.risk == DeadlineRisk.WARNING:
            days_str = (
                f"{dl.days_remaining} day(s)" if dl.days_remaining is not None
                else "unknown time"
            )
            alerts.append(Alert(
                message  = f"Upcoming: {dl.label.title()} in {days_str} — {dl.date_str}",
                severity = AlertSeverity.WARNING,
                category = "deadline",
            ))

    # ── Ambiguous language ───────────────────────────────────────────────
    if extracted.ambiguous_phrases:
        phrases = ", ".join(f'"{p}"' for p in extracted.ambiguous_phrases[:3])
        alerts.append(Alert(
            message  = f"Vague language detected in document: {phrases}. Verify with issuer.",
            severity = AlertSeverity.WARNING,
            category = "ambiguity",
        ))

    # ── Low confidence notice ────────────────────────────────────────────
    if confidence.overall < 0.40 and not ai_was_used:
        alerts.append(Alert(
            message  = (
                "Extraction confidence is low. Some information may be incomplete. "
                "Consider uploading a clearer document."
            ),
            severity = AlertSeverity.WARNING,
            category = "system",
        ))

    # ── Pending verification ─────────────────────────────────────────────
    pending_elig = [e for e in eligibility_results
                    if e.eligible and "please verify" in e.reason.lower()]
    for e in pending_elig:
        alerts.append(Alert(
            message  = f"Please verify manually: {e.reason}",
            severity = AlertSeverity.INFO,
            category = "eligibility",
        ))

    # Sort: critical first, then warning, then info
    severity_order = {
        AlertSeverity.CRITICAL: 0,
        AlertSeverity.WARNING:  1,
        AlertSeverity.INFO:     2,
    }
    alerts.sort(key=lambda a: severity_order[a.severity])
    return alerts
