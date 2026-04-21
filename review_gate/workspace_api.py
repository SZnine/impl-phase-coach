from review_gate.action_dtos import ProposalActionRequest, SubmitAnswerRequest
from review_gate.domain import WorkspaceSession
from review_gate.profile_space_service import ProfileSpaceService
from review_gate.proposal_center_service import ProposalCenterService
from review_gate.review_flow_service import ReviewFlowService
from review_gate.storage_sqlite import SQLiteStore
from review_gate.view_dtos import (
    GraphRevisionNodeDTO,
    GraphRevisionRelationDTO,
    GraphRevisionSummaryDTO,
    GraphRevisionViewDTO,
    HomeProjectItemDTO,
    HomeViewDTO,
    FocusClusterCardDTO,
    KnowledgeGraphMainViewDTO,
    KnowledgeGraphNodeDTO,
    KnowledgeGraphViewDTO,
    KnowledgeIndexItemDTO,
    KnowledgeIndexViewDTO,
    KnowledgeMapSummaryViewDTO,
    KnowledgeNodeCardDTO,
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
    _FOCUS_REASON_PRIORITY = {
        "weak_signal_active": 0,
        "current_project_hit": 1,
        "foundation_hot": 2,
        "recently_changed": 3,
        "high_structural_importance": 4,
        "cross_project_reuse": 5,
    }

    def __init__(
        self,
        flow: ReviewFlowService,
        profile_space: ProfileSpaceService | None = None,
        proposal_center: ProposalCenterService | None = None,
        session_store: JsonWorkspaceStateStore | None = None,
        checkpoint_store: SQLiteStore | None = None,
    ) -> None:
        self._flow = flow
        self._profile_space = profile_space or ProfileSpaceService.for_testing()
        self._proposal_center = proposal_center or ProposalCenterService.for_testing()
        self._session_store = session_store
        self._checkpoint_store = checkpoint_store

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

    def get_knowledge_map_summary_view(
        self,
        project_id: str | None = None,
        stage_id: str | None = None,
    ) -> KnowledgeMapSummaryViewDTO:
        focus_cluster_items = self._profile_space.list_focus_clusters(project_id, stage_id)
        focus_cluster_items.sort(key=self._focus_cluster_sort_key)
        focus_clusters = [
            FocusClusterCardDTO(
                cluster_id=item["cluster_id"],
                title=item["title"],
                center_node_id=item["center_node_id"],
                neighbor_node_ids=list(item.get("neighbor_node_ids", [])),
                focus_reason_codes=list(item.get("focus_reason_codes", [])),
                focus_reason_summary=self._focus_reason_summary(item, project_id=project_id),
            )
            for item in focus_cluster_items
        ]
        nodes = self._profile_space.list_map_nodes(project_id, stage_id)
        states = self._profile_space.list_user_node_states(project_id, stage_id)
        state_by_node_id = {item["node_id"]: item for item in states}

        current_weak_spots: list[str] = []
        for node in nodes:
            if state_by_node_id.get(node["node_id"], {}).get("review_needed") is not True:
                continue
            label = node["label"]
            if label not in current_weak_spots:
                current_weak_spots.append(label)
        foundation_hotspots = [node["label"] for node in nodes if node["node_type"] == "foundation"]
        return KnowledgeMapSummaryViewDTO(
            focus_clusters=focus_clusters,
            current_weak_spots=current_weak_spots,
            foundation_hotspots=foundation_hotspots,
        )

    def _empty_graph_revision_view(self, project_id: str, stage_id: str) -> GraphRevisionViewDTO:
        return GraphRevisionViewDTO(
            project_id=project_id,
            stage_id=stage_id,
            has_active_revision=False,
            revision=None,
            nodes=[],
            relations=[],
        )

    def _graph_revision_summary_to_dto(self, revision) -> GraphRevisionSummaryDTO:
        return GraphRevisionSummaryDTO(
            graph_revision_id=revision.graph_revision_id,
            project_id=revision.project_id,
            scope_type=revision.scope_type,
            scope_ref=revision.scope_ref,
            revision_type=revision.revision_type,
            status=revision.status,
            node_count=revision.node_count,
            relation_count=revision.relation_count,
            source_fact_batch_ids=list(revision.source_fact_batch_ids),
            source_signal_ids=list(revision.source_signal_ids),
            created_by=revision.created_by,
            created_at=revision.created_at,
            activated_at=revision.activated_at,
            revision_summary=revision.revision_summary,
        )

    def _graph_revision_node_to_dto(self, node) -> GraphRevisionNodeDTO:
        return GraphRevisionNodeDTO(
            knowledge_node_id=node.knowledge_node_id,
            graph_revision_id=node.graph_revision_id,
            topic_key=node.topic_key,
            label=node.label,
            node_type=node.node_type,
            description=node.description,
            source_signal_ids=list(node.source_signal_ids),
            supporting_fact_ids=list(node.supporting_fact_ids),
            confidence=node.confidence,
            status=node.status,
            created_by=node.created_by,
            created_at=node.created_at,
            updated_at=node.updated_at,
            payload=dict(node.payload),
        )

    def _graph_revision_relation_to_dto(self, relation) -> GraphRevisionRelationDTO:
        return GraphRevisionRelationDTO(
            knowledge_relation_id=relation.knowledge_relation_id,
            graph_revision_id=relation.graph_revision_id,
            from_node_id=relation.from_node_id,
            to_node_id=relation.to_node_id,
            relation_type=relation.relation_type,
            directionality=relation.directionality,
            description=relation.description,
            source_signal_ids=list(relation.source_signal_ids),
            supporting_fact_ids=list(relation.supporting_fact_ids),
            confidence=relation.confidence,
            status=relation.status,
            created_by=relation.created_by,
            created_at=relation.created_at,
            updated_at=relation.updated_at,
            payload=dict(relation.payload),
        )

    def get_graph_revision_view(self, project_id: str, stage_id: str) -> GraphRevisionViewDTO:
        if self._checkpoint_store is None:
            return self._empty_graph_revision_view(project_id, stage_id)

        pointer = self._checkpoint_store.get_active_graph_revision_pointer(project_id, "stage", stage_id)
        if pointer is None:
            return self._empty_graph_revision_view(project_id, stage_id)

        revision = self._checkpoint_store.get_graph_revision(pointer.active_graph_revision_id)
        if revision is None:
            return self._empty_graph_revision_view(project_id, stage_id)

        nodes = self._checkpoint_store.list_graph_nodes(revision.graph_revision_id)
        relations = self._checkpoint_store.list_graph_relations(revision.graph_revision_id)
        return GraphRevisionViewDTO(
            project_id=project_id,
            stage_id=stage_id,
            has_active_revision=True,
            revision=self._graph_revision_summary_to_dto(revision),
            nodes=[self._graph_revision_node_to_dto(node) for node in nodes],
            relations=[self._graph_revision_relation_to_dto(relation) for relation in relations],
        )

    def _get_active_graph_main_view(
        self,
        project_id: str | None,
        stage_id: str | None,
    ) -> KnowledgeGraphMainViewDTO | None:
        if self._checkpoint_store is None or project_id is None or stage_id is None:
            return None

        pointer = self._checkpoint_store.get_active_graph_revision_pointer(project_id, "stage", stage_id)
        if pointer is None:
            return None

        revision = self._checkpoint_store.get_graph_revision(pointer.active_graph_revision_id)
        if revision is None:
            return None

        nodes = self._checkpoint_store.list_graph_nodes(revision.graph_revision_id)
        if not nodes:
            return None

        relations = self._checkpoint_store.list_graph_relations(revision.graph_revision_id)
        relation_previews_by_node_id = self._graph_main_relation_previews(relations)
        node_cards = [
            KnowledgeNodeCardDTO(
                node_id=node.knowledge_node_id,
                label=node.label,
                node_type=node.node_type,
                abstract_level="topic",
                scope=revision.scope_type,
                canonical_summary=node.description,
                mastery_status="unverified",
                review_needed=node.node_type == "weakness_topic",
                relation_preview=relation_previews_by_node_id.get(node.knowledge_node_id, []),
                evidence_summary={
                    "topic_key": node.topic_key,
                    "confidence_percent": round(node.confidence * 100),
                    "signal_count": len(node.source_signal_ids),
                    "fact_count": len(node.supporting_fact_ids),
                },
            )
            for node in nodes
        ]
        return KnowledgeGraphMainViewDTO(
            selected_cluster=self._active_graph_primary_cluster(
                graph_revision_id=revision.graph_revision_id,
                nodes=nodes,
                relations=relations,
            ),
            nodes=node_cards,
            relations=[self._graph_main_relation_item(relation) for relation in relations],
        )

    def _graph_main_relation_item(self, relation) -> dict[str, object]:
        return {
            "relation_id": relation.knowledge_relation_id,
            "from_node_id": relation.from_node_id,
            "to_node_id": relation.to_node_id,
            "relation_type": relation.relation_type,
            "directionality": relation.directionality,
            "description": relation.description,
            "confidence": relation.confidence,
        }

    def _graph_main_relation_previews(self, relations) -> dict[str, list[dict[str, object]]]:
        previews: dict[str, list[dict[str, object]]] = {}
        for relation in relations:
            outgoing = {
                "relation_id": relation.knowledge_relation_id,
                "direction": "outgoing",
                "other_node_id": relation.to_node_id,
                "relation_type": relation.relation_type,
                "description": relation.description,
            }
            incoming = {
                "relation_id": relation.knowledge_relation_id,
                "direction": "incoming",
                "other_node_id": relation.from_node_id,
                "relation_type": relation.relation_type,
                "description": relation.description,
            }
            previews.setdefault(relation.from_node_id, []).append(outgoing)
            previews.setdefault(relation.to_node_id, []).append(incoming)
        return previews

    def _active_graph_primary_cluster(self, *, graph_revision_id: str, nodes, relations) -> FocusClusterCardDTO | None:
        if not nodes:
            return None
        center_node = self._active_graph_cluster_center(nodes)
        neighbor_node_ids = self._active_graph_neighbor_node_ids(center_node.knowledge_node_id, relations)
        reason_codes = ["weak_signal_active"] if center_node.node_type == "weakness_topic" else ["high_confidence_signal"]
        if neighbor_node_ids:
            reason_codes.append("relation_connected")
        return FocusClusterCardDTO(
            cluster_id=f"fc-{graph_revision_id}-primary",
            title=center_node.label,
            center_node_id=center_node.knowledge_node_id,
            neighbor_node_ids=neighbor_node_ids,
            focus_reason_codes=reason_codes,
            focus_reason_summary=self._active_graph_focus_reason_summary(
                center_label=center_node.label,
                is_weakness=center_node.node_type == "weakness_topic",
                neighbor_count=len(neighbor_node_ids),
            ),
        )

    def _active_graph_cluster_center(self, nodes):
        sorted_nodes = sorted(
            nodes,
            key=lambda node: (
                node.node_type != "weakness_topic",
                -node.confidence,
                node.label,
                node.knowledge_node_id,
            ),
        )
        return sorted_nodes[0]

    def _active_graph_neighbor_node_ids(self, center_node_id: str, relations) -> list[str]:
        neighbor_ids: list[str] = []
        for relation in relations:
            if relation.from_node_id == center_node_id:
                neighbor_id = relation.to_node_id
            elif relation.to_node_id == center_node_id:
                neighbor_id = relation.from_node_id
            else:
                continue
            if neighbor_id not in neighbor_ids:
                neighbor_ids.append(neighbor_id)
        return neighbor_ids

    def _active_graph_focus_reason_summary(
        self,
        *,
        center_label: str,
        is_weakness: bool,
        neighbor_count: int,
    ) -> str:
        if is_weakness:
            summary = f"{center_label} is the active weakness topic in this graph revision"
        else:
            summary = f"{center_label} is the highest-confidence topic in this graph revision"
        if neighbor_count:
            return f"{summary}, with {neighbor_count} related graph nodes."
        return f"{summary}."

    def get_knowledge_graph_main_view(
        self,
        project_id: str | None = None,
        stage_id: str | None = None,
        cluster_id: str | None = None,
        node_id: str | None = None,
    ) -> KnowledgeGraphMainViewDTO:
        if cluster_id is None and node_id is None:
            active_graph_view = self._get_active_graph_main_view(project_id, stage_id)
            if active_graph_view is not None:
                return active_graph_view

        nodes = self._profile_space.list_map_nodes(project_id, stage_id)
        states = self._profile_space.list_user_node_states(project_id, stage_id)
        state_by_node_id = {item["node_id"]: item for item in states}
        evidence_refs = self._profile_space.list_evidence_refs(project_id, stage_id)
        evidence_count_by_node_id: dict[str, int] = {}
        for item in evidence_refs:
            evidence_count_by_node_id[item["node_id"]] = evidence_count_by_node_id.get(item["node_id"], 0) + 1

        focus_cluster_items = self._profile_space.list_focus_clusters(project_id, stage_id)
        selected_cluster_item = None
        if cluster_id is not None:
            selected_cluster_item = next((item for item in focus_cluster_items if item["cluster_id"] == cluster_id), None)
        elif node_id is not None:
            selected_cluster_item = next((item for item in focus_cluster_items if item["center_node_id"] == node_id), None)
        elif focus_cluster_items:
            selected_cluster_item = focus_cluster_items[0]

        selected_cluster = (
            FocusClusterCardDTO(
                cluster_id=selected_cluster_item["cluster_id"],
                title=selected_cluster_item["title"],
                center_node_id=selected_cluster_item["center_node_id"],
                neighbor_node_ids=list(selected_cluster_item.get("neighbor_node_ids", [])),
                focus_reason_codes=list(selected_cluster_item.get("focus_reason_codes", [])),
                focus_reason_summary=self._focus_reason_summary(selected_cluster_item, project_id=project_id),
            )
            if selected_cluster_item is not None
            else None
        )

        visible_node_ids: set[str] | None = None
        if selected_cluster_item is not None:
            visible_node_ids = {
                selected_cluster_item["center_node_id"],
                *list(selected_cluster_item.get("neighbor_node_ids", [])),
            }

        node_cards = []
        for item in nodes:
            if visible_node_ids is not None and item["node_id"] not in visible_node_ids:
                continue
            state = state_by_node_id.get(item["node_id"], {})
            node_cards.append(
                KnowledgeNodeCardDTO(
                    node_id=item["node_id"],
                    label=item["label"],
                    node_type=item["node_type"],
                    abstract_level=item["abstract_level"],
                    scope=item["scope"],
                    canonical_summary=item["canonical_summary"],
                    mastery_status=state.get("mastery_status", "unverified"),
                    review_needed=bool(state.get("review_needed", False)),
                    relation_preview=[],
                    evidence_summary={"evidence_count": evidence_count_by_node_id.get(item["node_id"], 0)},
                )
            )

        visible_node_id_set = {item.node_id for item in node_cards}
        relations = [
            {
                "relation_id": item["relation_id"],
                "source_node_id": item["source_node_id"],
                "target_node_id": item["target_node_id"],
                "relation_type": item["relation_type"],
            }
            for item in self._profile_space.list_knowledge_relations(project_id, stage_id)
            if item["source_node_id"] in visible_node_id_set and item["target_node_id"] in visible_node_id_set
        ]

        return KnowledgeGraphMainViewDTO(
            selected_cluster=selected_cluster,
            nodes=node_cards,
            relations=relations,
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

    def _focus_cluster_sort_key(self, item: dict) -> tuple[int, str]:
        codes = list(item.get("focus_reason_codes", []))
        priority = min((self._FOCUS_REASON_PRIORITY.get(code, 99) for code in codes), default=99)
        pinned_rank = 0 if bool(item.get("is_pinned", False)) else 1
        return (pinned_rank, priority, str(item.get("title", "")))

    def _focus_reason_summary(self, item: dict, project_id: str | None = None) -> str:
        explanation = self._profile_space.get_focus_explanation(
            "focus_cluster",
            str(item.get("cluster_id", "")),
            project_id=project_id,
        )
        if explanation is not None:
            summary = str(explanation.get("summary", "")).strip()
            if summary:
                return summary

        summary = str(item.get("focus_reason_summary", "")).strip()
        if summary:
            return summary

        codes = list(item.get("focus_reason_codes", []))
        label = str(item.get("title", "this cluster")).replace(" hotspot", "")
        if "weak_signal_active" in codes and "current_project_hit" in codes:
            return f"This area matters now because the current project hit {label} and it still shows a weak signal."
        if "weak_signal_active" in codes:
            return f"This area matters now because {label} still shows a weak signal."
        if "current_project_hit" in codes:
            return f"This area matters now because the current project recently hit {label}."
        if "foundation_hot" in codes:
            return f"This area matters now because {label} is acting as a foundation hotspot."
        return f"This area matters now because {label} is part of the current knowledge map focus."
