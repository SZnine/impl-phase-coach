from review_gate.action_dtos import ProposalActionRequest, SubmitAnswerRequest
from review_gate.domain import WorkspaceSession
from review_gate.profile_space_service import ProfileSpaceService
from review_gate.proposal_center_service import ProposalCenterService
from review_gate.review_flow_service import ReviewFlowService
from review_gate.view_dtos import (
    HomeProjectItemDTO,
    HomeViewDTO,
    KnowledgeGraphNodeDTO,
    KnowledgeGraphViewDTO,
    KnowledgeIndexItemDTO,
    KnowledgeIndexViewDTO,
    MistakeItemDTO,
    MistakesViewDTO,
    ProjectViewDTO,
    ProposalActionResponseDTO,
    ProposalItemDTO,
    ProposalsViewDTO,
    QuestionSetViewDTO,
    QuestionViewDTO,
    StageKnowledgeSummaryDTO,
    StageViewDTO,
    SubmitAnswerResponseDTO,
    WorkspaceSessionDTO,
)
from review_gate.workspace_state_store import JsonWorkspaceStateStore


class WorkspaceAPI:
    _DEFAULT_SESSION_ID = "local-workspace-session"

    def __init__(
        self,
        flow: ReviewFlowService,
        profile_space: ProfileSpaceService | None = None,
        proposal_center: ProposalCenterService | None = None,
        session_store: JsonWorkspaceStateStore | None = None,
    ) -> None:
        self._flow = flow
        self._profile_space = profile_space or ProfileSpaceService.for_testing()
        self._proposal_center = proposal_center or ProposalCenterService.for_testing()
        self._session_store = session_store

    def _default_workspace_session(self) -> WorkspaceSession:
        return WorkspaceSession(
            workspace_session_id=self._DEFAULT_SESSION_ID,
            active_panel="questions",
        )

    def _session_to_dto(self, session: WorkspaceSession) -> WorkspaceSessionDTO:
        return WorkspaceSessionDTO(
            workspace_session_id=session.workspace_session_id,
            active_project_id=session.active_project_id,
            active_stage_id=session.active_stage_id,
            active_panel=session.active_panel,
            active_question_set_id=session.active_question_set_id,
            active_question_id=session.active_question_id,
            active_profile_space_id=session.active_profile_space_id,
            active_proposal_center_id=session.active_proposal_center_id,
            last_opened_at=session.last_opened_at,
            filters=dict(session.filters),
        )

    def _sanitize_workspace_session_dto(self, payload: WorkspaceSessionDTO) -> WorkspaceSessionDTO:
        sanitized = WorkspaceSessionDTO(
            workspace_session_id=payload.workspace_session_id,
            active_project_id=payload.active_project_id,
            active_stage_id=payload.active_stage_id,
            active_panel=payload.active_panel,
            active_question_set_id=payload.active_question_set_id,
            active_question_id=payload.active_question_id,
            active_profile_space_id=payload.active_profile_space_id,
            active_proposal_center_id=payload.active_proposal_center_id,
            last_opened_at=payload.last_opened_at,
            filters=dict(payload.filters),
        )

        if sanitized.active_panel in {"mistakes", "knowledge_index", "knowledge_graph", "proposals"}:
            return sanitized

        if not self._flow.project_exists(sanitized.active_project_id):
            sanitized.active_project_id = None
            sanitized.active_stage_id = None
            sanitized.active_question_set_id = None
            sanitized.active_question_id = None
            sanitized.active_panel = "projects"
            return sanitized

        if not self._flow.stage_exists(sanitized.active_project_id, sanitized.active_stage_id):
            sanitized.active_stage_id = None
            sanitized.active_question_set_id = None
            sanitized.active_question_id = None
            sanitized.active_panel = "projects"
            return sanitized

        if not self._flow.question_set_exists(
            sanitized.active_project_id,
            sanitized.active_stage_id,
            sanitized.active_question_set_id,
        ):
            sanitized.active_question_set_id = None
            sanitized.active_question_id = None
            sanitized.active_panel = "questions"
            return sanitized

        if not self._flow.question_exists(
            sanitized.active_project_id,
            sanitized.active_stage_id,
            sanitized.active_question_set_id,
            sanitized.active_question_id,
        ):
            sanitized.active_question_id = None
            sanitized.active_panel = "questions"

        return sanitized

    def get_workspace_session(self) -> WorkspaceSessionDTO:
        session = self._session_store.load() if self._session_store is not None else None
        if session is None:
            session = self._default_workspace_session()
        sanitized = self._sanitize_workspace_session_dto(self._session_to_dto(session))
        if self._session_store is not None:
            persisted = WorkspaceSession(
                workspace_session_id=sanitized.workspace_session_id,
                active_project_id=sanitized.active_project_id,
                active_stage_id=sanitized.active_stage_id,
                active_panel=sanitized.active_panel,
                active_question_set_id=sanitized.active_question_set_id,
                active_question_id=sanitized.active_question_id,
                active_profile_space_id=sanitized.active_profile_space_id,
                active_proposal_center_id=sanitized.active_proposal_center_id,
                last_opened_at=sanitized.last_opened_at,
                filters=dict(sanitized.filters),
            )
            self._session_store.save(persisted)
        return sanitized

    def save_workspace_session(self, payload: WorkspaceSessionDTO) -> WorkspaceSessionDTO:
        sanitized = self._sanitize_workspace_session_dto(payload)
        session = WorkspaceSession(
            workspace_session_id=sanitized.workspace_session_id,
            active_project_id=sanitized.active_project_id,
            active_stage_id=sanitized.active_stage_id,
            active_panel=sanitized.active_panel,
            active_question_set_id=sanitized.active_question_set_id,
            active_question_id=sanitized.active_question_id,
            active_profile_space_id=sanitized.active_profile_space_id,
            active_proposal_center_id=sanitized.active_proposal_center_id,
            last_opened_at=sanitized.last_opened_at,
            filters=dict(sanitized.filters),
        )
        if self._session_store is not None:
            self._session_store.save(session)
        return sanitized

    def get_home_view(self) -> HomeViewDTO:
        projects = []
        total_pending = 0
        for project in self._flow.list_projects():
            project_summary = self._profile_space.get_project_knowledge_summary(project["project_id"])
            pending_count = len(
                [proposal for proposal in self._proposal_center.list_proposals(project_id=project["project_id"]) if proposal["status"] == "pending_review"]
            )
            total_pending += pending_count
            projects.append(
                HomeProjectItemDTO(
                    project_id=project["project_id"],
                    project_label=project["project_label"],
                    project_summary=project["project_summary"],
                    active_stage_id=project["active_stage_id"],
                    active_stage_label=project["active_stage_label"],
                    pending_proposal_count=pending_count,
                    mistake_count=project_summary["mistake_count"],
                    knowledge_entry_count=project_summary["knowledge_entry_count"],
                )
            )
        active_project_id = projects[0].project_id if projects else None
        return HomeViewDTO(
            projects=projects,
            total_count=len(projects),
            pending_proposal_count=total_pending,
            active_project_id=active_project_id,
        )

    def get_project_view(self, project_id: str) -> ProjectViewDTO:
        project_view = self._flow.get_project_view(project_id)
        project_summary = self._profile_space.get_project_knowledge_summary(project_id)
        pending_count = len(
            [proposal for proposal in self._proposal_center.list_proposals(project_id=project_id) if proposal["status"] == "pending_review"]
        )
        return ProjectViewDTO(
            project_id=project_view.project_id,
            project_label=project_view.project_label,
            project_summary=project_view.project_summary,
            active_stage_id=project_view.active_stage_id,
            active_stage_label=project_view.active_stage_label,
            pending_proposal_count=pending_count,
            mistake_count=project_summary["mistake_count"],
            knowledge_entry_count=project_summary["knowledge_entry_count"],
            stages=project_view.stages,
        )

    def get_stage_view(self, project_id: str, stage_id: str) -> StageViewDTO:
        stage_view = self._flow.get_stage_view(project_id, stage_id)
        knowledge_summary = self._profile_space.get_stage_knowledge_summary(project_id, stage_id)
        return StageViewDTO(
            project_id=stage_view.project_id,
            stage_id=stage_view.stage_id,
            stage_label=stage_view.stage_label,
            stage_goal=stage_view.stage_goal,
            status=stage_view.status,
            mastery_status=stage_view.mastery_status,
            active_question_set_id=stage_view.active_question_set_id,
            knowledge_summary=StageKnowledgeSummaryDTO(**knowledge_summary),
        )

    def get_question_set_view(
        self,
        project_id: str,
        stage_id: str,
        question_set_id: str,
    ) -> QuestionSetViewDTO:
        return self._flow.get_question_set_view(project_id, stage_id, question_set_id)

    def get_question_view(
        self,
        project_id: str,
        stage_id: str,
        question_set_id: str,
        question_id: str,
    ) -> QuestionViewDTO:
        return self._flow.get_question_view(project_id, stage_id, question_set_id, question_id)

    def get_mistakes_view(self, project_id: str | None = None, stage_id: str | None = None) -> MistakesViewDTO:
        items = [MistakeItemDTO(**item) for item in self._profile_space.list_mistakes(project_id, stage_id)]
        return MistakesViewDTO(
            project_filter=project_id,
            stage_filter=stage_id,
            items=items,
            total_count=len(items),
        )

    def get_knowledge_index_view(self, project_id: str | None = None, stage_id: str | None = None) -> KnowledgeIndexViewDTO:
        items = [KnowledgeIndexItemDTO(**item) for item in self._profile_space.list_index_entries(project_id, stage_id)]
        return KnowledgeIndexViewDTO(
            project_filter=project_id,
            stage_filter=stage_id,
            items=items,
            total_count=len(items),
        )

    def get_knowledge_graph_view(self, project_id: str | None = None, stage_id: str | None = None) -> KnowledgeGraphViewDTO:
        nodes = [KnowledgeGraphNodeDTO(**item) for item in self._profile_space.list_knowledge_nodes(project_id, stage_id)]
        return KnowledgeGraphViewDTO(
            project_filter=project_id,
            stage_filter=stage_id,
            nodes=nodes,
            total_count=len(nodes),
        )

    def get_proposals_view(self) -> ProposalsViewDTO:
        proposals = self._proposal_center.list_proposals()
        items = [
            ProposalItemDTO(
                proposal_id=proposal["proposal_id"],
                proposal_type=proposal["proposal_type"],
                target_type=proposal["target_type"],
                target_count=len(proposal["target_ids"]),
                status=proposal["status"],
                reason=proposal["reason"],
                preview_summary=proposal["preview_summary"],
                latest_execution_status=proposal.get("latest_execution_status"),
                latest_execution_summary=proposal.get("latest_execution_summary"),
            )
            for proposal in proposals
        ]
        pending_count = sum(1 for proposal in proposals if proposal["status"] == "pending_review")
        return ProposalsViewDTO(items=items, total_count=len(items), pending_count=pending_count)

    def proposal_action(self, request: ProposalActionRequest) -> ProposalActionResponseDTO:
        proposal = self._proposal_center.get_proposal(request.proposal_id)
        selected_target_ids = request.selected_target_ids or list(proposal["target_ids"])
        action = self._proposal_center.record_user_action(request.proposal_id, request.action_type, selected_target_ids)
        execution = self._proposal_center.execute_proposal(request.proposal_id, action["action_id"])
        success = execution["status"] != "failed"
        return ProposalActionResponseDTO(
            request_id=request.request_id,
            success=success,
            action_type=request.action_type,
            result_type="execution_completed" if success else "failed",
            message=execution["summary"],
            refresh_targets=["proposals"],
            proposal_id=request.proposal_id,
            proposal_status=execution["proposal_status"],
            execution_status=execution["status"],
            execution_summary=execution["summary"],
        )

    def submit_answer_action(self, request: SubmitAnswerRequest) -> SubmitAnswerResponseDTO:
        response = self._flow.submit_answer(request)
        if response.success and response.result_type == "assessment_created":
            assessment = self._flow.get_latest_assessment_snapshot(request.project_id, request.stage_id)
            if assessment is not None:
                self._profile_space.sync_from_assessment(request.project_id, request.stage_id, assessment)
        return response
