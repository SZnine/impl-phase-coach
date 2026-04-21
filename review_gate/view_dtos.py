from __future__ import annotations

from dataclasses import dataclass, field

from review_gate.action_dtos import TransportModel


@dataclass(slots=True)
class WorkspaceSessionDTO(TransportModel):
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


@dataclass(slots=True)
class StageKnowledgeSummaryDTO(TransportModel):
    knowledge_entry_count: int
    mistake_count: int
    latest_summary: str


@dataclass(slots=True)
class HomeProjectItemDTO(TransportModel):
    project_id: str
    project_label: str
    project_summary: str
    active_stage_id: str
    active_stage_label: str
    pending_proposal_count: int
    mistake_count: int
    knowledge_entry_count: int


@dataclass(slots=True)
class HomeViewDTO(TransportModel):
    projects: list[HomeProjectItemDTO] = field(default_factory=list)
    total_count: int = 0
    pending_proposal_count: int = 0
    active_project_id: str | None = None


@dataclass(slots=True)
class ProjectStageItemDTO(TransportModel):
    stage_id: str
    stage_label: str
    status: str
    mastery_status: str
    active_question_set_id: str | None = None


@dataclass(slots=True)
class ProjectViewDTO(TransportModel):
    project_id: str
    project_label: str
    project_summary: str
    active_stage_id: str
    active_stage_label: str
    pending_proposal_count: int
    mistake_count: int
    knowledge_entry_count: int
    stages: list[ProjectStageItemDTO] = field(default_factory=list)


@dataclass(slots=True)
class MistakeItemDTO(TransportModel):
    mistake_id: str
    label: str
    mistake_type: str
    project_id: str
    stage_id: str
    root_cause_summary: str
    avoidance_summary: str
    status: str = "active"


@dataclass(slots=True)
class MistakesViewDTO(TransportModel):
    project_filter: str | None = None
    stage_filter: str | None = None
    items: list[MistakeItemDTO] = field(default_factory=list)
    total_count: int = 0


@dataclass(slots=True)
class KnowledgeIndexItemDTO(TransportModel):
    entry_id: str
    title: str
    entry_type: str
    summary: str
    project_id: str
    stage_id: str
    linked_mistake_ids: list[str] = field(default_factory=list)
    status: str = "active"


@dataclass(slots=True)
class KnowledgeIndexViewDTO(TransportModel):
    project_filter: str | None = None
    stage_filter: str | None = None
    items: list[KnowledgeIndexItemDTO] = field(default_factory=list)
    total_count: int = 0


@dataclass(slots=True)
class KnowledgeGraphNodeDTO(TransportModel):
    node_id: str
    label: str
    node_type: str
    project_id: str
    stage_id: str
    strength: int
    linked_mistake_ids: list[str] = field(default_factory=list)
    summary: str = ""
    status: str = "active"


@dataclass(slots=True)
class KnowledgeGraphViewDTO(TransportModel):
    project_filter: str | None = None
    stage_filter: str | None = None
    nodes: list[KnowledgeGraphNodeDTO] = field(default_factory=list)
    total_count: int = 0


@dataclass(slots=True)
class FocusClusterCardDTO(TransportModel):
    cluster_id: str
    title: str
    center_node_id: str
    neighbor_node_ids: list[str] = field(default_factory=list)
    focus_reason_codes: list[str] = field(default_factory=list)
    focus_reason_summary: str = ""


@dataclass(slots=True)
class KnowledgeMapSummaryViewDTO(TransportModel):
    focus_clusters: list[FocusClusterCardDTO] = field(default_factory=list)
    current_weak_spots: list[str] = field(default_factory=list)
    foundation_hotspots: list[str] = field(default_factory=list)


@dataclass(slots=True)
class KnowledgeNodeCardDTO(TransportModel):
    node_id: str
    label: str
    node_type: str
    abstract_level: str
    scope: str
    canonical_summary: str
    mastery_status: str
    review_needed: bool
    relation_preview: list[dict[str, str]] = field(default_factory=list)
    evidence_summary: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class KnowledgeGraphMainViewDTO(TransportModel):
    selected_cluster: FocusClusterCardDTO | None = None
    nodes: list[KnowledgeNodeCardDTO] = field(default_factory=list)
    relations: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class GraphRevisionSummaryDTO(TransportModel):
    graph_revision_id: str
    project_id: str
    scope_type: str
    scope_ref: str
    revision_type: str
    status: str
    node_count: int
    relation_count: int
    source_fact_batch_ids: list[str] = field(default_factory=list)
    source_signal_ids: list[str] = field(default_factory=list)
    created_by: str = ""
    created_at: str = ""
    activated_at: str = ""
    revision_summary: str = ""


@dataclass(slots=True)
class GraphRevisionNodeDTO(TransportModel):
    knowledge_node_id: str
    graph_revision_id: str
    topic_key: str
    label: str
    node_type: str
    description: str
    source_signal_ids: list[str] = field(default_factory=list)
    supporting_fact_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "active"
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class GraphRevisionRelationDTO(TransportModel):
    knowledge_relation_id: str
    graph_revision_id: str
    from_node_id: str
    to_node_id: str
    relation_type: str
    directionality: str
    description: str
    source_signal_ids: list[str] = field(default_factory=list)
    supporting_fact_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "active"
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class GraphRevisionViewDTO(TransportModel):
    project_id: str
    stage_id: str
    has_active_revision: bool = False
    revision: GraphRevisionSummaryDTO | None = None
    nodes: list[GraphRevisionNodeDTO] = field(default_factory=list)
    relations: list[GraphRevisionRelationDTO] = field(default_factory=list)


@dataclass(slots=True)
class ProposalItemDTO(TransportModel):
    proposal_id: str
    proposal_type: str
    target_type: str
    target_count: int
    status: str
    reason: str
    preview_summary: str
    latest_execution_status: str | None = None
    latest_execution_summary: str | None = None


@dataclass(slots=True)
class ProposalsViewDTO(TransportModel):
    items: list[ProposalItemDTO] = field(default_factory=list)
    total_count: int = 0
    pending_count: int = 0


@dataclass(slots=True)
class ProposalActionResponseDTO(TransportModel):
    request_id: str
    success: bool
    action_type: str
    result_type: str
    message: str
    refresh_targets: list[str]
    proposal_id: str
    proposal_status: str
    execution_status: str | None = None
    execution_summary: str | None = None


@dataclass(slots=True)
class StageViewDTO(TransportModel):
    project_id: str
    stage_id: str
    stage_label: str
    stage_goal: str
    status: str
    mastery_status: str
    active_question_set_id: str | None = None
    knowledge_summary: StageKnowledgeSummaryDTO | None = None


@dataclass(slots=True)
class QuestionSummaryDTO(TransportModel):
    question_id: str
    question_level: str
    prompt: str
    status: str = "ready"


@dataclass(slots=True)
class QuestionSetViewDTO(TransportModel):
    project_id: str
    stage_id: str
    question_set_id: str
    question_set_title: str
    status: str
    question_count: int
    current_question_id: str | None
    questions: list[QuestionSummaryDTO] = field(default_factory=list)


@dataclass(slots=True)
class QuestionViewDTO(TransportModel):
    project_id: str
    stage_id: str
    question_set_id: str
    question_id: str
    question_level: str
    prompt: str
    intent: str
    answer_placeholder: str
    allowed_actions: list[str] = field(default_factory=list)
    status: str = "ready"


@dataclass(slots=True)
class AssessmentSummaryDTO(TransportModel):
    assessment_id: str
    project_id: str
    stage_id: str
    question_set_id: str
    question_id: str
    answer_excerpt: str
    status: str = "created"


@dataclass(slots=True)
class SubmitAnswerResponseDTO(TransportModel):
    request_id: str
    success: bool
    action_type: str
    result_type: str
    message: str
    refresh_targets: list[str]
    assessment_summary: AssessmentSummaryDTO | None = None
