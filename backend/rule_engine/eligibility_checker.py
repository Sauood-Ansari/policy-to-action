"""
Rule Engine — Eligibility Checker (NO AI)
Evaluates extracted eligibility rules against the user's profile.
Uses structured pattern matching — no AI required.
"""
import re
from api.schemas import UserProfile, ExtractedData, EligibilityResult


def check_eligibility(extracted: ExtractedData,
                      profile: UserProfile) -> list[EligibilityResult]:
    """
    Evaluate each eligibility rule against the user profile.
    Returns a list of EligibilityResult.
    """
    results: list[EligibilityResult] = []

    for rule in extracted.eligibility:
        rule_lower = rule.lower()

        # ── CGPA / GPA ──────────────────────────────────────────────────
        cgpa_match = re.search(
            r"\b(cgpa|gpa)\s*([><=≥≤]{1,2}|above|below|minimum|at\s+least|"
            r"not\s+less\s+than)\s*(\d+(?:\.\d+)?)",
            rule_lower,
        )
        if cgpa_match:
            operator = cgpa_match.group(2).strip()
            threshold = float(cgpa_match.group(3))
            result = _compare_numeric(
                label     = f"CGPA {operator} {threshold}",
                user_val  = profile.cgpa,
                threshold = threshold,
                operator  = operator,
            )
            results.append(result)
            continue

        # ── Percentage / Aggregate ───────────────────────────────────────
        pct_match = re.search(
            r"\b(percentage|aggregate|marks|score)\s*"
            r"([><=≥≤]{1,2}|above|below|minimum|at\s+least)\s*(\d+(?:\.\d+)?)",
            rule_lower,
        )
        if pct_match:
            operator  = pct_match.group(2).strip()
            threshold = float(pct_match.group(3))
            result = _compare_numeric(
                label     = f"Percentage {operator} {threshold}",
                user_val  = profile.percentage,
                threshold = threshold,
                operator  = operator,
            )
            results.append(result)
            continue

        # ── No backlog / No arrear ───────────────────────────────────────
        if re.search(r"\b(no\s+backlog|no\s+arrear|zero\s+backlog)\b", rule_lower):
            results.append(EligibilityResult(
                rule     = rule,
                eligible = True,
                reason   = "Cannot verify backlog status automatically — please confirm",
            ))
            continue

        # ── Branch / stream — require explicit separator ─────────────────
        branch_match = re.search(
            r"\b(branch|stream)\s*[:\-]\s*(.+)", rule_lower
        )
        if branch_match and profile.branch:
            allowed_text = branch_match.group(2)
            allowed = [b.strip() for b in re.split(r"[,/&]", allowed_text) if b.strip()]
            user_branch = profile.branch.lower().strip()
            match_found = any(
                user_branch in b or b in user_branch
                for b in allowed
            )
            results.append(EligibilityResult(
                rule     = rule,
                eligible = match_found,
                reason   = (
                    f"Your branch '{profile.branch}' matches"
                    if match_found
                    else f"Your branch '{profile.branch}' is not in allowed list: {allowed_text}"
                ),
            ))
            continue

        # ── Year of study ────────────────────────────────────────────────
        year_match = re.search(r"(\d+)\s*(?:st|nd|rd|th)?\s*year", rule_lower)
        if year_match and profile.year_of_study:
            required_year = int(year_match.group(1))
            eligible      = profile.year_of_study >= required_year
            results.append(EligibilityResult(
                rule     = rule,
                eligible = eligible,
                reason   = (
                    f"You are in year {profile.year_of_study}"
                    if eligible
                    else f"Requires year {required_year}, you are in year {profile.year_of_study}"
                ),
            ))
            continue

        # ── Age limit ────────────────────────────────────────────────────
        age_match = re.search(r"age\s*(?:limit)?\s*[:<]?\s*(\d+)", rule_lower)
        if age_match:
            # We don't store age in profile, mark as pending
            results.append(EligibilityResult(
                rule     = rule,
                eligible = True,
                reason   = f"Please verify: age limit is {age_match.group(1)} years",
            ))
            continue

        # ── Unrecognised rule: mark as pending ───────────────────────────
        results.append(EligibilityResult(
            rule     = rule,
            eligible = True,
            reason   = "Could not evaluate automatically — please verify manually",
        ))

    return results


# ── Helpers ────────────────────────────────────────────────────────────────

def _compare_numeric(label: str,
                     user_val: float,
                     threshold: float,
                     operator: str) -> EligibilityResult:
    op = operator.strip().lower()

    op_clean = op.strip().lower().split()[0]   # "of 7.5" → "of"

    if op_clean in (">", "above"):
        eligible = user_val > threshold
    elif op_clean in (">=", "≥", "minimum", "at", "not", "of"):
        eligible = user_val >= threshold
    elif op_clean in ("<", "below"):
        eligible = user_val < threshold
    elif op_clean in ("<=", "≤"):
        eligible = user_val <= threshold
    elif op_clean == "=":
        eligible = abs(user_val - threshold) < 0.01
    else:
        eligible = user_val >= threshold   # safe default

    return EligibilityResult(
        rule     = label,
        eligible = eligible,
        reason   = (
            f"Your value {user_val} meets the requirement"
            if eligible
            else f"Your value {user_val} does not meet {label}"
        ),
    )
