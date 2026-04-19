"""
Layer 2 — Compiled Regex Pattern Bank (NO AI)
All patterns are pre-compiled at import time for speed.
"""
import re

# ── Date patterns ─────────────────────────────────────────────────────────

# DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
DATE_DMY = re.compile(
    r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b"
)

# Month name: "15 January 2025", "January 15, 2025", "15 Jan 2025"
DATE_MONTH_NAME = re.compile(
    r"\b(\d{1,2})\s*(january|february|march|april|may|june|july|august|"
    r"september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|"
    r"sept|oct|nov|dec)[,\s]*(\d{2,4})\b",
    re.IGNORECASE,
)
DATE_MONTH_NAME_REV = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|"
    r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|"
    r"oct|nov|dec)\s+(\d{1,2})[,\s]*(\d{2,4})\b",
    re.IGNORECASE,
)

# Temporal keywords that indicate a deadline line
DEADLINE_SIGNAL = re.compile(
    r"\b(last\s+date|deadline|due\s+by|submit\s+by|apply\s+before|"
    r"closing\s+date|last\s+day|end\s+date|valid\s+till|before)\b",
    re.IGNORECASE,
)

# ── Document patterns ─────────────────────────────────────────────────────

KNOWN_DOCS = re.compile(
    r"\b(marksheet|mark\s*sheet|transcript|aadhar|aadhaar|pan\s*card|"
    r"passport|photograph|photo|noc|no\s*objection|recommendation\s*letter|"
    r"sop|statement\s*of\s*purpose|resume|cv|biodata|bank\s*passbook|"
    r"bank\s*statement|income\s*certificate|income\s*proof|"
    r"caste\s*certificate|domicile|bonafide|character\s*certificate|"
    r"migration\s*certificate|degree\s*certificate|provisional\s*certificate|"
    r"admit\s*card|hall\s*ticket|id\s*proof|identity\s*proof|"
    r"birth\s*certificate|disability\s*certificate|signature)\b",
    re.IGNORECASE,
)

# Mandatory/required signals near a document mention
MANDATORY_SIGNAL = re.compile(
    r"\b(required|mandatory|compulsory|must|essential|necessary|"
    r"submit|upload|attach|enclose|bring)\b",
    re.IGNORECASE,
)

# ── Eligibility patterns ──────────────────────────────────────────────────

# CGPA/GPA/Percentage with comparison: "CGPA >= 7.5", "60% and above"
NUMERIC_CRITERION = re.compile(
    r"\b(cgpa|gpa|percentage|aggregate|marks|score)"
    r"\s*(?:[:\-])?\s*"
    r"([><=≥≤]{1,2}|above|below|minimum|at\s+least|not\s+less\s+than|of\s+(?=\d))\s*"
    r"(\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)

# Branch / department
BRANCH_CRITERION = re.compile(
    r"\b(branch|department|stream|discipline)\s*[:\-]?\s*"
    r"([A-Za-z,/\s&]+?)(?:\.|,|\n|$)",
    re.IGNORECASE,
)

# Year of study / semester
YEAR_CRITERION = re.compile(
    r"\b(\d(?:st|nd|rd|th)?)\s*year\b",
    re.IGNORECASE,
)

SEMESTER_CRITERION = re.compile(
    r"\b(\d(?:st|nd|rd|th)?)\s*semester\b",
    re.IGNORECASE,
)

# Backlog restriction
BACKLOG_CRITERION = re.compile(
    r"\b(no\s+backlog|no\s+arrear|no\s+active\s+backlog|zero\s+backlog|"
    r"backlog\s+not\s+allowed)\b",
    re.IGNORECASE,
)

# Age limit
AGE_CRITERION = re.compile(
    r"\bage\s*(?:limit\s*)?[:<\-]?\s*(\d+)\s*(?:years?)?",
    re.IGNORECASE,
)

# ── Stipend / Amount patterns ─────────────────────────────────────────────

STIPEND_AMOUNT = re.compile(
    r"(?:stipend|fellowship|award|grant|prize)[^\d₹\n]{0,30}"
    r"(₹\s*[\d,]+|rs\.?\s*[\d,]+|inr\s*[\d,]+|[\d,]{3,}\s*(?:per\s+month|p\.m\.|pm)?)",
    re.IGNORECASE,
)
