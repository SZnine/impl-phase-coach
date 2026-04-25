import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from review_gate.action_dtos import ProposalActionRequest, SubmitAnswerRequest
from review_gate.evaluator_agent_assessment_client import EvaluatorAgentAssessmentClient
from review_gate.http_api import create_app, create_default_workspace_api
from review_gate.project_agent_question_generation_client import ProjectAgentQuestionGenerationClient
from review_gate.profile_space_service import ProfileSpaceService
from review_gate.proposal_center_service import ProposalCenterService
from review_gate.review_flow_service import ReviewFlowService
from review_gate.storage_sqlite import SQLiteStore
from review_gate.workspace_api import WorkspaceAPI


def create_client() -> TestClient:
    return TestClient(create_app(api=WorkspaceAPI(flow=ReviewFlowService.for_testing())))


class StaticQuestionGenerationClient:
    def generate(self, request: dict) -> dict:
        return {
            "request_id": request["request_id"],
            "questions": [
                {
                    "question_id": "q-1",
                    "question_level": "why",
                    "prompt": "Why should generated questions cross the HTTP action boundary?",
                    "intent": "Check generated workflow wiring.",
                    "expected_signals": ["http generation action"],
                    "source_context": ["test_http_api"],
                }
            ],
            "generation_summary": "Generated a route-backed question.",
            "coverage_notes": [],
            "warnings": [],
            "confidence": 0.81,
        }


class SupportRelationAssessmentClient:
    def assess(self, request: dict) -> dict:
        return {
            "request_id": request["request_id"],
            "assessment": {
                "score_total": 0.76,
                "dimension_scores": {
                    "correctness": 3,
                    "reasoning": 2,
                    "boundary_awareness": 3,
                    "stability": 3,
                },
                "verdict": "partial",
                "core_gaps": ["api-boundary-discipline"],
                "misconceptions": [],
                "support_basis_tags": [
                    {
                        "source_label": "Boundary discipline",
                        "source_node_type": "foundation",
                        "target_label": "api-boundary-discipline",
                        "target_node_type": "method",
                        "basis_key": "boundary_awareness",
                    }
                ],
                "evidence": ["The answer names API boundaries but does not describe the contract."],
            },
            "recommended_action": "continue_answering",
            "recommended_follow_up_questions": ["Explain how the API contract is enforced."],
            "learning_recommendations": ["Review boundary discipline."],
            "warnings": [],
            "confidence": 0.76,
        }


class HumanReadableAssessmentClient:
    def assess(self, request: dict) -> dict:
        return {
            "request_id": request["request_id"],
            "assessment": {
                "score_total": 0.68,
                "dimension_scores": {
                    "correctness": 3,
                    "reasoning": 2,
                    "boundary_awareness": 1,
                    "stability": 2,
                },
                "verdict": "partial",
                "core_gaps": ["normalizer failure scenario"],
                "misconceptions": ["treats storage as provider compatibility layer"],
                "support_basis_tags": [],
                "evidence": ["The answer names normalizer but does not explain malformed provider output."],
            },
            "recommended_action": "continue_answering",
            "recommended_follow_up_questions": ["If provider output contains both questions and items, which field wins?"],
            "learning_recommendations": ["Review provider output normalization and storage boundaries."],
            "warnings": [],
            "confidence": 0.74,
        }


def test_http_api_returns_home_view() -> None:
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
    client = TestClient(
        create_app(api=WorkspaceAPI(flow=ReviewFlowService.for_testing(), proposal_center=proposal_center, profile_space=profile_space))
    )

    response = client.get("/api/home")

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert data["pending_proposal_count"] == 1
    assert data["projects"][0]["project_id"] == "proj-1"
    assert data["projects"][0]["knowledge_entry_count"] == 1


def test_http_api_returns_project_view() -> None:
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
    client = TestClient(
        create_app(api=WorkspaceAPI(flow=ReviewFlowService.for_testing(), proposal_center=proposal_center, profile_space=profile_space))
    )

    response = client.get("/api/projects/proj-1")

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "proj-1"
    assert data["project_label"] == "impl-phase-coach"
    assert data["pending_proposal_count"] == 1
    assert data["knowledge_entry_count"] == 1
    assert len(data["stages"]) == 2


def test_http_api_returns_stage_view() -> None:
    client = create_client()
    response = client.get("/api/projects/proj-1/stages/stage-1")

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "proj-1"
    assert data["stage_id"] == "stage-1"
    assert data["active_question_set_id"] == "set-1"
    assert data["knowledge_summary"]["knowledge_entry_count"] == 0
    assert data["knowledge_summary"]["mistake_count"] == 0


def test_http_api_returns_mistakes_view() -> None:
    client = create_client()
    client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-mistakes",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-03T00:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "This answer is long enough to avoid the weak fallback verdict.",
            "draft_id": None,
        },
    )

    response = client.get("/api/mistakes")

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert data["items"][0]["project_id"] == "proj-1"
    assert data["items"][0]["stage_id"] == "stage-1"


def test_http_api_returns_knowledge_index_view() -> None:
    client = create_client()
    client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-index",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-03T00:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "This answer is long enough to avoid the weak fallback verdict.",
            "draft_id": None,
        },
    )

    response = client.get("/api/knowledge/index")

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert data["items"][0]["title"] == "Needs deeper boundary explanation."


def test_http_api_returns_knowledge_graph_view() -> None:
    client = create_client()
    client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-graph",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-03T00:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "This answer is long enough to avoid the weak fallback verdict.",
            "draft_id": None,
        },
    )

    response = client.get("/api/knowledge/graph")

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert data["nodes"][0]["label"] == "Needs deeper boundary explanation."
    assert data["nodes"][0]["node_type"] == "decision"


def test_http_api_returns_knowledge_map_summary_and_graph_main_views() -> None:
    client = create_client()
    client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-km",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-03T00:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "This answer is long enough to avoid the weak fallback verdict.",
            "draft_id": None,
        },
    )

    summary = client.get("/api/knowledge", params={"project_id": "proj-1", "stage_id": "stage-1"})
    graph = client.get("/api/knowledge/graph-main", params={"project_id": "proj-1", "stage_id": "stage-1"})

    assert summary.status_code == 200
    summary_data = summary.json()
    assert summary_data["focus_clusters"]
    assert "current_weak_spots" in summary_data
    assert "foundation_hotspots" in summary_data
    assert "evidence_refs" not in summary_data
    assert "answers" not in summary_data

    assert graph.status_code == 200
    graph_data = graph.json()
    assert graph_data["selected_cluster"] is not None
    assert graph_data["nodes"]
    assert graph_data["nodes"][0]["mastery_status"] == "partial"
    assert all(":evidence-" not in node["node_id"] for node in graph_data["nodes"])


def test_default_http_api_graph_main_reads_submit_side_active_graph_revision(tmp_path: Path) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    session_path = tmp_path / "workspace-session.json"
    client = TestClient(create_app(db_path=db_path, session_path=session_path))
    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-active-graph-main",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-20T12:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "This answer is long enough to avoid the weak fallback verdict.",
            "draft_id": None,
        },
    )

    graph_response = client.get(
        "/api/knowledge/graph-main",
        params={"project_id": "proj-1", "stage_id": "stage-1"},
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["success"] is True
    assert graph_response.status_code == 200
    graph_data = graph_response.json()
    assert graph_data["relations"] == []
    assert graph_data["nodes"]
    assert graph_data["selected_cluster"] is not None
    assert graph_data["selected_cluster"]["center_node_id"] == graph_data["nodes"][0]["node_id"]
    assert graph_data["selected_cluster"]["neighbor_node_ids"] == []
    assert graph_data["selected_cluster"]["focus_reason_codes"] == ["weak_signal_active"]
    assert graph_data["nodes"][0]["node_type"] == "weakness_topic"
    assert graph_data["nodes"][0]["mastery_status"] == "unverified"
    assert graph_data["nodes"][0]["review_needed"] is True
    assert graph_data["nodes"][0]["evidence_summary"]["signal_count"] == 1
    assert graph_data["nodes"][0]["evidence_summary"]["fact_count"] == 1


def test_default_http_api_graph_revision_reads_submit_side_active_revision(tmp_path: Path) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    session_path = tmp_path / "workspace-session.json"
    client = TestClient(create_app(db_path=db_path, session_path=session_path))
    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-graph-revision-view",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-20T13:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "This answer is long enough to avoid the weak fallback verdict.",
            "draft_id": None,
        },
    )

    graph_response = client.get(
        "/api/knowledge/graph-revision",
        params={"project_id": "proj-1", "stage_id": "stage-1"},
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["success"] is True
    assert graph_response.status_code == 200
    graph_data = graph_response.json()
    assert graph_data["project_id"] == "proj-1"
    assert graph_data["stage_id"] == "stage-1"
    assert graph_data["has_active_revision"] is True
    assert graph_data["revision"]["graph_revision_id"] == "gr-proj-1-stage-stage-1-20260420130000"
    assert graph_data["revision"]["revision_type"] == "deterministic_signal_projection"
    assert graph_data["revision"]["node_count"] == 1
    assert graph_data["revision"]["relation_count"] == 0
    assert graph_data["revision"]["source_fact_batch_ids"]
    assert graph_data["revision"]["source_signal_ids"]
    assert len(graph_data["nodes"]) == 1
    assert graph_data["nodes"][0]["graph_revision_id"] == "gr-proj-1-stage-stage-1-20260420130000"
    assert graph_data["nodes"][0]["node_type"] == "weakness_topic"
    assert graph_data["nodes"][0]["source_signal_ids"]
    assert graph_data["nodes"][0]["supporting_fact_ids"]
    assert graph_data["nodes"][0]["confidence"] > 0
    assert graph_data["nodes"][0]["status"] == "active"
    assert graph_data["relations"] == []


def test_http_api_graph_revision_reads_support_relation_after_submit(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "workbench.sqlite3")
    store.initialize()
    flow = ReviewFlowService(
        assessment_client=SupportRelationAssessmentClient(),
        store=store,
    )
    client = TestClient(
        create_app(
            api=WorkspaceAPI(
                flow=flow,
                checkpoint_store=store,
            )
        )
    )
    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-graph-relation-view",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-21T11:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "The API boundary exists, but I did not define the request and response contract clearly.",
            "draft_id": None,
        },
    )

    graph_response = client.get(
        "/api/knowledge/graph-revision",
        params={"project_id": "proj-1", "stage_id": "stage-1"},
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["success"] is True
    assert graph_response.status_code == 200
    graph_data = graph_response.json()
    assert graph_data["has_active_revision"] is True
    assert graph_data["revision"]["graph_revision_id"] == "gr-proj-1-stage-stage-1-20260421110000"
    assert graph_data["revision"]["node_count"] == 2
    assert graph_data["revision"]["relation_count"] == 1
    assert {node["topic_key"] for node in graph_data["nodes"]} == {
        "api-boundary-discipline",
        "boundary-discipline",
    }
    assert len(graph_data["relations"]) == 1
    relation = graph_data["relations"][0]
    assert relation["relation_type"] == "supports"
    assert relation["directionality"] == "directed"
    assert relation["from_node_id"].endswith("-boundary-discipline")
    assert relation["to_node_id"].endswith("-api-boundary-discipline")
    assert relation["source_signal_ids"]
    assert relation["supporting_fact_ids"]
    assert relation["payload"] == {
        "basis_type": "support_basis_tag",
        "basis_key": "boundary_awareness",
        "projector_version": "signal-graph-v1",
    }


def test_http_api_graph_main_reads_support_relation_after_submit(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "workbench.sqlite3")
    store.initialize()
    flow = ReviewFlowService(
        assessment_client=SupportRelationAssessmentClient(),
        store=store,
    )
    client = TestClient(
        create_app(
            api=WorkspaceAPI(
                flow=flow,
                checkpoint_store=store,
            )
        )
    )
    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-graph-main-relation-view",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-21T11:30:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "The API boundary exists, but I did not define the request and response contract clearly.",
            "draft_id": None,
        },
    )

    graph_response = client.get(
        "/api/knowledge/graph-main",
        params={"project_id": "proj-1", "stage_id": "stage-1"},
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["success"] is True
    assert graph_response.status_code == 200
    graph_data = graph_response.json()
    assert len(graph_data["relations"]) == 1
    relation = graph_data["relations"][0]
    assert graph_data["selected_cluster"] is not None
    assert graph_data["selected_cluster"]["center_node_id"] == relation["to_node_id"]
    assert graph_data["selected_cluster"]["neighbor_node_ids"] == [relation["from_node_id"]]
    assert graph_data["selected_cluster"]["focus_reason_codes"] == [
        "weak_signal_active",
        "relation_connected",
    ]
    assert relation["relation_type"] == "supports"
    assert relation["from_node_id"].endswith("-boundary-discipline")
    assert relation["to_node_id"].endswith("-api-boundary-discipline")
    assert relation["confidence"] == 0.76
    previews_by_node_id = {node["node_id"]: node["relation_preview"] for node in graph_data["nodes"]}
    assert previews_by_node_id[relation["from_node_id"]][0]["direction"] == "outgoing"
    assert previews_by_node_id[relation["to_node_id"]][0]["direction"] == "incoming"


def test_http_api_returns_latest_assessment_review_surface_after_submit(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "workbench.sqlite3")
    store.initialize()
    flow = ReviewFlowService(
        assessment_client=HumanReadableAssessmentClient(),
        store=store,
    )
    client = TestClient(
        create_app(
            api=WorkspaceAPI(
                flow=flow,
                profile_space=ProfileSpaceService.with_store(store),
                checkpoint_store=store,
            )
        )
    )

    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-assessment-review",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-23T10:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "I would normalize provider output, but I did not describe the malformed-output branch.",
            "draft_id": None,
        },
    )

    review_response = client.get(
        "/api/assessments/latest-review",
        params={"project_id": "proj-1", "stage_id": "stage-1"},
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["success"] is True
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["has_assessment"] is True
    assert review["assessment_id"] == "assessment-req-assessment-review"
    assert review["verdict"] == "partial"
    assert review["verdict_label"] == "部分掌握"
    assert review["score_percent"] == 68
    assert review["confidence_percent"] == 74
    assert review["answer_excerpt"] == "I would normalize provider output, but I did not describe the malformed-output branch."
    assert review["review_title"] == "方向正确，但还需要补齐关键缺口"
    assert "结论方向基本正确" in review["correct_points"]
    assert "normalizer failure scenario" in review["gap_points"]
    assert "treats storage as provider compatibility layer" in review["misconception_points"]
    assert review["recommended_follow_up_questions"] == [
        "If provider output contains both questions and items, which field wins?"
    ]
    assert review["learning_recommendations"] == [
        "Review provider output normalization and storage boundaries."
    ]
    assert review["knowledge_updates"][0]["title"] == "normalizer failure scenario"
    assert review["next_action_label"] == "继续追问一个失败场景"


def test_default_http_api_graph_revision_returns_empty_without_active_revision(tmp_path: Path) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    session_path = tmp_path / "workspace-session.json"
    client = TestClient(create_app(db_path=db_path, session_path=session_path))

    graph_response = client.get(
        "/api/knowledge/graph-revision",
        params={"project_id": "proj-1", "stage_id": "stage-1"},
    )

    assert graph_response.status_code == 200
    graph_data = graph_response.json()
    assert graph_data["project_id"] == "proj-1"
    assert graph_data["stage_id"] == "stage-1"
    assert graph_data["has_active_revision"] is False
    assert graph_data["revision"] is None
    assert graph_data["nodes"] == []
    assert graph_data["relations"] == []


def test_http_api_returns_proposals_view() -> None:
    proposal_center = ProposalCenterService.for_testing()
    proposal_center.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
    )
    client = TestClient(create_app(api=WorkspaceAPI(flow=ReviewFlowService.for_testing(), proposal_center=proposal_center)))

    response = client.get("/api/proposals")

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert data["pending_count"] == 1
    assert data["items"][0]["proposal_type"] == "compress_mistake_entries"


def test_http_api_proposal_action_refreshes_proposal_status() -> None:
    proposal_center = ProposalCenterService.for_testing()
    proposal = proposal_center.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
    )[0]
    client = TestClient(create_app(api=WorkspaceAPI(flow=ReviewFlowService.for_testing(), proposal_center=proposal_center)))

    action_response = client.post(
        "/api/actions/proposal-action",
        json={
            "request_id": "proposal-1-accept",
            "source_page": "proposals",
            "actor_id": "local-user",
            "created_at": "2026-04-03T00:00:00Z",
            "proposal_id": proposal["proposal_id"],
            "action_type": "accept",
            "selected_target_ids": [],
        },
    )

    assert action_response.status_code == 200
    action_data = action_response.json()
    assert action_data["success"] is True
    assert action_data["proposal_status"] == "accepted"
    assert action_data["execution_status"] == "succeeded"

    proposals_response = client.get("/api/proposals")
    proposals_data = proposals_response.json()
    assert proposals_data["pending_count"] == 0
    assert proposals_data["items"][0]["status"] == "accepted"
    assert proposals_data["items"][0]["latest_execution_summary"] == "accept on proposal-1 => succeeded"


def test_http_api_returns_question_set_view() -> None:
    client = create_client()
    response = client.get("/api/projects/proj-1/stages/stage-1/questions/set-1")

    assert response.status_code == 200
    data = response.json()
    assert data["question_set_id"] == "set-1"
    assert data["question_count"] >= 1
    assert data["questions"]


def test_http_api_returns_question_view() -> None:
    client = create_client()
    response = client.get("/api/projects/proj-1/stages/stage-1/questions/set-1/set-1-q-2")

    assert response.status_code == 200
    data = response.json()
    assert data["question_id"] == "set-1-q-2"
    assert data["question_level"] == "why"
    assert data["allowed_actions"]


def test_http_api_generate_question_set_action_returns_generated_questions_and_persists_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "workbench.sqlite3")
    store.initialize()
    flow = ReviewFlowService(
        question_generation_client=StaticQuestionGenerationClient(),
        store=store,
    )
    client = TestClient(create_app(api=WorkspaceAPI(flow=flow, checkpoint_store=store)))

    response = client.post(
        "/api/actions/generate-question-set",
        json={
            "request_id": "req-http-generate-action",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "full_live_workflow_smoke",
            "actor_id": "local-user",
            "created_at": "2026-04-21T14:00:00Z",
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
            "stage_summary": "HTTP action smoke",
            "current_decisions": ["Question generation action"],
            "key_logic_points": ["HTTP route delegates to service"],
            "known_weak_points": ["generated question context"],
            "boundary_focus": ["action boundary"],
            "question_strategy": "full_depth",
            "max_questions": 1,
            "source_refs": ["tests/test_http_api.py"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "req-http-generate-action"
    assert data["questions"][0]["question_id"] == "q-1"
    assert data["questions"][0]["prompt"] == "Why should generated questions cross the HTTP action boundary?"
    assert store.get_workflow_request("req-http-generate-action") is not None
    assert store.get_question_batch("qb-req-http-generate-action") is not None


def test_http_api_answering_generated_question_updates_question_set_progress(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "workbench.sqlite3")
    store.initialize()
    flow = ReviewFlowService(
        question_generation_client=StaticQuestionGenerationClient(),
        assessment_client=HumanReadableAssessmentClient(),
        store=store,
    )
    client = TestClient(create_app(api=WorkspaceAPI(flow=flow, checkpoint_store=store)))
    generate_response = client.post(
        "/api/actions/generate-question-set",
        json={
            "request_id": "req-http-progress-qgen",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_set",
            "actor_id": "local-user",
            "created_at": "2026-04-23T10:00:00Z",
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
            "stage_summary": "HTTP progress regression",
            "current_decisions": ["Question progress action"],
            "key_logic_points": ["submit updates question status"],
            "known_weak_points": [],
            "boundary_focus": ["question progress"],
            "question_strategy": "full_depth",
            "max_questions": 1,
            "source_refs": ["tests/test_http_api.py"],
        },
    )

    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-http-progress-submit",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-23T10:01:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "The route must preserve generated question identity and update progress after assessment.",
            "draft_id": None,
        },
    )
    question_set_response = client.get("/api/projects/proj-1/stages/stage-1/questions/set-1")

    assert generate_response.status_code == 200
    assert submit_response.status_code == 200
    assert submit_response.json()["refresh_targets"] == ["question_detail", "stage_summary", "question_set"]
    assert question_set_response.status_code == 200
    question_set_data = question_set_response.json()
    assert question_set_data["question_count"] == 1
    assert question_set_data["questions"][0]["question_id"] == "set-1-q-1"
    assert question_set_data["questions"][0]["status"] == "answered"
    assert question_set_data["current_question_id"] == "set-1-q-1"


def test_http_api_submit_answer_returns_assessment_and_refreshes_stage_mastery() -> None:
    client = create_client()

    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-03T00:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "This answer is long enough to avoid the weak fallback verdict.",
            "draft_id": None,
        },
    )

    assert submit_response.status_code == 200
    submit_data = submit_response.json()
    assert submit_data["success"] is True
    assert submit_data["result_type"] == "assessment_created"
    assert submit_data["assessment_summary"]["answer_excerpt"] == "This answer is long enough to avoid the weak fallback verdict."

    stage_response = client.get("/api/projects/proj-1/stages/stage-1")

    assert stage_response.status_code == 200
    stage_data = stage_response.json()
    assert stage_data["mastery_status"] == "partially_verified"
    assert stage_data["knowledge_summary"]["knowledge_entry_count"] == 1
    assert stage_data["knowledge_summary"]["mistake_count"] == 1
    assert stage_data["knowledge_summary"]["latest_summary"] == "synced partial assessment with 1 knowledge entries and 1 mistakes"



def test_http_api_submit_answer_does_not_raise_mastery_for_weak_verdict() -> None:
    client = create_client()

    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-weak",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-03T00:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "short answer",
            "draft_id": None,
        },
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["success"] is True

    stage_response = client.get("/api/projects/proj-1/stages/stage-1")

    assert stage_response.status_code == 200
    assert stage_response.json()["mastery_status"] == "unverified"



def test_create_default_workspace_api_persists_profile_space_between_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    api_writer = create_default_workspace_api(db_path)
    response = api_writer.submit_answer_action(
        SubmitAnswerRequest(
            request_id="req-persist-profile",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-03T00:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="This answer is long enough to avoid the weak fallback verdict.",
            draft_id=None,
        )
    )

    assert response.success is True
    api_reader = create_default_workspace_api(db_path)
    stage_view = api_reader.get_stage_view("proj-1", "stage-1")
    mistakes_view = api_reader.get_mistakes_view(project_id="proj-1", stage_id="stage-1")

    assert stage_view.knowledge_summary is not None
    assert stage_view.knowledge_summary.knowledge_entry_count == 1
    assert stage_view.knowledge_summary.mistake_count == 1
    assert mistakes_view.total_count == 1


def test_create_default_workspace_api_initializes_first_checkpoint_tables_on_fresh_db(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh" / "workbench.sqlite3"

    assert not db_path.exists()

    api = create_default_workspace_api(db_path)
    response = api.submit_answer_action(
        SubmitAnswerRequest(
            request_id="req-fresh-db",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-03T00:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="This answer is long enough to avoid the weak fallback verdict.",
            draft_id=None,
        )
    )

    stage_view = api.get_stage_view("proj-1", "stage-1")
    with sqlite3.connect(db_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert response.success is True
    assert response.result_type == "assessment_created"
    assert db_path.exists()
    assert {
        "workflow_requests",
        "question_batches",
        "answer_batches",
        "evaluation_batches",
        "assessment_fact_batches",
    }.issubset(table_names)
    assert stage_view.knowledge_summary is not None
    assert stage_view.knowledge_summary.knowledge_entry_count == 1
    assert stage_view.knowledge_summary.mistake_count == 1



def test_create_default_workspace_api_persists_proposals_between_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    api_writer = create_default_workspace_api(db_path)
    proposal = api_writer._proposal_center.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
        project_id="proj-1",
        stage_id="stage-1",
    )[0]
    response = api_writer.proposal_action(
        ProposalActionRequest(
            request_id="proposal-persist-accept",
            source_page="proposals",
            actor_id="local-user",
            created_at="2026-04-03T00:00:00Z",
            proposal_id=proposal["proposal_id"],
            action_type="accept",
            selected_target_ids=[],
        )
    )

    assert response.success is True
    api_reader = create_default_workspace_api(db_path)
    proposals_view = api_reader.get_proposals_view()

    assert proposals_view.total_count == 1
    assert proposals_view.pending_count == 0
    assert proposals_view.items[0].status == "accepted"
    assert proposals_view.items[0].latest_execution_status == "succeeded"

def test_create_default_workspace_api_persists_stage_mastery_between_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    api_writer = create_default_workspace_api(db_path)
    response = api_writer.submit_answer_action(
        SubmitAnswerRequest(
            request_id="req-persist-stage-mastery",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-03T00:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="This answer is long enough to avoid the weak fallback verdict.",
            draft_id=None,
        )
    )

    assert response.success is True
    api_reader = create_default_workspace_api(db_path)
    stage_view = api_reader.get_stage_view("proj-1", "stage-1")

    assert stage_view.mastery_status == "partially_verified"
    assert stage_view.knowledge_summary is not None
    assert stage_view.knowledge_summary.knowledge_entry_count == 1
    assert stage_view.knowledge_summary.mistake_count == 1
    assert stage_view.knowledge_summary.latest_summary == "synced partial assessment with 1 knowledge entries and 1 mistakes"


def test_create_default_workspace_api_uses_environment_demo_paths(tmp_path: Path, monkeypatch) -> None:
    demo_dir = tmp_path / "demo"
    db_path = demo_dir / "review-workbench-demo.sqlite3"
    session_path = demo_dir / "workspace-session-demo.json"
    monkeypatch.setenv("REVIEW_WORKBENCH_DB_PATH", str(db_path))
    monkeypatch.setenv("REVIEW_WORKBENCH_SESSION_PATH", str(session_path))

    api = create_default_workspace_api()
    response = api.submit_answer_action(
        SubmitAnswerRequest(
            request_id="req-demo-env",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-09T00:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="This answer is long enough to avoid the weak fallback verdict.",
            draft_id=None,
        )
    )

    session = api.get_workspace_session()

    assert response.success is True
    assert session.workspace_session_id == "local-workspace-session"
    assert db_path.exists()
    assert session_path.exists()


def test_create_default_workspace_api_can_enable_local_project_agent(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    session_path = tmp_path / "workspace-session.json"
    config_dir = tmp_path / "agent-root" / ".env"
    config_dir.mkdir(parents=True)
    (config_dir / "api_key.md").write_text(
        "Base URL:https://example.test\nAPI Key:test-key\n",
        encoding="utf-8",
    )

    def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": """
                        {
                          "questions": [
                            {
                              "id": "llm-q-1",
                              "prompt": "Why is the first migration checkpoint intentionally stopping at facts?",
                              "intent": "Check migration trade-off reasoning.",
                              "difficulty": "intermediate",
                              "expected_signals": ["facts before graph"],
                              "source_context": ["project-agent"]
                            }
                          ],
                          "generation_summary": "Generated 1 llm-backed question.",
                          "coverage_notes": ["project-grounded", "interview-style"],
                          "warnings": [],
                          "confidence": 0.9
                        }
                        """
                    }
                }
            ]
        }

    monkeypatch.setattr(ProjectAgentQuestionGenerationClient, "_default_transport", staticmethod(fake_transport))

    api = create_default_workspace_api(
        db_path=db_path,
        session_path=session_path,
        use_local_project_agent=True,
        project_agent_root_dir=config_dir.parent,
        project_agent_model="gpt-5.4",
    )

    response = api._flow.generate_question_set(
        {
            "request_id": "req-http-llm-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "project-agent-llm-integration",
            "stage_goal": "switch generation to a real llm-backed project agent",
            "stage_summary": "transport-level llm generation regression",
            "current_decisions": ["split generation-side orchestration"],
            "key_logic_points": ["checkpoint continuity"],
            "known_weak_points": ["output normalization"],
            "boundary_focus": ["project + interview question mix"],
            "question_strategy": "full_depth",
            "max_questions": 1,
            "source_refs": ["docs/spec.md"],
        }
    )

    assert response["request_id"] == "req-http-llm-1"
    assert response["generation_summary"] == "Generated 1 llm-backed question."
    assert response["questions"] == [
        {
            "question_id": "q-1",
            "question_level": "why",
            "prompt": "Why is the first migration checkpoint intentionally stopping at facts?",
            "intent": "Check migration trade-off reasoning.",
            "expected_signals": ["facts before graph"],
            "source_context": ["project-agent"],
        }
    ]

    store = api._flow._store
    assert store is not None
    assert store.get_workflow_request("req-http-llm-1") is not None
    assert store.get_question_batch("qb-req-http-llm-1") is not None


def test_create_default_workspace_api_can_enable_local_evaluator_agent(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    session_path = tmp_path / "workspace-session.json"
    config_dir = tmp_path / "agent-root" / ".env"
    config_dir.mkdir(parents=True)
    (config_dir / "api_key.md").write_text(
        "Base URL:https://example.test\nAPI Key:test-key\n",
        encoding="utf-8",
    )

    def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": """
                        {
                          "assessment": {
                            "score_total": 0.64,
                            "dimension_scores": {
                              "correctness": 3,
                              "reasoning": 2,
                              "decision_awareness": 1,
                              "boundary_awareness": 1,
                              "stability": 2
                            },
                            "verdict": "partial",
                            "grounded_issues": [
                              "Misused sqlite transaction handling.",
                              "No regression test for malformed SSE chunks."
                            ],
                            "misconceptions": [
                              "Treats response_format as optional provider contract."
                            ],
                            "evidence": [
                              {"summary": "Used sqlite connection outside transaction scope."},
                              "Skipped malformed-output regression."
                            ]
                          },
                          "recommended_action": "redirect_to_learning",
                          "recommended_follow_up_questions": ["How would you guard malformed provider output?"],
                          "learning_recommendations": ["Add evaluator-output regression coverage."],
                          "warnings": [],
                          "confidence": 0.76
                        }
                        """
                    }
                }
            ]
        }

    monkeypatch.setattr(EvaluatorAgentAssessmentClient, "_default_transport", staticmethod(fake_transport))

    api = create_default_workspace_api(
        db_path=db_path,
        session_path=session_path,
        use_local_evaluator_agent=True,
        evaluator_agent_root_dir=config_dir.parent,
        evaluator_agent_model="gpt-5.4",
    )

    response = api.submit_answer_action(
        SubmitAnswerRequest(
            request_id="req-http-eval-llm-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-12T11:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="I used sqlite transaction boundaries loosely and I do not have a malformed-SSE regression yet.",
            draft_id=None,
        )
    )

    assert response.success is True
    assert response.result_type == "assessment_created"
    assert response.assessment_summary is not None

    store = api._flow._store
    assert store is not None
    assert store.get_evaluation_batch("eb-req-http-eval-llm-1") is not None
    assert store.get_latest_assessment_fact_batch("proj-1", "stage-1") is not None


def test_http_api_round_trips_workspace_session_between_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    writer = TestClient(create_app(db_path=db_path))

    save_response = writer.put(
        "/api/workspace-session",
        json={
            "workspace_session_id": "local-workspace-session",
            "active_project_id": "proj-1",
            "active_stage_id": "stage-1",
            "active_panel": "questions",
            "active_question_set_id": "set-1",
            "active_question_id": "set-1-q-2",
            "active_profile_space_id": None,
            "active_proposal_center_id": None,
            "last_opened_at": "2026-04-03T00:00:00Z",
            "filters": {},
        },
    )

    assert save_response.status_code == 200

    reader = TestClient(create_app(db_path=db_path))
    load_response = reader.get("/api/workspace-session")

    assert load_response.status_code == 200
    assert load_response.json()["active_project_id"] == "proj-1"
    assert load_response.json()["active_stage_id"] == "stage-1"
    assert load_response.json()["active_question_set_id"] == "set-1"
    assert load_response.json()["active_question_id"] == "set-1-q-2"

def test_http_api_sanitizes_invalid_question_restore_target(tmp_path: Path) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    client = TestClient(create_app(db_path=db_path))

    save_response = client.put(
        "/api/workspace-session",
        json={
            "workspace_session_id": "local-workspace-session",
            "active_project_id": "proj-1",
            "active_stage_id": "stage-1",
            "active_panel": "questions",
            "active_question_set_id": "set-1",
            "active_question_id": "set-1-q-99",
            "active_profile_space_id": None,
            "active_proposal_center_id": None,
            "last_opened_at": "2026-04-03T00:00:00Z",
            "filters": {},
        },
    )

    assert save_response.status_code == 200
    assert save_response.json()["active_project_id"] == "proj-1"
    assert save_response.json()["active_stage_id"] == "stage-1"
    assert save_response.json()["active_question_set_id"] == "set-1"
    assert save_response.json()["active_question_id"] is None

    load_response = client.get("/api/workspace-session")
    assert load_response.status_code == 200
    assert load_response.json()["active_question_set_id"] == "set-1"
    assert load_response.json()["active_question_id"] is None


def test_http_api_sanitizes_invalid_stage_restore_target(tmp_path: Path) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    client = TestClient(create_app(db_path=db_path))

    save_response = client.put(
        "/api/workspace-session",
        json={
            "workspace_session_id": "local-workspace-session",
            "active_project_id": "proj-1",
            "active_stage_id": "stage-99",
            "active_panel": "questions",
            "active_question_set_id": "set-99",
            "active_question_id": "set-99-q-1",
            "active_profile_space_id": None,
            "active_proposal_center_id": None,
            "last_opened_at": "2026-04-03T00:00:00Z",
            "filters": {},
        },
    )

    assert save_response.status_code == 200
    assert save_response.json()["active_project_id"] == "proj-1"
    assert save_response.json()["active_stage_id"] is None
    assert save_response.json()["active_question_set_id"] is None
    assert save_response.json()["active_question_id"] is None
    assert save_response.json()["active_panel"] == "projects"

    load_response = client.get("/api/workspace-session")
    assert load_response.status_code == 200
    assert load_response.json()["active_project_id"] == "proj-1"
    assert load_response.json()["active_stage_id"] is None
    assert load_response.json()["active_panel"] == "projects"
