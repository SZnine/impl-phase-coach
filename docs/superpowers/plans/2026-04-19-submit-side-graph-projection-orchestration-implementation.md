# Submit-Side Graph Projection Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task in the current session. Do not use subagents for this repository flow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one submit-side answer checkpoint automatically persist assessment facts, knowledge signals, graph revision, graph nodes, and the active graph pointer.

**Architecture:** Keep `AnswerCheckpointWriter` as the submit write boundary. It already owns workflow, answer, evaluation, and assessment fact writes; this plan adds deterministic derived writes immediately after fact persistence. `AssessmentSynthesizer` remains facts-only, `ReviewFlowService` remains orchestration-only, and legacy profile/map graph tables remain untouched.

**Tech Stack:** Python dataclasses, SQLite-backed `SQLiteStore`, pytest, existing deterministic projectors `AssessmentFactSignalProjector` and `KnowledgeSignalGraphProjector`.

---

## File Structure

- Modify: `tests/test_answer_checkpoint_writer.py`
  - Add submit-chain assertions for knowledge signals and graph revision records.
  - Add no-signal behavior coverage.
  - Add strict projection failure coverage.

- Modify: `review_gate/answer_checkpoint_writer.py`
  - Extend `CheckpointWriteResult` with derived projection observability fields.
  - Inject default `AssessmentFactSignalProjector` and `KnowledgeSignalGraphProjector`.
  - Persist signals and graph revision after assessment facts and before marking workflow completed.

- No changes:
  - `review_gate/review_flow_service.py`
  - `review_gate/assessment_synthesizer.py`
  - `review_gate/storage_sqlite.py`
  - HTTP/UI/read APIs
  - legacy `knowledge_nodes` / `knowledge_relations` profile-space tables

---

### Task 1: Add Failing Submit-Chain Graph Projection Assertions

**Files:**
- Modify: `tests/test_answer_checkpoint_writer.py`

- [ ] **Step 1: Extend imports**

Add these records to the existing `review_gate.checkpoint_models` import block:

```python
    ActiveGraphRevisionPointerRecord,
    GraphRevisionRecord,
    KnowledgeNodeRecord,
    KnowledgeSignalRecord,
```

- [ ] **Step 2: Update the expected `CheckpointWriteResult` in `test_answer_checkpoint_writer_persists_submit_chain`**

Replace the existing expected result with:

```python
    assert result == CheckpointWriteResult(
        workflow_run_id="run-req-submit-1",
        question_batch_id="qb-req-qgen-1",
        answer_batch_id="ab-req-submit-1",
        evaluation_batch_id="eb-req-submit-1",
        assessment_fact_batch_id="afb-eb-req-submit-1",
        assessment_fact_item_count=1,
        knowledge_signal_count=1,
        graph_revision_id="gr-proj-1-stage-stage-1-20260410110000",
        graph_node_count=1,
    )
```

- [ ] **Step 3: Add signal and graph assertions at the end of `test_answer_checkpoint_writer_persists_submit_chain`**

Append this block after the existing assessment fact item assertion:

```python
    signal_id = (
        "ks-afi-ei-req-submit-1-0-proposal-execution-separation"
        "-weakness-proposal-execution-separation"
    )
    assert store.list_knowledge_signals_for_fact_batch("afb-eb-req-submit-1") == [
        KnowledgeSignalRecord(
            signal_id=signal_id,
            assessment_fact_batch_id="afb-eb-req-submit-1",
            assessment_fact_item_id="afi-ei-req-submit-1-0-proposal-execution-separation",
            source_evaluation_item_id="ei-req-submit-1-0",
            signal_type="weakness",
            topic_key="proposal-execution-separation",
            polarity="negative",
            summary="proposal execution separation",
            confidence=0.8,
            status="active",
            projector_version="fact-signal-v1",
            created_at="2026-04-10T11:00:00Z",
            payload={
                "source_fact_type": "gap",
                "source_title": "proposal execution separation",
                "description": "Still mixes proposal and execution.",
                "source_payload": {
                    "description": "Still mixes proposal and execution.",
                    "dimension_refs": ["understanding", "causality"],
                    "evidence_span_ids": [],
                },
                "fact_batch_synthesizer_version": "first-checkpoint-v1",
            },
        )
    ]
    assert store.get_graph_revision("gr-proj-1-stage-stage-1-20260410110000") == GraphRevisionRecord(
        graph_revision_id="gr-proj-1-stage-stage-1-20260410110000",
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        revision_type="deterministic_signal_projection",
        based_on_revision_id=None,
        source_fact_batch_ids=["afb-eb-req-submit-1"],
        source_signal_ids=[signal_id],
        status="active",
        revision_summary="1 signals projected into 1 nodes",
        node_count=1,
        relation_count=0,
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-10T11:00:00Z",
        activated_at="2026-04-10T11:00:00Z",
        payload={"projector_version": "signal-graph-v1"},
    )
    assert store.list_graph_nodes("gr-proj-1-stage-stage-1-20260410110000") == [
        KnowledgeNodeRecord(
            knowledge_node_id=(
                "kn-gr-proj-1-stage-stage-1-20260410110000"
                "-proposal-execution-separation"
            ),
            graph_revision_id="gr-proj-1-stage-stage-1-20260410110000",
            topic_key="proposal-execution-separation",
            label="proposal execution separation",
            node_type="weakness_topic",
            description="Still mixes proposal and execution.",
            source_signal_ids=[signal_id],
            supporting_fact_ids=["afi-ei-req-submit-1-0-proposal-execution-separation"],
            confidence=0.8,
            status="active",
            created_by="knowledge_signal_graph_projector",
            created_at="2026-04-10T11:00:00Z",
            updated_at="2026-04-10T11:00:00Z",
            payload={
                "projector_version": "signal-graph-v1",
                "signal_types": ["weakness"],
                "polarity_counts": {"negative": 1},
            },
        )
    ]
    assert store.get_active_graph_revision_pointer("proj-1", "stage", "stage-1") == (
        ActiveGraphRevisionPointerRecord(
            project_id="proj-1",
            scope_type="stage",
            scope_ref="stage-1",
            active_graph_revision_id="gr-proj-1-stage-stage-1-20260410110000",
            updated_at="2026-04-10T11:00:00Z",
            updated_by="knowledge_signal_graph_projector",
            payload={"projector_version": "signal-graph-v1"},
        )
    )
    assert store.list_knowledge_nodes() == []
    assert store.list_knowledge_relations() == []
```

- [ ] **Step 4: Run the focused test and verify it fails for missing result fields or graph rows**

Run:

```bash
pytest tests/test_answer_checkpoint_writer.py::test_answer_checkpoint_writer_persists_submit_chain -q
```

Expected: FAIL before implementation because `CheckpointWriteResult` lacks the new fields and `AnswerCheckpointWriter` does not persist signals/graph rows.

---

### Task 2: Wire Signals and Graph Projection into `AnswerCheckpointWriter`

**Files:**
- Modify: `review_gate/answer_checkpoint_writer.py`

- [ ] **Step 1: Add projector imports**

Add these imports near the existing local imports:

```python
from review_gate.knowledge_graph_projector import KnowledgeSignalGraphProjector
from review_gate.knowledge_signal_projector import AssessmentFactSignalProjector
```

- [ ] **Step 2: Extend `CheckpointWriteResult`**

Replace the dataclass with:

```python
@dataclass(slots=True)
class CheckpointWriteResult:
    workflow_run_id: str
    question_batch_id: str
    answer_batch_id: str
    evaluation_batch_id: str
    assessment_fact_batch_id: str
    assessment_fact_item_count: int = 0
    knowledge_signal_count: int = 0
    graph_revision_id: str | None = None
    graph_node_count: int = 0
```

The defaults preserve existing tests and fakes that construct `CheckpointWriteResult` with the old five required IDs.

- [ ] **Step 3: Update the writer constructor**

Replace the current constructor with:

```python
    def __init__(
        self,
        *,
        store: SQLiteStore,
        synthesizer: AssessmentSynthesizer,
        signal_projector: AssessmentFactSignalProjector | None = None,
        graph_projector: KnowledgeSignalGraphProjector | None = None,
    ) -> None:
        self._store = store
        self._synthesizer = synthesizer
        self._signal_projector = signal_projector or AssessmentFactSignalProjector()
        self._graph_projector = graph_projector or KnowledgeSignalGraphProjector()
```

- [ ] **Step 4: Insert derived projection writes after fact persistence**

Immediately after:

```python
        self._store.insert_assessment_fact_batch(fact_batch)
        self._store.insert_assessment_fact_items(fact_items)
```

add:

```python
        knowledge_signals = self._signal_projector.project(
            fact_batch=fact_batch,
            fact_items=fact_items,
        )
        self._store.insert_knowledge_signals(knowledge_signals)

        graph_revision_id: str | None = None
        graph_node_count = 0
        if knowledge_signals:
            graph_revision, graph_nodes, active_pointer = self._graph_projector.project(
                project_id=request.project_id,
                scope_type="stage",
                scope_ref=request.stage_id,
                signals=knowledge_signals,
                created_at=request.created_at,
            )
            self._store.insert_graph_revision(graph_revision)
            self._store.insert_graph_nodes(graph_nodes)
            self._store.upsert_active_graph_revision_pointer(active_pointer)
            graph_revision_id = graph_revision.graph_revision_id
            graph_node_count = len(graph_nodes)
```

- [ ] **Step 5: Return the new observability fields**

Replace the current return block with:

```python
        return CheckpointWriteResult(
            workflow_run_id=submit_workflow_run_id,
            question_batch_id=resolved_chain.question_batch_id,
            answer_batch_id=answer_batch_id,
            evaluation_batch_id=evaluation_batch_id,
            assessment_fact_batch_id=fact_batch.assessment_fact_batch_id,
            assessment_fact_item_count=len(fact_items),
            knowledge_signal_count=len(knowledge_signals),
            graph_revision_id=graph_revision_id,
            graph_node_count=graph_node_count,
        )
```

- [ ] **Step 6: Run the focused happy-path test**

Run:

```bash
pytest tests/test_answer_checkpoint_writer.py::test_answer_checkpoint_writer_persists_submit_chain -q
```

Expected: PASS.

---

### Task 3: Cover Empty Signals Without Empty Graph Revision

**Files:**
- Modify: `tests/test_answer_checkpoint_writer.py`

- [ ] **Step 1: Add no-signal submit test**

Append this test after `test_answer_checkpoint_writer_uses_assessment_synthesizer_for_multiple_gaps`:

```python
def test_answer_checkpoint_writer_skips_graph_revision_when_assessment_has_no_signals(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = AnswerCheckpointWriter(store=store, synthesizer=AssessmentSynthesizer())
    _seed_generated_question_chain(store, request_id="req-qgen-1", created_at="2026-04-10T10:05:00Z")

    result = writer.write(
        request=_writer_request(
            request_id="req-submit-no-signal",
            answer_text="No diagnosed gaps in this answer.",
            created_at="2026-04-10T11:20:00Z",
        ),
        resolved_chain=_resolved_chain(),
        assessment={
            "verdict": "pass",
            "score": 0.95,
            "summary": "No durable gaps detected.",
            "gaps": [],
            "dimensions": ["understanding"],
        },
    )

    assert result.assessment_fact_batch_id == "afb-eb-req-submit-no-signal"
    assert result.assessment_fact_item_count == 0
    assert result.knowledge_signal_count == 0
    assert result.graph_revision_id is None
    assert result.graph_node_count == 0
    assert store.list_assessment_fact_items("afb-eb-req-submit-no-signal") == []
    assert store.list_knowledge_signals_for_fact_batch("afb-eb-req-submit-no-signal") == []
    assert store.get_active_graph_revision_pointer("proj-1", "stage", "stage-1") is None
```

- [ ] **Step 2: Run the no-signal test**

Run:

```bash
pytest tests/test_answer_checkpoint_writer.py::test_answer_checkpoint_writer_skips_graph_revision_when_assessment_has_no_signals -q
```

Expected: PASS after Task 2. If it fails because the synthesizer emits a non-gap fact for empty gaps, inspect `AssessmentSynthesizer.synthesize` and adjust the test input to use the existing no-fact path rather than changing graph behavior.

---

### Task 4: Preserve Strict Failure Boundary for Graph Projection

**Files:**
- Modify: `tests/test_answer_checkpoint_writer.py`

- [ ] **Step 1: Add a failing graph projector test double**

Add this helper class near the other test helpers:

```python
class FailingGraphProjector:
    def project(self, **_: object) -> object:
        raise RuntimeError("graph projection failed")
```

- [ ] **Step 2: Add strict failure test**

Append this test after the existing downstream failure test:

```python
def test_answer_checkpoint_writer_leaves_submit_workflow_in_progress_on_graph_projection_failure(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = AnswerCheckpointWriter(
        store=store,
        synthesizer=AssessmentSynthesizer(),
        graph_projector=FailingGraphProjector(),  # type: ignore[arg-type]
    )
    _seed_generated_question_chain(store, request_id="req-qgen-1", created_at="2026-04-10T10:05:00Z")

    with pytest.raises(RuntimeError, match="graph projection failed"):
        writer.write(
            request=_writer_request(
                request_id="req-submit-graph-fail",
                answer_text="We split state and scoring boundaries.",
                created_at="2026-04-10T11:25:00Z",
            ),
            resolved_chain=_resolved_chain(),
            assessment={
                "verdict": "partial",
                "score": 0.6,
                "summary": "Graph projection failure should not finalize workflow.",
                "gaps": ["proposal-execution-separation"],
                "dimensions": ["understanding"],
            },
        )

    assert store.get_workflow_request("req-submit-graph-fail") == WorkflowRequestRecord(
        request_id="req-submit-graph-fail",
        request_type="assessment",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="local-user",
        source="question_detail",
        status="in_progress",
        created_at="2026-04-10T11:25:00Z",
        payload={"request_id": "req-submit-graph-fail"},
    )
    assert store.get_workflow_run("run-req-submit-graph-fail") == WorkflowRunRecord(
        run_id="run-req-submit-graph-fail",
        request_id="req-submit-graph-fail",
        run_type="assessment",
        status="in_progress",
        started_at="2026-04-10T11:25:00Z",
        finished_at="2026-04-10T11:25:00Z",
        supersedes_run_id=None,
        payload={"request_id": "req-submit-graph-fail"},
    )
    assert store.list_knowledge_signals_for_fact_batch("afb-eb-req-submit-graph-fail") != []
    assert store.get_active_graph_revision_pointer("proj-1", "stage", "stage-1") is None
```

This encodes the current v1 boundary: projection failures are visible, not swallowed. Already-written fact and signal rows are allowed to remain because this phase does not introduce a cross-table transaction manager.

- [ ] **Step 3: Run the strict failure test**

Run:

```bash
pytest tests/test_answer_checkpoint_writer.py::test_answer_checkpoint_writer_leaves_submit_workflow_in_progress_on_graph_projection_failure -q
```

Expected: PASS.

---

### Task 5: Run Focused Regression Suite

**Files:**
- No edits.

- [ ] **Step 1: Run writer tests**

Run:

```bash
pytest tests/test_answer_checkpoint_writer.py -q
```

Expected: PASS.

- [ ] **Step 2: Run graph migration regression tests**

Run:

```bash
pytest tests/test_answer_checkpoint_writer.py tests/test_knowledge_signal_projector.py tests/test_knowledge_graph_projector.py tests/test_checkpoint_storage.py -q
```

Expected: PASS.

- [ ] **Step 3: Run service smoke tests that construct `CheckpointWriteResult` fakes**

Run:

```bash
pytest tests/test_review_flow_service.py -q
```

Expected: PASS. The result dataclass defaults should keep old five-field fake construction compatible.

---

### Task 6: Commit the Implementation

**Files:**
- Modify: `tests/test_answer_checkpoint_writer.py`
- Modify: `review_gate/answer_checkpoint_writer.py`

- [ ] **Step 1: Inspect the diff**

Run:

```bash
git diff -- tests/test_answer_checkpoint_writer.py review_gate/answer_checkpoint_writer.py
```

Expected:
- `AnswerCheckpointWriter` imports and owns the two projectors.
- `CheckpointWriteResult` has four new observability fields.
- Submit writes persist facts before signals, signals before graph revision/nodes/pointer, pointer last.
- No HTTP/UI/profile-space read code changed.

- [ ] **Step 2: Commit**

Run:

```bash
git add tests/test_answer_checkpoint_writer.py review_gate/answer_checkpoint_writer.py
git commit -m "feat: project submit facts into graph revisions"
```

Expected: commit succeeds.

---

## Self-Review

Spec coverage:
- Submit chain now reaches `AssessmentFact -> KnowledgeSignal -> GraphRevision`.
- Empty-signal submit completes without an empty graph revision.
- Strict failure remains visible and leaves workflow in progress.
- Legacy profile-space tables stay untouched.

Intentional exclusions:
- No graph read API.
- No UI wiring.
- No `KnowledgeRelationRecord`.
- No maintenance agent.
- No cross-table transaction manager.

Type consistency:
- New writer constructor dependencies are optional and default to concrete projectors.
- `CheckpointWriteResult` keeps backward-compatible defaults.
- Graph projection uses `project_id=request.project_id`, `scope_type="stage"`, `scope_ref=request.stage_id`, and `created_at=request.created_at`, matching existing projector signatures.

Execution choice for this repo:
- Use inline execution only.
- Do not dispatch subagents.
