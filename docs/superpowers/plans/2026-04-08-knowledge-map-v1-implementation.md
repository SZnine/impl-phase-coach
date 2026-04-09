# Knowledge Map V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable knowledge-map slice on top of the existing review workbench: durable knowledge nodes, evidence refs, user node state, minimal relations, user-side focus clusters, and a read-only summary/main-view flow.

**Architecture:** Extend the current `ProfileSpaceService` from mistake/index/node accumulation into a real knowledge-map owner. Keep facts in the existing review-flow path, then project them into `KnowledgeNode`, `EvidenceRef`, `UserNodeState`, `KnowledgeRelation`, and `FocusCluster`. Expose the map only through `workspace_api/http_api/api.ts`, with a summary page plus a graph main view; do not implement graph editing, merge execution, or global cluster templates in this plan.

**Tech Stack:** Python dataclasses, SQLite, FastAPI, pytest, React, Vite, React Router, Vitest

---

### Task 1: Add Knowledge Map Core Domain Objects And SQLite Tables

**Files:**
- Modify: `review_gate/domain.py`
- Modify: `review_gate/storage_sqlite.py`
- Test: `tests/test_workbench_storage.py`

- [ ] **Step 1: Write the failing persistence test**

```python
from pathlib import Path

from review_gate.domain import EvidenceRef, FocusCluster, KnowledgeNode, KnowledgeRelation, UserNodeState
from review_gate.storage_sqlite import SQLiteStore


def test_sqlite_store_round_trips_knowledge_map_objects(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()

    node = KnowledgeNode(
        node_id="node-1",
        profile_space_id="profile-space:proj-1",
        label="State and return value separation",
        node_type="concept",
        abstract_level="L2",
        scope="universal",
        canonical_summary="Separate persisted state from function return values.",
        source_refs=["assessment-1"],
        seed_or_generated="generated",
        status="active",
    )
    evidence = EvidenceRef(
        evidence_id="evidence-1",
        profile_space_id="profile-space:proj-1",
        node_id="node-1",
        evidence_type="assessment",
        ref_id="assessment-1",
        project_id="proj-1",
        stage_id="stage-1",
        summary="Assessment exposed boundary confusion.",
    )
    state = UserNodeState(
        profile_space_id="profile-space:proj-1",
        node_id="node-1",
        activation_status="active",
        mastery_status="partial",
        review_needed=True,
        weak_signal_count=2,
        linked_project_count=1,
        last_seen_at="2026-04-08T16:00:00Z",
        confidence=0.72,
    )
    relation = KnowledgeRelation(
        relation_id="relation-1",
        profile_space_id="profile-space:proj-1",
        source_node_id="node-1",
        target_node_id="node-2",
        relation_type="supports",
        strength=2,
        evidence_ids=["evidence-1"],
        status="active",
    )
    cluster = FocusCluster(
        cluster_id="cluster-1",
        profile_space_id="profile-space:proj-1",
        title="State boundary hotspot",
        center_node_id="node-1",
        neighbor_node_ids=["node-2", "node-3"],
        focus_reason_codes=["current_project_hit", "weak_signal_active"],
        focus_reason_summary="Current stage exposed a repeated boundary weakness.",
        generated_from="current_project",
        confidence=0.81,
        last_generated_at="2026-04-08T16:05:00Z",
        is_pinned=False,
        status="active",
    )

    store.upsert_knowledge_node(node)
    store.upsert_evidence_ref(evidence)
    store.upsert_user_node_state(state)
    store.upsert_knowledge_relation(relation)
    store.upsert_focus_cluster(cluster)

    assert store.get_knowledge_node("node-1") == node
    assert store.list_evidence_refs(node_id="node-1") == [evidence]
    assert store.get_user_node_state("profile-space:proj-1", "node-1") == state
    assert store.list_knowledge_relations(source_node_id="node-1") == [relation]
    assert store.list_focus_clusters(profile_space_id="profile-space:proj-1") == [cluster]
```

- [ ] **Step 2: Run the failing test**

Run: `python -m pytest tests/test_workbench_storage.py::test_sqlite_store_round_trips_knowledge_map_objects -q`
Expected: FAIL because the new domain types and SQLite helpers do not exist yet.

- [ ] **Step 3: Implement the minimal domain and SQLite support**

```python
@dataclass(slots=True)
class KnowledgeNode(JsonSerializable):
    node_id: str
    profile_space_id: str
    label: str
    node_type: str
    abstract_level: str
    scope: str
    canonical_summary: str
    source_refs: list[str] = field(default_factory=list)
    seed_or_generated: str = "generated"
    status: str = "active"


@dataclass(slots=True)
class EvidenceRef(JsonSerializable):
    evidence_id: str
    profile_space_id: str
    node_id: str
    evidence_type: str
    ref_id: str
    project_id: str
    stage_id: str
    summary: str


@dataclass(slots=True)
class UserNodeState(JsonSerializable):
    profile_space_id: str
    node_id: str
    activation_status: str
    mastery_status: str
    review_needed: bool
    weak_signal_count: int
    linked_project_count: int
    last_seen_at: str
    confidence: float


@dataclass(slots=True)
class KnowledgeRelation(JsonSerializable):
    relation_id: str
    profile_space_id: str
    source_node_id: str
    target_node_id: str
    relation_type: str
    strength: int
    evidence_ids: list[str] = field(default_factory=list)
    status: str = "active"


@dataclass(slots=True)
class FocusCluster(JsonSerializable):
    cluster_id: str
    profile_space_id: str
    title: str
    center_node_id: str
    neighbor_node_ids: list[str] = field(default_factory=list)
    focus_reason_codes: list[str] = field(default_factory=list)
    focus_reason_summary: str = ""
    generated_from: str = "current_project"
    confidence: float = 0.0
    last_generated_at: str = ""
    is_pinned: bool = False
    status: str = "active"
```

Add SQLite tables and helpers:
- `knowledge_node_store`
- `evidence_ref_store`
- `user_node_state_store`
- `knowledge_relation_store`
- `focus_cluster_store`

- [ ] **Step 4: Re-run the focused test**

Run: `python -m pytest tests/test_workbench_storage.py::test_sqlite_store_round_trips_knowledge_map_objects -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add review_gate/domain.py review_gate/storage_sqlite.py tests/test_workbench_storage.py
git commit -m "feat: add durable knowledge map core objects"
```

---

### Task 2: Project Assessment Signals Into Durable Nodes, Evidence, And User State

**Files:**
- Modify: `review_gate/profile_space_service.py`
- Modify: `review_gate/storage_sqlite.py`
- Test: `tests/test_profile_space_service.py`

- [ ] **Step 1: Write the failing service test**

```python
from pathlib import Path

from review_gate.profile_space_service import ProfileSpaceService
from review_gate.storage_sqlite import SQLiteStore


def test_sync_from_assessment_creates_node_evidence_and_user_state(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    service = ProfileSpaceService.with_store(store)

    result = service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "assessment-1",
            "verdict": "partial",
            "core_gaps": ["State and return value separation"],
            "misconceptions": ["Boundary confusion"],
        },
    )

    assert result["knowledge_node_ids"]
    assert result["evidence_ids"]
    assert result["user_node_state_ids"]

    nodes = service.list_knowledge_nodes(project_id="proj-1", stage_id="stage-1")
    assert nodes[0]["label"] == "State and return value separation"

    states = service.list_user_node_states(project_id="proj-1", stage_id="stage-1")
    assert states[0]["mastery_status"] == "partial"
```

- [ ] **Step 2: Run the failing test**

Run: `python -m pytest tests/test_profile_space_service.py::test_sync_from_assessment_creates_node_evidence_and_user_state -q`
Expected: FAIL because `ProfileSpaceService` only persists mistake/index/node dicts today.

- [ ] **Step 3: Implement the minimum projection logic**

```python
def sync_from_assessment(self, project_id: str, stage_id: str, assessment: dict) -> dict:
    profile_space_id = self._profile_space_id(project_id)
    node = KnowledgeNode(...)
    evidence = EvidenceRef(...)
    state = UserNodeState(...)

    self._store.upsert_knowledge_node(node)
    self._store.upsert_evidence_ref(evidence)
    self._store.upsert_user_node_state(state)

    return {
        "knowledge_node_ids": [node.node_id],
        "evidence_ids": [evidence.evidence_id],
        "user_node_state_ids": [f"{profile_space_id}:{node.node_id}"],
    }
```

Also add service reads:
- `list_knowledge_nodes(...)`
- `list_evidence_refs(...)`
- `list_user_node_states(...)`

- [ ] **Step 4: Re-run the focused service tests**

Run: `python -m pytest tests/test_profile_space_service.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add review_gate/profile_space_service.py review_gate/storage_sqlite.py tests/test_profile_space_service.py
git commit -m "feat: sync durable knowledge map assets from assessments"
```

---

### Task 3: Add Minimal Relations, Focus Clusters, And Knowledge Map Read DTOs

**Files:**
- Modify: `review_gate/profile_space_service.py`
- Modify: `review_gate/view_dtos.py`
- Modify: `review_gate/workspace_api.py`
- Modify: `review_gate/http_api.py`
- Test: `tests/test_workspace_api.py`
- Test: `tests/test_http_api.py`

- [ ] **Step 1: Write the failing API test**

```python
from review_gate.http_api import create_app


def test_http_api_returns_knowledge_map_summary_and_graph_views(tmp_path) -> None:
    app = create_app(db_path=tmp_path / "review.sqlite3", session_state_path=tmp_path / "workspace-session.json")
    client = TestClient(app)

    summary = client.get("/api/knowledge").json()
    graph = client.get("/api/knowledge/graph").json()

    assert summary["focus_clusters"]
    assert "foundation_hotspots" in summary
    assert "current_weak_spots" in summary
    assert "nodes" in graph
    assert "selected_cluster" in graph
```

- [ ] **Step 2: Run the failing tests**

Run: `python -m pytest tests/test_workspace_api.py tests/test_http_api.py -q`
Expected: FAIL because there is no knowledge-map summary DTO or endpoint today.

- [ ] **Step 3: Add minimal DTOs and read APIs**

```python
@dataclass(slots=True)
class FocusClusterCardDTO(TransportModel):
    cluster_id: str
    title: str
    center_node_id: str
    neighbor_node_ids: list[str]
    focus_reason_codes: list[str]
    focus_reason_summary: str


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
    evidence_summary: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class KnowledgeGraphMainViewDTO(TransportModel):
    selected_cluster: FocusClusterCardDTO | None
    nodes: list[KnowledgeGraphNodeDTO] = field(default_factory=list)
    relations: list[dict[str, str]] = field(default_factory=list)
    node_card: KnowledgeNodeCardDTO | None = None
```

Add APIs:
- `WorkspaceAPI.get_knowledge_map_summary_view()`
- `WorkspaceAPI.get_knowledge_graph_main_view(cluster_id: str | None = None, node_id: str | None = None)`
- HTTP routes:
  - `GET /api/knowledge`
  - `GET /api/knowledge/graph-main`

- [ ] **Step 4: Re-run the focused API tests**

Run: `python -m pytest tests/test_workspace_api.py tests/test_http_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add review_gate/profile_space_service.py review_gate/view_dtos.py review_gate/workspace_api.py review_gate/http_api.py tests/test_workspace_api.py tests/test_http_api.py
git commit -m "feat: expose knowledge map summary and graph views"
```

---

### Task 4: Add Knowledge Map Summary Page And Upgrade The Graph Main View

**Files:**
- Create: `frontend/src/pages/KnowledgeMapPage.tsx`
- Create: `frontend/src/components/KnowledgeNodeCard.tsx`
- Modify: `frontend/src/pages/KnowledgeGraphPage.tsx`
- Modify: `frontend/src/routes.tsx`
- Modify: `frontend/src/components/WorkbenchLayout.tsx`
- Modify: `frontend/src/lib/api.ts`
- Test: `frontend/src/lib/api.test.ts`
- Test: `frontend/src/read-pages.test.tsx`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing frontend tests**

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

test("knowledge nav points to summary page", () => {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>,
  );

  expect(screen.getByRole("link", { name: "Knowledge" })).toHaveAttribute("href", "/knowledge");
});
```

```tsx
test("knowledge summary page renders focus clusters", async () => {
  const client = createApiClient("/api", mockFetch);
  render(
    <ApiClientProvider client={client}>
      <MemoryRouter initialEntries={["/knowledge"]}>
        <KnowledgeMapPage />
      </MemoryRouter>
    </ApiClientProvider>,
  );

  expect(await screen.findByText("Current focus clusters")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the failing frontend tests**

Run: `npm --prefix frontend test -- src/lib/api.test.ts src/read-pages.test.tsx src/App.test.tsx`
Expected: FAIL because `/knowledge` and the summary page do not exist yet.

- [ ] **Step 3: Implement the minimal summary + main view UI**

Add API client methods:
- `getKnowledgeMapSummaryView()`
- `getKnowledgeGraphMainView(clusterId?: string, nodeId?: string)`

Add routes:
- `/knowledge` -> `KnowledgeMapPage`
- `/knowledge/graph` -> existing `KnowledgeGraphPage`

Update nav label from `Knowledge Graph` to `Knowledge` for the summary entry, and keep a secondary entry point into the graph main view from the summary cards.

`KnowledgeMapPage` should render only:
1. Current focus clusters
2. Current weak spots
3. Foundation hotspots
4. Links into graph main view

`KnowledgeGraphPage` should render only:
1. Selected cluster header
2. 1-hop nodes plus selected 2-hop preview
3. Relation list / simple edge summary
4. `KnowledgeNodeCard` side panel

- [ ] **Step 4: Re-run the frontend tests**

Run: `npm --prefix frontend test -- src/lib/api.test.ts src/read-pages.test.tsx src/App.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/KnowledgeMapPage.tsx frontend/src/components/KnowledgeNodeCard.tsx frontend/src/pages/KnowledgeGraphPage.tsx frontend/src/routes.tsx frontend/src/components/WorkbenchLayout.tsx frontend/src/lib/api.ts frontend/src/lib/api.test.ts frontend/src/read-pages.test.tsx frontend/src/App.test.tsx
git commit -m "feat: add knowledge map summary and graph entry views"
```

---

### Task 5: Lock Scope Boundaries With Integration Regression

**Files:**
- Modify: `tests/test_http_api.py`
- Modify: `frontend/src/read-pages.test.tsx`
- Modify: `docs/superpowers/handoffs/2026-04-08-current-state-handoff.md`

- [ ] **Step 1: Add the regression checks**

Add one backend integration assertion that proves:
1. evidence refs are not emitted as top-level graph nodes in the default map views
2. summary view returns focus clusters rather than raw project-answer lists

Add one frontend assertion that proves:
1. `/knowledge` is the entry page
2. `/knowledge/graph` is a deeper main-view route, not the default landing page

- [ ] **Step 2: Run the package-level regressions**

Run: `python -m pytest tests/test_workbench_storage.py tests/test_profile_space_service.py tests/test_workspace_api.py tests/test_http_api.py -q`
Expected: PASS.

Run: `npm --prefix frontend test`
Expected: PASS.

Run: `npm --prefix frontend run build`
Expected: PASS.

- [ ] **Step 3: Update the handoff and commit**

Update the current handoff with:
1. knowledge-map v1 object status
2. summary page route status
3. remaining non-goals: governance, editing, global cluster templates

```bash
git add tests/test_http_api.py frontend/src/read-pages.test.tsx docs/superpowers/handoffs/2026-04-08-current-state-handoff.md
git commit -m "docs: record knowledge map v1 implementation baseline"
```

---

### Task 6: Generate Minimal Relations And Stabilize Focus Clusters

**Files:**
- Modify: `review_gate/profile_space_service.py`
- Test: `tests/test_profile_space_service.py`

- [ ] **Step 1: Add failing tests for minimal structure**

Lock two behaviors:
1. `sync_from_assessment(...)` generates:
   - `abstracts`
   - `causes_mistake`
2. repeated assessments for the same stage hotspot reuse one `FocusCluster`

- [ ] **Step 2: Implement the minimum deterministic relation projection**

Only generate:
1. `abstracts`
2. `causes_mistake`

Do not expand to broad `supports / depends_on` inference yet.

- [ ] **Step 3: Stabilize FocusCluster ids**

Use a stable hotspot key:
- `project + stage + hotspot slug`

This stage keeps `FocusCluster` as a user-side object, not a global cluster template system.

- [ ] **Step 4: Re-run focused backend tests**

Run:
- `python -m pytest tests/test_profile_space_service.py -q`

Expected: PASS.

---

### Task 7: Add Focus Explanation Cache And Cache-First Fallback

**Files:**
- Modify: `review_gate/domain.py`
- Modify: `review_gate/storage_sqlite.py`
- Modify: `review_gate/profile_space_service.py`
- Modify: `review_gate/workspace_api.py`
- Test: `tests/test_workbench_storage.py`
- Test: `tests/test_profile_space_service.py`
- Test: `tests/test_workspace_api.py`

- [ ] **Step 1: Add the explanation object and store**

Introduce a small explanation cache object:
- `FocusExplanation`

It should persist:
1. `subject_type`
2. `subject_id`
3. `reason_codes`
4. `summary`
5. `generated_by`
6. `generated_at`
7. `version`

- [ ] **Step 2: Write deterministic explanation cache entries**

When `sync_from_assessment(...)` updates a `FocusCluster`, also write or refresh a deterministic `FocusExplanation`.

- [ ] **Step 3: Make workspace_api cache-first**

`workspace_api` should:
1. prefer cached explanation text
2. fall back to cluster summary or deterministic fallback only when cache is missing

This must not introduce realtime LLM dependency into page reads.

- [ ] **Step 4: Re-run focused backend regressions**

Run:
- `python -m pytest tests/test_workbench_storage.py::test_sqlite_store_round_trips_knowledge_map_objects -q`
- `python -m pytest tests/test_profile_space_service.py -q`
- `python -m pytest tests/test_workspace_api.py -q`

Expected: PASS.

---

### Task 8: Extract A Replaceable Explanation Generator Strategy

**Files:**
- Add: `review_gate/explanation_generators.py`
- Modify: `review_gate/profile_space_service.py`
- Test: `tests/test_profile_space_service.py`

- [ ] **Step 1: Introduce a minimal generator protocol**

Add a small strategy boundary:
1. `FocusExplanationGenerator`
2. `DeterministicFocusExplanationGenerator`

The generator must produce a `FocusExplanation`, not raw strings.

- [ ] **Step 2: Move deterministic explanation building behind the strategy**

`ProfileSpaceService` should no longer own explanation phrasing directly.
Instead it should:
1. accept a generator dependency
2. call the generator when writing explanation cache
3. keep the cache/store path unchanged

- [ ] **Step 3: Keep read behavior unchanged**

This task must not change:
1. `workspace_api` cache-first behavior
2. DTO shape
3. frontend page reads

The point is strategy replacement, not API replacement.

- [ ] **Step 4: Re-run focused backend tests**

Run:
- `python -m pytest tests/test_profile_space_service.py -q`
- `python -m pytest tests/test_workspace_api.py -q`

Expected: PASS.

---

### LLM Explanation Adoption Gate

This plan does **not** immediately switch to a realtime or default LLM explanation generator.

The next explanation upgrade should happen only when at least **2** of the following become true:

1. deterministic explanation text has become obviously repetitive and is no longer helping users distinguish why one focus cluster matters more than another
2. `focus_reason_codes` and evidence summaries are already stable enough that explanation quality is now limited more by expression than by weak underlying signals
3. the knowledge-map summary page has become a high-frequency entry point and explanation quality is clearly affecting product value
4. explanation refresh can run asynchronously and write cache without entering the page-read critical path
5. the team is willing to absorb one more quality-regression surface for explanation output

When that gate is reached, the first LLM adoption should still keep these boundaries:

1. add `LlmFocusExplanationGenerator` as an alternative generator, not a replacement for the cache/store shape
2. write explanation results into cache asynchronously
3. keep page reads `cache first`
4. retain deterministic fallback

In other words:

- current stage: `deterministic default strategy`
- future upgrade: `LLM as an explanation enhancement layer, not a realtime dependency`

---

### Task 9: Add High-Confidence Supports Relations

**Files:**
- Modify: `review_gate/profile_space_service.py`
- Test: `tests/test_profile_space_service.py`
- Regression: `tests/test_workspace_api.py`
- Regression: `tests/test_http_api.py`

- [ ] **Step 1: Lock supports generation behind explicit support signals**

Do not infer `supports` from raw co-occurrence.

Only generate `supports` when an assessment carries explicit `support_signals`.

- [ ] **Step 2: Restrict supports to the first high-confidence set**

Only allow:
1. `foundation -> concept`
2. `foundation -> method`
3. `concept -> decision`

Do not expand to `depends_on`, multi-hop supports, or LLM relation generation in this task.

- [ ] **Step 3: Keep relation ids stable and idempotent**

Repeated assessments for the same support pair should reuse a stable `supports` relation id instead of creating duplicates.

- [ ] **Step 4: Re-run focused regressions**

Run:
- `python -m pytest tests/test_profile_space_service.py -q`
- `python -m pytest tests/test_workspace_api.py tests/test_http_api.py -q`

Expected: PASS.

---

### Task 10: Derive Support Signals From Structured Assessment Signals

**Files:**
- Modify: assessment production path where structured scoring signals are assembled
- Modify: `review_gate/profile_space_service.py`
- Test: focused assessment-to-profile projection tests

- [ ] **Step 1: Freeze the allowed derivation sources**

Only allow `support_signals` to be derived from:
1. `core_gaps + support_basis tags`
2. `dimension_hits + core_gaps`

Do not derive `supports` from:
1. raw `answer_text`
2. explanation prose
3. keyword co-occurrence
4. unstructured reasoning paragraphs

- [ ] **Step 2: Extend support signal payload with basis metadata**

Derived `support_signals` should include:
1. `source_label`
2. `source_node_type`
3. `target_label`
4. `target_node_type`
5. `basis_type`
6. `basis_key`

The goal is not “more supports”, but “auditable high-confidence supports”.

- [ ] **Step 3: Keep relation generation deterministic**

This task must not:
1. introduce realtime LLM relation generation
2. expand to `depends_on`
3. infer supports from free-form text

- [ ] **Step 4: Freeze the contract boundary conservatively**

After this task lands:
1. treat `dimension_hits`, `support_basis_tags`, and `support_signals` as stable internal assessment-schema fields inside the review-flow path
2. do not yet freeze them as a formal external assessment client contract
3. keep `ProfileSpaceService` consuming these fields as structured internal signals rather than exposing them as required client-facing payload

---

### Task 11: Lightly Strengthen The Graph Main View

**Files:**
- Modify: `frontend/src/pages/KnowledgeGraphPage.tsx`
- Test: `frontend/src/read-pages.test.tsx`

- [ ] **Step 1: Strengthen center-node hierarchy**

Make the selected cluster center node visually stronger than neighbor nodes.
Do this without changing `KnowledgeNodeCard` ownership or introducing a new graph interaction state machine.

- [ ] **Step 2: Add a lightweight relation overview**

Expose at least:
1. visible node count
2. visible relation count
3. visible relation-type count

Keep this as a summary strip inside the existing graph main page.

- [ ] **Step 3: Group visible relations by type**

Render the current cluster relations grouped by `relation_type`, for example:
1. `abstracts`
2. `causes_mistake`
3. `supports`

This task improves graph readability only. It must not:
1. change relation generation rules
2. add new backend endpoints
3. introduce drag/zoom/force-layout behavior

- [ ] **Step 4: Make relations easier to trace back to node cards**

Relation rows should more clearly point back to the related node cards in the current page scope.
Keep this lightweight, for example via anchor links or stable in-page targeting.

---

## Self-Review

**1. Spec coverage:**
- Covers the first five core objects from the knowledge-map core model: `KnowledgeNode`, `EvidenceRef`, `UserNodeState`, `KnowledgeRelation`, `FocusCluster`.
- Extends the v1 plan with:
  - minimal relation generation
  - focus-cluster stabilization
  - cache-first explanation reads
- Covers the agreed first-entry flow: summary page first, graph main view second.
- Keeps evidence anchors out of the default main graph surface.
- Keeps LLM governance, merge execution, complex editing, and global cluster templates out of scope.
- Separates explanation cache hosting from explanation generation strategy without introducing realtime LLM dependency.
- Adds a minimal high-confidence `supports` slice without expanding into broad semantic relation inference.
- Keeps the next `support_signals` step constrained to structured assessment derivation rather than free-text inference.

**2. Placeholder scan:**
- No `TODO` / `TBD` placeholders remain.
- Every task has exact files, tests, commands, and implementation direction.

**3. Type consistency:**
- The plan consistently uses `KnowledgeNode`, `EvidenceRef`, `UserNodeState`, `KnowledgeRelation`, `FocusCluster`, `FocusExplanation`, `FocusExplanationGenerator`, `KnowledgeMapSummaryViewDTO`, and `KnowledgeGraphMainViewDTO` across all tasks.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-08-knowledge-map-v1-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
