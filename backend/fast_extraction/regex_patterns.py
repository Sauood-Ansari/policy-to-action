"""
Layer 2 — Compiled Regex Pattern Bank (NO AI)
All patterns are pre-compiled at import time for speed.
"""
import re

# ── Date patterns ─────────────────────────────────────────────────────────

DATE_DMY = re.compile(
    r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b"
)

# "25th March, 2025" / "25 March 2025" — ordinal suffix optional
DATE_MONTH_NAME = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
    r"(january|february|march|april|may|june|july|august|"
    r"september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
    r"[,\s]+(\d{2,4})\b",
    re.IGNORECASE,
)

# "March 25, 2025"
DATE_MONTH_NAME_REV = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|"
    r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|"
    r"oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?[,\s]+(\d{2,4})\b",
    re.IGNORECASE,
)

DEADLINE_SIGNAL = re.compile(
    r"\b(last\s+date|deadline|due\s+by|submit(?:ted)?\s+by|apply\s+before|"
    r"closing\s+date|last\s+day|end\s+date|valid\s+till|before|"
    r"registration\s+(?:closes?|ends?|deadline)|"
    r"event\s+date|result\s+declaration|opens?)\b",
    re.IGNORECASE,
)

# ── Document patterns ─────────────────────────────────────────────────────

KNOWN_DOCS = re.compile(
    r"\b("
    r"aadhar|aadhaar|pan\s*card|"
    r"passport\s+size\s+photograph|passport\s+size\s+photo|"
    r"passport(?!\s+size)(?!\s+photo)(?!\s+photograph)|"
    r"college\s+id(?:\s+card)?|student\s+id(?:\s+card)?|id\s+card|id\s+proof|identity\s+proof|"
    r"birth\s+certificate|domicile(?:\s+certificate)?|"
    r"photograph(?:\s+copy)?|photo(?:\s+copy)?(?!\s*graph)|"
    r"marksheet|mark\s*sheet|grade\s+card|grade\s+sheet|"
    r"transcript|degree\s+certificate|provisional\s+certificate|"
    r"admit\s+card|hall\s+ticket|migration\s+certificate|"
    r"bonafide(?:\s+certificate)?|character\s+certificate|"
    r"bank\s+passbook|bank\s+statement|income\s+certificate|income\s+proof|"
    r"fee\s+receipt|payment\s+receipt|challan|"
    r"noc|no\s+objection(?:\s+certificate)?|"
    r"recommendation\s+letter|reference\s+letter|"
    r"sop|statement\s+of\s+purpose|"
    r"resume|curriculum\s+vitae|biodata|"
    r"consent\s+form|undertaking|declaration\s+form|"
    r"caste\s+certificate|disability\s+certificate|"
    r"obc\s+certificate|ews\s+certificate"
    r")\b",
    re.IGNORECASE,
)

MANDATORY_SIGNAL = re.compile(
    r"\b(required|mandatory|compulsory|must|essential|necessary|"
    r"submit|upload|attach|enclose|bring|to\s+be\s+submitted)\b",
    re.IGNORECASE,
)

# ── Eligibility patterns ──────────────────────────────────────────────────

# CGPA: handles "CGPA 7.5", "7.5 CGPA", "minimum CGPA 7.5", "CGPA >= 7.5", "CGPA of 7.5"
CGPA_PATTERN = re.compile(
    r"(?:"
    r"\b(?:minimum\s+)?(?:cgpa|gpa)\s*(?:[:\-]|of|>=?|<=?|[≥≤]|above|below|minimum|at\s+least)?\s*(\d+(?:\.\d+)?)"
    r"|"
    r"(\d+(?:\.\d+)?)\s*(?:cgpa|gpa)\b"
    r")",
    re.IGNORECASE,
)

# Percentage: handles "60%", "60 percent", "60 percent aggregate", "minimum 60 percent"
PCT_PATTERN = re.compile(
    r"(?:"
    r"(\d+(?:\.\d+)?)\s*(?:%|percent(?:age)?)\b"
    r"|"
    r"\b(?:minimum\s+)?(?:percentage|aggregate|marks?)\s*(?:[:\-]|of|>=?|<=?|[≥≤]|above|minimum|at\s+least)?\s*(\d+(?:\.\d+)?)"
    r")",
    re.IGNORECASE,
)

# Generic fallback numeric criterion
NUMERIC_CRITERION = re.compile(
    r"\b(cgpa|gpa|percentage|aggregate|marks?|score)\s*"
    r"([><=≥≤]{1,2}|above|below|minimum|at\s+least|not\s+less\s+than|of\s+(?=\d))\s*"
    r"(\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)

BRANCH_CRITERION = re.compile(
    r"\b(branch|stream)\s*[:\-]\s*([A-Za-z,/\s&\.]+?)(?:\.|,|\n|$)",
    re.IGNORECASE,
)

BACKLOG_CRITERION = re.compile(
    r"\b(no\s+(?:active\s+)?backlog|no\s+arrear|zero\s+backlog|backlog\s+not\s+allowed)\b",
    re.IGNORECASE,
)

AGE_CRITERION = re.compile(
    r"\bage\s*(?:limit|criteria)?\s*[:<\-]?\s*(\d+)\s*(?:years?)?\b",
    re.IGNORECASE,
)

# ── Money patterns ────────────────────────────────────────────────────────

MONEY_RE = re.compile(
    r"(?:rs\.?\s*|₹\s*|inr\s*)(\d[\d,]*(?:\.\d+)?)",
    re.IGNORECASE,
)

STIPEND_AMOUNT = re.compile(
    r"(?:stipend|scholarship|fellowship|prize|award|grant|reward)"
    r"[^\n]{0,40}"
    r"(?:rs\.?\s*|₹\s*|inr\s*)(\d[\d,]*(?:\.\d+)?)",
    re.IGNORECASE,
)
