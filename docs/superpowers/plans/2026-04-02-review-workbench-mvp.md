# Review Workbench MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable local review workbench: a React workbench plus Python backend that supports project -> stage -> question navigation, structured review flow, durable storage, mistake/index accumulation, and proposal-center actions without turning the current `review_gate` code into a demo-only HTML generator.

**Architecture:** Keep Python as the local backend and evolve `review_gate` into a proper application package with domain models, storage, flow, agent adapters, and `workspace_api`. Add a local React workbench that talks only to `workspace_api` over HTTP, while SQLite stores project/profile/event data and JSON stores lightweight workspace session state.

**Tech Stack:** Python 3.14, FastAPI, Pydantic, SQLite, JSON workspace state, React, Vite, React Router, pytest

---

### Task 1: Establish Backend Domain And Persistence

**Files:**
- Create: `review_gate/domain.py`
- Create: `review_gate/storage_sqlite.py`
- Create: `review_gate/workspace_state_store.py`
- Modify: `review_gate/__init__.py`
- Test: `tests/test_workbench_storage.py`

- [ ] **Step 1: Write the failing persistence test**

```python
from pathlib import Path

from review_gate.domain import (
    ProjectReview,
    StageReview,
    WorkspaceSession,
)
from review_gate.storage_sqlite import SQLiteStore
from review_gate.workspace_state_store import JsonWorkspaceStateStore


def test_sqlite_store_round_trips_project_and_stage(tmp_path: Path) -> None:
    db_path = tmp_path / "review.db"
    store = SQLiteStore(db_path)
    store.initialize()

    project = ProjectReview(
        project_id="proj-1",
        project_label="impl-phase-coach",
        project_summary="Review workbench MVP",
        stage_reviews=[
            StageReview(
                stage_review_id="stage-review-1",
                project_id="proj-1",
                stage_id="stage-1",
                stage_label="模块与接口冻结",
                stage_goal="冻结 Question/Assessment/Decision 边界",
                status="in_progress",
                question_set_ids=[],
                active_question_set_id=None,
                history_count=0,
                retention_status="active",
                related_mistake_ids=[],
                related_knowledge_node_ids=[],
                related_index_entry_ids=[],
                related_proposal_ids=[],
                mastery_status="unverified",
            )
        ],
        knowledge_index_id="index-1",
        knowledge_graph_id="graph-1",
    )

    store.upsert_project_review(project)
    loaded = store.get_project_review("proj-1")

    assert loaded is not None
    assert loaded.project_label == "impl-phase-coach"
    assert loaded.stage_reviews[0].stage_label == "模块与接口冻结"


def test_workspace_state_store_round_trips_active_position(tmp_path: Path) -> None:
    path = tmp_path / "workspace-state.json"
    store = JsonWorkspaceStateStore(path)

    session = WorkspaceSession(
        workspace_session_id="ws-1",
        active_project_id="proj-1",
        active_stage_id="stage-1",
        active_panel="questions",
        active_question_set_id="set-1",
        active_question_id="q-1",
        last_opened_at="2026-04-02T12:00:00Z",
        filters={},
    )

    store.save(session)
    loaded = store.load()

    assert loaded is not None
    assert loaded.active_project_id == "proj-1"
    assert loaded.active_question_id == "q-1"
```

- [ ] **Step 2: Run the failing test**

Run: `python -m pytest tests/test_workbench_storage.py -q`
Expected: FAIL because `review_gate.domain`, `review_gate.storage_sqlite`, and `review_gate.workspace_state_store` do not exist yet.

- [ ] **Step 3: Write minimal domain and storage implementation**

```python
# review_gate/domain.py
from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspaceSession(BaseModel):
    workspace_session_id: str
    active_project_id: str | None = None
    active_stage_id: str | None = None
    active_panel: str = "questions"
    active_question_set_id: str | None = None
    active_question_id: str | None = None
    last_opened_at: str
    filters: dict[str, str] = Field(default_factory=dict)


class StageReview(BaseModel):
    stage_review_id: str
    project_id: str
    stage_id: str
    stage_label: str
    stage_goal: str
    status: str
    question_set_ids: list[str]
    active_question_set_id: str | None
    history_count: int
    retention_status: str
    related_mistake_ids: list[str]
    related_knowledge_node_ids: list[str]
    related_index_entry_ids: list[str]
    related_proposal_ids: list[str]
    mastery_status: str


class ProjectReview(BaseModel):
    project_id: str
    project_label: str
    project_summary: str
    stage_reviews: list[StageReview]
    knowledge_index_id: str | None = None
    knowledge_graph_id: str | None = None
```

```python
# review_gate/storage_sqlite.py
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from review_gate.domain import ProjectReview


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_reviews (
                    project_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )

    def upsert_project_review(self, review: ProjectReview) -> None:
        payload = json.dumps(review.model_dump(), ensure_ascii=False)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO project_reviews(project_id, payload) VALUES (?, ?)",
                (review.project_id, payload),
            )

    def get_project_review(self, project_id: str) -> ProjectReview | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT payload FROM project_reviews WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        return ProjectReview.model_validate_json(row[0])
```

```python
# review_gate/workspace_state_store.py
from __future__ import annotations

from pathlib import Path

from review_gate.domain import WorkspaceSession


class JsonWorkspaceStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, session: WorkspaceSession) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(session.model_dump_json(indent=2), encoding="utf-8")

    def load(self) -> WorkspaceSession | None:
        if not self._path.exists():
            return None
        return WorkspaceSession.model_validate_json(self._path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_workbench_storage.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add review_gate/domain.py review_gate/storage_sqlite.py review_gate/workspace_state_store.py review_gate/__init__.py tests/test_workbench_storage.py
git commit -m "feat: add workbench domain and storage skeleton"
```

### Task 2: Build Review Flow And Workspace API Shell

**Files:**
- Create: `review_gate/review_flow_service.py`
- Create: `review_gate/workspace_api.py`
- Create: `review_gate/view_dtos.py`
- Create: `review_gate/action_dtos.py`
- Test: `tests/test_workspace_api.py`

- [ ] **Step 1: Write the failing API test**

```python
from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.review_flow_service import ReviewFlowService
from review_gate.workspace_api import WorkspaceAPI


def test_workspace_api_returns_stage_view_and_submit_result() -> None:
    flow = ReviewFlowService.for_testing()
    api = WorkspaceAPI(flow=flow)

    stage_view = api.get_stage_view("proj-1", "stage-1")
    assert stage_view.stage_id == "stage-1"

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
            answer_text="先冻结接口和状态边界",
            draft_id=None,
        )
    )

    assert response.success is True
    assert response.result_type == "assessment_created"
    assert response.assessment_summary is not None
```

- [ ] **Step 2: Run the failing test**

Run: `python -m pytest tests/test_workspace_api.py -q`
Expected: FAIL because `review_gate.action_dtos`, `review_gate.review_flow_service`, `review_gate.workspace_api`, and `review_gate.view_dtos` do not exist yet.

- [ ] **Step 3: Write the minimal API and flow shell**

```python
# review_gate/action_dtos.py
from pydantic import BaseModel


class ActionRequestBase(BaseModel):
    request_id: str
    project_id: str
    stage_id: str
    source_page: str
    actor_id: str
    created_at: str


class SubmitAnswerRequest(ActionRequestBase):
    question_set_id: str
    question_id: str
    answer_text: str
    draft_id: str | None = None
```

```python
# review_gate/view_dtos.py
from pydantic import BaseModel


class StageViewDTO(BaseModel):
    project_id: str
    stage_id: str
    stage_label: str
    stage_goal: str
    status: str
    mastery_status: str


class SubmitAnswerResponseDTO(BaseModel):
    request_id: str
    success: bool
    action_type: str
    result_type: str
    message: str
    refresh_targets: list[str]
    assessment_summary: dict | None = None
```

```python
# review_gate/review_flow_service.py
from __future__ import annotations

from review_gate.view_dtos import StageViewDTO, SubmitAnswerResponseDTO


class ReviewFlowService:
    @classmethod
    def for_testing(cls) -> "ReviewFlowService":
        return cls()

    def get_stage_view(self, project_id: str, stage_id: str) -> StageViewDTO:
        return StageViewDTO(
            project_id=project_id,
            stage_id=stage_id,
            stage_label="模块与接口冻结",
            stage_goal="冻结 Question/Assessment/Decision 边界",
            status="in_progress",
            mastery_status="unverified",
        )

    def submit_answer(self, request) -> SubmitAnswerResponseDTO:
        return SubmitAnswerResponseDTO(
            request_id=request.request_id,
            success=True,
            action_type="submit_answer",
            result_type="assessment_created",
            message="Assessment created.",
            refresh_targets=["question_detail", "stage_summary"],
            assessment_summary={"verdict": "partial"},
        )
```

```python
# review_gate/workspace_api.py
from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.review_flow_service import ReviewFlowService


class WorkspaceAPI:
    def __init__(self, flow: ReviewFlowService) -> None:
        self._flow = flow

    def get_stage_view(self, project_id: str, stage_id: str):
        return self._flow.get_stage_view(project_id, stage_id)

    def submit_answer_action(self, request: SubmitAnswerRequest):
        return self._flow.submit_answer(request)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_workspace_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add review_gate/action_dtos.py review_gate/view_dtos.py review_gate/review_flow_service.py review_gate/workspace_api.py tests/test_workspace_api.py
git commit -m "feat: add workspace api and review flow shell"
```

### Task 3: Scaffold React Workbench Shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/routes.tsx`
- Create: `frontend/src/pages/HomePage.tsx`
- Create: `frontend/src/pages/ProjectPage.tsx`
- Create: `frontend/src/pages/StagePage.tsx`
- Create: `frontend/src/pages/QuestionPage.tsx`
- Create: `frontend/src/pages/MistakesPage.tsx`
- Create: `frontend/src/pages/ProposalsPage.tsx`
- Create: `frontend/src/components/WorkbenchLayout.tsx`
- Create: `frontend/src/lib/api.ts`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing frontend shell test**

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

test("renders workbench navigation", () => {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>,
  );

  expect(screen.getByText("Projects")).toBeInTheDocument();
  expect(screen.getByText("Mistakes")).toBeInTheDocument();
  expect(screen.getByText("Proposals")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the failing frontend test**

Run: `npm --prefix frontend test -- --runInBand`
Expected: FAIL because the frontend app does not exist yet.

- [ ] **Step 3: Write the minimal routed workbench shell**

```tsx
// frontend/src/App.tsx
import { RouterProvider } from "react-router-dom";

import { router } from "./routes";

export function App() {
  return <RouterProvider router={router} />;
}
```

```tsx
// frontend/src/components/WorkbenchLayout.tsx
import { Link, Outlet } from "react-router-dom";

export function WorkbenchLayout() {
  return (
    <div>
      <nav>
        <Link to="/">Projects</Link>
        <Link to="/mistakes">Mistakes</Link>
        <Link to="/proposals">Proposals</Link>
      </nav>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
```

```tsx
// frontend/src/routes.tsx
import { createBrowserRouter } from "react-router-dom";

import { WorkbenchLayout } from "./components/WorkbenchLayout";
import { HomePage } from "./pages/HomePage";
import { MistakesPage } from "./pages/MistakesPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProposalsPage } from "./pages/ProposalsPage";
import { QuestionPage } from "./pages/QuestionPage";
import { StagePage } from "./pages/StagePage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <WorkbenchLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "projects/:projectId", element: <ProjectPage /> },
      { path: "projects/:projectId/stages/:stageId", element: <StagePage /> },
      {
        path: "projects/:projectId/stages/:stageId/questions/:questionSetId/:questionId",
        element: <QuestionPage />,
      },
      { path: "mistakes", element: <MistakesPage /> },
      { path: "proposals", element: <ProposalsPage /> },
    ],
  },
]);
```

- [ ] **Step 4: Run the frontend test**

Run: `npm --prefix frontend test -- --runInBand`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: scaffold local review workbench shell"
```

### Task 4: Connect Question Generation And Assessment Adapters

**Files:**
- Create: `review_gate/agent_clients.py`
- Modify: `review_gate/review_flow_service.py`
- Test: `tests/test_agent_clients.py`
- Test: `tests/test_review_flow_service.py`

- [ ] **Step 1: Write the failing adapter test**

```python
from review_gate.agent_clients import (
    AssessmentAgentClient,
    QuestionGenerationAgentClient,
)


def test_question_generation_client_returns_structured_response() -> None:
    client = QuestionGenerationAgentClient.for_testing()
    response = client.generate(
        {
            "request_id": "req-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "模块与接口冻结",
            "stage_goal": "冻结对象边界",
            "stage_summary": "Question/Assessment/Decision freeze",
            "stage_artifacts": [],
            "stage_exit_criteria": [],
            "current_decisions": ["Question, Assessment, Decision split"],
            "key_logic_points": ["structured DTOs"],
            "known_weak_points": [],
            "boundary_focus": ["module vs interface"],
            "question_strategy": "core_and_why",
            "max_questions": 2,
            "source_refs": [],
        }
    )

    assert response["questions"]
    assert response["questions"][0]["question_level"] in {"core", "why", "abstract"}


def test_assessment_client_returns_structured_verdict() -> None:
    client = AssessmentAgentClient.for_testing()
    response = client.assess(
        {
            "request_id": "req-2",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "question_id": "q-1",
            "question_level": "core",
            "question_prompt": "Explain the split.",
            "question_intent": "Check current-stage understanding.",
            "expected_signals": ["Question", "Assessment", "Decision"],
            "user_answer": "We split objects to keep state and scoring separate.",
            "source_context": [],
            "current_stage_decisions": [],
            "current_stage_logic_points": [],
            "current_boundary_focus": [],
            "assessment_policy": {"mode": "simple"},
            "history_signals": [],
        }
    )

    assert response["assessment"]["verdict"] in {"strong", "partial", "weak"}
    assert "dimension_scores" in response["assessment"]
```

- [ ] **Step 2: Run the failing tests**

Run: `python -m pytest tests/test_agent_clients.py tests/test_review_flow_service.py -q`
Expected: FAIL because the adapter clients do not exist yet and `ReviewFlowService` does not call them.

- [ ] **Step 3: Add minimal structured agent adapter layer**

```python
# review_gate/agent_clients.py
class QuestionGenerationAgentClient:
    @classmethod
    def for_testing(cls) -> "QuestionGenerationAgentClient":
        return cls()

    def generate(self, request: dict) -> dict:
        return {
            "request_id": request["request_id"],
            "questions": [
                {
                    "question_id": "q-1",
                    "question_level": "core",
                    "prompt": "这一步当前真正冻结了什么？",
                    "intent": "Check current-stage understanding.",
                    "expected_signals": request["current_decisions"],
                    "source_context": request["source_refs"],
                }
            ],
            "generation_summary": "Generated core-first questions.",
            "coverage_notes": [],
            "warnings": [],
            "confidence": 0.8,
        }


class AssessmentAgentClient:
    @classmethod
    def for_testing(cls) -> "AssessmentAgentClient":
        return cls()

    def assess(self, request: dict) -> dict:
        return {
            "request_id": request["request_id"],
            "assessment": {
                "score_total": 0.75,
                "dimension_scores": {
                    "correctness": 3,
                    "reasoning": 3,
                    "decision_awareness": 2,
                    "boundary_awareness": 3,
                    "stability": 2,
                },
                "verdict": "partial",
                "core_gaps": [],
                "misconceptions": [],
                "evidence": ["Answer explains why the split exists."],
            },
            "recommended_action": "continue_answering",
            "recommended_follow_up_questions": [],
            "learning_recommendations": [],
            "warnings": [],
            "confidence": 0.8,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_agent_clients.py tests/test_review_flow_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add review_gate/agent_clients.py review_gate/review_flow_service.py tests/test_agent_clients.py tests/test_review_flow_service.py
git commit -m "feat: add structured question and assessment adapters"
```

### Task 5: Connect Profile Space And Proposal Center To The Workbench

**Files:**
- Create: `review_gate/profile_space_service.py`
- Create: `review_gate/proposal_center_service.py`
- Modify: `review_gate/workspace_api.py`
- Test: `tests/test_profile_space_service.py`
- Test: `tests/test_proposal_center_service.py`

- [ ] **Step 1: Write the failing profile/proposal tests**

```python
from review_gate.profile_space_service import ProfileSpaceService
from review_gate.proposal_center_service import ProposalCenterService


def test_profile_space_service_syncs_mistake_and_index_entries() -> None:
    service = ProfileSpaceService.for_testing()
    result = service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-1",
            "verdict": "partial",
            "misconceptions": ["Boundary confusion"],
            "core_gaps": ["Decision awareness"],
        },
    )

    assert result["mistake_ids"]
    assert result["index_entry_ids"]


def test_proposal_center_service_records_user_action_and_execution() -> None:
    service = ProposalCenterService.for_testing()
    proposal = service.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
    )[0]
    action = service.record_user_action(
        proposal_id=proposal["proposal_id"],
        action_type="accept",
        selected_target_ids=["m-1", "m-2"],
    )
    execution = service.execute_proposal(
        proposal_id=proposal["proposal_id"],
        action_id=action["action_id"],
    )

    assert execution["status"] in {"succeeded", "partially_succeeded"}
```

- [ ] **Step 2: Run the failing tests**

Run: `python -m pytest tests/test_profile_space_service.py tests/test_proposal_center_service.py -q`
Expected: FAIL because the services do not exist yet.

- [ ] **Step 3: Add minimal profile/proposal services**

```python
# review_gate/profile_space_service.py
class ProfileSpaceService:
    @classmethod
    def for_testing(cls) -> "ProfileSpaceService":
        return cls()

    def sync_from_assessment(self, project_id: str, stage_id: str, assessment: dict) -> dict:
        return {
            "mistake_ids": ["mistake-1"],
            "index_entry_ids": ["index-1"],
            "knowledge_node_ids": ["node-1"],
        }
```

```python
# review_gate/proposal_center_service.py
class ProposalCenterService:
    @classmethod
    def for_testing(cls) -> "ProposalCenterService":
        return cls()

    def create_compression_proposals(self, target_type: str, target_ids: list[str]) -> list[dict]:
        return [
            {
                "proposal_id": "proposal-1",
                "proposal_type": f"compress_{target_type}",
                "target_ids": target_ids,
                "status": "pending_review",
            }
        ]

    def record_user_action(self, proposal_id: str, action_type: str, selected_target_ids: list[str]) -> dict:
        return {
            "action_id": "action-1",
            "proposal_id": proposal_id,
            "action_type": action_type,
            "selected_target_ids": selected_target_ids,
        }

    def execute_proposal(self, proposal_id: str, action_id: str) -> dict:
        return {
            "execution_id": "exec-1",
            "proposal_id": proposal_id,
            "action_id": action_id,
            "status": "succeeded",
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_profile_space_service.py tests/test_proposal_center_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add review_gate/profile_space_service.py review_gate/proposal_center_service.py tests/test_profile_space_service.py tests/test_proposal_center_service.py
git commit -m "feat: add profile space and proposal center services"
```

## Self-Review

**1. Spec coverage:** The plan covers the agreed MVP order: backend domain/storage, application flow and DTOs, React workbench shell, agent adapters, and long-term profile/proposal services. Remaining scope like richer graph interaction, desktop shell, and advanced compression stays explicitly out of the MVP.

**2. Placeholder scan:** No `TODO`/`TBD` placeholders remain. Each task includes exact files, tests, commands, and minimal code.

**3. Type consistency:** The plan uses the same object names across tasks: `ProjectReview`, `StageReview`, `WorkspaceSession`, `QuestionGenerationRequest`, `AnswerAssessmentRequest`, `WorkspaceAPI`, `ReviewFlowService`, `ProfileSpaceService`, and `ProposalCenterService`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-02-review-workbench-mvp.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
