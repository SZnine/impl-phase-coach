# First Migration Checkpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the first terminal migration checkpoint by persisting the new `Workflow -> Question -> Answer -> Evaluation -> Facts` chain in SQLite while keeping the current HTTP and workspace transport shape stable.

**Architecture:** Add a parallel first-checkpoint write path beside the current durable-facts path. Keep `ReviewFlowService` as the transitional orchestration owner for this checkpoint, introduce explicit checkpoint record models plus an `AssessmentSynthesizer`, and let `SQLiteStore` host the first 11 tables and core read helpers. Graph and maintenance remain out of scope for this plan.

**Tech Stack:** Python dataclasses, SQLite, FastAPI, pytest

---

## File Structure

- Create: `review_gate/checkpoint_models.py`
  - First-checkpoint record dataclasses for the 11-table chain.
- Create: `review_gate/assessment_synthesizer.py`
  - Converts evaluation batch/item output into assessment fact batch/items.
- Modify: `review_gate/storage_sqlite.py`
  - Adds the first 11 tables, 16 real foreign keys, 18 initial indexes, and insert/list/get helpers.
- Modify: `review_gate/review_flow_service.py`
  - Persists generated question batches and submitted answer batches into the new checkpoint chain while preserving existing DTOs and legacy durable-facts writes.
- Create: `tests/test_assessment_synthesizer.py`
  - Locks the evaluation-to-facts transformation boundary.
- Create: `tests/test_checkpoint_storage.py`
  - Locks the new SQLite schema and round-trip behavior.
- Modify: `tests/test_review_flow_service.py`
  - Verifies the service writes the new chain without breaking the old response contract.
- Modify: `tests/test_http_api.py`
  - Verifies the default app path still works against a fresh database after the new schema lands.

## Transitional Rules This Plan Must Preserve

1. `submit_answer` still receives a single-question request.
2. The new schema is batch/item-based, so one submit currently writes:
   - one `answer_batch`
   - one `answer_item`
   - one `evaluation_batch`
   - one `evaluation_item`
3. Existing `AnswerFact / AssessmentFact / DecisionFact` writes stay in place during this checkpoint.
4. Graph projection, knowledge maintenance, and focus-cluster rewrites are not touched in this plan.

### Task 1: Add first-checkpoint records and the assessment synthesizer

**Files:**
- Create: `review_gate/checkpoint_models.py`
- Create: `review_gate/assessment_synthesizer.py`
- Test: `tests/test_assessment_synthesizer.py`

- [ ] **Step 1: Write the failing synthesizer test**

```python
from review_gate.assessment_synthesizer import AssessmentSynthesizer
from review_gate.checkpoint_models import (
    EvaluationBatchRecord,
    EvaluationItemRecord,
    EvidenceSpanRecord,
)


def test_assessment_synthesizer_emits_fact_batch_and_items() -> None:
    synthesizer = AssessmentSynthesizer()
    evaluation_batch = EvaluationBatchRecord(
        evaluation_batch_id="eb-1",
        answer_batch_id="ab-1",
        workflow_run_id="run-1",
        project_id="proj-1",
        stage_id="stage-1",
        evaluated_by="evaluator_agent",
        evaluator_version="test-v1",
        confidence=0.82,
        status="completed",
        evaluated_at="2026-04-09T12:00:00Z",
        payload={"rubric_scores": {"understanding": "partial"}},
    )
    evaluation_item = EvaluationItemRecord(
        evaluation_item_id="ei-1",
        evaluation_batch_id="eb-1",
        question_id="set-1-q-1",
        answer_item_id="ai-1",
        local_verdict="partial",
        confidence=0.8,
        status="completed",
        evaluated_at="2026-04-09T12:00:00Z",
        payload={
            "reasoned_summary": "Answer still mixes proposal status with execution status.",
            "diagnosed_gaps": ["proposal-execution-separation"],
            "dimension_refs": ["understanding", "causality"],
        },
    )
    evidence = [
        EvidenceSpanRecord(
            evidence_span_id="es-1",
            evaluation_item_id="ei-1",
            answer_item_id="ai-1",
            span_type="quoted_text",
            supports_dimension="causality",
            content="accept proposal means it already executed",
            start_offset=0,
            end_offset=41,
            created_at="2026-04-09T12:00:00Z",
            payload={"why_it_matters": "mixes proposal and execution"},
        )
    ]

    fact_batch, fact_items = synthesizer.synthesize(
        workflow_run_id="run-1",
        evaluation_batch=evaluation_batch,
        evaluation_items=[evaluation_item],
        evidence_spans=evidence,
    )

    assert fact_batch.evaluation_batch_id == "eb-1"
    assert fact_batch.workflow_run_id == "run-1"
    assert fact_batch.status == "completed"
    assert len(fact_items) == 1
    assert fact_items[0].source_evaluation_item_id == "ei-1"
    assert fact_items[0].fact_type == "gap"
    assert fact_items[0].topic_key == "proposal-execution-separation"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_assessment_synthesizer.py::test_assessment_synthesizer_emits_fact_batch_and_items -q`
Expected: FAIL because `checkpoint_models.py` and `assessment_synthesizer.py` do not exist yet.

- [ ] **Step 3: Implement the checkpoint records**

```python
# review_gate/checkpoint_models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from review_gate.domain import JsonSerializable


@dataclass(slots=True)
class WorkflowRequestRecord(JsonSerializable):
    request_id: str
    request_type: str
    project_id: str
    stage_id: str
    requested_by: str
    source: str
    status: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowRunRecord(JsonSerializable):
    run_id: str
    request_id: str
    run_type: str
    status: str
    started_at: str
    finished_at: str | None = None
    supersedes_run_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QuestionBatchRecord(JsonSerializable):
    question_batch_id: str
    workflow_run_id: str
    project_id: str
    stage_id: str
    generated_by: str
    source: str
    batch_goal: str
    entry_question_id: str
    status: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QuestionItemRecord(JsonSerializable):
    question_id: str
    question_batch_id: str
    question_type: str
    prompt: str
    intent: str
    difficulty_level: str
    order_index: int
    status: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AnswerBatchRecord(JsonSerializable):
    answer_batch_id: str
    question_batch_id: str
    workflow_run_id: str
    submitted_by: str
    submission_mode: str
    completion_status: str
    submitted_at: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AnswerItemRecord(JsonSerializable):
    answer_item_id: str
    answer_batch_id: str
    question_id: str
    answered_by: str
    answer_text: str
    answer_format: str
    order_index: int
    answered_at: str
    status: str
    revision_of_answer_item_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationBatchRecord(JsonSerializable):
    evaluation_batch_id: str
    answer_batch_id: str
    workflow_run_id: str
    project_id: str
    stage_id: str
    evaluated_by: str
    evaluator_version: str
    confidence: float
    status: str
    evaluated_at: str
    supersedes_evaluation_batch_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationItemRecord(JsonSerializable):
    evaluation_item_id: str
    evaluation_batch_id: str
    question_id: str
    answer_item_id: str
    local_verdict: str
    confidence: float
    status: str
    evaluated_at: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvidenceSpanRecord(JsonSerializable):
    evidence_span_id: str
    evaluation_item_id: str
    answer_item_id: str
    span_type: str
    supports_dimension: str
    content: str
    start_offset: int | None
    end_offset: int | None
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AssessmentFactBatchRecord(JsonSerializable):
    assessment_fact_batch_id: str
    evaluation_batch_id: str
    workflow_run_id: str
    synthesized_by: str
    synthesizer_version: str
    status: str
    synthesized_at: str
    supersedes_assessment_fact_batch_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AssessmentFactItemRecord(JsonSerializable):
    assessment_fact_item_id: str
    assessment_fact_batch_id: str
    source_evaluation_item_id: str | None
    fact_type: str
    topic_key: str
    title: str
    confidence: float
    status: str
    created_at: str
    supersedes_assessment_fact_item_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Implement the synthesizer**

```python
# review_gate/assessment_synthesizer.py
from __future__ import annotations

from dataclasses import dataclass

from review_gate.checkpoint_models import (
    AssessmentFactBatchRecord,
    AssessmentFactItemRecord,
    EvaluationBatchRecord,
    EvaluationItemRecord,
    EvidenceSpanRecord,
)


@dataclass(slots=True)
class AssessmentSynthesizer:
    synthesizer_version: str = "first-checkpoint-v1"

    def synthesize(
        self,
        *,
        workflow_run_id: str,
        evaluation_batch: EvaluationBatchRecord,
        evaluation_items: list[EvaluationItemRecord],
        evidence_spans: list[EvidenceSpanRecord],
    ) -> tuple[AssessmentFactBatchRecord, list[AssessmentFactItemRecord]]:
        fact_batch = AssessmentFactBatchRecord(
            assessment_fact_batch_id=f"afb-{evaluation_batch.evaluation_batch_id}",
            evaluation_batch_id=evaluation_batch.evaluation_batch_id,
            workflow_run_id=workflow_run_id,
            synthesized_by="assessment_synthesizer",
            synthesizer_version=self.synthesizer_version,
            status="completed",
            synthesized_at=evaluation_batch.evaluated_at,
            payload={"item_count": len(evaluation_items)},
        )
        fact_items: list[AssessmentFactItemRecord] = []
        for item in evaluation_items:
            diagnosed_gaps = list(item.payload.get("diagnosed_gaps", []))
            reasoned_summary = str(item.payload.get("reasoned_summary", ""))
            for gap in diagnosed_gaps:
                fact_items.append(
                    AssessmentFactItemRecord(
                        assessment_fact_item_id=f"afi-{item.evaluation_item_id}-{gap}",
                        assessment_fact_batch_id=fact_batch.assessment_fact_batch_id,
                        source_evaluation_item_id=item.evaluation_item_id,
                        fact_type="gap",
                        topic_key=gap,
                        title=gap.replace("-", " "),
                        confidence=item.confidence,
                        status="active",
                        created_at=item.evaluated_at,
                        payload={
                            "description": reasoned_summary,
                            "dimension_refs": item.payload.get("dimension_refs", []),
                            "evidence_span_ids": [
                                span.evidence_span_id
                                for span in evidence_spans
                                if span.evaluation_item_id == item.evaluation_item_id
                            ],
                        },
                    )
                )
        return fact_batch, fact_items
```

- [ ] **Step 5: Run the synthesizer test and commit**

Run: `pytest tests/test_assessment_synthesizer.py::test_assessment_synthesizer_emits_fact_batch_and_items -q`
Expected: PASS.

```bash
git add review_gate/checkpoint_models.py review_gate/assessment_synthesizer.py tests/test_assessment_synthesizer.py
git commit -m "feat: add first checkpoint records and synthesizer"
```

### Task 2: Add the first 11 tables and store helpers in SQLite

**Files:**
- Modify: `review_gate/storage_sqlite.py`
- Create: `tests/test_checkpoint_storage.py`

- [ ] **Step 1: Write the failing storage test**

```python
from pathlib import Path

from review_gate.checkpoint_models import (
    AnswerBatchRecord,
    AnswerItemRecord,
    AssessmentFactBatchRecord,
    AssessmentFactItemRecord,
    EvaluationBatchRecord,
    EvaluationItemRecord,
    EvidenceSpanRecord,
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)
from review_gate.storage_sqlite import SQLiteStore


def test_sqlite_store_round_trips_first_checkpoint_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()

    workflow_request = WorkflowRequestRecord(
        request_id="wr-1",
        request_type="question_cycle",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="local-user",
        source="frontend_manual",
        status="pending",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    workflow_run = WorkflowRunRecord(
        run_id="run-1",
        request_id="wr-1",
        run_type="question_cycle",
        status="running",
        started_at="2026-04-09T12:00:00Z",
        payload={},
    )
    question_batch = QuestionBatchRecord(
        question_batch_id="qb-1",
        workflow_run_id="run-1",
        project_id="proj-1",
        stage_id="stage-1",
        generated_by="project_agent_adapter",
        source="review_flow_service",
        batch_goal="freeze module-interface boundary",
        entry_question_id="set-1-q-1",
        status="active",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    question_item = QuestionItemRecord(
        question_id="set-1-q-1",
        question_batch_id="qb-1",
        question_type="diagnostic",
        prompt="Explain the current-stage boundary.",
        intent="Check current-stage understanding.",
        difficulty_level="standard",
        order_index=0,
        status="pending",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    answer_batch = AnswerBatchRecord(
        answer_batch_id="ab-1",
        question_batch_id="qb-1",
        workflow_run_id="run-1",
        submitted_by="local-user",
        submission_mode="single_submit",
        completion_status="complete",
        submitted_at="2026-04-09T12:01:00Z",
        status="submitted",
        payload={},
    )
    answer_item = AnswerItemRecord(
        answer_item_id="ai-1",
        answer_batch_id="ab-1",
        question_id="set-1-q-1",
        answered_by="local-user",
        answer_text="We split state and scoring.",
        answer_format="plain_text",
        order_index=0,
        answered_at="2026-04-09T12:01:00Z",
        status="answered",
        payload={},
    )
    evaluation_batch = EvaluationBatchRecord(
        evaluation_batch_id="eb-1",
        answer_batch_id="ab-1",
        workflow_run_id="run-1",
        project_id="proj-1",
        stage_id="stage-1",
        evaluated_by="evaluator_agent",
        evaluator_version="test-v1",
        confidence=0.8,
        status="completed",
        evaluated_at="2026-04-09T12:02:00Z",
        payload={"rubric_scores": {"understanding": "partial"}},
    )
    evaluation_item = EvaluationItemRecord(
        evaluation_item_id="ei-1",
        evaluation_batch_id="eb-1",
        question_id="set-1-q-1",
        answer_item_id="ai-1",
        local_verdict="partial",
        confidence=0.8,
        status="completed",
        evaluated_at="2026-04-09T12:02:00Z",
        payload={"diagnosed_gaps": ["proposal-execution-separation"]},
    )
    evidence_span = EvidenceSpanRecord(
        evidence_span_id="es-1",
        evaluation_item_id="ei-1",
        answer_item_id="ai-1",
        span_type="quoted_text",
        supports_dimension="causality",
        content="state and scoring",
        start_offset=14,
        end_offset=31,
        created_at="2026-04-09T12:02:00Z",
        payload={"why_it_matters": "boundary anchor"},
    )
    fact_batch = AssessmentFactBatchRecord(
        assessment_fact_batch_id="afb-1",
        evaluation_batch_id="eb-1",
        workflow_run_id="run-1",
        synthesized_by="assessment_synthesizer",
        synthesizer_version="v1",
        status="completed",
        synthesized_at="2026-04-09T12:03:00Z",
        payload={},
    )
    fact_item = AssessmentFactItemRecord(
        assessment_fact_item_id="afi-1",
        assessment_fact_batch_id="afb-1",
        source_evaluation_item_id="ei-1",
        fact_type="gap",
        topic_key="proposal-execution-separation",
        title="proposal execution separation",
        confidence=0.8,
        status="active",
        created_at="2026-04-09T12:03:00Z",
        payload={"description": "still mixed"},
    )

    store.insert_workflow_request(workflow_request)
    store.insert_workflow_run(workflow_run)
    store.insert_question_batch(question_batch)
    store.insert_question_items([question_item])
    store.insert_answer_batch(answer_batch)
    store.insert_answer_items([answer_item])
    store.insert_evaluation_batch(evaluation_batch)
    store.insert_evaluation_items([evaluation_item])
    store.insert_evidence_spans([evidence_span])
    store.insert_assessment_fact_batch(fact_batch)
    store.insert_assessment_fact_items([fact_item])

    assert store.get_workflow_request("wr-1") == workflow_request
    assert store.get_question_batch("qb-1") == question_batch
    assert store.list_question_items("qb-1") == [question_item]
    assert store.list_answer_items("ab-1") == [answer_item]
    assert store.list_evaluation_items("eb-1") == [evaluation_item]
    assert store.list_evidence_spans("ei-1") == [evidence_span]
    assert store.get_latest_assessment_fact_batch("proj-1", "stage-1") == fact_batch
    assert store.list_assessment_fact_items("afb-1") == [fact_item]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_checkpoint_storage.py::test_sqlite_store_round_trips_first_checkpoint_chain -q`
Expected: FAIL because the first-checkpoint tables and insert/list/get helpers do not exist yet.

- [ ] **Step 3: Implement the schema and helpers**

```python
# review_gate/storage_sqlite.py inside initialize()
conn.executescript(
    """
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS workflow_requests (
        request_id TEXT PRIMARY KEY,
        request_type TEXT NOT NULL,
        project_id TEXT NOT NULL,
        stage_id TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        source TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        payload TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS workflow_runs (
        run_id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL,
        run_type TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        supersedes_run_id TEXT,
        payload TEXT NOT NULL,
        FOREIGN KEY (request_id) REFERENCES workflow_requests(request_id)
    );
    CREATE INDEX IF NOT EXISTS idx_workflow_runs_request_id
        ON workflow_runs(request_id);

    CREATE TABLE IF NOT EXISTS question_batches (
        question_batch_id TEXT PRIMARY KEY,
        workflow_run_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        stage_id TEXT NOT NULL,
        generated_by TEXT NOT NULL,
        source TEXT NOT NULL,
        batch_goal TEXT NOT NULL,
        entry_question_id TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        payload TEXT NOT NULL,
        FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(run_id)
    );
    CREATE INDEX IF NOT EXISTS idx_question_batches_workflow_run_id
        ON question_batches(workflow_run_id);
    CREATE INDEX IF NOT EXISTS idx_question_batches_project_stage
        ON question_batches(project_id, stage_id);

    CREATE TABLE IF NOT EXISTS question_items (
        question_id TEXT PRIMARY KEY,
        question_batch_id TEXT NOT NULL,
        question_type TEXT NOT NULL,
        prompt TEXT NOT NULL,
        intent TEXT NOT NULL,
        difficulty_level TEXT NOT NULL,
        order_index INTEGER NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        payload TEXT NOT NULL,
        FOREIGN KEY (question_batch_id) REFERENCES question_batches(question_batch_id)
    );
    CREATE INDEX IF NOT EXISTS idx_question_items_batch_order
        ON question_items(question_batch_id, order_index);

    CREATE TABLE IF NOT EXISTS answer_batches (
        answer_batch_id TEXT PRIMARY KEY,
        question_batch_id TEXT NOT NULL,
        workflow_run_id TEXT NOT NULL,
        submitted_by TEXT NOT NULL,
        submission_mode TEXT NOT NULL,
        completion_status TEXT NOT NULL,
        submitted_at TEXT NOT NULL,
        status TEXT NOT NULL,
        payload TEXT NOT NULL,
        FOREIGN KEY (question_batch_id) REFERENCES question_batches(question_batch_id),
        FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(run_id)
    );
    CREATE INDEX IF NOT EXISTS idx_answer_batches_question_batch_id
        ON answer_batches(question_batch_id);
    CREATE INDEX IF NOT EXISTS idx_answer_batches_workflow_run_id
        ON answer_batches(workflow_run_id);

    CREATE TABLE IF NOT EXISTS answer_items (
        answer_item_id TEXT PRIMARY KEY,
        answer_batch_id TEXT NOT NULL,
        question_id TEXT NOT NULL,
        answered_by TEXT NOT NULL,
        answer_text TEXT NOT NULL,
        answer_format TEXT NOT NULL,
        order_index INTEGER NOT NULL,
        answered_at TEXT NOT NULL,
        status TEXT NOT NULL,
        revision_of_answer_item_id TEXT,
        payload TEXT NOT NULL,
        FOREIGN KEY (answer_batch_id) REFERENCES answer_batches(answer_batch_id),
        FOREIGN KEY (question_id) REFERENCES question_items(question_id)
    );
    CREATE INDEX IF NOT EXISTS idx_answer_items_batch_order
        ON answer_items(answer_batch_id, order_index);
    CREATE INDEX IF NOT EXISTS idx_answer_items_question_id
        ON answer_items(question_id);

    CREATE TABLE IF NOT EXISTS evaluation_batches (
        evaluation_batch_id TEXT PRIMARY KEY,
        answer_batch_id TEXT NOT NULL,
        workflow_run_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        stage_id TEXT NOT NULL,
        evaluated_by TEXT NOT NULL,
        evaluator_version TEXT NOT NULL,
        confidence REAL NOT NULL,
        status TEXT NOT NULL,
        evaluated_at TEXT NOT NULL,
        supersedes_evaluation_batch_id TEXT,
        payload TEXT NOT NULL,
        FOREIGN KEY (answer_batch_id) REFERENCES answer_batches(answer_batch_id),
        FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(run_id)
    );
    CREATE INDEX IF NOT EXISTS idx_evaluation_batches_answer_batch_id
        ON evaluation_batches(answer_batch_id);
    CREATE INDEX IF NOT EXISTS idx_evaluation_batches_workflow_run_id
        ON evaluation_batches(workflow_run_id);

    CREATE TABLE IF NOT EXISTS evaluation_items (
        evaluation_item_id TEXT PRIMARY KEY,
        evaluation_batch_id TEXT NOT NULL,
        question_id TEXT NOT NULL,
        answer_item_id TEXT NOT NULL,
        local_verdict TEXT NOT NULL,
        confidence REAL NOT NULL,
        status TEXT NOT NULL,
        evaluated_at TEXT NOT NULL,
        payload TEXT NOT NULL,
        FOREIGN KEY (evaluation_batch_id) REFERENCES evaluation_batches(evaluation_batch_id),
        FOREIGN KEY (answer_item_id) REFERENCES answer_items(answer_item_id)
    );
    CREATE INDEX IF NOT EXISTS idx_evaluation_items_batch_id
        ON evaluation_items(evaluation_batch_id);
    CREATE INDEX IF NOT EXISTS idx_evaluation_items_answer_item_id
        ON evaluation_items(answer_item_id);

    CREATE TABLE IF NOT EXISTS evidence_spans (
        evidence_span_id TEXT PRIMARY KEY,
        evaluation_item_id TEXT NOT NULL,
        answer_item_id TEXT NOT NULL,
        span_type TEXT NOT NULL,
        supports_dimension TEXT NOT NULL,
        content TEXT NOT NULL,
        start_offset INTEGER,
        end_offset INTEGER,
        created_at TEXT NOT NULL,
        payload TEXT NOT NULL,
        FOREIGN KEY (evaluation_item_id) REFERENCES evaluation_items(evaluation_item_id),
        FOREIGN KEY (answer_item_id) REFERENCES answer_items(answer_item_id)
    );
    CREATE INDEX IF NOT EXISTS idx_evidence_spans_evaluation_item_id
        ON evidence_spans(evaluation_item_id);
    CREATE INDEX IF NOT EXISTS idx_evidence_spans_answer_item_id
        ON evidence_spans(answer_item_id);

    CREATE TABLE IF NOT EXISTS assessment_fact_batches (
        assessment_fact_batch_id TEXT PRIMARY KEY,
        evaluation_batch_id TEXT NOT NULL,
        workflow_run_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        stage_id TEXT NOT NULL,
        synthesized_by TEXT NOT NULL,
        synthesizer_version TEXT NOT NULL,
        status TEXT NOT NULL,
        synthesized_at TEXT NOT NULL,
        supersedes_assessment_fact_batch_id TEXT,
        payload TEXT NOT NULL,
        FOREIGN KEY (evaluation_batch_id) REFERENCES evaluation_batches(evaluation_batch_id),
        FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(run_id)
    );
    CREATE INDEX IF NOT EXISTS idx_assessment_fact_batches_evaluation_batch_id
        ON assessment_fact_batches(evaluation_batch_id);
    CREATE INDEX IF NOT EXISTS idx_assessment_fact_batches_workflow_run_id
        ON assessment_fact_batches(workflow_run_id);

    CREATE TABLE IF NOT EXISTS assessment_fact_items (
        assessment_fact_item_id TEXT PRIMARY KEY,
        assessment_fact_batch_id TEXT NOT NULL,
        source_evaluation_item_id TEXT,
        fact_type TEXT NOT NULL,
        topic_key TEXT NOT NULL,
        title TEXT NOT NULL,
        confidence REAL NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        supersedes_assessment_fact_item_id TEXT,
        payload TEXT NOT NULL,
        FOREIGN KEY (assessment_fact_batch_id) REFERENCES assessment_fact_batches(assessment_fact_batch_id)
    );
    CREATE INDEX IF NOT EXISTS idx_assessment_fact_items_batch_id
        ON assessment_fact_items(assessment_fact_batch_id);
    CREATE INDEX IF NOT EXISTS idx_assessment_fact_items_fact_type_topic_key
        ON assessment_fact_items(fact_type, topic_key);
    """
)
```

```python
# review_gate/storage_sqlite.py helper shape
def insert_workflow_request(self, record: WorkflowRequestRecord) -> None:
    self._insert_json_record(
        table="workflow_requests",
        pk_column="request_id",
        pk_value=record.request_id,
        payload=record,
        columns={
            "request_type": record.request_type,
            "project_id": record.project_id,
            "stage_id": record.stage_id,
            "requested_by": record.requested_by,
            "source": record.source,
            "status": record.status,
            "created_at": record.created_at,
        },
    )


def list_question_items(self, question_batch_id: str) -> list[QuestionItemRecord]:
    with self._connect() as conn:
        rows = conn.execute(
            """
            SELECT payload
            FROM question_items
            WHERE question_batch_id = ?
            ORDER BY order_index
            """,
            (question_batch_id,),
        ).fetchall()
    return [QuestionItemRecord.from_json(row[0]) for row in rows]
```

- [ ] **Step 4: Run the storage tests and commit**

Run: `pytest tests/test_checkpoint_storage.py -q`
Expected: PASS.

```bash
git add review_gate/storage_sqlite.py tests/test_checkpoint_storage.py
git commit -m "feat: add first checkpoint sqlite schema"
```

### Task 3: Wire `ReviewFlowService` to persist the new checkpoint chain

**Files:**
- Modify: `review_gate/review_flow_service.py`
- Test: `tests/test_review_flow_service.py`

- [ ] **Step 1: Write the failing service tests**

```python
from pathlib import Path

from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.review_flow_service import ReviewFlowService
from review_gate.storage_sqlite import SQLiteStore
from tests.test_review_flow_service import CapturingAssessmentClient


def test_generate_question_set_persists_checkpoint_question_batch(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    service = ReviewFlowService(assessment_client=CapturingAssessmentClient.for_testing(), store=store)

    response = service.generate_question_set(
        {
            "request_id": "req-qgen-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
            "stage_summary": "task 1",
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
    question_batch = store.get_question_batch("req-qgen-1")
    question_items = store.list_question_items("req-qgen-1")
    assert question_batch is not None
    assert len(question_items) == 2
    assert question_items[0].question_id == "q-1"


def test_submit_answer_persists_first_checkpoint_chain_even_without_prior_generation(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    service = ReviewFlowService(assessment_client=CapturingAssessmentClient.for_testing(), store=store)

    response = service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-submit-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-09T12:10:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="This answer is long enough to produce a partial verdict and a durable batch chain.",
            draft_id=None,
        )
    )

    assert response.success is True
    question_batch = store.get_question_batch("set-1")
    answer_batches = store.list_answer_batches("set-1")
    evaluation_batches = store.list_evaluation_batches(answer_batches[0].answer_batch_id)
    fact_batch = store.get_latest_assessment_fact_batch("proj-1", "stage-1")

    assert question_batch is not None
    assert len(answer_batches) == 1
    assert len(evaluation_batches) == 1
    assert fact_batch is not None
    assert fact_batch.workflow_run_id == "run-set-1"
```

- [ ] **Step 2: Run the failing tests**

Run: `pytest tests/test_review_flow_service.py::test_generate_question_set_persists_checkpoint_question_batch tests/test_review_flow_service.py::test_submit_answer_persists_first_checkpoint_chain_even_without_prior_generation -q`
Expected: FAIL because `ReviewFlowService` still writes only the old question set / answer fact / assessment fact path.

- [ ] **Step 3: Implement the transitional persistence path**

```python
# review_gate/review_flow_service.py
from review_gate.assessment_synthesizer import AssessmentSynthesizer
from review_gate.checkpoint_models import (
    AnswerBatchRecord,
    AnswerItemRecord,
    EvaluationBatchRecord,
    EvaluationItemRecord,
    EvidenceSpanRecord,
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)


def _checkpoint_question_batch_id(self, request_id: str, fallback_question_set_id: str) -> str:
    return request_id or fallback_question_set_id


def _ensure_checkpoint_question_batch(self, request: SubmitAnswerRequest) -> str:
    existing = self._store.get_question_batch(request.question_set_id)
    if existing is not None:
        return existing.question_batch_id

    run = WorkflowRunRecord(
        run_id=f"run-{request.question_set_id}",
        request_id=request.request_id,
        run_type="question_cycle",
        status="completed",
        started_at=request.created_at,
        finished_at=request.created_at,
        payload={"source": "submit_backfill"},
    )
    batch = QuestionBatchRecord(
        question_batch_id=request.question_set_id,
        workflow_run_id=run.run_id,
        project_id=request.project_id,
        stage_id=request.stage_id,
        generated_by="review_flow_service_backfill",
        source="submit_answer",
        batch_goal=self.get_stage_view(request.project_id, request.stage_id).stage_goal,
        entry_question_id=request.question_id,
        status="active",
        created_at=request.created_at,
        payload={},
    )
    view = self.get_question_set_view(request.project_id, request.stage_id, request.question_set_id)
    items = [
        QuestionItemRecord(
            question_id=item.question_id,
            question_batch_id=batch.question_batch_id,
            question_type=item.question_level,
            prompt=item.prompt,
            intent=self.get_question_view(
                request.project_id,
                request.stage_id,
                request.question_set_id,
                item.question_id,
            ).intent,
            difficulty_level="standard",
            order_index=index,
            status="pending",
            created_at=request.created_at,
            payload={},
        )
        for index, item in enumerate(view.questions)
    ]

    self._store.insert_workflow_request(
        WorkflowRequestRecord(
            request_id=request.request_id,
            request_type="question_cycle",
            project_id=request.project_id,
            stage_id=request.stage_id,
            requested_by=request.actor_id,
            source="submit_backfill",
            status="completed",
            created_at=request.created_at,
            payload={},
        )
    )
    self._store.insert_workflow_run(run)
    self._store.insert_question_batch(batch)
    self._store.insert_question_items(items)
    return batch.question_batch_id
```

```python
def submit_answer(self, request: SubmitAnswerRequest) -> SubmitAnswerResponseDTO:
    question_batch_id = request.question_set_id
    if self._store is not None:
        question_batch_id = self._ensure_checkpoint_question_batch(request)

    context = self._build_current_question_context(request)
    assessment_response = self._assessment_client.assess(
        {
            "request_id": request.request_id,
            "project_id": request.project_id,
            "stage_id": request.stage_id,
            "question_set_id": request.question_set_id,
            "question_id": request.question_id,
            "question_level": context.question_level,
            "question_prompt": context.question_prompt,
            "question_intent": context.question_intent,
            "expected_signals": context.expected_signals,
            "source_context": context.source_context,
            "user_answer": request.answer_text,
        }
    )
    assessment = assessment_response["assessment"]
    confidence = float(assessment_response["confidence"])
    response = SubmitAnswerResponseDTO(
        request_id=request.request_id,
        success=True,
        result_type="assessment_created",
        message=f"Assessment created with verdict {assessment['verdict']}.",
        assessment_summary=AssessmentSummaryDTO(
            assessment_id=f"assessment-{request.request_id}",
            project_id=request.project_id,
            stage_id=request.stage_id,
            question_set_id=request.question_set_id,
            question_id=request.question_id,
            answer_excerpt=request.answer_text[:120],
            status="created",
        ),
        refresh_targets=["stage_view", "question_view"],
        next_action=assessment_response["recommended_action"],
        warnings=list(assessment_response["warnings"]),
    )

    if self._store is not None:
        answer_batch = AnswerBatchRecord(
            answer_batch_id=f"ab-{request.request_id}",
            question_batch_id=question_batch_id,
            workflow_run_id=f"run-{question_batch_id}",
            submitted_by=request.actor_id,
            submission_mode="single_submit",
            completion_status="complete",
            submitted_at=request.created_at,
            status="submitted",
            payload={"source_page": request.source_page},
        )
        answer_item = AnswerItemRecord(
            answer_item_id=f"ai-{request.request_id}",
            answer_batch_id=answer_batch.answer_batch_id,
            question_id=request.question_id,
            answered_by=request.actor_id,
            answer_text=request.answer_text,
            answer_format="plain_text",
            order_index=0,
            answered_at=request.created_at,
            status="answered",
            payload={"draft_id": request.draft_id},
        )
        evaluation_batch = EvaluationBatchRecord(
            evaluation_batch_id=f"eb-{request.request_id}",
            answer_batch_id=answer_batch.answer_batch_id,
            workflow_run_id=answer_batch.workflow_run_id,
            project_id=request.project_id,
            stage_id=request.stage_id,
            evaluated_by="assessment_agent_client",
            evaluator_version="review-flow-v1",
            confidence=confidence,
            status="completed",
            evaluated_at=request.created_at,
            payload={"rubric_scores": assessment["dimension_scores"]},
        )
        evaluation_item = EvaluationItemRecord(
            evaluation_item_id=f"ei-{request.request_id}",
            evaluation_batch_id=evaluation_batch.evaluation_batch_id,
            question_id=request.question_id,
            answer_item_id=answer_item.answer_item_id,
            local_verdict=assessment["verdict"],
            confidence=confidence,
            status="completed",
            evaluated_at=request.created_at,
            payload={
                "reasoned_summary": assessment["evidence"][0] if assessment["evidence"] else "",
                "diagnosed_gaps": assessment["core_gaps"],
                "dimension_refs": self._derive_dimension_hits(assessment),
            },
        )
        evidence_spans = [
            EvidenceSpanRecord(
                evidence_span_id=f"es-{request.request_id}-0",
                evaluation_item_id=evaluation_item.evaluation_item_id,
                answer_item_id=answer_item.answer_item_id,
                span_type="quoted_text",
                supports_dimension="reasoning",
                content=request.answer_text[:120],
                start_offset=0,
                end_offset=min(len(request.answer_text), 120),
                created_at=request.created_at,
                payload={"why_it_matters": "submit answer excerpt"},
            )
        ]
        fact_batch, fact_items = self._assessment_synthesizer.synthesize(
            workflow_run_id=evaluation_batch.workflow_run_id,
            evaluation_batch=evaluation_batch,
            evaluation_items=[evaluation_item],
            evidence_spans=evidence_spans,
        )

        self._store.insert_answer_batch(answer_batch)
        self._store.insert_answer_items([answer_item])
        self._store.insert_evaluation_batch(evaluation_batch)
        self._store.insert_evaluation_items([evaluation_item])
        self._store.insert_evidence_spans(evidence_spans)
        self._store.insert_assessment_fact_batch(fact_batch)
        self._store.insert_assessment_fact_items(fact_items)

        legacy_answer = AnswerFact(
            answer_id=f"answer-{request.request_id}",
            request_id=request.request_id,
            project_id=request.project_id,
            stage_id=request.stage_id,
            question_set_id=request.question_set_id,
            question_id=request.question_id,
            actor_id=request.actor_id,
            source_page=request.source_page,
            created_at=request.created_at,
            answer_text=request.answer_text,
            draft_id=request.draft_id,
        )
        legacy_assessment = AssessmentFact(
            assessment_id=response.assessment_summary.assessment_id,
            request_id=request.request_id,
            answer_id=legacy_answer.answer_id,
            project_id=request.project_id,
            stage_id=request.stage_id,
            question_set_id=request.question_set_id,
            question_id=request.question_id,
            verdict=assessment["verdict"],
            score_total=float(assessment["score_total"]),
            dimension_scores=dict(assessment["dimension_scores"]),
            dimension_hits=self._derive_dimension_hits(assessment),
            core_gaps=list(assessment["core_gaps"]),
            misconceptions=list(assessment["misconceptions"]),
            support_basis_tags=list(assessment.get("support_basis_tags", [])),
            support_signals=self._derive_support_signals(assessment),
            confidence=confidence,
        )
        self._store.upsert_answer_fact(legacy_answer)
        self._store.upsert_assessment_fact(legacy_assessment)

    return response
```

- [ ] **Step 4: Run the service tests and commit**

Run: `pytest tests/test_review_flow_service.py::test_generate_question_set_persists_checkpoint_question_batch tests/test_review_flow_service.py::test_submit_answer_persists_first_checkpoint_chain_even_without_prior_generation -q`
Expected: PASS.

```bash
git add review_gate/review_flow_service.py tests/test_review_flow_service.py
git commit -m "feat: persist first checkpoint review flow chain"
```

### Task 4: Lock transport regressions and fresh-database wiring

**Files:**
- Modify: `tests/test_http_api.py`
- Modify: `tests/test_workspace_api.py` only if a backend-only assertion cannot be expressed through `http_api`

- [ ] **Step 1: Add the fresh-db regression**

```python
from pathlib import Path
import sqlite3

from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.http_api import create_default_workspace_api


def test_create_default_workspace_api_initializes_first_checkpoint_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "review.sqlite3"
    api = create_default_workspace_api(db_path=db_path, session_path=tmp_path / "workspace-session.json")

    response = api.submit_answer_action(
        SubmitAnswerRequest(
            request_id="req-http-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-09T13:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="This answer is long enough to preserve the transport response while new tables fill.",
            draft_id=None,
        )
    )

    with sqlite3.connect(db_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert response.success is True
    assert response.result_type == "assessment_created"
    assert {"workflow_requests", "question_batches", "answer_batches", "evaluation_batches", "assessment_fact_batches"}.issubset(table_names)
```

- [ ] **Step 2: Run the regression set**

Run: `pytest tests/test_assessment_synthesizer.py tests/test_checkpoint_storage.py tests/test_review_flow_service.py tests/test_http_api.py -q`
Expected: PASS.

- [ ] **Step 3: Run the existing compatibility set**

Run: `pytest tests/test_workspace_api.py tests/test_http_api.py::test_http_api_submit_answer_returns_assessment_and_refreshes_stage_mastery -q`
Expected: PASS with the same response shape and no Graph-layer work added.

- [ ] **Step 4: Commit**

```bash
git add tests/test_http_api.py tests/test_workspace_api.py
git commit -m "test: lock first checkpoint transport regressions"
```

---

## Frozen Boundary For This Plan

1. This plan lands the first migration checkpoint only.
2. `ReviewFlowService` remains the transitional orchestration owner for now.
3. The new chain is additive beside the current `AnswerFact / AssessmentFact / DecisionFact` path.
4. No Graph-layer tables, read models, or maintenance workflows are implemented here.
5. The current HTTP and workspace DTOs stay unchanged during this checkpoint.
