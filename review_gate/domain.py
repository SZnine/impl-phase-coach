from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import Enum
from json import dumps, loads
from typing import Any, Self


def _to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return {item.name: _to_plain_data(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_to_plain_data(item) for item in value]
    if isinstance(value, tuple):
        return [_to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_plain_data(item) for key, item in value.items()}
    return value


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


def _coerce_dict_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, tuple):
        items = list(value)
    else:
        items = [value]
    return [item for item in items if isinstance(item, dict)]


def _coerce_str_dict(value: Any) -> dict[str, str]:
    if value is None or not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _coerce_payload_dict(value: Any) -> dict[str, Any]:
    if value is None or not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _coerce_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return bool(value)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)



@dataclass(slots=True)
class JsonSerializable:
    def to_dict(self) -> dict[str, Any]:
        return _to_plain_data(self)

    def to_json(self) -> str:
        return dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, payload: str) -> Self:
        return cls.from_dict(loads(payload))


@dataclass(slots=True)
class WorkspaceSession(JsonSerializable):
    workspace_session_id: str
    active_project_id: str | None = None
    active_stage_id: str | None = None
    active_panel: str = "questions"
    active_question_set_id: str | None = None
    active_question_id: str | None = None
    active_profile_space_id: str | None = None
    active_proposal_center_id: str | None = None
    last_opened_at: str = ""
    filters: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            workspace_session_id=_coerce_str(payload["workspace_session_id"]),
            active_project_id=_coerce_optional_str(payload.get("active_project_id")),
            active_stage_id=_coerce_optional_str(payload.get("active_stage_id")),
            active_panel=_coerce_str(payload.get("active_panel"), "questions"),
            active_question_set_id=_coerce_optional_str(payload.get("active_question_set_id")),
            active_question_id=_coerce_optional_str(payload.get("active_question_id")),
            active_profile_space_id=_coerce_optional_str(payload.get("active_profile_space_id")),
            active_proposal_center_id=_coerce_optional_str(payload.get("active_proposal_center_id")),
            last_opened_at=_coerce_str(payload.get("last_opened_at"), ""),
            filters=_coerce_str_dict(payload.get("filters")),
        )


@dataclass(slots=True)
class AnswerFact(JsonSerializable):
    answer_id: str
    request_id: str
    project_id: str
    stage_id: str
    question_set_id: str
    question_id: str
    actor_id: str
    source_page: str
    created_at: str
    answer_text: str
    draft_id: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            answer_id=_coerce_str(payload["answer_id"]),
            request_id=_coerce_str(payload["request_id"]),
            project_id=_coerce_str(payload["project_id"]),
            stage_id=_coerce_str(payload["stage_id"]),
            question_set_id=_coerce_str(payload["question_set_id"]),
            question_id=_coerce_str(payload["question_id"]),
            actor_id=_coerce_str(payload["actor_id"]),
            source_page=_coerce_str(payload["source_page"]),
            created_at=_coerce_str(payload["created_at"]),
            answer_text=_coerce_str(payload["answer_text"]),
            draft_id=_coerce_optional_str(payload.get("draft_id")),
        )


@dataclass(slots=True)
class AssessmentFact(JsonSerializable):
    assessment_id: str
    request_id: str
    answer_id: str
    project_id: str
    stage_id: str
    question_set_id: str
    question_id: str
    verdict: str
    score_total: float
    dimension_scores: dict[str, int]
    core_gaps: list[str]
    misconceptions: list[str]
    confidence: float

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        dimension_scores_payload = payload.get("dimension_scores")
        if not isinstance(dimension_scores_payload, dict):
            dimension_scores_payload = {}
        return cls(
            assessment_id=_coerce_str(payload["assessment_id"]),
            request_id=_coerce_str(payload["request_id"]),
            answer_id=_coerce_str(payload["answer_id"]),
            project_id=_coerce_str(payload["project_id"]),
            stage_id=_coerce_str(payload["stage_id"]),
            question_set_id=_coerce_str(payload["question_set_id"]),
            question_id=_coerce_str(payload["question_id"]),
            verdict=_coerce_str(payload["verdict"]),
            score_total=_coerce_float(payload.get("score_total"), 0.0),
            dimension_scores={str(key): _coerce_int(value, 0) for key, value in dimension_scores_payload.items()},
            core_gaps=_coerce_str_list(payload.get("core_gaps")),
            misconceptions=_coerce_str_list(payload.get("misconceptions")),
            confidence=_coerce_float(payload.get("confidence"), 0.0),
        )


@dataclass(slots=True)
class DecisionFact(JsonSerializable):
    decision_id: str
    request_id: str
    assessment_id: str
    project_id: str
    stage_id: str
    decision_type: str
    decision_value: str
    reason_summary: str
    created_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            decision_id=_coerce_str(payload["decision_id"]),
            request_id=_coerce_str(payload["request_id"]),
            assessment_id=_coerce_str(payload["assessment_id"]),
            project_id=_coerce_str(payload["project_id"]),
            stage_id=_coerce_str(payload["stage_id"]),
            decision_type=_coerce_str(payload["decision_type"]),
            decision_value=_coerce_str(payload["decision_value"]),
            reason_summary=_coerce_str(payload["reason_summary"]),
            created_at=_coerce_str(payload["created_at"]),
        )


@dataclass(slots=True)
class KnowledgeNode(JsonSerializable):
    node_id: str
    profile_space_id: str
    label: str
    node_type: str
    abstract_level: str
    scope: str
    canonical_summary: str
    source_refs: list[str] = field(default_factory=list)
    seed_or_generated: str = "generated"
    status: str = "active"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            node_id=_coerce_str(payload["node_id"]),
            profile_space_id=_coerce_str(payload["profile_space_id"]),
            label=_coerce_str(payload.get("label"), ""),
            node_type=_coerce_str(payload.get("node_type"), ""),
            abstract_level=_coerce_str(payload.get("abstract_level"), ""),
            scope=_coerce_str(payload.get("scope"), ""),
            canonical_summary=_coerce_str(payload.get("canonical_summary"), ""),
            source_refs=_coerce_str_list(payload.get("source_refs")),
            seed_or_generated=_coerce_str(payload.get("seed_or_generated"), "generated"),
            status=_coerce_str(payload.get("status"), "active"),
        )


@dataclass(slots=True)
class EvidenceRef(JsonSerializable):
    evidence_id: str
    profile_space_id: str
    node_id: str
    evidence_type: str
    ref_id: str
    project_id: str
    stage_id: str
    summary: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            evidence_id=_coerce_str(payload["evidence_id"]),
            profile_space_id=_coerce_str(payload["profile_space_id"]),
            node_id=_coerce_str(payload["node_id"]),
            evidence_type=_coerce_str(payload.get("evidence_type"), ""),
            ref_id=_coerce_str(payload.get("ref_id"), ""),
            project_id=_coerce_str(payload.get("project_id"), ""),
            stage_id=_coerce_str(payload.get("stage_id"), ""),
            summary=_coerce_str(payload.get("summary"), ""),
        )


@dataclass(slots=True)
class UserNodeState(JsonSerializable):
    profile_space_id: str
    node_id: str
    activation_status: str = "inactive"
    mastery_status: str = "unverified"
    review_needed: bool = False
    weak_signal_count: int = 0
    linked_project_count: int = 0
    last_seen_at: str | None = None
    confidence: float = 0.0

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            profile_space_id=_coerce_str(payload["profile_space_id"]),
            node_id=_coerce_str(payload["node_id"]),
            activation_status=_coerce_str(payload.get("activation_status"), "inactive"),
            mastery_status=_coerce_str(payload.get("mastery_status"), "unverified"),
            review_needed=_coerce_bool(payload.get("review_needed"), False),
            weak_signal_count=_coerce_int(payload.get("weak_signal_count"), 0),
            linked_project_count=_coerce_int(payload.get("linked_project_count"), 0),
            last_seen_at=_coerce_optional_str(payload.get("last_seen_at")),
            confidence=_coerce_float(payload.get("confidence"), 0.0),
        )


@dataclass(slots=True)
class KnowledgeRelation(JsonSerializable):
    relation_id: str
    profile_space_id: str
    source_node_id: str
    target_node_id: str
    relation_type: str
    strength: int = 1
    evidence_ids: list[str] = field(default_factory=list)
    status: str = "active"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            relation_id=_coerce_str(payload["relation_id"]),
            profile_space_id=_coerce_str(payload["profile_space_id"]),
            source_node_id=_coerce_str(payload.get("source_node_id"), ""),
            target_node_id=_coerce_str(payload.get("target_node_id"), ""),
            relation_type=_coerce_str(payload.get("relation_type"), ""),
            strength=_coerce_int(payload.get("strength"), 1),
            evidence_ids=_coerce_str_list(payload.get("evidence_ids")),
            status=_coerce_str(payload.get("status"), "active"),
        )


@dataclass(slots=True)
class FocusCluster(JsonSerializable):
    cluster_id: str
    profile_space_id: str
    title: str
    center_node_id: str
    neighbor_node_ids: list[str] = field(default_factory=list)
    focus_reason_codes: list[str] = field(default_factory=list)
    focus_reason_summary: str = ""
    generated_from: str = "system"
    confidence: float = 0.0
    last_generated_at: str = ""
    is_pinned: bool = False
    status: str = "active"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            cluster_id=_coerce_str(payload["cluster_id"]),
            profile_space_id=_coerce_str(payload["profile_space_id"]),
            title=_coerce_str(payload.get("title"), ""),
            center_node_id=_coerce_str(payload.get("center_node_id"), ""),
            neighbor_node_ids=_coerce_str_list(payload.get("neighbor_node_ids")),
            focus_reason_codes=_coerce_str_list(payload.get("focus_reason_codes")),
            focus_reason_summary=_coerce_str(payload.get("focus_reason_summary"), ""),
            generated_from=_coerce_str(payload.get("generated_from"), "system"),
            confidence=_coerce_float(payload.get("confidence"), 0.0),
            last_generated_at=_coerce_str(payload.get("last_generated_at"), ""),
            is_pinned=_coerce_bool(payload.get("is_pinned"), False),
            status=_coerce_str(payload.get("status"), "active"),
        )


@dataclass(slots=True)
class QuestionSet(JsonSerializable):
    question_set_id: str
    stage_review_id: str
    title: str = ""
    status: str = "active"
    question_ids: list[str] = field(default_factory=list)
    active_question_id: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            question_set_id=_coerce_str(payload["question_set_id"]),
            stage_review_id=_coerce_str(payload["stage_review_id"]),
            title=_coerce_str(payload.get("title"), ""),
            status=_coerce_str(payload.get("status"), "active"),
            question_ids=_coerce_str_list(payload.get("question_ids")),
            active_question_id=_coerce_optional_str(payload.get("active_question_id")),
        )


@dataclass(slots=True)
class StageReview(JsonSerializable):
    stage_review_id: str
    project_id: str
    stage_id: str
    stage_label: str
    stage_goal: str
    status: str
    question_set_ids: list[str] = field(default_factory=list)
    active_question_set_id: str | None = None
    history_count: int = 0
    retention_status: str = "active"
    related_mistake_ids: list[str] = field(default_factory=list)
    related_knowledge_node_ids: list[str] = field(default_factory=list)
    related_index_entry_ids: list[str] = field(default_factory=list)
    related_proposal_ids: list[str] = field(default_factory=list)
    mastery_status: str = "unverified"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            stage_review_id=_coerce_str(payload["stage_review_id"]),
            project_id=_coerce_str(payload["project_id"]),
            stage_id=_coerce_str(payload["stage_id"]),
            stage_label=_coerce_str(payload.get("stage_label"), ""),
            stage_goal=_coerce_str(payload.get("stage_goal"), ""),
            status=_coerce_str(payload.get("status"), ""),
            question_set_ids=_coerce_str_list(payload.get("question_set_ids")),
            active_question_set_id=_coerce_optional_str(payload.get("active_question_set_id")),
            history_count=_coerce_int(payload.get("history_count"), 0),
            retention_status=_coerce_str(payload.get("retention_status"), "active"),
            related_mistake_ids=_coerce_str_list(payload.get("related_mistake_ids")),
            related_knowledge_node_ids=_coerce_str_list(payload.get("related_knowledge_node_ids")),
            related_index_entry_ids=_coerce_str_list(payload.get("related_index_entry_ids")),
            related_proposal_ids=_coerce_str_list(payload.get("related_proposal_ids")),
            mastery_status=_coerce_str(payload.get("mastery_status"), "unverified"),
        )


@dataclass(slots=True)
class ProjectReview(JsonSerializable):
    project_id: str
    project_label: str
    project_summary: str
    stage_reviews: list[StageReview] = field(default_factory=list)
    knowledge_index_id: str | None = None
    knowledge_graph_id: str | None = None
    profile_space_id: str | None = None
    proposal_center_id: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            project_id=_coerce_str(payload["project_id"]),
            project_label=_coerce_str(payload.get("project_label"), ""),
            project_summary=_coerce_str(payload.get("project_summary"), ""),
            stage_reviews=[StageReview.from_dict(item) for item in _coerce_dict_list(payload.get("stage_reviews"))],
            knowledge_index_id=_coerce_optional_str(payload.get("knowledge_index_id")),
            knowledge_graph_id=_coerce_optional_str(payload.get("knowledge_graph_id")),
            profile_space_id=_coerce_optional_str(payload.get("profile_space_id")),
            proposal_center_id=_coerce_optional_str(payload.get("proposal_center_id")),
        )


@dataclass(slots=True)
class ProfileSpace(JsonSerializable):
    profile_space_id: str
    project_id: str
    label: str = ""
    summary: str = ""
    mistake_ids: list[str] = field(default_factory=list)
    index_entry_ids: list[str] = field(default_factory=list)
    knowledge_node_ids: list[str] = field(default_factory=list)
    proposal_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            profile_space_id=_coerce_str(payload["profile_space_id"]),
            project_id=_coerce_str(payload["project_id"]),
            label=_coerce_str(payload.get("label"), ""),
            summary=_coerce_str(payload.get("summary"), ""),
            mistake_ids=_coerce_str_list(payload.get("mistake_ids")),
            index_entry_ids=_coerce_str_list(payload.get("index_entry_ids")),
            knowledge_node_ids=_coerce_str_list(payload.get("knowledge_node_ids")),
            proposal_ids=_coerce_str_list(payload.get("proposal_ids")),
        )


@dataclass(slots=True)
class ProposalCenter(JsonSerializable):
    proposal_center_id: str
    project_id: str
    proposal_ids: list[str] = field(default_factory=list)
    active_proposal_id: str | None = None
    status: str = "active"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            proposal_center_id=_coerce_str(payload["proposal_center_id"]),
            project_id=_coerce_str(payload["project_id"]),
            proposal_ids=_coerce_str_list(payload.get("proposal_ids")),
            active_proposal_id=_coerce_optional_str(payload.get("active_proposal_id")),
            status=_coerce_str(payload.get("status"), "active"),
        )


@dataclass(slots=True)
class WorkspaceEvent(JsonSerializable):
    event_id: str
    project_id: str | None
    event_type: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            event_id=_coerce_str(payload["event_id"]),
            project_id=_coerce_optional_str(payload.get("project_id")),
            event_type=_coerce_str(payload["event_type"]),
            created_at=_coerce_str(payload["created_at"]),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


def current_utc_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"




