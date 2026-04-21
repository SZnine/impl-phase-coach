# KnowledgeRelation v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task in the current session. Do not use subagents for this repository flow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add provenance-backed `KnowledgeRelation` support to the new revision-scoped Graph Layer and verify it through a real HTTP submit + SQLite + graph-revision read smoke.

**Architecture:** Add `KnowledgeRelationRecord` and SQLite persistence first, then materialize explicit `support_signals` into `support_relation` facts/signals. The graph projector creates relation records only from `support_relation` signals, and the revision-aware read model exposes them through `/api/knowledge/graph-revision`.

**Tech Stack:** Python dataclasses, SQLite JSON payload persistence, deterministic projectors, FastAPI TestClient, pytest.

---

## File Map

- Modify: `review_gate/checkpoint_models.py`
  - Add `KnowledgeRelationRecord`.
- Modify: `review_gate/storage_sqlite.py`
  - Add `graph_knowledge_relations` table, indexes, `insert_graph_relations()`, and `list_graph_relations()`.
- Modify: `review_gate/assessment_synthesizer.py`
  - Preserve explicit `support_signals` as `support_relation` facts.
  - Normalize topic keys through one stable slug helper.
- Modify: `review_gate/knowledge_signal_projector.py`
  - Convert `support_relation` facts into `support_relation` signals.
- Modify: `review_gate/knowledge_graph_projector.py`
  - Return `(revision, nodes, relations, pointer)`.
  - Create relations only from `support_relation` signals.
- Modify: `review_gate/answer_checkpoint_writer.py`
  - Pass `support_signals` through the evaluation item payload.
  - Insert graph relations before activating the pointer.
  - Return `graph_relation_count`.
- Modify: `review_gate/review_flow_service.py`
  - Include derived `support_signals` in `writer_assessment`.
- Modify: `review_gate/view_dtos.py`
  - Add `GraphRevisionRelationDTO`.
  - Type `GraphRevisionViewDTO.relations` as relation DTOs.
- Modify: `review_gate/workspace_api.py`
  - Map `KnowledgeRelationRecord` to `GraphRevisionRelationDTO`.
- Modify tests:
  - `tests/test_knowledge_graph_projector.py`
  - `tests/test_checkpoint_storage.py`
  - `tests/test_assessment_synthesizer.py`
  - `tests/test_knowledge_signal_projector.py`
  - `tests/test_answer_checkpoint_writer.py`
  - `tests/test_workspace_api.py`
  - `tests/test_http_api.py`

## Boundary Decisions

1. Relation generation is provenance-backed only.
2. No relation is created from broad node-type heuristics.
3. Only `supports` is generated in v1.
4. `support_signals` are already derived by `ReviewFlowService`; this phase only persists them into the checkpoint graph path.
5. The final acceptance test must use the HTTP submit path and real SQLite persistence.

## Task 1: Add Relation Record and SQLite Persistence

**Files:**
- Modify: `review_gate/checkpoint_models.py`
- Modify: `review_gate/storage_sqlite.py`
- Modify: `tests/test_knowledge_graph_projector.py`
- Modify: `tests/test_checkpoint_storage.py`

- [ ] **Step 1: Write `KnowledgeRelationRecord` round-trip test**

In `tests/test_knowledge_graph_projector.py`, add `KnowledgeRelationRecord` to the import block and add this test after `test_knowledge_node_record_round_trips_json_payload`.

```python
def test_knowledge_relation_record_round_trips_json_payload() -> None:
    relation = KnowledgeRelationRecord(
        knowledge_relation_id="kr-gr-1-boundary-discipline-supports-api-boundary-discipline",
        graph_revision_id="gr-1",
        from_node_id="kn-gr-1-boundary-discipline",
        to_node_id="kn-gr-1-api-boundary-discipline",
        relation_type="supports",
        directionality="directed",
        description="Boundary discipline supports API boundary discipline.",
        source_signal_ids=["ks-support-1"],
        supporting_fact_ids=["afi-support-1"],
        confidence=0.82,
        status="active",
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-21T10:00:00Z",
        updated_at="2026-04-21T10:00:00Z",
        payload={"basis_key": "boundary_awareness"},
    )

    assert KnowledgeRelationRecord.from_json(relation.to_json()) == relation
```

- [ ] **Step 2: Run red record test**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py::test_knowledge_relation_record_round_trips_json_payload -q
```

Expected:

```text
ImportError: cannot import name 'KnowledgeRelationRecord'
```

- [ ] **Step 3: Implement `KnowledgeRelationRecord`**

In `review_gate/checkpoint_models.py`, add this dataclass after `KnowledgeNodeRecord`.

```python
@dataclass(slots=True)
class KnowledgeRelationRecord(JsonSerializable):
    knowledge_relation_id: str
    graph_revision_id: str
    from_node_id: str
    to_node_id: str
    relation_type: str
    directionality: str
    description: str
    source_signal_ids: list[str]
    supporting_fact_ids: list[str]
    confidence: float
    status: str
    created_by: str
    created_at: str
    updated_at: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            knowledge_relation_id=_coerce_str(payload["knowledge_relation_id"]),
            graph_revision_id=_coerce_str(payload.get("graph_revision_id"), ""),
            from_node_id=_coerce_str(payload.get("from_node_id"), ""),
            to_node_id=_coerce_str(payload.get("to_node_id"), ""),
            relation_type=_coerce_str(payload.get("relation_type"), ""),
            directionality=_coerce_str(payload.get("directionality"), ""),
            description=_coerce_str(payload.get("description"), ""),
            source_signal_ids=_coerce_str_list(payload.get("source_signal_ids")),
            supporting_fact_ids=_coerce_str_list(payload.get("supporting_fact_ids")),
            confidence=_coerce_float(payload.get("confidence"), 0.0),
            status=_coerce_str(payload.get("status"), ""),
            created_by=_coerce_str(payload.get("created_by"), ""),
            created_at=_coerce_str(payload.get("created_at"), ""),
            updated_at=_coerce_str(payload.get("updated_at"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )
```

- [ ] **Step 4: Run green record test**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py::test_knowledge_relation_record_round_trips_json_payload -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Write SQLite relation persistence test**

In `tests/test_checkpoint_storage.py`, add `KnowledgeRelationRecord` to the import block and update `test_checkpoint_storage_round_trips_graph_projection_records`:

```python
    revision = GraphRevisionRecord(
        graph_revision_id="gr-proj-1-stage-1-20260409120400",
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        revision_type="deterministic_signal_projection",
        based_on_revision_id=None,
        source_fact_batch_ids=["afb-1"],
        source_signal_ids=["ks-1", "ks-support-1"],
        status="active",
        revision_summary="2 signals projected into 2 nodes and 1 relations",
        node_count=2,
        relation_count=1,
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-09T12:04:00Z",
        activated_at="2026-04-09T12:04:00Z",
        payload={"projector_version": "signal-graph-v1"},
    )
```

Add a source node before the existing target node:

```python
    source_node = KnowledgeNodeRecord(
        knowledge_node_id="kn-gr-proj-1-stage-1-20260409120400-boundary-discipline",
        graph_revision_id="gr-proj-1-stage-1-20260409120400",
        topic_key="boundary-discipline",
        label="Boundary discipline",
        node_type="evidence_topic",
        description="Boundary discipline was cited as supporting evidence.",
        source_signal_ids=["ks-support-1"],
        supporting_fact_ids=["afi-support-1"],
        confidence=0.82,
        status="active",
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-09T12:04:00Z",
        updated_at="2026-04-09T12:04:00Z",
        payload={"signal_types": ["support_relation"]},
    )
```

Keep the existing node as `target_node`, then add:

```python
    relation = KnowledgeRelationRecord(
        knowledge_relation_id=(
            "kr-gr-proj-1-stage-1-20260409120400"
            "-boundary-discipline-supports-proposal-execution-separation"
        ),
        graph_revision_id="gr-proj-1-stage-1-20260409120400",
        from_node_id=source_node.knowledge_node_id,
        to_node_id=target_node.knowledge_node_id,
        relation_type="supports",
        directionality="directed",
        description="Boundary discipline supports proposal execution separation.",
        source_signal_ids=["ks-support-1"],
        supporting_fact_ids=["afi-support-1"],
        confidence=0.82,
        status="active",
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-09T12:04:00Z",
        updated_at="2026-04-09T12:04:00Z",
        payload={"basis_key": "boundary_awareness"},
    )
```

Update inserts and assertions:

```python
    store.insert_graph_revision(revision)
    store.insert_graph_nodes([source_node, target_node])
    store.insert_graph_relations([relation])
    store.upsert_active_graph_revision_pointer(pointer)

    assert store.get_graph_revision("gr-proj-1-stage-1-20260409120400") == revision
    assert store.list_graph_nodes("gr-proj-1-stage-1-20260409120400") == [source_node, target_node]
    assert store.list_graph_relations("gr-proj-1-stage-1-20260409120400") == [relation]
    assert store.get_active_graph_revision_pointer("proj-1", "stage", "stage-1") == pointer
```

- [ ] **Step 6: Run red storage test**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_checkpoint_storage.py::test_checkpoint_storage_round_trips_graph_projection_records -q
```

Expected:

```text
AttributeError: 'SQLiteStore' object has no attribute 'insert_graph_relations'
```

- [ ] **Step 7: Implement SQLite table and methods**

In `review_gate/storage_sqlite.py`, import `KnowledgeRelationRecord`, add table creation after `graph_knowledge_nodes`, and add methods after `list_graph_nodes`.

```python
                CREATE TABLE IF NOT EXISTS graph_knowledge_relations (
                    knowledge_relation_id TEXT PRIMARY KEY,
                    graph_revision_id TEXT NOT NULL,
                    from_node_id TEXT NOT NULL,
                    to_node_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    directionality TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (graph_revision_id) REFERENCES graph_revisions(graph_revision_id),
                    FOREIGN KEY (from_node_id) REFERENCES graph_knowledge_nodes(knowledge_node_id),
                    FOREIGN KEY (to_node_id) REFERENCES graph_knowledge_nodes(knowledge_node_id)
                );

                CREATE INDEX IF NOT EXISTS idx_graph_knowledge_relations_revision
                    ON graph_knowledge_relations(graph_revision_id);

                CREATE INDEX IF NOT EXISTS idx_graph_knowledge_relations_from_node
                    ON graph_knowledge_relations(from_node_id);

                CREATE INDEX IF NOT EXISTS idx_graph_knowledge_relations_to_node
                    ON graph_knowledge_relations(to_node_id);

                CREATE INDEX IF NOT EXISTS idx_graph_knowledge_relations_type
                    ON graph_knowledge_relations(relation_type);
```

```python
    def insert_graph_relations(self, records: list[KnowledgeRelationRecord]) -> None:
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO graph_knowledge_relations (
                        knowledge_relation_id,
                        graph_revision_id,
                        from_node_id,
                        to_node_id,
                        relation_type,
                        directionality,
                        confidence,
                        status,
                        created_at,
                        updated_at,
                        payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.knowledge_relation_id,
                        record.graph_revision_id,
                        record.from_node_id,
                        record.to_node_id,
                        record.relation_type,
                        record.directionality,
                        record.confidence,
                        record.status,
                        record.created_at,
                        record.updated_at,
                        record.to_json(),
                    ),
                )

    def list_graph_relations(self, graph_revision_id: str) -> list[KnowledgeRelationRecord]:
        rows = self._fetch_all(
            """
            SELECT payload
            FROM graph_knowledge_relations
            WHERE graph_revision_id = ?
            ORDER BY relation_type, from_node_id, to_node_id, knowledge_relation_id
            """,
            (graph_revision_id,),
        )
        return [KnowledgeRelationRecord.from_json(row["payload"]) for row in rows]
```

- [ ] **Step 8: Run green storage tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py::test_knowledge_relation_record_round_trips_json_payload tests/test_checkpoint_storage.py::test_checkpoint_storage_round_trips_graph_projection_records -q
```

Expected:

```text
2 passed
```

## Task 2: Materialize Explicit Support Signals as Facts and Signals

**Files:**
- Modify: `tests/test_assessment_synthesizer.py`
- Modify: `tests/test_knowledge_signal_projector.py`
- Modify: `review_gate/assessment_synthesizer.py`
- Modify: `review_gate/knowledge_signal_projector.py`

- [ ] **Step 1: Write support fact synthesizer test**

In `tests/test_assessment_synthesizer.py`, add this test after `test_assessment_synthesizer_counts_multiple_gaps_as_multiple_fact_items`.

```python
def test_assessment_synthesizer_materializes_support_signals_as_relation_facts() -> None:
    synthesizer = AssessmentSynthesizer()
    evaluation_batch = EvaluationBatchRecord(
        evaluation_batch_id="eb-support",
        answer_batch_id="ab-support",
        workflow_run_id="run-support",
        project_id="proj-1",
        stage_id="stage-1",
        evaluated_by="evaluator_agent",
        evaluator_version="test-v1",
        confidence=0.84,
        status="completed",
        evaluated_at="2026-04-21T10:00:00Z",
        payload={},
    )
    evaluation_item = EvaluationItemRecord(
        evaluation_item_id="ei-support",
        evaluation_batch_id="eb-support",
        question_id="set-1-q-1",
        answer_item_id="ai-support",
        local_verdict="partial",
        confidence=0.84,
        status="completed",
        evaluated_at="2026-04-21T10:00:00Z",
        payload={
            "reasoned_summary": "API boundary discipline still needs a supporting method.",
            "diagnosed_gaps": ["API boundary discipline"],
            "dimension_refs": ["boundary_awareness"],
            "support_signals": [
                {
                    "source_label": "Boundary discipline",
                    "source_node_type": "foundation",
                    "target_label": "API boundary discipline",
                    "target_node_type": "method",
                    "basis_type": "support_basis_tag",
                    "basis_key": "boundary_awareness",
                }
            ],
        },
    )

    fact_batch, fact_items = synthesizer.synthesize(
        workflow_run_id="run-support",
        evaluation_batch=evaluation_batch,
        evaluation_items=[evaluation_item],
        evidence_spans=[],
    )

    assert fact_batch.payload["item_count"] == 2
    assert [item.fact_type for item in fact_items] == ["gap", "support_relation"]
    support_fact = fact_items[1]
    assert support_fact.assessment_fact_item_id == "afi-ei-support-supports-boundary-discipline-api-boundary-discipline"
    assert support_fact.topic_key == "boundary-discipline"
    assert support_fact.title == "Boundary discipline supports API boundary discipline"
    assert support_fact.payload["relation_type"] == "supports"
    assert support_fact.payload["source_topic_key"] == "boundary-discipline"
    assert support_fact.payload["target_topic_key"] == "api-boundary-discipline"
```

- [ ] **Step 2: Run red synthesizer test**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_assessment_synthesizer.py::test_assessment_synthesizer_materializes_support_signals_as_relation_facts -q
```

Expected:

```text
FAILED ... assert ['gap'] == ['gap', 'support_relation']
```

- [ ] **Step 3: Implement support fact materialization**

In `review_gate/assessment_synthesizer.py`, import `re` and add helper methods to `AssessmentSynthesizer`.

```python
    def _topic_key(self, value: str) -> str:
        key = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
        return key or "untagged"

    def _support_relation_fact_id(self, *, evaluation_item_id: str, source_topic_key: str, target_topic_key: str) -> str:
        return f"afi-{evaluation_item_id}-supports-{source_topic_key}-{target_topic_key}"
```

Change gap fact creation to use a normalized topic key:

```python
            for gap in diagnosed_gaps:
                topic_key = self._topic_key(str(gap))
                fact_items.append(
                    AssessmentFactItemRecord(
                        assessment_fact_item_id=f"afi-{item.evaluation_item_id}-{topic_key}",
                        assessment_fact_batch_id=assessment_fact_batch_id,
                        source_evaluation_item_id=item.evaluation_item_id,
                        fact_type="gap",
                        topic_key=topic_key,
                        title=str(gap).replace("-", " "),
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
```

After the gap loop, add support fact creation:

```python
            for support_signal in item.payload.get("support_signals", []):
                if not isinstance(support_signal, dict):
                    continue
                source_label = str(support_signal.get("source_label", "")).strip()
                target_label = str(support_signal.get("target_label", "")).strip()
                source_node_type = str(support_signal.get("source_node_type", "")).strip()
                target_node_type = str(support_signal.get("target_node_type", "")).strip()
                basis_type = str(support_signal.get("basis_type", "")).strip()
                basis_key = str(support_signal.get("basis_key", "")).strip()
                if not (source_label and target_label and source_node_type and target_node_type and basis_type and basis_key):
                    continue
                source_topic_key = self._topic_key(source_label)
                target_topic_key = self._topic_key(target_label)
                fact_items.append(
                    AssessmentFactItemRecord(
                        assessment_fact_item_id=self._support_relation_fact_id(
                            evaluation_item_id=item.evaluation_item_id,
                            source_topic_key=source_topic_key,
                            target_topic_key=target_topic_key,
                        ),
                        assessment_fact_batch_id=assessment_fact_batch_id,
                        source_evaluation_item_id=item.evaluation_item_id,
                        fact_type="support_relation",
                        topic_key=source_topic_key,
                        title=f"{source_label} supports {target_label}",
                        confidence=item.confidence,
                        status="active",
                        created_at=item.evaluated_at,
                        payload={
                            "relation_type": "supports",
                            "directionality": "directed",
                            "source_label": source_label,
                            "source_node_type": source_node_type,
                            "source_topic_key": source_topic_key,
                            "target_label": target_label,
                            "target_node_type": target_node_type,
                            "target_topic_key": target_topic_key,
                            "basis_type": basis_type,
                            "basis_key": basis_key,
                            "description": f"{source_label} supports {target_label}.",
                        },
                    )
                )
```

- [ ] **Step 4: Run green synthesizer test**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_assessment_synthesizer.py::test_assessment_synthesizer_materializes_support_signals_as_relation_facts tests/test_assessment_synthesizer.py::test_assessment_synthesizer_emits_fact_batch_and_items tests/test_assessment_synthesizer.py::test_assessment_synthesizer_counts_multiple_gaps_as_multiple_fact_items -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Write support signal projector test**

In `tests/test_knowledge_signal_projector.py`, add this test after `test_projector_converts_gap_fact_to_weakness_signal`.

```python
def test_projector_converts_support_relation_fact_to_support_relation_signal() -> None:
    fact_batch = AssessmentFactBatchRecord(
        assessment_fact_batch_id="afb-support",
        evaluation_batch_id="eb-support",
        workflow_run_id="run-support",
        synthesized_by="assessment_synthesizer",
        synthesizer_version="v1",
        status="completed",
        synthesized_at="2026-04-21T10:00:00Z",
        payload={},
    )
    fact_item = AssessmentFactItemRecord(
        assessment_fact_item_id="afi-support",
        assessment_fact_batch_id="afb-support",
        source_evaluation_item_id="ei-support",
        fact_type="support_relation",
        topic_key="boundary-discipline",
        title="Boundary discipline supports API boundary discipline",
        confidence=0.84,
        status="active",
        created_at="2026-04-21T10:00:00Z",
        payload={
            "relation_type": "supports",
            "directionality": "directed",
            "source_label": "Boundary discipline",
            "source_node_type": "foundation",
            "source_topic_key": "boundary-discipline",
            "target_label": "API boundary discipline",
            "target_node_type": "method",
            "target_topic_key": "api-boundary-discipline",
            "basis_type": "support_basis_tag",
            "basis_key": "boundary_awareness",
            "description": "Boundary discipline supports API boundary discipline.",
        },
    )

    signals = AssessmentFactSignalProjector().project(fact_batch=fact_batch, fact_items=[fact_item])

    assert len(signals) == 1
    assert signals[0].signal_id == "ks-afi-support-support_relation-boundary-discipline"
    assert signals[0].signal_type == "support_relation"
    assert signals[0].topic_key == "boundary-discipline"
    assert signals[0].polarity == "positive"
    assert signals[0].summary == "Boundary discipline supports API boundary discipline"
    assert signals[0].payload["target_topic_key"] == "api-boundary-discipline"
    assert signals[0].payload["relation_type"] == "supports"
```

- [ ] **Step 6: Run red signal projector test**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_signal_projector.py::test_projector_converts_support_relation_fact_to_support_relation_signal -q
```

Expected:

```text
FAILED ... assert 'evidence' == 'support_relation'
```

- [ ] **Step 7: Implement support relation signal classification**

In `review_gate/knowledge_signal_projector.py`, update `_classify_fact`:

```python
        if normalized == "support_relation":
            return "support_relation", "positive"
```

The existing `_project_item()` already carries `source_payload`; keep that, and ensure the top-level payload also exposes relation keys:

```python
            payload={
                "source_fact_type": fact_item.fact_type,
                "source_title": fact_item.title,
                "description": str(fact_item.payload.get("description", "")),
                "source_payload": fact_item.payload,
                "fact_batch_synthesizer_version": fact_batch.synthesizer_version,
                **{
                    key: value
                    for key, value in fact_item.payload.items()
                    if key
                    in {
                        "relation_type",
                        "directionality",
                        "source_label",
                        "source_node_type",
                        "source_topic_key",
                        "target_label",
                        "target_node_type",
                        "target_topic_key",
                        "basis_type",
                        "basis_key",
                    }
                },
            },
```

- [ ] **Step 8: Run green signal tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_signal_projector.py -q
```

Expected:

```text
All tests in tests/test_knowledge_signal_projector.py pass.
```

## Task 3: Project Relations from Support Relation Signals

**Files:**
- Modify: `tests/test_knowledge_graph_projector.py`
- Modify: `review_gate/knowledge_graph_projector.py`

- [ ] **Step 1: Write graph projector relation test**

In `tests/test_knowledge_graph_projector.py`, add this test after `test_graph_projector_creates_one_node_per_topic`.

```python
def test_graph_projector_creates_supports_relation_from_support_relation_signal() -> None:
    signals = [
        KnowledgeSignalRecord(
            signal_id="ks-gap",
            assessment_fact_batch_id="afb-1",
            assessment_fact_item_id="afi-gap",
            source_evaluation_item_id="ei-1",
            signal_type="weakness",
            topic_key="api-boundary-discipline",
            polarity="negative",
            summary="API boundary discipline",
            confidence=0.72,
            status="active",
            projector_version="fact-signal-v1",
            created_at="2026-04-21T10:00:00Z",
            payload={"description": "API boundary discipline is still unstable."},
        ),
        KnowledgeSignalRecord(
            signal_id="ks-support",
            assessment_fact_batch_id="afb-1",
            assessment_fact_item_id="afi-support",
            source_evaluation_item_id="ei-1",
            signal_type="support_relation",
            topic_key="boundary-discipline",
            polarity="positive",
            summary="Boundary discipline supports API boundary discipline",
            confidence=0.84,
            status="active",
            projector_version="fact-signal-v1",
            created_at="2026-04-21T10:00:00Z",
            payload={
                "relation_type": "supports",
                "directionality": "directed",
                "source_label": "Boundary discipline",
                "source_node_type": "foundation",
                "source_topic_key": "boundary-discipline",
                "target_label": "API boundary discipline",
                "target_node_type": "method",
                "target_topic_key": "api-boundary-discipline",
                "basis_type": "support_basis_tag",
                "basis_key": "boundary_awareness",
                "description": "Boundary discipline supports API boundary discipline.",
            },
        ),
    ]

    revision, nodes, relations, pointer = KnowledgeSignalGraphProjector().project(
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        signals=signals,
        created_at="2026-04-21T10:00:00Z",
    )

    assert revision.node_count == 2
    assert revision.relation_count == 1
    assert [node.topic_key for node in nodes] == ["api-boundary-discipline", "boundary-discipline"]
    assert len(relations) == 1
    assert relations[0].relation_type == "supports"
    assert relations[0].directionality == "directed"
    assert relations[0].from_node_id.endswith("-boundary-discipline")
    assert relations[0].to_node_id.endswith("-api-boundary-discipline")
    assert relations[0].source_signal_ids == ["ks-support"]
    assert relations[0].supporting_fact_ids == ["afi-support"]
    assert pointer.active_graph_revision_id == revision.graph_revision_id
```

- [ ] **Step 2: Run red graph projector test**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py::test_graph_projector_creates_supports_relation_from_support_relation_signal -q
```

Expected:

```text
ValueError: not enough values to unpack
```

- [ ] **Step 3: Implement relation projection**

In `review_gate/knowledge_graph_projector.py`, import `KnowledgeRelationRecord` and update return type:

```python
    ) -> tuple[
        GraphRevisionRecord,
        list[KnowledgeNodeRecord],
        list[KnowledgeRelationRecord],
        ActiveGraphRevisionPointerRecord,
    ]:
```

After `_project_nodes(...)`, add:

```python
        relations = self._project_relations(
            graph_revision_id=graph_revision_id,
            signals=signals,
            nodes=nodes,
            created_at=created_at,
        )
```

Set `relation_count=len(relations)` and return:

```python
        return revision, nodes, relations, pointer
```

Add relation helper:

```python
    def _project_relations(
        self,
        *,
        graph_revision_id: str,
        signals: list[KnowledgeSignalRecord],
        nodes: list[KnowledgeNodeRecord],
        created_at: str,
    ) -> list[KnowledgeRelationRecord]:
        node_by_topic = {node.topic_key: node for node in nodes}
        relations: list[KnowledgeRelationRecord] = []
        for signal in sorted(signals, key=lambda item: item.signal_id):
            if signal.signal_type != "support_relation":
                continue
            relation_type = str(signal.payload.get("relation_type", "")).strip()
            source_topic_key = str(signal.payload.get("source_topic_key", signal.topic_key)).strip()
            target_topic_key = str(signal.payload.get("target_topic_key", "")).strip()
            if relation_type != "supports" or not source_topic_key or not target_topic_key:
                continue
            source_node = node_by_topic.get(source_topic_key)
            target_node = node_by_topic.get(target_topic_key)
            if source_node is None or target_node is None:
                continue
            relation_id = (
                f"kr-{graph_revision_id}-"
                f"{self._safe_key(source_topic_key)}-supports-{self._safe_key(target_topic_key)}"
            )
            relations.append(
                KnowledgeRelationRecord(
                    knowledge_relation_id=relation_id,
                    graph_revision_id=graph_revision_id,
                    from_node_id=source_node.knowledge_node_id,
                    to_node_id=target_node.knowledge_node_id,
                    relation_type="supports",
                    directionality=str(signal.payload.get("directionality", "directed")),
                    description=str(signal.payload.get("description", signal.summary)),
                    source_signal_ids=[signal.signal_id],
                    supporting_fact_ids=[signal.assessment_fact_item_id],
                    confidence=signal.confidence,
                    status=signal.status,
                    created_by=self.created_by,
                    created_at=created_at,
                    updated_at=created_at,
                    payload={
                        "projector_version": self.projector_version,
                        "basis_type": str(signal.payload.get("basis_type", "")),
                        "basis_key": str(signal.payload.get("basis_key", "")),
                    },
                )
            )
        return relations
```

Update `_node_type`:

```python
        if "support_relation" in signal_types:
            return "evidence_topic"
```

- [ ] **Step 4: Update existing projector tests for 4-tuple return**

Replace existing unpacking:

```python
revision, nodes, pointer = KnowledgeSignalGraphProjector().project(...)
```

with:

```python
revision, nodes, relations, pointer = KnowledgeSignalGraphProjector().project(...)
```

Then assert `relations == []` in existing no-relation tests.

- [ ] **Step 5: Run graph projector tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py -q
```

Expected:

```text
All tests in tests/test_knowledge_graph_projector.py pass.
```

## Task 4: Wire Submit Side and Revision Read Model

**Files:**
- Modify: `review_gate/answer_checkpoint_writer.py`
- Modify: `review_gate/review_flow_service.py`
- Modify: `review_gate/view_dtos.py`
- Modify: `review_gate/workspace_api.py`
- Modify: `tests/test_answer_checkpoint_writer.py`
- Modify: `tests/test_workspace_api.py`
- Modify: `tests/test_http_api.py`

- [ ] **Step 1: Update submit-side writer test expectation**

In `tests/test_answer_checkpoint_writer.py`, extend the existing submit-side graph projection test with one support signal in the assessment payload:

```python
        assessment={
            "verdict": "partial",
            "score": 0.8,
            "summary": "Still mixes proposal and execution.",
            "gaps": ["api-boundary-discipline"],
            "dimensions": ["boundary_awareness"],
            "support_signals": [
                {
                    "source_label": "Boundary discipline",
                    "source_node_type": "foundation",
                    "target_label": "API boundary discipline",
                    "target_node_type": "method",
                    "basis_type": "support_basis_tag",
                    "basis_key": "boundary_awareness",
                }
            ],
        },
```

Update assertions:

```python
    result = writer.write(...)
    assert result.graph_relation_count == 1
    relations = store.list_graph_relations("gr-proj-1-stage-stage-1-20260410110000")
    assert len(relations) == 1
    assert relations[0].relation_type == "supports"
    assert relations[0].from_node_id.endswith("-boundary-discipline")
    assert relations[0].to_node_id.endswith("-api-boundary-discipline")
```

- [ ] **Step 2: Run red writer test**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_answer_checkpoint_writer.py::test_submit_answer_writes_first_checkpoint_records -q
```

Expected:

```text
AttributeError: 'CheckpointWriteResult' object has no attribute 'graph_relation_count'
```

- [ ] **Step 3: Implement writer relation persistence**

In `review_gate/answer_checkpoint_writer.py`, add `graph_relation_count` to `CheckpointWriteResult`:

```python
    graph_relation_count: int = 0
```

Pass support signals through the evaluation item payload:

```python
                "support_signals": [
                    dict(item)
                    for item in assessment.get("support_signals", [])
                    if isinstance(item, dict)
                ],
```

Update projector call:

```python
            graph_revision, graph_nodes, graph_relations, active_pointer = self._graph_projector.project(...)
            self._store.insert_graph_revision(graph_revision)
            self._store.insert_graph_nodes(graph_nodes)
            self._store.insert_graph_relations(graph_relations)
            self._store.upsert_active_graph_revision_pointer(active_pointer)
            graph_relation_count = len(graph_relations)
```

Return it:

```python
            graph_relation_count=graph_relation_count,
```

- [ ] **Step 4: Pass support signals from ReviewFlowService into writer assessment**

In `review_gate/review_flow_service.py`, update `writer_assessment`:

```python
                "support_signals": [
                    dict(item)
                    for item in assessment.get("support_signals", [])
                    if isinstance(item, dict)
                ],
```

- [ ] **Step 5: Add relation DTO and read mapping**

In `review_gate/view_dtos.py`, add `GraphRevisionRelationDTO` after `GraphRevisionNodeDTO`:

```python
@dataclass(slots=True)
class GraphRevisionRelationDTO(TransportModel):
    knowledge_relation_id: str
    graph_revision_id: str
    from_node_id: str
    to_node_id: str
    relation_type: str
    directionality: str
    description: str
    source_signal_ids: list[str] = field(default_factory=list)
    supporting_fact_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "active"
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    payload: dict[str, object] = field(default_factory=dict)
```

Update `GraphRevisionViewDTO`:

```python
    relations: list[GraphRevisionRelationDTO] = field(default_factory=list)
```

In `review_gate/workspace_api.py`, import `GraphRevisionRelationDTO` and add mapper:

```python
    def _graph_revision_relation_to_dto(self, relation) -> GraphRevisionRelationDTO:
        return GraphRevisionRelationDTO(
            knowledge_relation_id=relation.knowledge_relation_id,
            graph_revision_id=relation.graph_revision_id,
            from_node_id=relation.from_node_id,
            to_node_id=relation.to_node_id,
            relation_type=relation.relation_type,
            directionality=relation.directionality,
            description=relation.description,
            source_signal_ids=list(relation.source_signal_ids),
            supporting_fact_ids=list(relation.supporting_fact_ids),
            confidence=relation.confidence,
            status=relation.status,
            created_by=relation.created_by,
            created_at=relation.created_at,
            updated_at=relation.updated_at,
            payload=dict(relation.payload),
        )
```

Update `get_graph_revision_view`:

```python
        relations = self._checkpoint_store.list_graph_relations(revision.graph_revision_id)
        return GraphRevisionViewDTO(
            project_id=project_id,
            stage_id=stage_id,
            has_active_revision=True,
            revision=self._graph_revision_summary_to_dto(revision),
            nodes=[self._graph_revision_node_to_dto(node) for node in nodes],
            relations=[self._graph_revision_relation_to_dto(relation) for relation in relations],
        )
```

- [ ] **Step 6: Add minimal real HTTP + SQLite smoke test**

In `tests/test_http_api.py`, add this local helper class near the top of the file:

```python
class SupportRelationAssessmentClient:
    def assess(self, request: dict) -> dict:
        return {
            "request_id": request["request_id"],
            "assessment": {
                "score_total": 0.72,
                "dimension_scores": {
                    "correctness": 3,
                    "reasoning": 2,
                    "decision_awareness": 3,
                    "boundary_awareness": 2,
                    "stability": 2,
                },
                "verdict": "partial",
                "core_gaps": ["API boundary discipline"],
                "misconceptions": [],
                "support_basis_tags": [
                    {
                        "source_label": "Boundary discipline",
                        "source_node_type": "foundation",
                        "target_label": "API boundary discipline",
                        "target_node_type": "method",
                        "basis_key": "boundary_awareness",
                    }
                ],
                "evidence": ["The answer names API boundaries but does not isolate the contract."],
            },
            "recommended_action": "continue_answering",
            "recommended_follow_up_questions": ["Explain the API boundary again."],
            "learning_recommendations": ["Revisit boundary discipline."],
            "warnings": [],
            "confidence": 0.84,
        }
```

Add this test after `test_default_http_api_graph_revision_reads_submit_side_active_revision`:

```python
def test_http_api_graph_revision_reads_relation_after_real_submit_with_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "workbench.sqlite3"
    store = SQLiteStore(db_path)
    store.initialize()
    flow = ReviewFlowService(assessment_client=SupportRelationAssessmentClient(), store=store)
    client = TestClient(create_app(api=WorkspaceAPI(flow=flow, checkpoint_store=store)))

    submit_response = client.post(
        "/api/actions/submit-answer",
        json={
            "request_id": "req-real-relation-smoke",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "source_page": "question_detail",
            "actor_id": "local-user",
            "created_at": "2026-04-21T10:00:00Z",
            "question_set_id": "set-1",
            "question_id": "set-1-q-1",
            "answer_text": "The API boundary is named, but I still need to separate transport contract from storage writes.",
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
    assert graph_data["has_active_revision"] is True
    assert graph_data["revision"]["relation_count"] == 1
    assert len(graph_data["relations"]) == 1
    assert graph_data["relations"][0]["relation_type"] == "supports"
    assert graph_data["relations"][0]["directionality"] == "directed"
    assert graph_data["relations"][0]["source_signal_ids"]
    assert graph_data["relations"][0]["supporting_fact_ids"]
```

Make sure `tests/test_http_api.py` imports `SQLiteStore`:

```python
from review_gate.storage_sqlite import SQLiteStore
```

- [ ] **Step 7: Run focused submit/read tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_answer_checkpoint_writer.py::test_submit_answer_writes_first_checkpoint_records tests/test_http_api.py::test_http_api_graph_revision_reads_relation_after_real_submit_with_sqlite -q
```

Expected:

```text
2 passed
```

## Task 5: Regression and Commit

**Files:**
- Validate all files touched above.

- [ ] **Step 1: Run focused relation regression**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_assessment_synthesizer.py tests/test_knowledge_signal_projector.py tests/test_knowledge_graph_projector.py tests/test_checkpoint_storage.py tests/test_answer_checkpoint_writer.py tests/test_workspace_api.py tests/test_http_api.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run full backend tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest -q
```

Expected:

```text
All backend tests pass.
```

- [ ] **Step 3: Commit implementation**

Run:

```powershell
git add review_gate/checkpoint_models.py review_gate/storage_sqlite.py review_gate/assessment_synthesizer.py review_gate/knowledge_signal_projector.py review_gate/knowledge_graph_projector.py review_gate/answer_checkpoint_writer.py review_gate/review_flow_service.py review_gate/view_dtos.py review_gate/workspace_api.py tests/test_knowledge_graph_projector.py tests/test_checkpoint_storage.py tests/test_assessment_synthesizer.py tests/test_knowledge_signal_projector.py tests/test_answer_checkpoint_writer.py tests/test_workspace_api.py tests/test_http_api.py
git commit -m "feat: project provenance-backed graph relations"
```

Expected:

```text
[main <sha>] feat: project provenance-backed graph relations
```

## Self-Review

Spec coverage:

1. `KnowledgeRelationRecord` is covered in Task 1.
2. `graph_knowledge_relations` persistence is covered in Task 1.
3. `support_signals -> support_relation facts -> support_relation signals` is covered in Task 2.
4. Projector relation generation from explicit provenance is covered in Task 3.
5. Submit-side persistence is covered in Task 4.
6. Revision read model relation DTOs are covered in Task 4.
7. Minimal real HTTP + SQLite smoke is covered in Task 4.
8. UI, LLM, Maintenance Agent, focus cluster, and user state are excluded from implementation.

Type consistency:

1. Record name: `KnowledgeRelationRecord`.
2. DTO name: `GraphRevisionRelationDTO`.
3. Store methods: `insert_graph_relations()` and `list_graph_relations()`.
4. Relation ids use `kr-<graph_revision_id>-<source>-supports-<target>`.
5. Relation endpoint remains `/api/knowledge/graph-revision`.
