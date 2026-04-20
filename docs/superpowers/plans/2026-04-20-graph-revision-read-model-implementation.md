# Graph Revision Read Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task in the current session. Do not use subagents for this repository flow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the active `GraphRevision` as a first-class revision-aware read model without extending the legacy profile-space `graph-main` DTO.

**Architecture:** Add dedicated transport DTOs in `review_gate/view_dtos.py`, map active graph revision records in `WorkspaceAPI`, and expose them through `GET /api/knowledge/graph-revision`. The endpoint returns only the new Graph Layer state and deliberately does not fall back to the old profile-space graph.

**Tech Stack:** Python 3, dataclass DTOs via `TransportModel`, FastAPI-style route registration in `review_gate/http_api.py`, SQLite-backed checkpoint store, pytest.

---

## File Map

- Modify: `review_gate/view_dtos.py`
  - Owns transport DTOs used by HTTP and workspace API boundaries.
  - Add `GraphRevisionSummaryDTO`, `GraphRevisionNodeDTO`, and `GraphRevisionViewDTO` next to the existing graph DTOs.
- Modify: `review_gate/workspace_api.py`
  - Owns application-facing read methods.
  - Add active revision lookup, record-to-DTO mapping, and empty-view behavior.
- Modify: `review_gate/http_api.py`
  - Owns HTTP route wiring.
  - Add `GET /api/knowledge/graph-revision`.
- Modify: `tests/test_workspace_api.py`
  - Owns direct WorkspaceAPI contract tests.
  - Add active-revision and no-fallback tests.
- Modify: `tests/test_http_api.py`
  - Owns HTTP contract tests.
  - Add route test that reads submit-side active graph output.

## Boundary Decisions

1. `graph-main` remains the product compatibility read surface.
2. `graph-revision` becomes the new Graph Layer debug and stable-contract read surface.
3. Missing store, missing pointer, and missing revision all return an empty `GraphRevisionViewDTO`.
4. Existing SQLite or programming exceptions are not swallowed.
5. `relations` is returned as an empty list in v1 because `KnowledgeRelationRecord` is not part of this phase.

## Task 1: Add WorkspaceAPI Contract Tests

**Files:**
- Modify: `tests/test_workspace_api.py`

- [ ] **Step 1: Add the active-revision read model test**

Place this test after `test_workspace_api_graph_main_view_reads_active_graph_revision_before_profile_fallback`.

```python
def test_workspace_api_returns_graph_revision_view_for_active_revision(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    _seed_active_graph_revision(store)
    api = WorkspaceAPI(
        flow=ReviewFlowService.for_testing(),
        checkpoint_store=store,
    )

    view = api.get_graph_revision_view("proj-1", "stage-1")

    assert view.project_id == "proj-1"
    assert view.stage_id == "stage-1"
    assert view.has_active_revision is True
    assert view.revision is not None
    assert view.revision.graph_revision_id == "gr-proj-1-stage-stage-1-20260420110000"
    assert view.revision.project_id == "proj-1"
    assert view.revision.scope_type == "stage"
    assert view.revision.scope_ref == "stage-1"
    assert view.revision.revision_type == "deterministic_signal_projection"
    assert view.revision.status == "active"
    assert view.revision.node_count == 1
    assert view.revision.relation_count == 0
    assert view.revision.source_fact_batch_ids == ["afb-eb-req-graph-read"]
    assert view.revision.source_signal_ids == ["ks-graph-read-surface"]
    assert view.revision.created_by == "knowledge_signal_graph_projector"
    assert view.revision.created_at == "2026-04-20T11:00:00Z"
    assert view.revision.activated_at == "2026-04-20T11:00:00Z"
    assert view.revision.revision_summary == "1 signals projected into 1 nodes"
    assert len(view.nodes) == 1
    node = view.nodes[0]
    assert node.knowledge_node_id == "kn-gr-proj-1-stage-stage-1-20260420110000-graph-read-surface"
    assert node.graph_revision_id == "gr-proj-1-stage-stage-1-20260420110000"
    assert node.topic_key == "graph-read-surface"
    assert node.label == "Graph read surface"
    assert node.node_type == "weakness_topic"
    assert node.description == "The read side must consume the active graph revision."
    assert node.source_signal_ids == ["ks-graph-read-surface"]
    assert node.supporting_fact_ids == ["afi-graph-read-surface"]
    assert node.confidence == 0.81
    assert node.status == "active"
    assert node.created_by == "knowledge_signal_graph_projector"
    assert node.created_at == "2026-04-20T11:00:00Z"
    assert node.updated_at == "2026-04-20T11:00:00Z"
    assert node.payload == {"projector_version": "signal-graph-v1"}
    assert view.relations == []
```

- [ ] **Step 2: Add the no-profile-fallback test**

Place this test immediately after the active-revision test.

```python
def test_workspace_api_graph_revision_view_returns_empty_without_active_revision(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    profile_space = ProfileSpaceService.for_testing()
    profile_space.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-profile-fallback",
            "verdict": "partial",
            "core_gaps": ["Profile fallback node"],
            "misconceptions": [],
        },
    )
    api = WorkspaceAPI(
        flow=ReviewFlowService.for_testing(),
        profile_space=profile_space,
        checkpoint_store=store,
    )

    view = api.get_graph_revision_view("proj-1", "stage-1")

    assert view.project_id == "proj-1"
    assert view.stage_id == "stage-1"
    assert view.has_active_revision is False
    assert view.revision is None
    assert view.nodes == []
    assert view.relations == []
```

- [ ] **Step 3: Run the first failing test**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_workspace_api.py::test_workspace_api_returns_graph_revision_view_for_active_revision -q
```

Expected result:

```text
FAILED tests/test_workspace_api.py::test_workspace_api_returns_graph_revision_view_for_active_revision
AttributeError: 'WorkspaceAPI' object has no attribute 'get_graph_revision_view'
```

- [ ] **Step 4: Commit the red tests only if the repository workflow needs a visible red checkpoint**

Default for this repo flow is to skip the red-test-only commit and continue to Task 2, because the current branch already contains an unpushed doc checkpoint.

## Task 2: Add Graph Revision DTOs

**Files:**
- Modify: `review_gate/view_dtos.py`

- [ ] **Step 1: Add DTO classes after `KnowledgeGraphMainViewDTO`**

Insert this code immediately after `KnowledgeGraphMainViewDTO`.

```python
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
class GraphRevisionViewDTO(TransportModel):
    project_id: str
    stage_id: str
    has_active_revision: bool = False
    revision: GraphRevisionSummaryDTO | None = None
    nodes: list[GraphRevisionNodeDTO] = field(default_factory=list)
    relations: list[dict[str, object]] = field(default_factory=list)
```

- [ ] **Step 2: Verify import-level consistency**

Run:

```powershell
$env:PYTHONPATH='.'; python -m py_compile review_gate/view_dtos.py
```

Expected result:

```text
```

The command exits with status 0 and prints no output.

## Task 3: Implement WorkspaceAPI Revision Read Model

**Files:**
- Modify: `review_gate/workspace_api.py`

- [ ] **Step 1: Add DTO imports**

In the `from review_gate.view_dtos import (` block, add these names in alphabetical position with the nearby graph DTOs.

```python
    GraphRevisionNodeDTO,
    GraphRevisionSummaryDTO,
    GraphRevisionViewDTO,
```

- [ ] **Step 2: Add mapping helpers before `_get_active_graph_main_view`**

Insert this code immediately before `_get_active_graph_main_view`.

```python
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
```

- [ ] **Step 3: Add the public read method before `_get_active_graph_main_view`**

Insert this method after the helpers from Step 2.

```python
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
        return GraphRevisionViewDTO(
            project_id=project_id,
            stage_id=stage_id,
            has_active_revision=True,
            revision=self._graph_revision_summary_to_dto(revision),
            nodes=[self._graph_revision_node_to_dto(node) for node in nodes],
            relations=[],
        )
```

- [ ] **Step 4: Run the WorkspaceAPI tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_workspace_api.py::test_workspace_api_returns_graph_revision_view_for_active_revision tests/test_workspace_api.py::test_workspace_api_graph_revision_view_returns_empty_without_active_revision -q
```

Expected result:

```text
2 passed
```

## Task 4: Add HTTP Route Contract Test

**Files:**
- Modify: `tests/test_http_api.py`

- [ ] **Step 1: Add submit-side route test**

Place this test after `test_default_http_api_graph_main_reads_submit_side_active_graph_revision`.

```python
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
```

- [ ] **Step 2: Add empty route test**

Place this test immediately after the submit-side route test.

```python
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
```

- [ ] **Step 3: Run the route test to verify it fails before route implementation**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_http_api.py::test_default_http_api_graph_revision_reads_submit_side_active_revision -q
```

Expected result:

```text
FAILED tests/test_http_api.py::test_default_http_api_graph_revision_reads_submit_side_active_revision
assert 404 == 200
```

## Task 5: Implement HTTP Route

**Files:**
- Modify: `review_gate/http_api.py`

- [ ] **Step 1: Add route after `/api/knowledge/graph-main`**

Insert this route after `get_knowledge_graph_main_view`.

```python
    @app.get("/api/knowledge/graph-revision")
    def get_graph_revision_view(project_id: str, stage_id: str) -> dict:
        return workspace_api.get_graph_revision_view(project_id, stage_id).model_dump()
```

- [ ] **Step 2: Run focused HTTP route tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_http_api.py::test_default_http_api_graph_revision_reads_submit_side_active_revision tests/test_http_api.py::test_default_http_api_graph_revision_returns_empty_without_active_revision -q
```

Expected result:

```text
2 passed
```

## Task 6: Focused Regression

**Files:**
- Validate: `tests/test_workspace_api.py`
- Validate: `tests/test_http_api.py`
- Validate: `tests/test_demo_seed.py`
- Validate: `tests/test_answer_checkpoint_writer.py`
- Validate: `tests/test_knowledge_graph_projector.py`
- Validate: `tests/test_checkpoint_storage.py`

- [ ] **Step 1: Run graph read-model focused tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_workspace_api.py::test_workspace_api_returns_graph_revision_view_for_active_revision tests/test_workspace_api.py::test_workspace_api_graph_revision_view_returns_empty_without_active_revision tests/test_http_api.py::test_default_http_api_graph_revision_reads_submit_side_active_revision tests/test_http_api.py::test_default_http_api_graph_revision_returns_empty_without_active_revision tests/test_http_api.py::test_default_http_api_graph_main_reads_submit_side_active_graph_revision -q
```

Expected result:

```text
5 passed
```

- [ ] **Step 2: Run backend regression around submit-side graph projection**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_workspace_api.py tests/test_http_api.py tests/test_demo_seed.py tests/test_answer_checkpoint_writer.py tests/test_knowledge_graph_projector.py tests/test_checkpoint_storage.py -q
```

Expected result:

```text
All selected tests pass.
```

- [ ] **Step 3: Commit implementation**

Run:

```powershell
git add review_gate/view_dtos.py review_gate/workspace_api.py review_gate/http_api.py tests/test_workspace_api.py tests/test_http_api.py
git commit -m "feat: expose graph revision read model"
```

Expected result:

```text
[main <sha>] feat: expose graph revision read model
```

## Self-Review

Spec coverage:

1. Dedicated DTOs are covered by Task 2.
2. `WorkspaceAPI.get_graph_revision_view(project_id, stage_id)` is covered by Task 3.
3. `GET /api/knowledge/graph-revision` is covered by Tasks 4 and 5.
4. Empty-view behavior for missing active revision is covered by Task 1 and Task 4.
5. No profile-space fallback is covered by `test_workspace_api_graph_revision_view_returns_empty_without_active_revision`.
6. Existing `graph-main` compatibility is protected by Task 6 focused regression.
7. Relations stay empty in v1 and are asserted as `[]`.

Type consistency:

1. DTO names match the design: `GraphRevisionSummaryDTO`, `GraphRevisionNodeDTO`, `GraphRevisionViewDTO`.
2. Workspace method name matches the design: `get_graph_revision_view`.
3. HTTP path matches the design: `/api/knowledge/graph-revision`.
4. Revision scope is stage-based: `get_active_graph_revision_pointer(project_id, "stage", stage_id)`.
