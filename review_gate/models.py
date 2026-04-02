from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import uuid4


class ReviewMode(str, Enum):
    SIMPLE = "simple"
    DEEP = "deep"


class ReviewSessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    NEEDS_FOLLOW_UP = "needs_follow_up"
    REDIRECTED_TO_LEARNING = "redirected_to_learning"


class ReviewPassState(str, Enum):
    PASS = "pass"
    CONTINUE_PROBING = "continue_probing"
    REDIRECT_TO_LEARNING = "redirect_to_learning"
    FAIL = "fail"


class KnowledgeEntryType(str, Enum):
    ERROR_PATTERN = "error_pattern"
    CAPABILITY_PROFILE = "capability_profile"


class CompactionMode(str, Enum):
    LIGHT = "light"
    DEEP = "deep"


class MaintenanceTaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class ReviewRequest:
    stage_id: str
    stage_summary: str
    candidate_answer: str
    mode: ReviewMode
    trigger_reason: str


@dataclass(slots=True)
class ReviewQuestion:
    question_id: str
    question_type: str
    prompt: str
    severity: str


@dataclass(slots=True)
class ReviewAssessment:
    pass_state: Optional[ReviewPassState]
    confidence: float
    core_gaps: list[str] = field(default_factory=list)
    failure_reason: Optional[str] = None
    allow_next_stage: bool = False
    recommend_learning: bool = False
    learning_recommendations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ReviewSession:
    session_id: str
    stage_id: str
    mode: ReviewMode
    status: ReviewSessionStatus
    questions: list[ReviewQuestion] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    assessment: ReviewAssessment = field(
        default_factory=lambda: ReviewAssessment(pass_state=None, confidence=0.0)
    )


@dataclass(slots=True)
class ReviewSummaryCard:
    stage_id: str
    pass_state: ReviewPassState
    headline: str
    next_step: str


@dataclass(slots=True)
class ReviewReport:
    summary_card: ReviewSummaryCard
    expanded_report: str


@dataclass(slots=True)
class KnowledgeEntry:
    entry_id: str
    entry_type: KnowledgeEntryType
    stage_id: str
    summary: str
    root_cause: str
    avoidance: str
    evidence: list[str] = field(default_factory=list)
    learning_recommendations: list[str] = field(default_factory=list)
    source_assessment: Optional[ReviewAssessment] = None


@dataclass(slots=True)
class CompactionResult:
    entries: list[KnowledgeEntry] = field(default_factory=list)
    merged_entries: list[str] = field(default_factory=list)
    dropped_entries: list[str] = field(default_factory=list)
    compression_reason: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass(slots=True)
class MaintenanceTask:
    task_id: str
    mode: CompactionMode
    status: MaintenanceTaskStatus
    source_entry_count: int


@dataclass(slots=True)
class CompactionPlan:
    mode: CompactionMode
    candidate_entry_ids: list[str] = field(default_factory=list)
    requires_manual_review: bool = False
    strategy_summary: str = ""


@dataclass(slots=True)
class MaintenanceExecution:
    task: MaintenanceTask
    plan: CompactionPlan
    result: CompactionResult


def new_session_id() -> str:
    return f"review-{uuid4()}"


def new_question_id() -> str:
    return f"question-{uuid4()}"


def new_entry_id(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"


def new_task_id() -> str:
    return f"maint-{uuid4()}"
