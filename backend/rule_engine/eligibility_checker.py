"""
Rule Engine — Eligibility Checker (NO AI)
Evaluates extracted eligibility rules against the user profile.
"""
import re
from api.schemas import UserProfile, ExtractedData, EligibilityResult


def check_eligibility(extracted: ExtractedData,
                      profile: UserProfile) -> list[EligibilityResult]:
    results: list[EligibilityResult] = []

    for rule in extracted.eligibility:
        rule_lower = rule.lower()

        # ── Minimum CGPA ─────────────────────────────────────────────────
        cgpa_m = re.search(
            r"(?:minimum\s+)?cgpa[:\s]*(?:of\s+)?(\d+(?:\.\d+)?)",
            rule_lower
        )
        if cgpa_m:
            threshold = float(cgpa_m.group(1))
            eligible  = profile.cgpa >= threshold
            results.append(EligibilityResult(
                rule     = rule,
                eligible = eligible,
                reason   = (
                    f"Your CGPA {profile.cgpa} meets minimum {threshold}"
                    if eligible
                    else f"Your CGPA {profile.cgpa} is below required {threshold}"
                ),
            ))
            continue

        # ── Minimum percentage ───────────────────────────────────────────
        pct_m = re.search(
            r"(?:minimum\s+)?percentage[:\s]*(?:of\s+)?(\d+(?:\.\d+)?)",
            rule_lower
        )
        if not pct_m:
            pct_m = re.search(r"(\d+(?:\.\d+)?)\s*%", rule_lower)
        if pct_m:
            threshold = float(pct_m.group(1))
            eligible  = profile.percentage >= threshold
            results.append(EligibilityResult(
                rule     = rule,
                eligible = eligible,
                reason   = (
                    f"Your percentage {profile.percentage}% meets minimum {threshold}%"
                    if eligible
                    else f"Your percentage {profile.percentage}% is below required {threshold}%"
                ),
            ))
            continue

        # ── Programme (B.Tech / M.Tech / MCA …) ─────────────────────────
        if rule_lower.startswith("programme:"):
            # Informational only — we don't store programme in profile
            results.append(EligibilityResult(
                rule     = rule,
                eligible = True,
                reason   = "Please verify your programme is listed",
            ))
            continue

        # ── No backlog ───────────────────────────────────────────────────
        if re.search(r"\b(no\s+(?:active\s+)?backlog|no\s+arrear)\b", rule_lower):
            results.append(EligibilityResult(
                rule     = rule,
                eligible = True,
                reason   = "Cannot verify backlog status — please confirm",
            ))
            continue

        # ── Branch / stream ──────────────────────────────────────────────
        branch_m = re.search(r"\b(?:branch|stream)\s*[:\-]\s*(.+)", rule_lower)
        if branch_m and profile.branch:
            allowed_text = branch_m.group(1)
            allowed = [b.strip() for b in re.split(r"[,/&]", allowed_text) if b.strip()]
            user_branch = profile.branch.lower().strip()
            match_found = any(user_branch in b or b in user_branch for b in allowed)
            results.append(EligibilityResult(
                rule     = rule,
                eligible = match_found,
                reason   = (
                    f"Your branch '{profile.branch}' matches"
                    if match_found
                    else f"Your branch '{profile.branch}' not in: {allowed_text}"
                ),
            ))
            continue

        # ── Year of study ────────────────────────────────────────────────
        year_m = re.search(r"year\s+of\s+study[:\s]+(.+)", rule_lower)
        if year_m and profile.year_of_study:
            allowed_years = re.findall(r"\d+", year_m.group(1))
            if allowed_years:
                eligible = str(profile.year_of_study) in allowed_years
                results.append(EligibilityResult(
                    rule     = rule,
                    eligible = eligible,
                    reason   = (
                        f"You are in year {profile.year_of_study} ✓"
                        if eligible
                        else f"Year {profile.year_of_study} not in allowed years: {', '.join(allowed_years)}"
                    ),
                ))
                continue

        # ── Age limit ────────────────────────────────────────────────────
        age_m = re.search(r"age\s*(?:limit)?\s*[:<]?\s*(\d+)", rule_lower)
        if age_m:
            results.append(EligibilityResult(
                rule     = rule,
                eligible = True,
                reason   = f"Please verify: age limit is {age_m.group(1)} years",
            ))
            continue

        # ── Fallback ─────────────────────────────────────────────────────
        results.append(EligibilityResult(
            rule     = rule,
            eligible = True,
            reason   = "Please verify this criterion manually",
        ))

    return results
