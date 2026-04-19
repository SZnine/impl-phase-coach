# Facts To Graph Migration Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Do not use background/subagents while the current user directive is active. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first stable Facts -> Graph migration entrance by projecting `AssessmentFactItemRecord` into persisted `KnowledgeSignalRecord` objects.

**Architecture:** Keep Assessment Facts as the historical truth layer and add `KnowledgeSignal` as an append-only bridge object. The deterministic projector reads fact batch/items and emits signals without touching legacy profile graph tables or creating `GraphRevision`.

**Tech Stack:** Python dataclasses, existing `JsonSerializable`, SQLite through `review_gate/storage_sqlite.py`, pytest.

---

## File Structure

- Modify: `review_gate/checkpoint_models.py`
  - Add `KnowledgeSignalRecord` beside checkpoint-layer records.
- Modify: `review_gate/storage_sqlite.py`
  - Add `knowledge_signals` table and storage methods.
- Create: `review_gate/knowledge_signal_projector.py`
  - Add deterministic `AssessmentFactSignalProjector`.
- Modify: `tests/test_checkpoint_storage.py`
  - Cover persisted `KnowledgeSignalRecord` round-trip and idempotent replacement.
- Create: `tests/test_knowledge_signal_projector.py`
  - Cover one-to-one and one-to-many signal generation from facts.
- Modify: `docs/superpowers/plans/2026-04-19-facts-to-graph-migration-entry-implementation.md`
  - Check off steps as they are completed.

---

### Task 1: Add KnowledgeSignalRecord Model

**Files:**
- Modify: `review_gate/checkpoint_models.py`
- Test: `tests/test_knowledge_signal_projector.py`

- [x] **Step 1: Write the failing serialization test**

Create `tests/test_knowledge_signal_projector.py` with this initial test:

```python
from review_gate.checkpoint_models import KnowledgeSignalRecord


def test_knowledge_signal_record_round_trips_json_payload() -> None:
    signal = KnowledgeSignalRecord(
        signal_id="ks-afi-1-weakness-proposal-execution-separation",
        assessment_fact_batch_id="afb-1",
        assessment_fact_item_id="afi-1",
        source_evaluation_item_id="ei-1",
        signal_type="weakness",
        topic_key="proposal-execution-separation",
        polarity="negative",
        summary="proposal execution separation",
        confidence=0.8,
        status="active",
        projector_version="fact-signal-v1",
        created_at="2026-04-09T12:03:00Z",
        payload={"source_fact_type": "gap"},
    )

    assert KnowledgeSignalRecord.from_json(signal.to_json()) == signal
```

- [x] **Step 2: Run the model test to verify it fails**

Run:

```powershell
pytest tests/test_knowledge_signal_projector.py::test_knowledge_signal_record_round_trips_json_payload -q
```

Expected: FAIL with import error for `KnowledgeSignalRecord`.

- [x] **Step 3: Add the model**

Append this dataclass after `AssessmentFactItemRecord` in `review_gate/checkpoint_models.py`:

```python
@dataclass(slots=True)
class KnowledgeSignalRecord(JsonSerializable):
    signal_id: str
    assessment_fact_batch_id: str
    assessment_fact_item_id: str
    source_evaluation_item_id: str | None
    signal_type: str
    topic_key: str
    polarity: str
    summary: str
    confidence: float
    status: str
    projector_version: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            signal_id=_coerce_str(payload["signal_id"]),
            assessment_fact_batch_id=_coerce_str(payload.get("assessment_fact_batch_id"), ""),
            assessment_fact_item_id=_coerce_str(payload.get("assessment_fact_item_id"), ""),
            source_evaluation_item_id=_coerce_optional_str(payload.get("source_evaluation_item_id")),
            signal_type=_coerce_str(payload.get("signal_type"), ""),
            topic_key=_coerce_str(payload.get("topic_key"), ""),
            polarity=_coerce_str(payload.get("polarity"), ""),
            summary=_coerce_str(payload.get("summary"), ""),
            confidence=_coerce_float(payload.get("confidence"), 0.0),
            status=_coerce_str(payload.get("status"), ""),
            projector_version=_coerce_str(payload.get("projector_version"), ""),
            created_at=_coerce_str(payload.get("created_at"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )
```

- [x] **Step 4: Run the model test to verify it passes**

Run:

```powershell
pytest tests/test_knowledge_signal_projector.py::test_knowledge_signal_record_round_trips_json_payload -q
```

Expected: PASS.

- [x] **Step 5: Commit Task 1**

Run:

```powershell
git add review_gate/checkpoint_models.py tests/test_knowledge_signal_projector.py
git commit -m "feat: add knowledge signal checkpoint model"
```

---

### Task 2: Persist Knowledge Signals In SQLite

**Files:**
- Modify: `review_gate/storage_sqlite.py`
- Modify: `tests/test_checkpoint_storage.py`

- [x] **Step 1: Write the failing storage round-trip test**

Add `KnowledgeSignalRecord` to the import list in `tests/test_checkpoint_storage.py`, then append this test:

```python
def test_checkpoint_storage_round_trips_knowledge_signals(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "checkpoint.db")
    store.initialize()
    _seed_minimal_assessment_fact(store)

    signal = KnowledgeSignalRecord(
        signal_id="ks-afi-1-weakness-proposal-execution-separation",
        assessment_fact_batch_id="afb-1",
        assessment_fact_item_id="afi-1",
        source_evaluation_item_id="ei-1",
        signal_type="weakness",
        topic_key="proposal-execution-separation",
        polarity="negative",
        summary="proposal execution separation",
        confidence=0.8,
        status="active",
        projector_version="fact-signal-v1",
        created_at="2026-04-09T12:03:00Z",
        payload={"source_fact_type": "gap"},
    )

    store.insert_knowledge_signals([signal])

    assert store.list_knowledge_signals_for_fact_batch("afb-1") == [signal]
    assert store.list_knowledge_signals_for_fact_item("afi-1") == [signal]

    replacement = KnowledgeSignalRecord(
        signal_id="ks-afi-1-weakness-proposal-execution-separation",
        assessment_fact_batch_id="afb-1",
        assessment_fact_item_id="afi-1",
        source_evaluation_item_id="ei-1",
        signal_type="weakness",
        topic_key="proposal-execution-separation",
        polarity="negative",
        summary="updated proposal execution separation",
        confidence=0.85,
        status="active",
        projector_version="fact-signal-v1",
        created_at="2026-04-09T12:03:30Z",
        payload={"source_fact_type": "gap", "description": "updated"},
    )

    store.insert_knowledge_signals([replacement])

    assert store.list_knowledge_signals_for_fact_batch("afb-1") == [replacement]
```

If `test_checkpoint_storage.py` does not yet have `_seed_minimal_assessment_fact`, add this helper near the test:

```python
def _seed_minimal_assessment_fact(store: SQLiteStore) -> None:
    workflow_request = WorkflowRequestRecord(
        request_id="wr-1",
        request_type="review",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="user",
        source="test",
        status="accepted",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    workflow_run = WorkflowRunRecord(
        run_id="run-1",
        request_id="wr-1",
        run_type="review",
        status="completed",
        started_at="2026-04-09T12:00:00Z",
        finished_at="2026-04-09T12:04:00Z",
        payload={},
    )
    question_batch = QuestionBatchRecord(
        question_batch_id="qb-1",
        workflow_run_id="run-1",
        project_id="proj-1",
        stage_id="stage-1",
        generated_by="project_agent",
        source="test",
        batch_goal="checkpoint",
        entry_question_id="q-1",
        status="completed",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    question_item = QuestionItemRecord(
        question_id="q-1",
        question_batch_id="qb-1",
        question_type="conceptual",
        prompt="Explain proposal and execution separation.",
        intent="diagnose gap",
        difficulty_level="medium",
        order_index=0,
        status="active",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    answer_batch = AnswerBatchRecord(
        answer_batch_id="ab-1",
        question_batch_id="qb-1",
        workflow_run_id="run-1",
        submitted_by="user",
        submission_mode="batch",
        completion_status="completed",
        submitted_at="2026-04-09T12:01:00Z",
        status="submitted",
        payload={},
    )
    answer_item = AnswerItemRecord(
        answer_item_id="ai-1",
        answer_batch_id="ab-1",
        question_id="q-1",
        answered_by="user",
        answer_text="They are the same thing.",
        answer_format="plain_text",
        order_index=0,
        answered_at="2026-04-09T12:01:00Z",
        status="submitted",
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
        payload={},
    )
    evaluation_item = EvaluationItemRecord(
        evaluation_item_id="ei-1",
        evaluation_batch_id="eb-1",
        question_id="q-1",
        answer_item_id="ai-1",
        local_verdict="partial",
        confidence=0.8,
        status="completed",
        evaluated_at="2026-04-09T12:02:00Z",
        payload={"diagnosed_gaps": ["proposal-execution-separation"]},
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
    store.insert_assessment_fact_batch(fact_batch)
    store.insert_assessment_fact_items([fact_item])
```

- [x] **Step 2: Run the storage test to verify it fails**

Run:

```powershell
pytest tests/test_checkpoint_storage.py::test_checkpoint_storage_round_trips_knowledge_signals -q
```

Expected: FAIL because `SQLiteStore` has no `insert_knowledge_signals` method.

- [x] **Step 3: Add imports and schema**

In `review_gate/storage_sqlite.py`, add `KnowledgeSignalRecord` to the `review_gate.checkpoint_models` import list.

Inside `initialize()`, immediately after the `assessment_fact_items` indexes, add:

```sql
CREATE TABLE IF NOT EXISTS knowledge_signals (
    signal_id TEXT PRIMARY KEY,
    assessment_fact_batch_id TEXT NOT NULL,
    assessment_fact_item_id TEXT NOT NULL,
    source_evaluation_item_id TEXT,
    signal_type TEXT NOT NULL,
    topic_key TEXT NOT NULL,
    polarity TEXT NOT NULL,
    confidence REAL NOT NULL,
    status TEXT NOT NULL,
    projector_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    FOREIGN KEY (assessment_fact_batch_id) REFERENCES assessment_fact_batches(assessment_fact_batch_id),
    FOREIGN KEY (assessment_fact_item_id) REFERENCES assessment_fact_items(assessment_fact_item_id)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_signals_fact_batch_id
    ON knowledge_signals(assessment_fact_batch_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_signals_fact_item_id
    ON knowledge_signals(assessment_fact_item_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_signals_type_topic
    ON knowledge_signals(signal_type, topic_key);
```

- [x] **Step 4: Add storage methods**

Add these methods near the assessment fact methods in `review_gate/storage_sqlite.py`:

```python
    def insert_knowledge_signals(self, records: list[KnowledgeSignalRecord]) -> None:
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO knowledge_signals (
                        signal_id,
                        assessment_fact_batch_id,
                        assessment_fact_item_id,
                        source_evaluation_item_id,
                        signal_type,
                        topic_key,
                        polarity,
                        confidence,
                        status,
                        projector_version,
                        created_at,
                        payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.signal_id,
                        record.assessment_fact_batch_id,
                        record.assessment_fact_item_id,
                        record.source_evaluation_item_id,
                        record.signal_type,
                        record.topic_key,
                        record.polarity,
                        record.confidence,
                        record.status,
                        record.projector_version,
                        record.created_at,
                        record.to_json(),
                    ),
                )

    def list_knowledge_signals_for_fact_batch(self, assessment_fact_batch_id: str) -> list[KnowledgeSignalRecord]:
        rows = self._fetch_all(
            """
            SELECT payload
            FROM knowledge_signals
            WHERE assessment_fact_batch_id = ?
            ORDER BY created_at, signal_id
            """,
            (assessment_fact_batch_id,),
        )
        return [KnowledgeSignalRecord.from_json(row["payload"]) for row in rows]

    def list_knowledge_signals_for_fact_item(self, assessment_fact_item_id: str) -> list[KnowledgeSignalRecord]:
        rows = self._fetch_all(
            """
            SELECT payload
            FROM knowledge_signals
            WHERE assessment_fact_item_id = ?
            ORDER BY created_at, signal_id
            """,
            (assessment_fact_item_id,),
        )
        return [KnowledgeSignalRecord.from_json(row["payload"]) for row in rows]
```

- [x] **Step 5: Run the storage test to verify it passes**

Run:

```powershell
pytest tests/test_checkpoint_storage.py::test_checkpoint_storage_round_trips_knowledge_signals -q
```

Expected: PASS.

- [x] **Step 6: Commit Task 2**

Run:

```powershell
git add review_gate/storage_sqlite.py tests/test_checkpoint_storage.py
git commit -m "feat: persist knowledge signals"
```

---

### Task 3: Add Deterministic AssessmentFactSignalProjector

**Files:**
- Create: `review_gate/knowledge_signal_projector.py`
- Modify: `tests/test_knowledge_signal_projector.py`

- [x] **Step 1: Add failing one-to-one projector test**

Append this test to `tests/test_knowledge_signal_projector.py`:

```python
from review_gate.checkpoint_models import AssessmentFactBatchRecord, AssessmentFactItemRecord
from review_gate.knowledge_signal_projector import AssessmentFactSignalProjector


def test_projector_converts_gap_fact_to_weakness_signal() -> None:
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
        payload={"description": "Answer still mixes proposal status with execution status."},
    )

    signals = AssessmentFactSignalProjector().project(fact_batch=fact_batch, fact_items=[fact_item])

    assert len(signals) == 1
    assert signals[0].signal_id == "ks-afi-1-weakness-proposal-execution-separation"
    assert signals[0].assessment_fact_batch_id == "afb-1"
    assert signals[0].assessment_fact_item_id == "afi-1"
    assert signals[0].source_evaluation_item_id == "ei-1"
    assert signals[0].signal_type == "weakness"
    assert signals[0].topic_key == "proposal-execution-separation"
    assert signals[0].polarity == "negative"
    assert signals[0].summary == "proposal execution separation"
    assert signals[0].confidence == 0.8
    assert signals[0].status == "active"
    assert signals[0].projector_version == "fact-signal-v1"
    assert signals[0].created_at == "2026-04-09T12:03:00Z"
    assert signals[0].payload["source_fact_type"] == "gap"
    assert signals[0].payload["description"] == "Answer still mixes proposal status with execution status."
```

- [x] **Step 2: Run the one-to-one projector test to verify it fails**

Run:

```powershell
pytest tests/test_knowledge_signal_projector.py::test_projector_converts_gap_fact_to_weakness_signal -q
```

Expected: FAIL because `review_gate.knowledge_signal_projector` does not exist.

- [x] **Step 3: Implement the projector**

Create `review_gate/knowledge_signal_projector.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from review_gate.checkpoint_models import (
    AssessmentFactBatchRecord,
    AssessmentFactItemRecord,
    KnowledgeSignalRecord,
)


@dataclass(slots=True)
class AssessmentFactSignalProjector:
    projector_version: str = "fact-signal-v1"

    def project(
        self,
        *,
        fact_batch: AssessmentFactBatchRecord,
        fact_items: list[AssessmentFactItemRecord],
    ) -> list[KnowledgeSignalRecord]:
        signals: list[KnowledgeSignalRecord] = []
        for fact_item in fact_items:
            signals.append(self._project_item(fact_batch=fact_batch, fact_item=fact_item))
        return signals

    def _project_item(
        self,
        *,
        fact_batch: AssessmentFactBatchRecord,
        fact_item: AssessmentFactItemRecord,
    ) -> KnowledgeSignalRecord:
        signal_type, polarity = self._classify_fact(fact_item.fact_type)
        return KnowledgeSignalRecord(
            signal_id=self._signal_id(fact_item=fact_item, signal_type=signal_type),
            assessment_fact_batch_id=fact_batch.assessment_fact_batch_id,
            assessment_fact_item_id=fact_item.assessment_fact_item_id,
            source_evaluation_item_id=fact_item.source_evaluation_item_id,
            signal_type=signal_type,
            topic_key=fact_item.topic_key,
            polarity=polarity,
            summary=fact_item.title or fact_item.topic_key,
            confidence=fact_item.confidence,
            status=fact_item.status,
            projector_version=self.projector_version,
            created_at=fact_item.created_at,
            payload={
                "source_fact_type": fact_item.fact_type,
                "source_title": fact_item.title,
                "description": str(fact_item.payload.get("description", "")),
                "source_payload": fact_item.payload,
                "fact_batch_synthesizer_version": fact_batch.synthesizer_version,
            },
        )

    def _classify_fact(self, fact_type: str) -> tuple[str, str]:
        normalized = fact_type.strip().lower()
        if normalized in {"gap", "weakness", "misconception"}:
            return "weakness", "negative"
        if normalized in {"strength", "mastery"}:
            return "strength", "positive"
        return "evidence", "neutral"

    def _signal_id(self, *, fact_item: AssessmentFactItemRecord, signal_type: str) -> str:
        topic_key = fact_item.topic_key or "untagged"
        return f"ks-{fact_item.assessment_fact_item_id}-{signal_type}-{topic_key}"
```

- [x] **Step 4: Run the one-to-one projector test to verify it passes**

Run:

```powershell
pytest tests/test_knowledge_signal_projector.py::test_projector_converts_gap_fact_to_weakness_signal -q
```

Expected: PASS.

- [x] **Step 5: Add one-to-many projector test**

Append this test:

```python
def test_projector_preserves_one_signal_per_fact_item() -> None:
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
    fact_items = [
        AssessmentFactItemRecord(
            assessment_fact_item_id="afi-gap",
            assessment_fact_batch_id="afb-1",
            source_evaluation_item_id="ei-1",
            fact_type="gap",
            topic_key="state-boundary",
            title="state boundary",
            confidence=0.7,
            status="active",
            created_at="2026-04-09T12:03:00Z",
            payload={"description": "state boundary is unclear"},
        ),
        AssessmentFactItemRecord(
            assessment_fact_item_id="afi-strength",
            assessment_fact_batch_id="afb-1",
            source_evaluation_item_id="ei-2",
            fact_type="strength",
            topic_key="test-discipline",
            title="test discipline",
            confidence=0.9,
            status="active",
            created_at="2026-04-09T12:04:00Z",
            payload={"description": "tests are concrete"},
        ),
    ]

    signals = AssessmentFactSignalProjector().project(fact_batch=fact_batch, fact_items=fact_items)

    assert [signal.signal_type for signal in signals] == ["weakness", "strength"]
    assert [signal.polarity for signal in signals] == ["negative", "positive"]
    assert [signal.topic_key for signal in signals] == ["state-boundary", "test-discipline"]
```

- [x] **Step 6: Run all projector tests**

Run:

```powershell
pytest tests/test_knowledge_signal_projector.py -q
```

Expected: PASS.

- [x] **Step 7: Commit Task 3**

Run:

```powershell
git add review_gate/knowledge_signal_projector.py tests/test_knowledge_signal_projector.py
git commit -m "feat: project assessment facts into knowledge signals"
```

---

### Task 4: Verify The Migration Entrance Does Not Touch Legacy Graph Tables

**Files:**
- Modify: `tests/test_checkpoint_storage.py`

- [x] **Step 1: Add regression test for legacy graph isolation**

Append this test:

```python
def test_knowledge_signal_storage_does_not_write_legacy_graph_tables(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "checkpoint.db")
    store.initialize()
    _seed_minimal_assessment_fact(store)

    signal = KnowledgeSignalRecord(
        signal_id="ks-afi-1-weakness-proposal-execution-separation",
        assessment_fact_batch_id="afb-1",
        assessment_fact_item_id="afi-1",
        source_evaluation_item_id="ei-1",
        signal_type="weakness",
        topic_key="proposal-execution-separation",
        polarity="negative",
        summary="proposal execution separation",
        confidence=0.8,
        status="active",
        projector_version="fact-signal-v1",
        created_at="2026-04-09T12:03:00Z",
        payload={"source_fact_type": "gap"},
    )

    store.insert_knowledge_signals([signal])

    assert store.list_knowledge_nodes() == []
    assert store.list_knowledge_relations() == []
```

- [x] **Step 2: Run the legacy isolation test**

Run:

```powershell
pytest tests/test_checkpoint_storage.py::test_knowledge_signal_storage_does_not_write_legacy_graph_tables -q
```

Expected: PASS once Task 2 is complete. If it fails because `list_knowledge_nodes` requires a profile id in the current implementation, call `store.list_knowledge_nodes(None)` instead and keep the assertion as an empty list.

- [x] **Step 3: Run focused migration entrance tests**

Run:

```powershell
pytest tests/test_knowledge_signal_projector.py tests/test_checkpoint_storage.py::test_checkpoint_storage_round_trips_knowledge_signals tests/test_checkpoint_storage.py::test_knowledge_signal_storage_does_not_write_legacy_graph_tables -q
```

Expected: PASS.

- [x] **Step 4: Run related checkpoint regression tests**

Run:

```powershell
pytest tests/test_assessment_synthesizer.py tests/test_checkpoint_storage.py -q
```

Expected: PASS, with existing Windows cleanup warnings acceptable if tests pass.

- [x] **Step 5: Commit Task 4**

Run:

```powershell
git add tests/test_checkpoint_storage.py
git commit -m "test: guard knowledge signal graph isolation"
```

---

## Final Verification

- [x] Run focused tests:

```powershell
pytest tests/test_knowledge_signal_projector.py tests/test_checkpoint_storage.py tests/test_assessment_synthesizer.py -q
```

Expected: PASS.

- [x] Check changed files:

```powershell
git status --short --branch
```

Expected: only intentional tracked changes remain, plus pre-existing untracked `.env/`, `eval-live-smoke-*`, and `tmp_review_check*` directories if they still exist.

- [x] Push if the implementation commits are complete:

```powershell
git push
```

Expected: branch updates successfully.

---

## Self-Review

Spec coverage:

1. `KnowledgeSignalRecord` is covered by Task 1.
2. `knowledge_signals` persistence is covered by Task 2.
3. Deterministic `AssessmentFactItemRecord -> KnowledgeSignalRecord` projection is covered by Task 3.
4. Legacy graph isolation is covered by Task 4.
5. GraphRevision, node/relation projection, active pointers, maintenance agent, and LLM calls are intentionally excluded from this implementation batch.

Type consistency:

1. The model field names match the SQLite column names where columns are indexed or queried.
2. The storage methods return `KnowledgeSignalRecord.from_json(...)`, matching existing checkpoint storage style.
3. The projector depends only on `AssessmentFactBatchRecord`, `AssessmentFactItemRecord`, and `KnowledgeSignalRecord`.

Implementation boundary:

1. Do not modify `ProfileSpaceService`.
2. Do not write to `knowledge_node_store` or `knowledge_relation_store`.
3. Do not add LLM calls to the signal projector.
4. Do not introduce `GraphRevision` in this batch.
