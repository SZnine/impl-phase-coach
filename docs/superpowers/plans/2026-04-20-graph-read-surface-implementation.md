# Graph Read Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task in the current session. Do not use subagents for this repository flow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/api/knowledge/graph-main` read the new active graph revision when available, while preserving the existing profile-space graph fallback.

**Architecture:** `WorkspaceAPI` receives an optional `SQLiteStore` as `checkpoint_store`. `get_knowledge_graph_main_view()` first tries `active_graph_revision_pointer -> graph_revision -> graph_nodes`; if any of those are absent, it falls back to the existing `ProfileSpaceService` implementation. `create_default_workspace_api()` passes the same initialized store to `ReviewFlowService`, profile/proposal services, and `WorkspaceAPI` so submit-then-read works through HTTP.

**Tech Stack:** Python dataclasses, existing `SQLiteStore`, existing `KnowledgeGraphMainViewDTO`, pytest, FastAPI TestClient.

---

## File Structure

- Modify: `review_gate/view_dtos.py`
  - Widen `KnowledgeNodeCardDTO.evidence_summary` from `dict[str, int]` to `dict[str, object]` so graph node provenance can include `topic_key` while preserving numeric evidence counts.

- Modify: `review_gate/workspace_api.py`
  - Accept optional `checkpoint_store`.
  - Add private new-graph read helper.
  - Keep old profile-space graph-main logic as fallback.

- Modify: `review_gate/http_api.py`
  - Pass the initialized `SQLiteStore` into `WorkspaceAPI` inside `create_default_workspace_api()`.

- Modify: `tests/test_workspace_api.py`
  - Add a direct `WorkspaceAPI` test for active graph revision priority.
  - Keep existing profile-space fallback test unchanged.

- Modify: `tests/test_http_api.py`
  - Add submit-then-read HTTP coverage for `/api/knowledge/graph-main` using `create_default_workspace_api(db_path=...)`.

- No changes:
  - `review_gate/answer_checkpoint_writer.py`
  - `review_gate/knowledge_graph_projector.py`
  - `review_gate/storage_sqlite.py`
  - Frontend/UI files

---

### Task 1: Add WorkspaceAPI New Graph Read Test

**Files:**
- Modify: `tests/test_workspace_api.py`

- [ ] **Step 1: Extend imports**

Add these imports near the top of `tests/test_workspace_api.py`:

```python
from review_gate.checkpoint_models import (
    ActiveGraphRevisionPointerRecord,
    GraphRevisionRecord,
    KnowledgeNodeRecord,
)
from review_gate.storage_sqlite import SQLiteStore
```

- [ ] **Step 2: Add active graph seed helper**

Add this helper after `CapturingAssessmentClient`:

```python
def _seed_active_graph_revision(store: SQLiteStore) -> None:
    revision = GraphRevisionRecord(
        graph_revision_id="gr-proj-1-stage-stage-1-20260420110000",
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        revision_type="deterministic_signal_projection",
        based_on_revision_id=None,
        source_fact_batch_ids=["afb-eb-req-graph-read"],
        source_signal_ids=["ks-graph-read-surface"],
        status="active",
        revision_summary="1 signals projected into 1 nodes",
        node_count=1,
        relation_count=0,
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-20T11:00:00Z",
        activated_at="2026-04-20T11:00:00Z",
        payload={"projector_version": "signal-graph-v1"},
    )
    node = KnowledgeNodeRecord(
        knowledge_node_id="kn-gr-proj-1-stage-stage-1-20260420110000-graph-read-surface",
        graph_revision_id=revision.graph_revision_id,
        topic_key="graph-read-surface",
        label="Graph read surface",
        node_type="weakness_topic",
        description="The read side must consume the active graph revision.",
        source_signal_ids=["ks-graph-read-surface"],
        supporting_fact_ids=["afi-graph-read-surface"],
        confidence=0.81,
        status="active",
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-20T11:00:00Z",
        updated_at="2026-04-20T11:00:00Z",
        payload={"projector_version": "signal-graph-v1"},
    )
    pointer = ActiveGraphRevisionPointerRecord(
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        active_graph_revision_id=revision.graph_revision_id,
        updated_at="2026-04-20T11:00:00Z",
        updated_by="knowledge_signal_graph_projector",
        payload={"projector_version": "signal-graph-v1"},
    )
    store.insert_graph_revision(revision)
    store.insert_graph_nodes([node])
    store.upsert_active_graph_revision_pointer(pointer)
```

- [ ] **Step 3: Add failing test for active graph priority**

Add this test after `test_workspace_api_returns_knowledge_map_summary_and_graph_main_view`:

```python
def test_workspace_api_graph_main_view_reads_active_graph_revision_before_profile_fallback(
    tmp_path,
) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    _seed_active_graph_revision(store)
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

    graph_main_view = api.get_knowledge_graph_main_view(project_id="proj-1", stage_id="stage-1")

    assert graph_main_view.selected_cluster is None
    assert graph_main_view.relations == []
    assert len(graph_main_view.nodes) == 1
    node = graph_main_view.nodes[0]
    assert node.node_id == "kn-gr-proj-1-stage-stage-1-20260420110000-graph-read-surface"
    assert node.label == "Graph read surface"
    assert node.node_type == "weakness_topic"
    assert node.abstract_level == "topic"
    assert node.scope == "stage"
    assert node.canonical_summary == "The read side must consume the active graph revision."
    assert node.mastery_status == "unverified"
    assert node.review_needed is True
    assert node.relation_preview == []
    assert node.evidence_summary == {
        "topic_key": "graph-read-surface",
        "confidence_percent": 81,
        "signal_count": 1,
        "fact_count": 1,
    }
```

- [ ] **Step 4: Run the new test and verify RED**

Run:

```bash
$env:PYTHONPATH='.'; pytest tests/test_workspace_api.py::test_workspace_api_graph_main_view_reads_active_graph_revision_before_profile_fallback -q
```

Expected: FAIL with `TypeError: WorkspaceAPI.__init__() got an unexpected keyword argument 'checkpoint_store'`.

---

### Task 2: Implement WorkspaceAPI Active Graph Read Helper

**Files:**
- Modify: `review_gate/view_dtos.py`
- Modify: `review_gate/workspace_api.py`

- [ ] **Step 1: Widen `KnowledgeNodeCardDTO.evidence_summary`**

In `review_gate/view_dtos.py`, replace:

```python
    evidence_summary: dict[str, int] = field(default_factory=dict)
```

with:

```python
    evidence_summary: dict[str, object] = field(default_factory=dict)
```

- [ ] **Step 2: Import `SQLiteStore` in `WorkspaceAPI`**

In `review_gate/workspace_api.py`, add:

```python
from review_gate.storage_sqlite import SQLiteStore
```

- [ ] **Step 3: Accept `checkpoint_store` in `WorkspaceAPI.__init__`**

Replace the constructor signature and body with:

```python
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
```

- [ ] **Step 4: Add active graph helper methods**

Add these private methods before `get_knowledge_graph_main_view()`:

```python
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
                relation_preview=[],
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
            selected_cluster=None,
            nodes=node_cards,
            relations=[],
        )
```

- [ ] **Step 5: Route `get_knowledge_graph_main_view()` through the helper**

At the start of `get_knowledge_graph_main_view()`, before reading from `_profile_space`, add:

```python
        if cluster_id is None and node_id is None:
            active_graph_view = self._get_active_graph_main_view(project_id, stage_id)
            if active_graph_view is not None:
                return active_graph_view
```

Selection parameters still belong to the legacy profile-space graph-main path in this phase. This preserves existing demo/focus-cluster behavior until the new Graph Layer has revision-scoped cluster and node selection semantics.

- [ ] **Step 6: Run the WorkspaceAPI active graph test**

Run:

```bash
$env:PYTHONPATH='.'; pytest tests/test_workspace_api.py::test_workspace_api_graph_main_view_reads_active_graph_revision_before_profile_fallback -q
```

Expected: PASS.

---

### Task 3: Preserve Profile-Space Fallback Behavior

**Files:**
- No new production edits expected.
- Test: `tests/test_workspace_api.py`

- [ ] **Step 1: Run existing fallback test**

Run:

```bash
$env:PYTHONPATH='.'; pytest tests/test_workspace_api.py::test_workspace_api_returns_knowledge_map_summary_and_graph_main_view -q
```

Expected: PASS. This proves that a `WorkspaceAPI` without `checkpoint_store` still uses profile-space graph-main behavior, including `selected_cluster is not None` and `mastery_status == "partial"`.

- [ ] **Step 2: If fallback fails, inspect only `get_knowledge_graph_main_view()`**

Expected fix, if needed: ensure the active graph helper returns `None` when `self._checkpoint_store is None`, so old profile-space code remains reachable.

---

### Task 4: Wire Default WorkspaceAPI Store into Graph Read Surface

**Files:**
- Modify: `review_gate/http_api.py`

- [ ] **Step 1: Pass store to `WorkspaceAPI`**

In `create_default_workspace_api()`, replace:

```python
    return WorkspaceAPI(
        flow=flow,
        profile_space=ProfileSpaceService.with_store(store),
        proposal_center=ProposalCenterService.with_store(store),
        session_store=JsonWorkspaceStateStore(resolved_session_path),
    )
```

with:

```python
    return WorkspaceAPI(
        flow=flow,
        profile_space=ProfileSpaceService.with_store(store),
        proposal_center=ProposalCenterService.with_store(store),
        session_store=JsonWorkspaceStateStore(resolved_session_path),
        checkpoint_store=store,
    )
```

- [ ] **Step 2: Add HTTP submit-then-read test**

In `tests/test_http_api.py`, add this test after `test_http_api_returns_knowledge_map_summary_and_graph_main_views`:

```python
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
    assert graph_data["selected_cluster"] is None
    assert graph_data["relations"] == []
    assert graph_data["nodes"]
    assert graph_data["nodes"][0]["node_type"] == "weakness_topic"
    assert graph_data["nodes"][0]["mastery_status"] == "unverified"
    assert graph_data["nodes"][0]["review_needed"] is True
    assert graph_data["nodes"][0]["evidence_summary"]["signal_count"] == 1
    assert graph_data["nodes"][0]["evidence_summary"]["fact_count"] == 1
```

- [ ] **Step 3: Run the new HTTP test**

Run:

```bash
$env:PYTHONPATH='.'; pytest tests/test_http_api.py::test_default_http_api_graph_main_reads_submit_side_active_graph_revision -q
```

Expected: PASS.

---

### Task 5: Run Focused Regression Suite

**Files:**
- No edits.

- [ ] **Step 1: Run workspace and HTTP graph tests**

Run:

```bash
$env:PYTHONPATH='.'; pytest tests/test_workspace_api.py::test_workspace_api_graph_main_view_reads_active_graph_revision_before_profile_fallback tests/test_workspace_api.py::test_workspace_api_returns_knowledge_map_summary_and_graph_main_view tests/test_http_api.py::test_default_http_api_graph_main_reads_submit_side_active_graph_revision tests/test_http_api.py::test_http_api_returns_knowledge_map_summary_and_graph_main_views -q
```

Expected: PASS.

- [ ] **Step 2: Run full workspace/http/demo seed coverage**

Run:

```bash
$env:PYTHONPATH='.'; pytest tests/test_workspace_api.py tests/test_http_api.py tests/test_demo_seed.py -q
```

Expected: PASS.

- [ ] **Step 3: Run submit-side graph projection regression**

Run:

```bash
$env:PYTHONPATH='.'; pytest tests/test_answer_checkpoint_writer.py tests/test_knowledge_graph_projector.py tests/test_checkpoint_storage.py -q
```

Expected: PASS.

---

### Task 6: Commit the Implementation

**Files:**
- Modify: `review_gate/view_dtos.py`
- Modify: `review_gate/workspace_api.py`
- Modify: `review_gate/http_api.py`
- Modify: `tests/test_workspace_api.py`
- Modify: `tests/test_http_api.py`

- [ ] **Step 1: Inspect the diff**

Run:

```bash
git diff -- review_gate/view_dtos.py review_gate/workspace_api.py review_gate/http_api.py tests/test_workspace_api.py tests/test_http_api.py
```

Expected:
- `WorkspaceAPI` has optional `checkpoint_store`.
- `get_knowledge_graph_main_view()` tries active graph first only when no `cluster_id` or `node_id` is supplied, and falls back to old profile-space logic otherwise.
- `create_default_workspace_api()` passes `checkpoint_store=store`.
- No frontend, relation, maintenance, or projection-write files changed.

- [ ] **Step 2: Commit**

Run:

```bash
git add review_gate/view_dtos.py review_gate/workspace_api.py review_gate/http_api.py tests/test_workspace_api.py tests/test_http_api.py
git commit -m "feat: read active graph revision in graph main view"
```

Expected: commit succeeds.

---

## Self-Review

Spec coverage:
- New graph read path consumes `active_graph_revision_pointer -> graph_revision -> graph_nodes`.
- Missing store, missing pointer, missing revision, empty nodes, or selected `cluster_id` / `node_id` falls back to profile-space behavior.
- Existing `/api/knowledge/graph-main` is reused; no endpoint is added.
- `get_knowledge_graph_view()` stays unchanged.

Intentional exclusions:
- No graph relations.
- No UI rewrite.
- No Maintenance Agent.
- No submit-side write changes.
- No old `ProfileSpaceService` removal.

Type consistency:
- `KnowledgeNodeCardDTO.evidence_summary` is widened to `dict[str, object]` because the spec requires `topic_key` plus numeric counters.
- `checkpoint_store` is optional so existing `WorkspaceAPI(...)` tests and constructors remain compatible.
- New graph path returns `selected_cluster=None` and `relations=[]`, matching current Graph Layer v1 capabilities.

Execution choice for this repo:
- Use inline execution only.
- Do not dispatch subagents.
