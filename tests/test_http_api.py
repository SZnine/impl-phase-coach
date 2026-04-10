from pathlib import Path

from fastapi.testclient import TestClient

from review_gate.action_dtos import ProposalActionRequest, SubmitAnswerRequest
from review_gate.http_api import create_app, create_default_workspace_api
from review_gate.profile_space_service import ProfileSpaceService
from review_gate.proposal_center_service import ProposalCenterService
from review_gate.review_flow_service import ReviewFlowService
from review_gate.workspace_api import WorkspaceAPI


def create_client() -> TestClient:
    return TestClient(create_app(api=WorkspaceAPI(flow=ReviewFlowService.for_testing())))


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

    assert response.success is True
    assert db_path.exists()
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
