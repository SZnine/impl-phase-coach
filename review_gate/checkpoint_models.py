from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self

from review_gate.domain import JsonSerializable


def _coerce_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, tuple):
        items = list(value)
    else:
        items = [value]
    return [str(item) for item in items]


def _coerce_payload_dict(value: Any) -> dict[str, Any]:
    if value is None or not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _coerce_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            request_id=_coerce_str(payload["request_id"]),
            request_type=_coerce_str(payload.get("request_type"), ""),
            project_id=_coerce_str(payload.get("project_id"), ""),
            stage_id=_coerce_str(payload.get("stage_id"), ""),
            requested_by=_coerce_str(payload.get("requested_by"), ""),
            source=_coerce_str(payload.get("source"), ""),
            status=_coerce_str(payload.get("status"), ""),
            created_at=_coerce_str(payload.get("created_at"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            run_id=_coerce_str(payload["run_id"]),
            request_id=_coerce_str(payload.get("request_id"), ""),
            run_type=_coerce_str(payload.get("run_type"), ""),
            status=_coerce_str(payload.get("status"), ""),
            started_at=_coerce_str(payload.get("started_at"), ""),
            finished_at=_coerce_optional_str(payload.get("finished_at")),
            supersedes_run_id=_coerce_optional_str(payload.get("supersedes_run_id")),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            question_batch_id=_coerce_str(payload["question_batch_id"]),
            workflow_run_id=_coerce_str(payload.get("workflow_run_id"), ""),
            project_id=_coerce_str(payload.get("project_id"), ""),
            stage_id=_coerce_str(payload.get("stage_id"), ""),
            generated_by=_coerce_str(payload.get("generated_by"), ""),
            source=_coerce_str(payload.get("source"), ""),
            batch_goal=_coerce_str(payload.get("batch_goal"), ""),
            entry_question_id=_coerce_str(payload.get("entry_question_id"), ""),
            status=_coerce_str(payload.get("status"), ""),
            created_at=_coerce_str(payload.get("created_at"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            question_id=_coerce_str(payload["question_id"]),
            question_batch_id=_coerce_str(payload.get("question_batch_id"), ""),
            question_type=_coerce_str(payload.get("question_type"), ""),
            prompt=_coerce_str(payload.get("prompt"), ""),
            intent=_coerce_str(payload.get("intent"), ""),
            difficulty_level=_coerce_str(payload.get("difficulty_level"), ""),
            order_index=_coerce_int(payload.get("order_index"), 0),
            status=_coerce_str(payload.get("status"), ""),
            created_at=_coerce_str(payload.get("created_at"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            answer_batch_id=_coerce_str(payload["answer_batch_id"]),
            question_batch_id=_coerce_str(payload.get("question_batch_id"), ""),
            workflow_run_id=_coerce_str(payload.get("workflow_run_id"), ""),
            submitted_by=_coerce_str(payload.get("submitted_by"), ""),
            submission_mode=_coerce_str(payload.get("submission_mode"), ""),
            completion_status=_coerce_str(payload.get("completion_status"), ""),
            submitted_at=_coerce_str(payload.get("submitted_at"), ""),
            status=_coerce_str(payload.get("status"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            answer_item_id=_coerce_str(payload["answer_item_id"]),
            answer_batch_id=_coerce_str(payload.get("answer_batch_id"), ""),
            question_id=_coerce_str(payload.get("question_id"), ""),
            answered_by=_coerce_str(payload.get("answered_by"), ""),
            answer_text=_coerce_str(payload.get("answer_text"), ""),
            answer_format=_coerce_str(payload.get("answer_format"), ""),
            order_index=_coerce_int(payload.get("order_index"), 0),
            answered_at=_coerce_str(payload.get("answered_at"), ""),
            status=_coerce_str(payload.get("status"), ""),
            revision_of_answer_item_id=_coerce_optional_str(payload.get("revision_of_answer_item_id")),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            evaluation_batch_id=_coerce_str(payload["evaluation_batch_id"]),
            answer_batch_id=_coerce_str(payload.get("answer_batch_id"), ""),
            workflow_run_id=_coerce_str(payload.get("workflow_run_id"), ""),
            project_id=_coerce_str(payload.get("project_id"), ""),
            stage_id=_coerce_str(payload.get("stage_id"), ""),
            evaluated_by=_coerce_str(payload.get("evaluated_by"), ""),
            evaluator_version=_coerce_str(payload.get("evaluator_version"), ""),
            confidence=_coerce_float(payload.get("confidence"), 0.0),
            status=_coerce_str(payload.get("status"), ""),
            evaluated_at=_coerce_str(payload.get("evaluated_at"), ""),
            supersedes_evaluation_batch_id=_coerce_optional_str(payload.get("supersedes_evaluation_batch_id")),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            evaluation_item_id=_coerce_str(payload["evaluation_item_id"]),
            evaluation_batch_id=_coerce_str(payload.get("evaluation_batch_id"), ""),
            question_id=_coerce_str(payload.get("question_id"), ""),
            answer_item_id=_coerce_str(payload.get("answer_item_id"), ""),
            local_verdict=_coerce_str(payload.get("local_verdict"), ""),
            confidence=_coerce_float(payload.get("confidence"), 0.0),
            status=_coerce_str(payload.get("status"), ""),
            evaluated_at=_coerce_str(payload.get("evaluated_at"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            evidence_span_id=_coerce_str(payload["evidence_span_id"]),
            evaluation_item_id=_coerce_str(payload.get("evaluation_item_id"), ""),
            answer_item_id=_coerce_str(payload.get("answer_item_id"), ""),
            span_type=_coerce_str(payload.get("span_type"), ""),
            supports_dimension=_coerce_str(payload.get("supports_dimension"), ""),
            content=_coerce_str(payload.get("content"), ""),
            start_offset=(
                None if payload.get("start_offset") is None else _coerce_int(payload.get("start_offset"), 0)
            ),
            end_offset=(
                None if payload.get("end_offset") is None else _coerce_int(payload.get("end_offset"), 0)
            ),
            created_at=_coerce_str(payload.get("created_at"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            assessment_fact_batch_id=_coerce_str(payload["assessment_fact_batch_id"]),
            evaluation_batch_id=_coerce_str(payload.get("evaluation_batch_id"), ""),
            workflow_run_id=_coerce_str(payload.get("workflow_run_id"), ""),
            synthesized_by=_coerce_str(payload.get("synthesized_by"), ""),
            synthesizer_version=_coerce_str(payload.get("synthesizer_version"), ""),
            status=_coerce_str(payload.get("status"), ""),
            synthesized_at=_coerce_str(payload.get("synthesized_at"), ""),
            supersedes_assessment_fact_batch_id=_coerce_optional_str(
                payload.get("supersedes_assessment_fact_batch_id")
            ),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            assessment_fact_item_id=_coerce_str(payload["assessment_fact_item_id"]),
            assessment_fact_batch_id=_coerce_str(payload.get("assessment_fact_batch_id"), ""),
            source_evaluation_item_id=_coerce_optional_str(payload.get("source_evaluation_item_id")),
            fact_type=_coerce_str(payload.get("fact_type"), ""),
            topic_key=_coerce_str(payload.get("topic_key"), ""),
            title=_coerce_str(payload.get("title"), ""),
            confidence=_coerce_float(payload.get("confidence"), 0.0),
            status=_coerce_str(payload.get("status"), ""),
            created_at=_coerce_str(payload.get("created_at"), ""),
            supersedes_assessment_fact_item_id=_coerce_optional_str(
                payload.get("supersedes_assessment_fact_item_id")
            ),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


@dataclass(slots=True)
class KnowledgeSignalRecord(JsonSerializable):
    signal_id: str
    assessment_fact_batch_id: str
    assessment_fact_item_id: str
    source_evaluation_item_id: str | None
    signal_type: str
    topic_key: str
    polarity: str
    summary: str
    confidence: float
    status: str
    projector_version: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            signal_id=_coerce_str(payload["signal_id"]),
            assessment_fact_batch_id=_coerce_str(payload.get("assessment_fact_batch_id"), ""),
            assessment_fact_item_id=_coerce_str(payload.get("assessment_fact_item_id"), ""),
            source_evaluation_item_id=_coerce_optional_str(payload.get("source_evaluation_item_id")),
            signal_type=_coerce_str(payload.get("signal_type"), ""),
            topic_key=_coerce_str(payload.get("topic_key"), ""),
            polarity=_coerce_str(payload.get("polarity"), ""),
            summary=_coerce_str(payload.get("summary"), ""),
            confidence=_coerce_float(payload.get("confidence"), 0.0),
            status=_coerce_str(payload.get("status"), ""),
            projector_version=_coerce_str(payload.get("projector_version"), ""),
            created_at=_coerce_str(payload.get("created_at"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


@dataclass(slots=True)
class GraphRevisionRecord(JsonSerializable):
    graph_revision_id: str
    project_id: str
    scope_type: str
    scope_ref: str
    revision_type: str
    based_on_revision_id: str | None
    source_fact_batch_ids: list[str]
    source_signal_ids: list[str]
    status: str
    revision_summary: str
    node_count: int
    relation_count: int
    created_by: str
    created_at: str
    activated_at: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            graph_revision_id=_coerce_str(payload["graph_revision_id"]),
            project_id=_coerce_str(payload.get("project_id"), ""),
            scope_type=_coerce_str(payload.get("scope_type"), ""),
            scope_ref=_coerce_str(payload.get("scope_ref"), ""),
            revision_type=_coerce_str(payload.get("revision_type"), ""),
            based_on_revision_id=_coerce_optional_str(payload.get("based_on_revision_id")),
            source_fact_batch_ids=_coerce_str_list(payload.get("source_fact_batch_ids")),
            source_signal_ids=_coerce_str_list(payload.get("source_signal_ids")),
            status=_coerce_str(payload.get("status"), ""),
            revision_summary=_coerce_str(payload.get("revision_summary"), ""),
            node_count=_coerce_int(payload.get("node_count"), 0),
            relation_count=_coerce_int(payload.get("relation_count"), 0),
            created_by=_coerce_str(payload.get("created_by"), ""),
            created_at=_coerce_str(payload.get("created_at"), ""),
            activated_at=_coerce_optional_str(payload.get("activated_at")),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


@dataclass(slots=True)
class KnowledgeNodeRecord(JsonSerializable):
    knowledge_node_id: str
    graph_revision_id: str
    topic_key: str
    label: str
    node_type: str
    description: str
    source_signal_ids: list[str]
    supporting_fact_ids: list[str]
    confidence: float
    status: str
    created_by: str
    created_at: str
    updated_at: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            knowledge_node_id=_coerce_str(payload["knowledge_node_id"]),
            graph_revision_id=_coerce_str(payload.get("graph_revision_id"), ""),
            topic_key=_coerce_str(payload.get("topic_key"), ""),
            label=_coerce_str(payload.get("label"), ""),
            node_type=_coerce_str(payload.get("node_type"), ""),
            description=_coerce_str(payload.get("description"), ""),
            source_signal_ids=_coerce_str_list(payload.get("source_signal_ids")),
            supporting_fact_ids=_coerce_str_list(payload.get("supporting_fact_ids")),
            confidence=_coerce_float(payload.get("confidence"), 0.0),
            status=_coerce_str(payload.get("status"), ""),
            created_by=_coerce_str(payload.get("created_by"), ""),
            created_at=_coerce_str(payload.get("created_at"), ""),
            updated_at=_coerce_str(payload.get("updated_at"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


@dataclass(slots=True)
class KnowledgeRelationRecord(JsonSerializable):
    knowledge_relation_id: str
    graph_revision_id: str
    from_node_id: str
    to_node_id: str
    relation_type: str
    directionality: str
    description: str
    source_signal_ids: list[str]
    supporting_fact_ids: list[str]
    confidence: float
    status: str
    created_by: str
    created_at: str
    updated_at: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            knowledge_relation_id=_coerce_str(payload["knowledge_relation_id"]),
            graph_revision_id=_coerce_str(payload.get("graph_revision_id"), ""),
            from_node_id=_coerce_str(payload.get("from_node_id"), ""),
            to_node_id=_coerce_str(payload.get("to_node_id"), ""),
            relation_type=_coerce_str(payload.get("relation_type"), ""),
            directionality=_coerce_str(payload.get("directionality"), ""),
            description=_coerce_str(payload.get("description"), ""),
            source_signal_ids=_coerce_str_list(payload.get("source_signal_ids")),
            supporting_fact_ids=_coerce_str_list(payload.get("supporting_fact_ids")),
            confidence=_coerce_float(payload.get("confidence"), 0.0),
            status=_coerce_str(payload.get("status"), ""),
            created_by=_coerce_str(payload.get("created_by"), ""),
            created_at=_coerce_str(payload.get("created_at"), ""),
            updated_at=_coerce_str(payload.get("updated_at"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


@dataclass(slots=True)
class ActiveGraphRevisionPointerRecord(JsonSerializable):
    project_id: str
    scope_type: str
    scope_ref: str
    active_graph_revision_id: str
    updated_at: str
    updated_by: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            project_id=_coerce_str(payload["project_id"]),
            scope_type=_coerce_str(payload.get("scope_type"), ""),
            scope_ref=_coerce_str(payload.get("scope_ref"), ""),
            active_graph_revision_id=_coerce_str(payload.get("active_graph_revision_id"), ""),
            updated_at=_coerce_str(payload.get("updated_at"), ""),
            updated_by=_coerce_str(payload.get("updated_by"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )
