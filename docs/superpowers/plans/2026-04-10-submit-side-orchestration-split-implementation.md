# Submit-Side Orchestration Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract submit-side checkpoint orchestration out of `ReviewFlowService` so generated-chain resolution and checkpoint persistence stop growing inside the transport-facing service.

**Architecture:** Introduce two application-layer components: `GeneratedChainResolver` for reuse/fallback resolution and `AnswerCheckpointWriter` for building and persisting the submit-side checkpoint chain. Keep DTOs, Graph/Maintenance, and SQLite schema unchanged; this stage is a boundary split, not a feature expansion.

**Tech Stack:** Python 3.14, dataclasses, existing `SQLiteStore`, pytest

---

## File Structure

### New files

- `review_gate/generated_chain_resolver.py`
  - Owns generated-chain lookup, latest-event selection, fallback chain assembly, and returns a stable `ResolvedQuestionChain`.
- `review_gate/answer_checkpoint_writer.py`
  - Owns submit-side checkpoint record construction and persistence for `Workflow -> Answer -> Evaluation -> Facts`.
- `tests/test_generated_chain_resolver.py`
  - Unit tests for generated-chain reuse, fallback, and latest-event selection.
- `tests/test_answer_checkpoint_writer.py`
  - Unit tests for submit-side checkpoint writes and `AssessmentSynthesizer` integration.

### Modified files

- `review_gate/review_flow_service.py`
  - Shrinks to transport request validation, assessment client invocation, resolver/writer coordination, DTO assembly, and legacy fact compatibility writes.
- `tests/test_review_flow_service.py`
  - Regression coverage that `ReviewFlowService` delegates correctly while keeping existing response shape.

### Files explicitly out of scope

- `review_gate/storage_sqlite.py`
- `review_gate/http_api.py`
- `review_gate/workspace_api.py`
- Graph / Maintenance / Focus files

---

### Task 1: Extract generated-chain resolution into its own component

**Files:**
- Create: `review_gate/generated_chain_resolver.py`
- Create: `tests/test_generated_chain_resolver.py`

- [ ] **Step 1: Write the failing resolver tests**

```python
from pathlib import Path

from review_gate.generated_chain_resolver import GeneratedChainResolver, ResolvedQuestionChain
from review_gate.storage_sqlite import SQLiteStore
from review_gate.domain import WorkspaceEvent
from review_gate.checkpoint_models import (
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)


def _seed_generated_chain(store: SQLiteStore, *, request_id: str, created_at: str) -> None:
    store.insert_workflow_request(
        WorkflowRequestRecord(
            request_id=request_id,
            request_type="question_cycle",
            project_id="proj-1",
            stage_id="stage-1",
            requested_by="question_generation_client",
            source="review_flow_service",
            status="completed",
            created_at=created_at,
            payload={"request_id": request_id},
        )
    )
    store.insert_workflow_run(
        WorkflowRunRecord(
            run_id=f"run-{request_id}",
            request_id=request_id,
            run_type="question_cycle",
            status="completed",
            started_at=created_at,
            finished_at=created_at,
            supersedes_run_id=None,
            payload={"request_id": request_id},
        )
    )
    store.insert_question_batch(
        QuestionBatchRecord(
            question_batch_id=f"qb-{request_id}",
            workflow_run_id=f"run-{request_id}",
            project_id="proj-1",
            stage_id="stage-1",
            generated_by="question_generation_client",
            source="review_flow_service",
            batch_goal="freeze boundary",
            entry_question_id=f"{request_id}-q-1",
            status="active",
            created_at=created_at,
            payload={"request_id": request_id},
        )
    )
    store.insert_question_items(
        [
            QuestionItemRecord(
                question_id=f"{request_id}-q-1",
                question_batch_id=f"qb-{request_id}",
                question_type="core",
                prompt="Explain the boundary.",
                intent="Check understanding.",
                difficulty_level="core",
                order_index=0,
                status="ready",
                created_at=created_at,
                payload={"transport_question_id": "set-1-q-1"},
            )
        ]
    )


def test_generated_chain_resolver_reuses_latest_generated_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    resolver = GeneratedChainResolver(store=store)

    _seed_generated_chain(store, request_id="req-qgen-1", created_at="2026-04-10T10:00:00Z")
    _seed_generated_chain(store, request_id="req-qgen-2", created_at="2026-04-10T10:05:00Z")
    store.append_event(
        WorkspaceEvent(
            event_id="evt-question-set-generated-00000001-req-qgen-1",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="2026-04-10T10:00:00Z",
            payload={
                "generation_index": 1,
                "stage_id": "stage-1",
                "question_set_id": "set-1",
                "question_batch_id": "qb-req-qgen-1",
                "workflow_run_id": "run-req-qgen-1",
                "question_item_ids": ["req-qgen-1-q-1"],
            },
        )
    )
    store.append_event(
        WorkspaceEvent(
            event_id="evt-question-set-generated-00000002-req-qgen-2",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="2026-04-10T10:05:00Z",
            payload={
                "generation_index": 2,
                "stage_id": "stage-1",
                "question_set_id": "set-1",
                "question_batch_id": "qb-req-qgen-2",
                "workflow_run_id": "run-req-qgen-2",
                "question_item_ids": ["req-qgen-2-q-1"],
            },
        )
    )

    resolved = resolver.resolve(
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        transport_question_id="set-1-q-1",
        request_id="req-submit-1",
        created_at="2026-04-10T10:10:00Z",
    )

    assert resolved.resolution_mode == "reused"
    assert resolved.workflow_run_id == "run-req-qgen-2"
    assert resolved.question_batch_id == "qb-req-qgen-2"
    assert resolved.question_item_id == "req-qgen-2-q-1"


def test_generated_chain_resolver_backfills_when_generation_absent(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    resolver = GeneratedChainResolver(store=store)

    resolved = resolver.resolve(
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        transport_question_id="set-1-q-1",
        request_id="req-submit-1",
        created_at="2026-04-10T10:10:00Z",
    )

    assert resolved.resolution_mode == "fallback"
    assert resolved.workflow_run_id == "run-req-submit-1"
    assert resolved.question_batch_id == "qb-req-submit-1"
    assert resolved.question_item_id == "req-submit-1-set-1-q-1"
    assert resolved.transport_question_id == "set-1-q-1"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_generated_chain_resolver.py -q`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `review_gate.generated_chain_resolver`

- [ ] **Step 3: Implement the resolver**

```python
from __future__ import annotations

from dataclasses import dataclass

from review_gate.checkpoint_models import QuestionBatchRecord, QuestionItemRecord, WorkflowRunRecord
from review_gate.domain import WorkspaceEvent
from review_gate.storage_sqlite import SQLiteStore


@dataclass(slots=True)
class ResolvedQuestionChain:
    workflow_run_id: str
    question_batch_id: str
    question_item_id: str
    transport_question_id: str
    resolution_mode: str
    generated_batch: QuestionBatchRecord | None = None
    generated_item: QuestionItemRecord | None = None


class GeneratedChainResolver:
    def __init__(self, *, store: SQLiteStore) -> None:
        self._store = store

    def resolve(
        self,
        *,
        project_id: str,
        stage_id: str,
        question_set_id: str,
        transport_question_id: str,
        request_id: str,
        created_at: str,
    ) -> ResolvedQuestionChain:
        event = self._find_latest_generated_question_set_event(
            project_id=project_id,
            stage_id=stage_id,
            question_set_id=question_set_id,
        )
        if event is None:
            return ResolvedQuestionChain(
                workflow_run_id=f"run-{request_id}",
                question_batch_id=f"qb-{request_id}",
                question_item_id=f"{request_id}-{transport_question_id}",
                transport_question_id=transport_question_id,
                resolution_mode="fallback",
            )

        question_batch_id = str(event.payload["question_batch_id"])
        workflow_run_id = str(event.payload["workflow_run_id"])
        generated_batch = self._store.get_question_batch(question_batch_id)
        generated_items = self._store.list_question_items(question_batch_id)
        generated_item = next(
            (
                item
                for item in generated_items
                if str(item.payload.get("transport_question_id", item.question_id)) == transport_question_id
            ),
            None,
        )
        if generated_batch is None or generated_item is None:
            return ResolvedQuestionChain(
                workflow_run_id=f"run-{request_id}",
                question_batch_id=f"qb-{request_id}",
                question_item_id=f"{request_id}-{transport_question_id}",
                transport_question_id=transport_question_id,
                resolution_mode="fallback",
            )

        return ResolvedQuestionChain(
            workflow_run_id=workflow_run_id,
            question_batch_id=question_batch_id,
            question_item_id=generated_item.question_id,
            transport_question_id=transport_question_id,
            resolution_mode="reused",
            generated_batch=generated_batch,
            generated_item=generated_item,
        )

    def _find_latest_generated_question_set_event(
        self,
        *,
        project_id: str,
        stage_id: str,
        question_set_id: str,
    ) -> WorkspaceEvent | None:
        latest_match: WorkspaceEvent | None = None
        for event in self._store.list_events(project_id=project_id):
            if event.event_type != "question_set_generated":
                continue
            if str(event.payload.get("stage_id")) != stage_id:
                continue
            if str(event.payload.get("question_set_id")) != question_set_id:
                continue
            latest_match = event
        return latest_match
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_generated_chain_resolver.py -q`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add review_gate/generated_chain_resolver.py tests/test_generated_chain_resolver.py
git commit -m "feat: extract generated chain resolver"
```

---

### Task 2: Extract submit-side checkpoint writes into a dedicated writer

**Files:**
- Create: `review_gate/answer_checkpoint_writer.py`
- Create: `tests/test_answer_checkpoint_writer.py`

- [ ] **Step 1: Write the failing writer tests**

```python
from pathlib import Path

from review_gate.answer_checkpoint_writer import AnswerCheckpointWriter
from review_gate.assessment_synthesizer import AssessmentSynthesizer
from review_gate.generated_chain_resolver import ResolvedQuestionChain
from review_gate.storage_sqlite import SQLiteStore
from review_gate.action_dtos import SubmitAnswerRequest


def test_answer_checkpoint_writer_persists_submit_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = AnswerCheckpointWriter(store=store, synthesizer=AssessmentSynthesizer())

    request = SubmitAnswerRequest(
        request_id="req-submit-1",
        project_id="proj-1",
        stage_id="stage-1",
        source_page="question_detail",
        actor_id="local-user",
        created_at="2026-04-10T11:00:00Z",
        question_set_id="set-1",
        question_id="set-1-q-1",
        answer_text="We split state and scoring boundaries.",
        draft_id=None,
    )
    resolved = ResolvedQuestionChain(
        workflow_run_id="run-req-qgen-1",
        question_batch_id="qb-req-qgen-1",
        question_item_id="req-qgen-1-q-1",
        transport_question_id="set-1-q-1",
        resolution_mode="reused",
    )
    assessment = {
        "verdict": "partial",
        "score": 0.8,
        "dimensions": {"understanding": "partial"},
        "gaps": ["proposal-execution-separation"],
        "summary": "Still mixes proposal and execution.",
    }

    result = writer.write(
        request=request,
        resolved_chain=resolved,
        assessment=assessment,
    )

    assert result.answer_batch_id == "ab-req-submit-1"
    assert result.evaluation_batch_id == "eb-req-submit-1"
    assert result.assessment_fact_batch_id == "afb-eb-req-submit-1"
    assert store.get_answer_batch("ab-req-submit-1") is not None
    assert store.get_evaluation_batch("eb-req-submit-1") is not None
    assert store.get_latest_assessment_fact_batch("proj-1", "stage-1") is not None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_answer_checkpoint_writer.py -q`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `review_gate.answer_checkpoint_writer`

- [ ] **Step 3: Implement the writer**

```python
from __future__ import annotations

from dataclasses import dataclass

from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.assessment_synthesizer import AssessmentSynthesizer
from review_gate.checkpoint_models import (
    AnswerBatchRecord,
    AnswerItemRecord,
    EvaluationBatchRecord,
    EvaluationItemRecord,
)
from review_gate.generated_chain_resolver import ResolvedQuestionChain
from review_gate.storage_sqlite import SQLiteStore


@dataclass(slots=True)
class CheckpointWriteResult:
    workflow_run_id: str
    question_batch_id: str
    answer_batch_id: str
    evaluation_batch_id: str
    assessment_fact_batch_id: str


class AnswerCheckpointWriter:
    def __init__(self, *, store: SQLiteStore, synthesizer: AssessmentSynthesizer) -> None:
        self._store = store
        self._synthesizer = synthesizer

    def write(
        self,
        *,
        request: SubmitAnswerRequest,
        resolved_chain: ResolvedQuestionChain,
        assessment: dict,
    ) -> CheckpointWriteResult:
        answer_batch = AnswerBatchRecord(
            answer_batch_id=f"ab-{request.request_id}",
            question_batch_id=resolved_chain.question_batch_id,
            workflow_run_id=resolved_chain.workflow_run_id,
            submitted_by=request.actor_id,
            submission_mode="single_submit",
            completion_status="complete",
            submitted_at=request.created_at,
            status="submitted",
            payload={"request_id": request.request_id, "resolution_mode": resolved_chain.resolution_mode},
        )
        answer_item = AnswerItemRecord(
            answer_item_id=f"ai-{request.request_id}-0",
            answer_batch_id=answer_batch.answer_batch_id,
            question_id=resolved_chain.question_item_id,
            answered_by=request.actor_id,
            answer_text=request.answer_text,
            answer_format="plain_text",
            order_index=0,
            answered_at=request.created_at,
            status="answered",
            revision_of_answer_item_id=None,
            payload={"transport_question_id": request.question_id},
        )
        evaluation_batch = EvaluationBatchRecord(
            evaluation_batch_id=f"eb-{request.request_id}",
            answer_batch_id=answer_batch.answer_batch_id,
            workflow_run_id=resolved_chain.workflow_run_id,
            project_id=request.project_id,
            stage_id=request.stage_id,
            evaluated_by="assessment_agent",
            evaluator_version="review_flow_service:first-checkpoint",
            confidence=float(assessment.get("score", 0.0)),
            status="completed",
            evaluated_at=request.created_at,
            supersedes_evaluation_batch_id=None,
            payload={"summary": assessment.get("summary", "")},
        )
        evaluation_item = EvaluationItemRecord(
            evaluation_item_id=f"ei-{request.request_id}",
            evaluation_batch_id=evaluation_batch.evaluation_batch_id,
            question_id=resolved_chain.question_item_id,
            answer_item_id=answer_item.answer_item_id,
            local_verdict=str(assessment.get("verdict", "")),
            confidence=float(assessment.get("score", 0.0)),
            status="completed",
            evaluated_at=request.created_at,
            payload={
                "diagnosed_gaps": list(assessment.get("gaps", [])),
                "reasoned_summary": str(assessment.get("summary", "")),
                "dimension_refs": list(assessment.get("dimensions", {}).keys()),
            },
        )

        self._store.insert_answer_batch(answer_batch)
        self._store.insert_answer_items([answer_item])
        self._store.insert_evaluation_batch(evaluation_batch)
        self._store.insert_evaluation_items([evaluation_item])

        fact_batch, fact_items = self._synthesizer.synthesize(
            workflow_run_id=resolved_chain.workflow_run_id,
            evaluation_batch=evaluation_batch,
            evaluation_items=[evaluation_item],
            evidence_spans=[],
        )
        self._store.insert_assessment_fact_batch(fact_batch)
        self._store.insert_assessment_fact_items(fact_items)

        return CheckpointWriteResult(
            workflow_run_id=resolved_chain.workflow_run_id,
            question_batch_id=resolved_chain.question_batch_id,
            answer_batch_id=answer_batch.answer_batch_id,
            evaluation_batch_id=evaluation_batch.evaluation_batch_id,
            assessment_fact_batch_id=fact_batch.assessment_fact_batch_id,
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_answer_checkpoint_writer.py -q`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add review_gate/answer_checkpoint_writer.py tests/test_answer_checkpoint_writer.py
git commit -m "feat: extract answer checkpoint writer"
```

---

### Task 3: Shrink ReviewFlowService to transport orchestration

**Files:**
- Modify: `review_gate/review_flow_service.py`
- Modify: `tests/test_review_flow_service.py`

- [ ] **Step 1: Add the failing delegation regressions**

```python
from pathlib import Path

from review_gate.review_flow_service import ReviewFlowService
from review_gate.storage_sqlite import SQLiteStore
from tests.test_review_flow_service import CapturingAssessmentClient


def test_submit_answer_uses_generated_chain_resolver_and_checkpoint_writer(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    service = ReviewFlowService(assessment_client=CapturingAssessmentClient.for_testing(), store=store)

    service.generate_question_set(
        {
            "request_id": "req-qgen-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze submit boundary",
            "stage_summary": "checkpoint",
            "stage_artifacts": [],
            "stage_exit_criteria": [],
            "current_decisions": ["Question, Assessment, Decision split"],
            "key_logic_points": ["structured DTOs"],
            "known_weak_points": [],
            "boundary_focus": ["module vs interface"],
            "question_strategy": "core_and_why",
            "max_questions": 1,
            "source_refs": [],
        }
    )

    response = service.submit_answer(
        request=type("Req", (), {
            "request_id": "req-submit-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-10T12:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "We split state and scoring boundaries.",
            "draft_id": None,
        })()
    )

    assert response.success is True
    assert store.list_answer_batches("qb-req-qgen-1")
    assert store.list_evaluation_batches("ab-req-submit-1")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_review_flow_service.py::test_submit_answer_uses_generated_chain_resolver_and_checkpoint_writer -q`
Expected: FAIL because `ReviewFlowService` still owns the resolution/write assembly directly

- [ ] **Step 3: Refactor ReviewFlowService**

```python
# review_gate/review_flow_service.py inside __init__
from review_gate.answer_checkpoint_writer import AnswerCheckpointWriter
from review_gate.generated_chain_resolver import GeneratedChainResolver

        self._assessment_synthesizer = AssessmentSynthesizer()
        self._generated_chain_resolver = GeneratedChainResolver(store=self._store) if self._store is not None else None
        self._answer_checkpoint_writer = (
            AnswerCheckpointWriter(store=self._store, synthesizer=self._assessment_synthesizer)
            if self._store is not None
            else None
        )

# inside submit_answer()
        resolved_chain = None
        if self._generated_chain_resolver is not None:
            resolved_chain = self._generated_chain_resolver.resolve(
                project_id=request.project_id,
                stage_id=request.stage_id,
                question_set_id=request.question_set_id,
                transport_question_id=request.question_id,
                request_id=request.request_id,
                created_at=request.created_at,
            )

        if self._answer_checkpoint_writer is not None and resolved_chain is not None:
            self._answer_checkpoint_writer.write(
                request=request,
                resolved_chain=resolved_chain,
                assessment={
                    "verdict": verdict,
                    "score": score,
                    "summary": assessment_summary.summary,
                    "gaps": assessment_summary.core_gaps,
                    "dimensions": assessment_summary.dimension_hits,
                },
            )
```

- [ ] **Step 4: Run focused regressions**

Run: `python -m pytest tests/test_generated_chain_resolver.py tests/test_answer_checkpoint_writer.py tests/test_review_flow_service.py -q`
Expected: PASS

- [ ] **Step 5: Run compatibility regressions**

Run: `python -m pytest tests/test_workspace_api.py tests/test_http_api.py -q`
Expected: PASS with unchanged response shape

- [ ] **Step 6: Commit**

```bash
git add review_gate/generated_chain_resolver.py review_gate/answer_checkpoint_writer.py review_gate/review_flow_service.py tests/test_generated_chain_resolver.py tests/test_answer_checkpoint_writer.py tests/test_review_flow_service.py
git commit -m "refactor: split submit checkpoint orchestration"
```

---

### Task 4: Freeze the new orchestration boundary

**Files:**
- Modify: `tests/test_http_api.py` only if transport-level regression is needed
- Modify: `docs/superpowers/plans/2026-04-10-post-checkpoint-migration-checklist.md` only if review notes must be reflected

- [ ] **Step 1: Run the full checkpoint regression set**

Run: `python -m pytest tests/test_assessment_synthesizer.py tests/test_checkpoint_storage.py tests/test_generated_chain_resolver.py tests/test_answer_checkpoint_writer.py tests/test_review_flow_service.py tests/test_workspace_api.py tests/test_http_api.py -q`
Expected: PASS

- [ ] **Step 2: Verify ReviewFlowService no longer owns the heaviest submit-side assembly**

Run: `rg -n \"question_set_generated|generation_index|insert_answer_batch|insert_evaluation_batch|insert_assessment_fact_batch\" review_gate/review_flow_service.py`
Expected: only thin orchestration references remain; direct record-construction density is reduced versus the current checkpoint version

- [ ] **Step 3: Commit any final test/doc updates**

```bash
git add tests/test_http_api.py docs/superpowers/plans/2026-04-10-post-checkpoint-migration-checklist.md
git commit -m "test: freeze submit orchestration split boundary"
```

---

## Review checkpoints

1. After Task 1, verify `GeneratedChainResolver` has no DTO leakage and no `QuestionSet` overloading.
2. After Task 2, verify `AnswerCheckpointWriter` constructs and persists only submit-side checkpoint records.
3. After Task 3, verify `ReviewFlowService` is thinner and still keeps legacy fact compatibility writes.
4. After Task 4, verify the full checkpoint regression set still passes before starting any Graph/Maintenance work.

---

## Frozen Boundary For This Plan

1. This plan only splits submit-side application orchestration.
2. `ReviewFlowService` still remains the transitional transport-facing orchestration owner after this plan, but with reduced responsibility.
3. The SQLite schema from the first migration checkpoint remains unchanged.
4. No Graph-layer tables, read models, focus logic, or maintenance workflows are implemented here.
5. HTTP and workspace DTOs remain unchanged during this split.
