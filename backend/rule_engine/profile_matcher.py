"""
Rule Engine — Profile Matcher (NO AI)
Compares required documents from the notice against
the user's available_docs list.
Returns per-document match results.
"""
import re
from api.schemas import UserProfile, ExtractedData, DocMatchResult, ChecklistStatus


# Normalise aliases so "aadhar" matches "aadhaar card", etc.
_ALIASES: dict[str, list[str]] = {
    "aadhar":                 ["aadhaar", "aadhar card", "aadhaar card"],
    "pan card":               ["pan", "pan number"],
    "marksheet":              ["mark sheet", "marks sheet", "grade sheet", "transcript"],
    "photograph":             ["photo", "passport size photo", "passport photo"],
    "bank passbook":          ["bank statement", "passbook"],
    "income certificate":     ["income proof", "income affidavit"],
    "character certificate":  ["conduct certificate"],
    "bonafide":               ["bonafide certificate"],
    "provisional certificate":["provisional"],
    "degree certificate":     ["degree"],
    "noc":                    ["no objection certificate", "no objection"],
    "sop":                    ["statement of purpose"],
    "passport":               ["passport copy"],
}

def _normalise(doc: str) -> str:
    d = doc.lower().strip()
    d = re.sub(r"\s+", " ", d)
    return d


def _expand_aliases(doc_name: str) -> list[str]:
    """Return doc_name plus all known aliases."""
    base = _normalise(doc_name)
    variants = {base}
    for canonical, aliases in _ALIASES.items():
        if base == canonical or base in [_normalise(a) for a in aliases]:
            variants.add(canonical)
            variants.update(_normalise(a) for a in aliases)
    return list(variants)


def match_documents(extracted: ExtractedData,
                    profile: UserProfile) -> list[DocMatchResult]:
    """
    For each required document, determine if the user has it.
    Returns a list of DocMatchResult objects.
    """
    user_docs_norm = {_normalise(d) for d in profile.available_docs}
    results: list[DocMatchResult] = []

    for doc in extracted.required_docs:
        variants = _expand_aliases(doc)
        found = any(v in user_docs_norm for v in variants)

        status = (
            ChecklistStatus.DONE    if found  else
            ChecklistStatus.MISSING
        )
        results.append(DocMatchResult(doc_name=doc, status=status))

    return results
