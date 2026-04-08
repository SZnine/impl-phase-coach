import json

from review_gate.action_dtos import ProposalActionRequest, SubmitAnswerRequest
from review_gate.domain import FocusExplanation
from review_gate.profile_space_service import ProfileSpaceService
from review_gate.proposal_center_service import ProposalCenterService
from review_gate.review_flow_service import ReviewFlowService
from review_gate.view_dtos import (
    AssessmentSummaryDTO,
    FocusClusterCardDTO,
    HomeProjectItemDTO,
    KnowledgeGraphMainViewDTO,
    KnowledgeGraphNodeDTO,
    KnowledgeIndexItemDTO,
    KnowledgeMapSummaryViewDTO,
    MistakeItemDTO,
    ProposalItemDTO,
    ProjectViewDTO,
    QuestionSetViewDTO,
    QuestionSummaryDTO,
    QuestionViewDTO,
    SubmitAnswerResponseDTO,
)
from review_gate.workspace_api import WorkspaceAPI


class CapturingAssessmentClient:
    def __init__(self, verdict: str = "partial", core_gaps: list[str] | None = None, misconceptions: list[str] | None = None) -> None:
        self.verdict = verdict
        self.core_gaps = core_gaps if core_gaps is not None else (["Needs deeper boundary explanation."] if verdict != "strong" else [])
        self.misconceptions = misconceptions if misconceptions is not None else []
        self.last_request: dict | None = None

    def assess(self, request: dict) -> dict:
        self.last_request = request
        return {
            "request_id": request["request_id"],
            "assessment": {
                "score_total": 0.72 if self.verdict != "weak" else 0.35,
                "dimension_scores": {
                    "correctness": 3 if self.verdict != "weak" else 1,
                    "reasoning": 3 if self.verdict == "strong" else 2,
                    "decision_awareness": 2 if self.verdict != "weak" else 1,
                    "boundary_awareness": 3 if self.verdict != "weak" else 1,
                    "stability": 3 if self.verdict == "strong" else 2,
                },
                "verdict": self.verdict,
                "core_gaps": self.core_gaps,
                "misconceptions": self.misconceptions,
                "evidence": [f"assessment evidence: verdict={self.verdict}"],
            },
            "recommended_action": "redirect_to_learning" if self.verdict == "weak" else "continue_answering",
            "recommended_follow_up_questions": [] if self.verdict == "strong" else ["Explain the why again."],
            "learning_recommendations": [] if self.verdict == "strong" else ["Revisit the stage boundary."],
            "warnings": [],
            "confidence": 0.7 if self.verdict == "weak" else 0.8,
        }


def test_workspace_api_returns_home_view() -> None:
    proposal_center = ProposalCenterService.for_testing()
    proposal_center.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
        project_id="proj-1",
    )
    profile_space = ProfileSpaceService.for_testing()
    profile_space.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-1",
            "verdict": "partial",
            "core_gaps": ["Decision awareness"],
            "misconceptions": [],
        },
    )
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing(), proposal_center=proposal_center, profile_space=profile_space)

    home_view = api.get_home_view()

    assert home_view.total_count == 1
    assert home_view.pending_proposal_count == 1
    assert home_view.active_project_id == "proj-1"
    assert isinstance(home_view.projects[0], HomeProjectItemDTO)
    assert home_view.projects[0].project_label == "impl-phase-coach"
    assert home_view.projects[0].knowledge_entry_count == 1
    assert home_view.projects[0].mistake_count == 1


def test_workspace_api_returns_project_view() -> None:
    proposal_center = ProposalCenterService.for_testing()
    proposal_center.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1"],
        project_id="proj-1",
        stage_id="stage-1",
    )
    profile_space = ProfileSpaceService.for_testing()
    profile_space.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-1",
            "verdict": "partial",
            "core_gaps": ["Decision awareness"],
            "misconceptions": [],
        },
    )
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing(), proposal_center=proposal_center, profile_space=profile_space)

    project_view = api.get_project_view("proj-1")

    assert isinstance(project_view, ProjectViewDTO)
    assert project_view.project_label == "impl-phase-coach"
    assert project_view.pending_proposal_count == 1
    assert project_view.knowledge_entry_count == 1
    assert project_view.mistake_count == 1
    assert len(project_view.stages) == 2
    assert project_view.stages[0].stage_id == "stage-1"


def test_workspace_api_returns_stage_view() -> None:
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing())

    stage_view = api.get_stage_view("proj-1", "stage-1")

    assert stage_view.project_id == "proj-1"
    assert stage_view.stage_id == "stage-1"
    assert stage_view.stage_label
    assert stage_view.status == "in_progress"
    assert stage_view.knowledge_summary is not None
    assert stage_view.knowledge_summary.knowledge_entry_count == 0
    assert stage_view.knowledge_summary.mistake_count == 0


def test_workspace_api_returns_mistakes_view() -> None:
    profile_space = ProfileSpaceService.for_testing()
    profile_space.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-1",
            "verdict": "partial",
            "core_gaps": ["Decision awareness"],
            "misconceptions": ["Boundary confusion"],
        },
    )
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing(), profile_space=profile_space)

    mistakes_view = api.get_mistakes_view(project_id="proj-1", stage_id="stage-1")

    assert mistakes_view.total_count == 1
    assert isinstance(mistakes_view.items[0], MistakeItemDTO)
    assert mistakes_view.items[0].root_cause_summary == "Decision awareness"


def test_workspace_api_returns_knowledge_index_view() -> None:
    profile_space = ProfileSpaceService.for_testing()
    profile_space.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-1",
            "verdict": "partial",
            "core_gaps": ["Decision awareness"],
            "misconceptions": [],
        },
    )
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing(), profile_space=profile_space)

    index_view = api.get_knowledge_index_view(project_id="proj-1", stage_id="stage-1")

    assert index_view.total_count == 1
    assert isinstance(index_view.items[0], KnowledgeIndexItemDTO)
    assert index_view.items[0].title == "Decision awareness"


def test_workspace_api_returns_knowledge_graph_view() -> None:
    profile_space = ProfileSpaceService.for_testing()
    profile_space.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-1",
            "verdict": "partial",
            "core_gaps": ["Decision awareness"],
            "misconceptions": [],
        },
    )
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing(), profile_space=profile_space)

    graph_view = api.get_knowledge_graph_view(project_id="proj-1", stage_id="stage-1")

    assert graph_view.total_count == 1
    assert isinstance(graph_view.nodes[0], KnowledgeGraphNodeDTO)
    assert graph_view.nodes[0].label == "Decision awareness"


def test_workspace_api_returns_knowledge_map_summary_and_graph_main_view() -> None:
    profile_space = ProfileSpaceService.for_testing()
    profile_space.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-km-1",
            "verdict": "partial",
            "core_gaps": ["State and return value separation"],
            "misconceptions": ["Boundary confusion"],
            "confidence": 0.78,
        },
    )
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing(), profile_space=profile_space)

    summary_view = api.get_knowledge_map_summary_view(project_id="proj-1", stage_id="stage-1")
    graph_main_view = api.get_knowledge_graph_main_view(project_id="proj-1", stage_id="stage-1")

    assert isinstance(summary_view, KnowledgeMapSummaryViewDTO)
    assert summary_view.focus_clusters
    assert isinstance(summary_view.focus_clusters[0], FocusClusterCardDTO)
    assert "State and return value separation" in summary_view.current_weak_spots
    assert isinstance(summary_view.foundation_hotspots, list)

    assert isinstance(graph_main_view, KnowledgeGraphMainViewDTO)
    assert graph_main_view.selected_cluster is not None
    assert graph_main_view.nodes
    assert graph_main_view.nodes[0].label == "State and return value separation"
    assert graph_main_view.nodes[0].mastery_status == "partial"


def test_workspace_api_sorts_focus_clusters_by_reason_priority() -> None:
    profile_space = ProfileSpaceService.for_testing()
    profile_space.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-km-strong",
            "verdict": "strong",
            "core_gaps": ["Encoding boundary"],
            "misconceptions": [],
            "confidence": 0.62,
        },
    )
    profile_space.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-km-partial",
            "verdict": "partial",
            "core_gaps": ["State and return value separation"],
            "misconceptions": ["Boundary confusion"],
            "confidence": 0.84,
        },
    )
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing(), profile_space=profile_space)

    summary_view = api.get_knowledge_map_summary_view(project_id="proj-1", stage_id="stage-1")

    assert len(summary_view.focus_clusters) == 2
    assert summary_view.focus_clusters[0].title == "State and return value separation hotspot"
    assert "weak_signal_active" in summary_view.focus_clusters[0].focus_reason_codes
    assert summary_view.focus_clusters[1].title == "Encoding boundary hotspot"


def test_workspace_api_prefers_cached_focus_explanation_over_cluster_summary() -> None:
    profile_space = ProfileSpaceService.for_testing()
    profile_space.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "assessment-1",
            "verdict": "partial",
            "core_gaps": ["State and return value separation"],
            "misconceptions": [],
        },
    )
    cluster = profile_space.list_focus_clusters(project_id="proj-1", stage_id="stage-1")[0]
    profile_space._focus_explanations[("focus_cluster", cluster["cluster_id"])] = FocusExplanation(
        explanation_id=f"focus_cluster:{cluster['cluster_id']}",
        profile_space_id="profile-space:proj-1",
        subject_type="focus_cluster",
        subject_id=cluster["cluster_id"],
        reason_codes=["current_project_hit", "weak_signal_active"],
        summary="Cached explanation wins.",
        generated_by="deterministic",
        generated_at="2026-04-08T16:10:00Z",
        version="v1",
    ).to_dict()
    profile_space._focus_clusters[cluster["cluster_id"]]["focus_reason_summary"] = "Stale cluster summary."

    api = WorkspaceAPI(flow=ReviewFlowService.for_testing(), profile_space=profile_space)

    summary_view = api.get_knowledge_map_summary_view(project_id="proj-1", stage_id="stage-1")

    assert summary_view.focus_clusters[0].focus_reason_summary == "Cached explanation wins."


def test_workspace_api_falls_back_when_focus_explanation_cache_is_missing() -> None:
    profile_space = ProfileSpaceService.for_testing()
    profile_space.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "assessment-1",
            "verdict": "partial",
            "core_gaps": ["State and return value separation"],
            "misconceptions": [],
        },
    )
    cluster = profile_space.list_focus_clusters(project_id="proj-1", stage_id="stage-1")[0]
    profile_space._focus_explanations.clear()
    profile_space._focus_clusters[cluster["cluster_id"]]["focus_reason_summary"] = ""

    api = WorkspaceAPI(flow=ReviewFlowService.for_testing(), profile_space=profile_space)

    summary_view = api.get_knowledge_map_summary_view(project_id="proj-1", stage_id="stage-1")

    assert "State and return value separation" in summary_view.focus_clusters[0].focus_reason_summary
    assert summary_view.focus_clusters[0].focus_reason_summary.endswith(".")


def test_workspace_api_returns_proposals_view() -> None:
    proposal_center = ProposalCenterService.for_testing()
    proposal_center.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
    )
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing(), proposal_center=proposal_center)

    proposals_view = api.get_proposals_view()

    assert proposals_view.total_count == 1
    assert proposals_view.pending_count == 1
    assert isinstance(proposals_view.items[0], ProposalItemDTO)
    assert proposals_view.items[0].proposal_type == "compress_mistake_entries"


def test_workspace_api_proposal_action_returns_execution_and_refreshes_view() -> None:
    proposal_center = ProposalCenterService.for_testing()
    proposal = proposal_center.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
    )[0]
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing(), proposal_center=proposal_center)

    response = api.proposal_action(
        ProposalActionRequest(
            request_id="proposal-1-accept",
            source_page="proposals",
            actor_id="local-user",
            created_at="2026-04-03T12:00:00Z",
            proposal_id=proposal["proposal_id"],
            action_type="accept",
            selected_target_ids=[],
        )
    )

    assert response.success is True
    assert response.proposal_status == "accepted"
    assert response.execution_status == "succeeded"

    refreshed = api.get_proposals_view()
    assert refreshed.pending_count == 0
    assert refreshed.items[0].status == "accepted"
    assert refreshed.items[0].latest_execution_summary == "accept on proposal-1 => succeeded"


def test_workspace_api_returns_question_set_view() -> None:
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing())

    question_set_view = api.get_question_set_view("proj-1", "stage-1", "set-1")

    assert question_set_view.project_id == "proj-1"
    assert question_set_view.stage_id == "stage-1"
    assert question_set_view.question_set_id == "set-1"
    assert question_set_view.question_count >= 1
    assert question_set_view.questions
    assert isinstance(question_set_view.questions[0], QuestionSummaryDTO)


def test_workspace_api_returns_question_view() -> None:
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing())

    question_view = api.get_question_view("proj-1", "stage-1", "set-1", "q-1")

    assert question_view.project_id == "proj-1"
    assert question_view.stage_id == "stage-1"
    assert question_view.question_set_id == "set-1"
    assert question_view.question_id == "q-1"
    assert question_view.question_level in {"core", "why", "abstract"}
    assert question_view.allowed_actions


def test_submit_answer_action_returns_assessment_created_response() -> None:
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing())

    response = api.submit_answer_action(
        SubmitAnswerRequest(
            request_id="req-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-02T12:00:00Z",
            question_set_id="set-1",
            question_id="q-1",
            answer_text="This answer is long enough to avoid the weak fallback verdict.",
            draft_id=None,
        )
    )

    assert response.request_id == "req-1"
    assert response.success is True
    assert response.result_type == "assessment_created"
    assert response.assessment_summary is not None
    assert response.assessment_summary.answer_excerpt == "This answer is long enough to avoid the weak fallback verdict."

    stage_view = api.get_stage_view("proj-1", "stage-1")
    assert stage_view.knowledge_summary is not None
    assert stage_view.knowledge_summary.knowledge_entry_count == 1
    assert stage_view.knowledge_summary.mistake_count == 1
    assert stage_view.knowledge_summary.latest_summary == "synced partial assessment with 1 knowledge entries and 1 mistakes"

    mistakes_view = api.get_mistakes_view(project_id="proj-1", stage_id="stage-1")
    assert mistakes_view.total_count == 1
    assert mistakes_view.items[0].project_id == "proj-1"

    index_view = api.get_knowledge_index_view(project_id="proj-1", stage_id="stage-1")
    assert index_view.total_count == 1
    assert index_view.items[0].title == "Needs deeper boundary explanation."


def test_submit_answer_request_and_response_are_stable_transport_models() -> None:
    request = SubmitAnswerRequest(
        request_id="req-1",
        project_id="proj-1",
        stage_id="stage-1",
        source_page="question_detail",
        actor_id="local-user",
        created_at="2026-04-02T12:00:00Z",
        question_set_id="set-1",
        question_id="q-1",
        answer_text="Need review",
        draft_id=None,
    )

    request_dump = request.model_dump()
    request_json = request.model_dump_json()

    assert request_dump["question_id"] == "q-1"
    assert json.loads(request_json)["answer_text"] == "Need review"
    assert SubmitAnswerRequest.model_validate_json(request_json).model_dump() == request_dump

    response = SubmitAnswerResponseDTO(
        request_id="req-1",
        success=True,
        action_type="submit_answer",
        result_type="assessment_created",
        message="Assessment created.",
        refresh_targets=["question_detail", "stage_summary"],
        assessment_summary=AssessmentSummaryDTO(
            assessment_id="assessment-req-1",
            project_id="proj-1",
            stage_id="stage-1",
            question_set_id="set-1",
            question_id="q-1",
            answer_excerpt="Need review",
        ),
    )

    response_dump = response.model_dump()
    validated_response = SubmitAnswerResponseDTO.model_validate_json(response.model_dump_json())

    assert response_dump["refresh_targets"] == ["question_detail", "stage_summary"]
    assert response_dump["assessment_summary"] == {
        "assessment_id": "assessment-req-1",
        "project_id": "proj-1",
        "stage_id": "stage-1",
        "question_set_id": "set-1",
        "question_id": "q-1",
        "answer_excerpt": "Need review",
        "status": "created",
    }
    assert isinstance(validated_response.assessment_summary, AssessmentSummaryDTO)
    assert validated_response.model_dump() == response_dump


def test_submit_answer_action_rejects_blank_answer_text() -> None:
    api = WorkspaceAPI(flow=ReviewFlowService.for_testing())

    response = api.submit_answer_action(
        SubmitAnswerRequest(
            request_id="req-blank",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-02T12:00:00Z",
            question_set_id="set-1",
            question_id="q-1",
            answer_text="   ",
            draft_id=None,
        )
    )

    assert response.success is False
    assert response.result_type != "assessment_created"
    assert response.assessment_summary is None


def test_submit_answer_action_assesses_the_actual_current_question_context() -> None:
    assessment_client = CapturingAssessmentClient()
    api = WorkspaceAPI(flow=ReviewFlowService(assessment_client=assessment_client))

    response = api.submit_answer_action(
        SubmitAnswerRequest(
            request_id="req-why",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-03T12:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-2",
            answer_text="This is a sufficiently long answer to avoid the weak fallback.",
            draft_id=None,
        )
    )

    assert response.success is True
    assert assessment_client.last_request is not None
    assert assessment_client.last_request["question_level"] == "why"
    assert assessment_client.last_request["question_prompt"] == "Why do we use this boundary for question set-1-q-2?"
    assert assessment_client.last_request["question_intent"] == "Check the reasoning behind the decision."


def test_submit_answer_action_does_not_raise_mastery_for_weak_verdict() -> None:
    assessment_client = CapturingAssessmentClient(verdict="weak")
    flow = ReviewFlowService(assessment_client=assessment_client)
    api = WorkspaceAPI(flow=flow)

    response = api.submit_answer_action(
        SubmitAnswerRequest(
            request_id="req-weak",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-03T12:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="Need review",
            draft_id=None,
        )
    )

    assert response.success is True
    stage_view = api.get_stage_view("proj-1", "stage-1")
    assert stage_view.mastery_status == "unverified"
    assert stage_view.knowledge_summary is not None
    assert stage_view.knowledge_summary.knowledge_entry_count == 1
    assert stage_view.knowledge_summary.mistake_count == 1


def test_submit_answer_action_keeps_zero_knowledge_summary_for_weak_assessment_without_gaps() -> None:
    assessment_client = CapturingAssessmentClient(verdict="weak", core_gaps=[], misconceptions=[])
    api = WorkspaceAPI(
        flow=ReviewFlowService(assessment_client=assessment_client),
        profile_space=ProfileSpaceService.for_testing(),
    )

    response = api.submit_answer_action(
        SubmitAnswerRequest(
            request_id="req-weak-empty",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-03T12:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="Need review",
            draft_id=None,
        )
    )

    assert response.success is True
    summary = api.get_stage_view("proj-1", "stage-1").knowledge_summary
    assert summary is not None
    assert summary.knowledge_entry_count == 0
    assert summary.mistake_count == 0
