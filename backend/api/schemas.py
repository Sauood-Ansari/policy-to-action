from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Enums ──────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING        = "pending"
    FAST_COMPLETE  = "fast_complete"
    AI_PENDING     = "ai_pending"
    AI_COMPLETE    = "ai_complete"
    FAILED         = "failed"

class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING  = "warning"
    INFO     = "info"

class DeadlineRisk(str, Enum):
    CRITICAL = "critical"
    WARNING  = "warning"
    SAFE     = "safe"

class ChecklistStatus(str, Enum):
    DONE      = "done"
    MISSING   = "missing"
    PENDING   = "pending"
    UNKNOWN   = "unknown"


# ── User Profile ────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    name:             str             = ""
    cgpa:             float           = 0.0
    percentage:       float           = 0.0
    branch:           str             = ""
    year_of_study:    int             = 1
    semester:         int             = 1
    nationality:      str             = "Indian"
    available_docs:   list[str]       = Field(default_factory=list)
    # e.g. ["aadhar", "marksheet", "photo", "bank_passbook"]


# ── Extracted Data ──────────────────────────────────────────────────────────

class ExtractedDeadline(BaseModel):
    raw_text:   str
    date_str:   Optional[str]  = None   # normalised "DD/MM/YYYY" if parseable
    label:      str            = ""     # "last date", "submission deadline", …
    confidence: float          = 0.0

class ExtractedData(BaseModel):
    deadlines:         list[ExtractedDeadline] = Field(default_factory=list)
    required_docs:     list[str]               = Field(default_factory=list)
    eligibility:       list[str]               = Field(default_factory=list)
    instructions:      list[str]               = Field(default_factory=list)
    stipend:           Optional[str]           = None
    ambiguous_phrases: list[str]               = Field(default_factory=list)
    source_lines:      list[str]               = Field(default_factory=list)
    # filtered lines (used as AI input)


# ── Confidence Scores ───────────────────────────────────────────────────────

class ConfidenceScores(BaseModel):
    deadline_score:    float = 0.0
    doc_score:         float = 0.0
    eligibility_score: float = 0.0
    overall:           float = 0.0


# ── Rule Engine outputs ─────────────────────────────────────────────────────

class DocMatchResult(BaseModel):
    doc_name: str
    status:   ChecklistStatus

class EligibilityResult(BaseModel):
    rule:      str
    eligible:  bool
    reason:    str = ""

class DeadlineRiskResult(BaseModel):
    label:         str
    date_str:      str
    days_remaining: Optional[int]
    risk:          DeadlineRisk


# ── Output ──────────────────────────────────────────────────────────────────

class ChecklistItem(BaseModel):
    task:     str
    status:   ChecklistStatus
    category: str            # "documents" | "eligibility" | "submission"

class Alert(BaseModel):
    message:  str
    severity: AlertSeverity
    category: str

class TimelineEntry(BaseModel):
    date_str:       str
    task:           str
    days_remaining: Optional[int]
    risk:           DeadlineRisk


# ── Job / Result ────────────────────────────────────────────────────────────

class JobResult(BaseModel):
    job_id:          str
    status:          JobStatus
    extracted:       Optional[ExtractedData]        = None
    confidence:      Optional[ConfidenceScores]     = None
    checklist:       list[ChecklistItem]            = Field(default_factory=list)
    alerts:          list[Alert]                    = Field(default_factory=list)
    timeline:        list[TimelineEntry]            = Field(default_factory=list)
    ai_was_used:     bool                           = False
    error:           Optional[str]                  = None


# ── Request bodies ──────────────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    job_id:  str
    profile: UserProfile
