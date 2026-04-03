from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from review_gate.action_dtos import ProposalActionRequest, SubmitAnswerRequest
from review_gate.profile_space_service import ProfileSpaceService
from review_gate.proposal_center_service import ProposalCenterService
from review_gate.review_flow_service import ReviewFlowService
from review_gate.storage_sqlite import SQLiteStore
from review_gate.view_dtos import WorkspaceSessionDTO
from review_gate.workspace_api import WorkspaceAPI
from review_gate.workspace_state_store import JsonWorkspaceStateStore


def _default_db_path() -> Path:
    return Path(__file__).resolve().parent.parent / ".workbench" / "review-workbench.sqlite3"


def _default_session_path(db_path: Path) -> Path:
    return db_path.with_name("workspace-session.json")


def create_default_workspace_api(db_path: Path | None = None, session_path: Path | None = None) -> WorkspaceAPI:
    resolved_db_path = db_path or _default_db_path()
    resolved_session_path = session_path or _default_session_path(resolved_db_path)
    store = SQLiteStore(resolved_db_path)
    store.initialize()
    return WorkspaceAPI(
        flow=ReviewFlowService.with_store(store),
        profile_space=ProfileSpaceService.with_store(store),
        proposal_center=ProposalCenterService.with_store(store),
        session_store=JsonWorkspaceStateStore(resolved_session_path),
    )


def create_app(api: WorkspaceAPI | None = None, db_path: Path | None = None) -> FastAPI:
    workspace_api = api or create_default_workspace_api(db_path)
    app = FastAPI(title="Review Workbench API")

    @app.get("/api/workspace-session")
    def get_workspace_session() -> dict:
        return workspace_api.get_workspace_session().model_dump()

    @app.put("/api/workspace-session")
    def put_workspace_session(payload: dict) -> dict:
        request = WorkspaceSessionDTO.model_validate(payload)
        return workspace_api.save_workspace_session(request).model_dump()

    @app.get("/api/home")
    def get_home_view() -> dict:
        return workspace_api.get_home_view().model_dump()

    @app.get("/api/projects/{project_id}")
    def get_project_view(project_id: str) -> dict:
        return workspace_api.get_project_view(project_id).model_dump()

    @app.get("/api/projects/{project_id}/stages/{stage_id}")
    def get_stage_view(project_id: str, stage_id: str) -> dict:
        return workspace_api.get_stage_view(project_id, stage_id).model_dump()

    @app.get("/api/projects/{project_id}/stages/{stage_id}/questions/{question_set_id}")
    def get_question_set_view(project_id: str, stage_id: str, question_set_id: str) -> dict:
        return workspace_api.get_question_set_view(project_id, stage_id, question_set_id).model_dump()

    @app.get("/api/projects/{project_id}/stages/{stage_id}/questions/{question_set_id}/{question_id}")
    def get_question_view(project_id: str, stage_id: str, question_set_id: str, question_id: str) -> dict:
        return workspace_api.get_question_view(project_id, stage_id, question_set_id, question_id).model_dump()

    @app.get("/api/mistakes")
    def get_mistakes_view(project_id: str | None = None, stage_id: str | None = None) -> dict:
        return workspace_api.get_mistakes_view(project_id, stage_id).model_dump()

    @app.get("/api/knowledge/index")
    def get_knowledge_index_view(project_id: str | None = None, stage_id: str | None = None) -> dict:
        return workspace_api.get_knowledge_index_view(project_id, stage_id).model_dump()

    @app.get("/api/knowledge/graph")
    def get_knowledge_graph_view(project_id: str | None = None, stage_id: str | None = None) -> dict:
        return workspace_api.get_knowledge_graph_view(project_id, stage_id).model_dump()

    @app.get("/api/proposals")
    def get_proposals_view() -> dict:
        return workspace_api.get_proposals_view().model_dump()

    @app.post("/api/actions/proposal-action")
    def proposal_action(payload: dict) -> dict:
        request = ProposalActionRequest.model_validate(payload)
        return workspace_api.proposal_action(request).model_dump()

    @app.post("/api/actions/submit-answer")
    def submit_answer(payload: dict) -> dict:
        request = SubmitAnswerRequest.model_validate(payload)
        return workspace_api.submit_answer_action(request).model_dump()

    return app


app = create_app()
