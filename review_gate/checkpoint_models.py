from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from review_gate.domain import JsonSerializable


@dataclass(slots=True)
class WorkflowRequestRecord(JsonSerializable):
    request_id: str
    request_type: str
    project_id: str
    stage_id: str
    requested_by: str
    source: str
    status: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowRunRecord(JsonSerializable):
    run_id: str
    request_id: str
    run_type: str
    status: str
    started_at: str
    finished_at: str | None = None
    supersedes_run_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QuestionBatchRecord(JsonSerializable):
    question_batch_id: str
    workflow_run_id: str
    project_id: str
    stage_id: str
    generated_by: str
    source: str
    batch_goal: str
    entry_question_id: str
    status: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QuestionItemRecord(JsonSerializable):
    question_id: str
    question_batch_id: str
    question_type: str
    prompt: str
    intent: str
    difficulty_level: str
    order_index: int
    status: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AnswerBatchRecord(JsonSerializable):
    answer_batch_id: str
    question_batch_id: str
    workflow_run_id: str
    submitted_by: str
    submission_mode: str
    completion_status: str
    submitted_at: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AnswerItemRecord(JsonSerializable):
    answer_item_id: str
    answer_batch_id: str
    question_id: str
    answered_by: str
    answer_text: str
    answer_format: str
    order_index: int
    answered_at: str
    status: str
    revision_of_answer_item_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationBatchRecord(JsonSerializable):
    evaluation_batch_id: str
    answer_batch_id: str
    workflow_run_id: str
    project_id: str
    stage_id: str
    evaluated_by: str
    evaluator_version: str
    confidence: float
    status: str
    evaluated_at: str
    supersedes_evaluation_batch_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationItemRecord(JsonSerializable):
    evaluation_item_id: str
    evaluation_batch_id: str
    question_id: str
    answer_item_id: str
    local_verdict: str
    confidence: float
    status: str
    evaluated_at: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvidenceSpanRecord(JsonSerializable):
    evidence_span_id: str
    evaluation_item_id: str
    answer_item_id: str
    span_type: str
    supports_dimension: str
    content: str
    start_offset: int | None
    end_offset: int | None
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AssessmentFactBatchRecord(JsonSerializable):
    assessment_fact_batch_id: str
    evaluation_batch_id: str
    workflow_run_id: str
    synthesized_by: str
    synthesizer_version: str
    status: str
    synthesized_at: str
    supersedes_assessment_fact_batch_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AssessmentFactItemRecord(JsonSerializable):
    assessment_fact_item_id: str
    assessment_fact_batch_id: str
    source_evaluation_item_id: str | None
    fact_type: str
    topic_key: str
    title: str
    confidence: float
    status: str
    created_at: str
    supersedes_assessment_fact_item_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
