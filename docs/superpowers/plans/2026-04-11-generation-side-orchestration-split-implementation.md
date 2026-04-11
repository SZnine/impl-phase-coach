# Generation-Side Orchestration Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract generation-side checkpoint persistence and question-set event publishing out of `ReviewFlowService` so the transport-facing service no longer owns the heaviest `generate_question_set` assembly.

**Architecture:** Introduce `QuestionCheckpointWriter` to persist `Workflow -> Question` checkpoint records and `QuestionSetGenerationPublisher` to publish `question_set_generated` events with stable generation ordering. Keep DTOs, submit-side split, SQLite schema, and Graph/Maintenance unchanged; this stage only thins the generation side of the application-layer orchestration.

**Tech Stack:** Python 3.14, dataclasses, existing `SQLiteStore`, pytest

---

## File Structure

### New files

- `review_gate/question_checkpoint_writer.py`
  - Owns generation-side checkpoint persistence for `WorkflowRequest`, `WorkflowRun`, `QuestionBatch`, and `QuestionItem`.
- `review_gate/question_set_generation_publisher.py`
  - Owns `question_set_generated` event publishing and `generation_index` calculation.
- `tests/test_question_checkpoint_writer.py`
  - Unit tests for generation-side checkpoint persistence and transport question id mapping.
- `tests/test_question_set_generation_publisher.py`
  - Unit tests for generation event publishing, same-stage/set ordering, and malformed-index handling.

### Modified files

- `review_gate/review_flow_service.py`
  - Shrinks to question-generation client invocation, `question_set_id` resolution, writer/publisher coordination, and unchanged transport response return.
- `tests/test_review_flow_service.py`
  - Regression coverage that `generate_question_set` delegates correctly while keeping current response shape.

### Files explicitly out of scope

- `review_gate/storage_sqlite.py`
- `review_gate/http_api.py`
- `review_gate/workspace_api.py`
- `review_gate/answer_checkpoint_writer.py`
- Graph / Maintenance / Focus files

---

### Task 1: Extract generation-side checkpoint persistence into its own writer

**Files:**
- Create: `review_gate/question_checkpoint_writer.py`
- Create: `tests/test_question_checkpoint_writer.py`

- [ ] **Step 1: Write the failing writer tests**

```python
from pathlib import Path

from review_gate.checkpoint_models import (
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)
from review_gate.question_checkpoint_writer import (
    PersistedQuestionGeneration,
    QuestionCheckpointWriter,
)
from review_gate.storage_sqlite import SQLiteStore


def test_question_checkpoint_writer_persists_generation_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = QuestionCheckpointWriter(store=store)

    result = writer.write(
        request={
            "request_id": "req-qgen-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_goal": "freeze submit boundary",
            "created_at": "2026-04-11T09:00:00Z",
        },
        response={
            "questions": [
                {
                    "question_id": "q-1",
                    "question_level": "core",
                    "prompt": "Explain the boundary.",
                    "intent": "Check understanding.",
                    "expected_signals": ["Question, Assessment, Decision split"],
                    "source_context": [],
                },
                {
                    "question_id": "q-2",
                    "question_level": "why",
                    "prompt": "Why this boundary?",
                    "intent": "Check reasoning.",
                    "expected_signals": ["module vs interface"],
                    "source_context": [],
                },
            ]
        },
        question_set_id="set-1",
    )

    assert result == PersistedQuestionGeneration(
        workflow_run_id="run-req-qgen-1",
        question_batch_id="qb-req-qgen-1",
        question_item_ids=["req-qgen-1-q-1", "req-qgen-1-q-2"],
        question_set_id="set-1",
    )
    assert store.get_workflow_request("req-qgen-1") == WorkflowRequestRecord(
        request_id="req-qgen-1",
        request_type="question_cycle",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="question_generation_client",
        source="review_flow_service",
        status="completed",
        created_at="2026-04-11T09:00:00Z",
        payload={
            "request": {
                "request_id": "req-qgen-1",
                "project_id": "proj-1",
                "stage_id": "stage-1",
                "stage_goal": "freeze submit boundary",
                "created_at": "2026-04-11T09:00:00Z",
            }
        },
    )
    assert store.get_workflow_run("run-req-qgen-1") == WorkflowRunRecord(
        run_id="run-req-qgen-1",
        request_id="req-qgen-1",
        run_type="question_cycle",
        status="completed",
        started_at="2026-04-11T09:00:00Z",
        finished_at="2026-04-11T09:00:00Z",
        supersedes_run_id=None,
        payload={"question_count": 2, "request_id": "req-qgen-1"},
    )
    assert store.get_question_batch("qb-req-qgen-1") == QuestionBatchRecord(
        question_batch_id="qb-req-qgen-1",
        workflow_run_id="run-req-qgen-1",
        project_id="proj-1",
        stage_id="stage-1",
        generated_by="question_generation_client",
        source="review_flow_service",
        batch_goal="freeze submit boundary",
        entry_question_id="req-qgen-1-q-1",
        status="active",
        created_at="2026-04-11T09:00:00Z",
        payload={"question_count": 2, "request_id": "req-qgen-1"},
    )
    assert store.list_question_items("qb-req-qgen-1") == [
        QuestionItemRecord(
            question_id="req-qgen-1-q-1",
            question_batch_id="qb-req-qgen-1",
            question_type="core",
            prompt="Explain the boundary.",
            intent="Check understanding.",
            difficulty_level="core",
            order_index=0,
            status="ready",
            created_at="2026-04-11T09:00:00Z",
            payload={
                "expected_signals": ["Question, Assessment, Decision split"],
                "source_context": [],
                "transport_question_id": "set-1-q-1",
            },
        ),
        QuestionItemRecord(
            question_id="req-qgen-1-q-2",
            question_batch_id="qb-req-qgen-1",
            question_type="why",
            prompt="Why this boundary?",
            intent="Check reasoning.",
            difficulty_level="why",
            order_index=1,
            status="ready",
            created_at="2026-04-11T09:00:00Z",
            payload={
                "expected_signals": ["module vs interface"],
                "source_context": [],
                "transport_question_id": "set-1-q-2",
            },
        ),
    ]


def test_question_checkpoint_writer_keeps_existing_transport_question_ids(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = QuestionCheckpointWriter(store=store)

    result = writer.write(
        request={
            "request_id": "req-qgen-2",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_goal": "freeze submit boundary",
            "created_at": "2026-04-11T09:05:00Z",
        },
        response={
            "questions": [
                {
                    "question_id": "set-1-q-1",
                    "question_level": "core",
                    "prompt": "Explain the boundary.",
                    "intent": "Check understanding.",
                    "expected_signals": [],
                    "source_context": [],
                }
            ]
        },
        question_set_id="set-1",
    )

    assert result.question_item_ids == ["req-qgen-2-set-1-q-1"]
    assert store.list_question_items("qb-req-qgen-2")[0].payload["transport_question_id"] == "set-1-q-1"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_question_checkpoint_writer.py -q`  
Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `review_gate.question_checkpoint_writer`

- [ ] **Step 3: Implement the writer**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from review_gate.checkpoint_models import (
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)
from review_gate.storage_sqlite import SQLiteStore


@dataclass(slots=True)
class PersistedQuestionGeneration:
    workflow_run_id: str
    question_batch_id: str
    question_item_ids: list[str]
    question_set_id: str


class QuestionCheckpointWriter:
    def __init__(self, *, store: SQLiteStore) -> None:
        self._store = store

    def write(
        self,
        *,
        request: dict[str, Any],
        response: dict[str, Any],
        question_set_id: str,
    ) -> PersistedQuestionGeneration:
        request_id = str(request["request_id"])
        created_at = str(request.get("created_at", ""))
        workflow_run_id = f"run-{request_id}"
        question_batch_id = f"qb-{request_id}"
        questions = list(response.get("questions", []))

        self._store.insert_workflow_request(
            WorkflowRequestRecord(
                request_id=request_id,
                request_type="question_cycle",
                project_id=str(request["project_id"]),
                stage_id=str(request["stage_id"]),
                requested_by="question_generation_client",
                source="review_flow_service",
                status="completed",
                created_at=created_at,
                payload={"request": dict(request)},
            )
        )
        self._store.insert_workflow_run(
            WorkflowRunRecord(
                run_id=workflow_run_id,
                request_id=request_id,
                run_type="question_cycle",
                status="completed",
                started_at=created_at,
                finished_at=created_at,
                supersedes_run_id=None,
                payload={"question_count": len(questions), "request_id": request_id},
            )
        )

        question_items: list[QuestionItemRecord] = []
        for index, item in enumerate(questions):
            raw_question_id = str(item.get("question_id", f"q-{index + 1}"))
            persisted_question_id = f"{request_id}-{raw_question_id}"
            transport_question_id = self._build_transport_question_id(
                question_set_id=question_set_id,
                raw_question_id=raw_question_id,
            )
            question_items.append(
                QuestionItemRecord(
                    question_id=persisted_question_id,
                    question_batch_id=question_batch_id,
                    question_type=str(item.get("question_level", "core")),
                    prompt=str(item.get("prompt", "")),
                    intent=str(item.get("intent", "")),
                    difficulty_level=str(item.get("question_level", "core")),
                    order_index=index,
                    status="ready",
                    created_at=created_at,
                    payload={
                        "expected_signals": list(item.get("expected_signals", [])),
                        "source_context": list(item.get("source_context", [])),
                        "transport_question_id": transport_question_id,
                    },
                )
            )

        self._store.insert_question_batch(
            QuestionBatchRecord(
                question_batch_id=question_batch_id,
                workflow_run_id=workflow_run_id,
                project_id=str(request["project_id"]),
                stage_id=str(request["stage_id"]),
                generated_by="question_generation_client",
                source="review_flow_service",
                batch_goal=str(request.get("stage_goal", "")),
                entry_question_id=(question_items[0].question_id if question_items else ""),
                status="active",
                created_at=created_at,
                payload={"question_count": len(question_items), "request_id": request_id},
            )
        )
        self._store.insert_question_items(question_items)

        return PersistedQuestionGeneration(
            workflow_run_id=workflow_run_id,
            question_batch_id=question_batch_id,
            question_item_ids=[item.question_id for item in question_items],
            question_set_id=question_set_id,
        )

    def _build_transport_question_id(self, *, question_set_id: str, raw_question_id: str) -> str:
        if not question_set_id:
            return raw_question_id
        if raw_question_id.startswith(f"{question_set_id}-"):
            return raw_question_id
        return f"{question_set_id}-{raw_question_id}"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_question_checkpoint_writer.py -q`  
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add review_gate/question_checkpoint_writer.py tests/test_question_checkpoint_writer.py
git commit -m "feat: extract question checkpoint writer"
```

---

### Task 2: Extract question-set event publishing into its own publisher

**Files:**
- Create: `review_gate/question_set_generation_publisher.py`
- Create: `tests/test_question_set_generation_publisher.py`

- [ ] **Step 1: Write the failing publisher tests**

```python
from pathlib import Path

from review_gate.domain import WorkspaceEvent
from review_gate.question_set_generation_publisher import QuestionSetGenerationPublisher
from review_gate.storage_sqlite import SQLiteStore


def test_question_set_generation_publisher_appends_indexed_event(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    publisher = QuestionSetGenerationPublisher(store=store)

    event = publisher.publish(
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        request_id="req-qgen-1",
        created_at="2026-04-11T09:00:00Z",
        question_batch_id="qb-req-qgen-1",
        workflow_run_id="run-req-qgen-1",
        question_item_ids=["req-qgen-1-q-1", "req-qgen-1-q-2"],
    )

    assert event == WorkspaceEvent(
        event_id="evt-question-set-generated-00000001-req-qgen-1",
        project_id="proj-1",
        event_type="question_set_generated",
        created_at="2026-04-11T09:00:00Z",
        payload={
            "generation_index": 1,
            "stage_id": "stage-1",
            "question_set_id": "set-1",
            "question_batch_id": "qb-req-qgen-1",
            "workflow_run_id": "run-req-qgen-1",
            "question_item_ids": ["req-qgen-1-q-1", "req-qgen-1-q-2"],
        },
    )
    assert store.list_events(project_id="proj-1") == [event]


def test_question_set_generation_publisher_ignores_other_scopes_and_bad_indexes(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    publisher = QuestionSetGenerationPublisher(store=store)
    store.append_event(
        WorkspaceEvent(
            event_id="evt-question-set-generated-00000005-other",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="2026-04-11T08:55:00Z",
            payload={
                "generation_index": 5,
                "stage_id": "stage-2",
                "question_set_id": "set-9",
                "question_batch_id": "qb-other",
                "workflow_run_id": "run-other",
                "question_item_ids": [],
            },
        )
    )
    store.append_event(
        WorkspaceEvent(
            event_id="evt-question-set-generated-bad-index",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="2026-04-11T08:56:00Z",
            payload={
                "generation_index": "bad",
                "stage_id": "stage-1",
                "question_set_id": "set-1",
                "question_batch_id": "qb-old",
                "workflow_run_id": "run-old",
                "question_item_ids": [],
            },
        )
    )

    event = publisher.publish(
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        request_id="req-qgen-2",
        created_at="2026-04-11T09:00:00Z",
        question_batch_id="qb-req-qgen-2",
        workflow_run_id="run-req-qgen-2",
        question_item_ids=["req-qgen-2-q-1"],
    )

    assert event.payload["generation_index"] == 1
    assert event.event_id == "evt-question-set-generated-00000001-req-qgen-2"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_question_set_generation_publisher.py -q`  
Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `review_gate.question_set_generation_publisher`

- [ ] **Step 3: Implement the publisher**

```python
from __future__ import annotations

from review_gate.domain import WorkspaceEvent
from review_gate.storage_sqlite import SQLiteStore


class QuestionSetGenerationPublisher:
    def __init__(self, *, store: SQLiteStore) -> None:
        self._store = store

    def publish(
        self,
        *,
        project_id: str,
        stage_id: str,
        question_set_id: str,
        request_id: str,
        created_at: str,
        question_batch_id: str,
        workflow_run_id: str,
        question_item_ids: list[str],
    ) -> WorkspaceEvent:
        generation_index = self._next_generation_index(
            project_id=project_id,
            stage_id=stage_id,
            question_set_id=question_set_id,
        )
        event = WorkspaceEvent(
            event_id=f"evt-question-set-generated-{generation_index:08d}-{request_id}",
            project_id=project_id,
            event_type="question_set_generated",
            created_at=created_at,
            payload={
                "generation_index": generation_index,
                "stage_id": stage_id,
                "question_set_id": question_set_id,
                "question_batch_id": question_batch_id,
                "workflow_run_id": workflow_run_id,
                "question_item_ids": list(question_item_ids),
            },
        )
        self._store.append_event(event)
        return event

    def _next_generation_index(self, *, project_id: str, stage_id: str, question_set_id: str) -> int:
        latest_generation_index = 0
        for event in self._store.list_events(project_id=project_id):
            if event.event_type != "question_set_generated":
                continue
            if str(event.payload.get("stage_id", "")) != stage_id:
                continue
            if str(event.payload.get("question_set_id", "")) != question_set_id:
                continue
            try:
                latest_generation_index = max(
                    latest_generation_index,
                    int(event.payload.get("generation_index", 0)),
                )
            except (TypeError, ValueError):
                continue
        return latest_generation_index + 1
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_question_set_generation_publisher.py -q`  
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add review_gate/question_set_generation_publisher.py tests/test_question_set_generation_publisher.py
git commit -m "feat: extract question set generation publisher"
```

---

### Task 3: Shrink ReviewFlowService generation-side orchestration

**Files:**
- Modify: `review_gate/review_flow_service.py`
- Modify: `tests/test_review_flow_service.py`

- [ ] **Step 1: Add the failing delegation regression**

```python
class CapturingQuestionCheckpointWriter:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def write(self, **kwargs) -> PersistedQuestionGeneration:
        self.calls.append(dict(kwargs))
        return PersistedQuestionGeneration(
            workflow_run_id="run-req-qgen-1",
            question_batch_id="qb-req-qgen-1",
            question_item_ids=["req-qgen-1-q-1", "req-qgen-1-q-2"],
            question_set_id="set-1",
        )


class CapturingQuestionSetGenerationPublisher:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def publish(self, **kwargs) -> WorkspaceEvent:
        self.calls.append(dict(kwargs))
        return WorkspaceEvent(
            event_id="evt-question-set-generated-00000001-req-qgen-1",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="2026-04-11T09:00:00Z",
            payload=dict(kwargs),
        )


def test_generate_question_set_delegates_checkpoint_persistence_and_event_publish(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    question_set = _semantic_question_set()
    store.upsert_question_set(question_set)
    service = ReviewFlowService.with_store(store)
    writer = CapturingQuestionCheckpointWriter()
    publisher = CapturingQuestionSetGenerationPublisher()
    service._question_checkpoint_writer = writer
    service._question_set_generation_publisher = publisher

    response = service.generate_question_set(
        {
            "request_id": "req-qgen-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_goal": "freeze submit boundary",
            "created_at": "2026-04-11T09:00:00Z",
            "question_strategy": "core_and_why",
            "max_questions": 2,
            "source_refs": [],
        }
    )

    assert response["request_id"] == "req-qgen-1"
    assert len(writer.calls) == 1
    assert writer.calls[0]["question_set_id"] == "set-1"
    assert len(publisher.calls) == 1
    assert publisher.calls[0]["question_batch_id"] == "qb-req-qgen-1"
    assert publisher.calls[0]["workflow_run_id"] == "run-req-qgen-1"
    assert publisher.calls[0]["question_item_ids"] == ["req-qgen-1-q-1", "req-qgen-1-q-2"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_review_flow_service.py::test_generate_question_set_delegates_checkpoint_persistence_and_event_publish -q`  
Expected: FAIL because `ReviewFlowService` still persists the generation checkpoint directly

- [ ] **Step 3: Refactor ReviewFlowService**

```python
# review_gate/review_flow_service.py
from review_gate.question_checkpoint_writer import QuestionCheckpointWriter
from review_gate.question_set_generation_publisher import QuestionSetGenerationPublisher


class ReviewFlowService:
    def __init__(
        self,
        *,
        question_generation_client: QuestionGenerationAgentClient | None = None,
        assessment_client: AssessmentAgentClient | None = None,
        store: SQLiteStore | None = None,
    ) -> None:
        self._question_generation_client = question_generation_client or QuestionGenerationAgentClient.for_testing()
        self._assessment_client = assessment_client or AssessmentAgentClient.for_testing()
        self._assessment_synthesizer = AssessmentSynthesizer()
        self._store = store
        self._question_checkpoint_writer = QuestionCheckpointWriter(store=store) if store is not None else None
        self._question_set_generation_publisher = (
            QuestionSetGenerationPublisher(store=store) if store is not None else None
        )

    def generate_question_set(self, request: dict) -> dict:
        response = self._question_generation_client.generate(request)
        if self._store is not None and self._question_checkpoint_writer is not None:
            question_set_id = self._resolve_stage_question_set_id(
                project_id=str(request["project_id"]),
                stage_id=str(request["stage_id"]),
            )
            persisted = self._question_checkpoint_writer.write(
                request=request,
                response=response,
                question_set_id=question_set_id,
            )
            if question_set_id and self._question_set_generation_publisher is not None:
                self._question_set_generation_publisher.publish(
                    project_id=str(request["project_id"]),
                    stage_id=str(request["stage_id"]),
                    question_set_id=question_set_id,
                    request_id=str(request["request_id"]),
                    created_at=str(request.get("created_at", "")),
                    question_batch_id=persisted.question_batch_id,
                    workflow_run_id=persisted.workflow_run_id,
                    question_item_ids=persisted.question_item_ids,
                )
        return response
```

- [ ] **Step 4: Remove the old generation-side direct persistence helpers**

Delete from `review_gate/review_flow_service.py`:
- `_persist_question_generation_checkpoint`
- `_next_question_set_generation_index`
- `_coerce_generation_index`

Keep:
- `_resolve_stage_question_set_id`

- [ ] **Step 5: Run focused regressions**

Run: `python -m pytest tests/test_question_checkpoint_writer.py tests/test_question_set_generation_publisher.py tests/test_review_flow_service.py -q`  
Expected: PASS

- [ ] **Step 6: Run compatibility regressions**

Run: `python -m pytest tests/test_workspace_api.py tests/test_http_api.py -q`  
Expected: PASS with unchanged response shape

- [ ] **Step 7: Commit**

```bash
git add review_gate/question_checkpoint_writer.py review_gate/question_set_generation_publisher.py review_gate/review_flow_service.py tests/test_question_checkpoint_writer.py tests/test_question_set_generation_publisher.py tests/test_review_flow_service.py
git commit -m "refactor: split generation checkpoint orchestration"
```

---

### Task 4: Freeze the generation-side orchestration boundary

**Files:**
- Modify: `tests/test_http_api.py` only if a transport-level generation regression is needed
- Modify: `docs/superpowers/plans/2026-04-10-post-checkpoint-migration-checklist.md` only if review notes truly need updating

- [ ] **Step 1: Run the full checkpoint regression set**

Run: `python -m pytest tests/test_assessment_synthesizer.py tests/test_checkpoint_storage.py tests/test_generated_chain_resolver.py tests/test_answer_checkpoint_writer.py tests/test_question_checkpoint_writer.py tests/test_question_set_generation_publisher.py tests/test_review_flow_service.py tests/test_workspace_api.py tests/test_http_api.py -q`  
Expected: PASS

- [ ] **Step 2: Verify ReviewFlowService no longer owns the heaviest generation-side assembly**

Run: `rg -n "insert_workflow_request|insert_workflow_run|insert_question_batch|insert_question_items|append_event|generation_index" review_gate/review_flow_service.py`  
Expected: only thin coordination references remain; no direct generation-side record construction or event publishing helpers remain

- [ ] **Step 3: Commit any final test/doc updates**

```bash
git add tests/test_http_api.py docs/superpowers/plans/2026-04-10-post-checkpoint-migration-checklist.md
git commit -m "test: freeze generation orchestration split boundary"
```

---

## Review checkpoints

1. After Task 1, verify `QuestionCheckpointWriter` owns only generation-side checkpoint records and transport question id mapping.
2. After Task 2, verify `QuestionSetGenerationPublisher` owns only generation event publishing and generation-index ordering.
3. After Task 3, verify `ReviewFlowService` is thinner and generation-side direct persistence/event logic has moved out.
4. After Task 4, verify the full checkpoint regression set still passes before moving to Graph / Maintenance.

---

## Frozen Boundary For This Plan

1. This plan only splits generation-side application orchestration.
2. `ReviewFlowService` remains the transitional transport-facing orchestration owner after this plan, but with reduced `generate_question_set` responsibility.
3. The SQLite schema from the first migration checkpoint remains unchanged.
4. Submit-side resolver/writer split remains unchanged in this plan.
5. No Graph-layer tables, read models, focus logic, or maintenance workflows are implemented here.
6. HTTP and workspace DTOs remain unchanged during this split.
