# Knowledge Signal To Graph Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Do not use background/subagents while the current user directive is active. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build GraphProjection v1 by projecting persisted `KnowledgeSignalRecord` objects into a revision-scoped node graph with an active revision pointer.

**Architecture:** Add graph checkpoint records, SQLite persistence, and a deterministic `KnowledgeSignalGraphProjector`. This batch creates `GraphRevisionRecord`, `KnowledgeNodeRecord`, and `ActiveGraphRevisionPointerRecord`; it does not create relations, does not call LLM, does not touch `ProfileSpaceService`, and does not write legacy graph tables.

**Tech Stack:** Python dataclasses, existing `JsonSerializable`, SQLite through `review_gate/storage_sqlite.py`, pytest.

---

## File Structure

- Modify: `review_gate/checkpoint_models.py`
  - Add `GraphRevisionRecord`, `KnowledgeNodeRecord`, and `ActiveGraphRevisionPointerRecord`.
- Modify: `review_gate/storage_sqlite.py`
  - Add `graph_revisions`, `graph_knowledge_nodes`, and `active_graph_revision_pointers` tables plus store methods.
- Create: `review_gate/knowledge_graph_projector.py`
  - Add deterministic `KnowledgeSignalGraphProjector`.
- Create: `tests/test_knowledge_graph_projector.py`
  - Cover record round-trips, single-topic aggregation, and multi-topic aggregation.
- Modify: `tests/test_checkpoint_storage.py`
  - Cover graph projection persistence and active pointer replacement.
- Modify: `docs/superpowers/plans/2026-04-19-knowledge-signal-to-graph-revision-implementation.md`
  - Check off steps as they are completed.

---

### Task 1: Add Graph Projection Records

**Files:**
- Modify: `review_gate/checkpoint_models.py`
- Create: `tests/test_knowledge_graph_projector.py`

- [ ] **Step 1: Write failing record round-trip tests**

Create `tests/test_knowledge_graph_projector.py`:

```python
from review_gate.checkpoint_models import (
    ActiveGraphRevisionPointerRecord,
    GraphRevisionRecord,
    KnowledgeNodeRecord,
)


def test_graph_revision_record_round_trips_json_payload() -> None:
    revision = GraphRevisionRecord(
        graph_revision_id="gr-proj-1-stage-1-20260409120300",
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        revision_type="deterministic_signal_projection",
        based_on_revision_id=None,
        source_fact_batch_ids=["afb-1"],
        source_signal_ids=["ks-1", "ks-2"],
        status="active",
        revision_summary="2 signals projected into 1 node",
        node_count=1,
        relation_count=0,
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-09T12:04:00Z",
        activated_at="2026-04-09T12:04:00Z",
        payload={"projector_version": "signal-graph-v1"},
    )

    assert GraphRevisionRecord.from_json(revision.to_json()) == revision


def test_knowledge_node_record_round_trips_json_payload() -> None:
    node = KnowledgeNodeRecord(
        knowledge_node_id="kn-gr-1-proposal-execution-separation",
        graph_revision_id="gr-1",
        topic_key="proposal-execution-separation",
        label="proposal execution separation",
        node_type="weakness_topic",
        description="Answer still mixes proposal status with execution status.",
        source_signal_ids=["ks-1"],
        supporting_fact_ids=["afi-1"],
        confidence=0.8,
        status="active",
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-09T12:04:00Z",
        updated_at="2026-04-09T12:04:00Z",
        payload={"signal_types": ["weakness"]},
    )

    assert KnowledgeNodeRecord.from_json(node.to_json()) == node


def test_active_graph_revision_pointer_record_round_trips_json_payload() -> None:
    pointer = ActiveGraphRevisionPointerRecord(
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        active_graph_revision_id="gr-1",
        updated_at="2026-04-09T12:04:00Z",
        updated_by="knowledge_signal_graph_projector",
        payload={"reason": "deterministic projection completed"},
    )

    assert ActiveGraphRevisionPointerRecord.from_json(pointer.to_json()) == pointer
```

- [ ] **Step 2: Run record tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py -q
```

Expected: FAIL because the three graph records do not exist.

- [ ] **Step 3: Add graph records**

Append these dataclasses after `KnowledgeSignalRecord` in `review_gate/checkpoint_models.py`:

```python
@dataclass(slots=True)
class GraphRevisionRecord(JsonSerializable):
    graph_revision_id: str
    project_id: str
    scope_type: str
    scope_ref: str
    revision_type: str
    based_on_revision_id: str | None
    source_fact_batch_ids: list[str]
    source_signal_ids: list[str]
    status: str
    revision_summary: str
    node_count: int
    relation_count: int
    created_by: str
    created_at: str
    activated_at: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            graph_revision_id=_coerce_str(payload["graph_revision_id"]),
            project_id=_coerce_str(payload.get("project_id"), ""),
            scope_type=_coerce_str(payload.get("scope_type"), ""),
            scope_ref=_coerce_str(payload.get("scope_ref"), ""),
            revision_type=_coerce_str(payload.get("revision_type"), ""),
            based_on_revision_id=_coerce_optional_str(payload.get("based_on_revision_id")),
            source_fact_batch_ids=_coerce_str_list(payload.get("source_fact_batch_ids")),
            source_signal_ids=_coerce_str_list(payload.get("source_signal_ids")),
            status=_coerce_str(payload.get("status"), ""),
            revision_summary=_coerce_str(payload.get("revision_summary"), ""),
            node_count=_coerce_int(payload.get("node_count"), 0),
            relation_count=_coerce_int(payload.get("relation_count"), 0),
            created_by=_coerce_str(payload.get("created_by"), ""),
            created_at=_coerce_str(payload.get("created_at"), ""),
            activated_at=_coerce_optional_str(payload.get("activated_at")),
            payload=_coerce_payload_dict(payload.get("payload")),
        )


@dataclass(slots=True)
class KnowledgeNodeRecord(JsonSerializable):
    knowledge_node_id: str
    graph_revision_id: str
    topic_key: str
    label: str
    node_type: str
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
            knowledge_node_id=_coerce_str(payload["knowledge_node_id"]),
            graph_revision_id=_coerce_str(payload.get("graph_revision_id"), ""),
            topic_key=_coerce_str(payload.get("topic_key"), ""),
            label=_coerce_str(payload.get("label"), ""),
            node_type=_coerce_str(payload.get("node_type"), ""),
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


@dataclass(slots=True)
class ActiveGraphRevisionPointerRecord(JsonSerializable):
    project_id: str
    scope_type: str
    scope_ref: str
    active_graph_revision_id: str
    updated_at: str
    updated_by: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        return cls(
            project_id=_coerce_str(payload["project_id"]),
            scope_type=_coerce_str(payload.get("scope_type"), ""),
            scope_ref=_coerce_str(payload.get("scope_ref"), ""),
            active_graph_revision_id=_coerce_str(payload.get("active_graph_revision_id"), ""),
            updated_at=_coerce_str(payload.get("updated_at"), ""),
            updated_by=_coerce_str(payload.get("updated_by"), ""),
            payload=_coerce_payload_dict(payload.get("payload")),
        )
```

- [ ] **Step 4: Run record tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add review_gate/checkpoint_models.py tests/test_knowledge_graph_projector.py
git commit -m "feat: add graph projection checkpoint records"
```

---

### Task 2: Persist Graph Revisions, Nodes, And Active Pointer

**Files:**
- Modify: `review_gate/storage_sqlite.py`
- Modify: `tests/test_checkpoint_storage.py`

- [ ] **Step 1: Write failing graph storage test**

Add these imports to the checkpoint model import list in `tests/test_checkpoint_storage.py`:

```python
    ActiveGraphRevisionPointerRecord,
    GraphRevisionRecord,
    KnowledgeNodeRecord,
```

Append this test:

```python
def test_checkpoint_storage_round_trips_graph_projection_records(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "checkpoint.db")
    store.initialize()

    revision = GraphRevisionRecord(
        graph_revision_id="gr-proj-1-stage-1-20260409120400",
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        revision_type="deterministic_signal_projection",
        based_on_revision_id=None,
        source_fact_batch_ids=["afb-1"],
        source_signal_ids=["ks-1"],
        status="active",
        revision_summary="1 signal projected into 1 node",
        node_count=1,
        relation_count=0,
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-09T12:04:00Z",
        activated_at="2026-04-09T12:04:00Z",
        payload={"projector_version": "signal-graph-v1"},
    )
    node = KnowledgeNodeRecord(
        knowledge_node_id="kn-gr-proj-1-stage-1-20260409120400-proposal-execution-separation",
        graph_revision_id="gr-proj-1-stage-1-20260409120400",
        topic_key="proposal-execution-separation",
        label="proposal execution separation",
        node_type="weakness_topic",
        description="Answer still mixes proposal status with execution status.",
        source_signal_ids=["ks-1"],
        supporting_fact_ids=["afi-1"],
        confidence=0.8,
        status="active",
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-09T12:04:00Z",
        updated_at="2026-04-09T12:04:00Z",
        payload={"signal_types": ["weakness"]},
    )
    pointer = ActiveGraphRevisionPointerRecord(
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        active_graph_revision_id="gr-proj-1-stage-1-20260409120400",
        updated_at="2026-04-09T12:04:00Z",
        updated_by="knowledge_signal_graph_projector",
        payload={"reason": "deterministic projection completed"},
    )

    store.insert_graph_revision(revision)
    store.insert_graph_nodes([node])
    store.upsert_active_graph_revision_pointer(pointer)

    assert store.get_graph_revision("gr-proj-1-stage-1-20260409120400") == revision
    assert store.list_graph_nodes("gr-proj-1-stage-1-20260409120400") == [node]
    assert store.get_active_graph_revision_pointer("proj-1", "stage", "stage-1") == pointer
```

- [ ] **Step 2: Run graph storage test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_checkpoint_storage.py::test_checkpoint_storage_round_trips_graph_projection_records -q
```

Expected: FAIL because `SQLiteStore` has no graph revision methods.

- [ ] **Step 3: Add imports and schema**

In `review_gate/storage_sqlite.py`, add these records to the `review_gate.checkpoint_models` import list:

```python
    ActiveGraphRevisionPointerRecord,
    GraphRevisionRecord,
    KnowledgeNodeRecord,
```

Add these tables in `initialize()` after `knowledge_signals` indexes:

```sql
CREATE TABLE IF NOT EXISTS graph_revisions (
    graph_revision_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    scope_type TEXT NOT NULL,
    scope_ref TEXT NOT NULL,
    revision_type TEXT NOT NULL,
    based_on_revision_id TEXT,
    status TEXT NOT NULL,
    node_count INTEGER NOT NULL,
    relation_count INTEGER NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    activated_at TEXT,
    payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_graph_revisions_project_scope
    ON graph_revisions(project_id, scope_type, scope_ref);

CREATE TABLE IF NOT EXISTS graph_knowledge_nodes (
    knowledge_node_id TEXT PRIMARY KEY,
    graph_revision_id TEXT NOT NULL,
    topic_key TEXT NOT NULL,
    node_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    FOREIGN KEY (graph_revision_id) REFERENCES graph_revisions(graph_revision_id)
);

CREATE INDEX IF NOT EXISTS idx_graph_knowledge_nodes_revision
    ON graph_knowledge_nodes(graph_revision_id);

CREATE INDEX IF NOT EXISTS idx_graph_knowledge_nodes_topic
    ON graph_knowledge_nodes(topic_key);

CREATE TABLE IF NOT EXISTS active_graph_revision_pointers (
    project_id TEXT NOT NULL,
    scope_type TEXT NOT NULL,
    scope_ref TEXT NOT NULL,
    active_graph_revision_id TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (project_id, scope_type, scope_ref),
    FOREIGN KEY (active_graph_revision_id) REFERENCES graph_revisions(graph_revision_id)
);
```

- [ ] **Step 4: Add storage methods**

Add these methods near the existing knowledge signal storage methods:

```python
    def insert_graph_revision(self, record: GraphRevisionRecord) -> None:
        self._insert_json_record(
            table_name="graph_revisions",
            pk_column="graph_revision_id",
            pk_value=record.graph_revision_id,
            record=record,
            columns={
                "project_id": record.project_id,
                "scope_type": record.scope_type,
                "scope_ref": record.scope_ref,
                "revision_type": record.revision_type,
                "based_on_revision_id": record.based_on_revision_id,
                "status": record.status,
                "node_count": record.node_count,
                "relation_count": record.relation_count,
                "created_by": record.created_by,
                "created_at": record.created_at,
                "activated_at": record.activated_at,
            },
        )

    def get_graph_revision(self, graph_revision_id: str) -> GraphRevisionRecord | None:
        row = self._fetch_one(
            "SELECT payload FROM graph_revisions WHERE graph_revision_id = ?",
            (graph_revision_id,),
        )
        if row is None:
            return None
        return GraphRevisionRecord.from_json(row["payload"])

    def insert_graph_nodes(self, records: list[KnowledgeNodeRecord]) -> None:
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO graph_knowledge_nodes (
                        knowledge_node_id,
                        graph_revision_id,
                        topic_key,
                        node_type,
                        confidence,
                        status,
                        created_at,
                        updated_at,
                        payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.knowledge_node_id,
                        record.graph_revision_id,
                        record.topic_key,
                        record.node_type,
                        record.confidence,
                        record.status,
                        record.created_at,
                        record.updated_at,
                        record.to_json(),
                    ),
                )

    def list_graph_nodes(self, graph_revision_id: str) -> list[KnowledgeNodeRecord]:
        rows = self._fetch_all(
            """
            SELECT payload
            FROM graph_knowledge_nodes
            WHERE graph_revision_id = ?
            ORDER BY topic_key, knowledge_node_id
            """,
            (graph_revision_id,),
        )
        return [KnowledgeNodeRecord.from_json(row["payload"]) for row in rows]

    def upsert_active_graph_revision_pointer(self, record: ActiveGraphRevisionPointerRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO active_graph_revision_pointers (
                    project_id,
                    scope_type,
                    scope_ref,
                    active_graph_revision_id,
                    updated_at,
                    updated_by,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.project_id,
                    record.scope_type,
                    record.scope_ref,
                    record.active_graph_revision_id,
                    record.updated_at,
                    record.updated_by,
                    record.to_json(),
                ),
            )

    def get_active_graph_revision_pointer(
        self,
        project_id: str,
        scope_type: str,
        scope_ref: str,
    ) -> ActiveGraphRevisionPointerRecord | None:
        row = self._fetch_one(
            """
            SELECT payload
            FROM active_graph_revision_pointers
            WHERE project_id = ? AND scope_type = ? AND scope_ref = ?
            """,
            (project_id, scope_type, scope_ref),
        )
        if row is None:
            return None
        return ActiveGraphRevisionPointerRecord.from_json(row["payload"])
```

- [ ] **Step 5: Run graph storage test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_checkpoint_storage.py::test_checkpoint_storage_round_trips_graph_projection_records -q
```

Expected: PASS.

- [ ] **Step 6: Add active pointer replacement test**

Append this test:

```python
def test_active_graph_revision_pointer_replaces_previous_revision(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "checkpoint.db")
    store.initialize()
    first_revision = GraphRevisionRecord(
        graph_revision_id="gr-1",
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        revision_type="deterministic_signal_projection",
        based_on_revision_id=None,
        source_fact_batch_ids=["afb-1"],
        source_signal_ids=["ks-1"],
        status="active",
        revision_summary="first",
        node_count=1,
        relation_count=0,
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-09T12:04:00Z",
        activated_at="2026-04-09T12:04:00Z",
        payload={},
    )
    second_revision = GraphRevisionRecord(
        graph_revision_id="gr-2",
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        revision_type="deterministic_signal_projection",
        based_on_revision_id="gr-1",
        source_fact_batch_ids=["afb-2"],
        source_signal_ids=["ks-2"],
        status="active",
        revision_summary="second",
        node_count=1,
        relation_count=0,
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-09T12:05:00Z",
        activated_at="2026-04-09T12:05:00Z",
        payload={},
    )
    store.insert_graph_revision(first_revision)
    store.insert_graph_revision(second_revision)
    store.upsert_active_graph_revision_pointer(
        ActiveGraphRevisionPointerRecord(
            project_id="proj-1",
            scope_type="stage",
            scope_ref="stage-1",
            active_graph_revision_id="gr-1",
            updated_at="2026-04-09T12:04:00Z",
            updated_by="knowledge_signal_graph_projector",
            payload={},
        )
    )
    replacement = ActiveGraphRevisionPointerRecord(
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        active_graph_revision_id="gr-2",
        updated_at="2026-04-09T12:05:00Z",
        updated_by="knowledge_signal_graph_projector",
        payload={"reason": "new projection"},
    )

    store.upsert_active_graph_revision_pointer(replacement)

    assert store.get_active_graph_revision_pointer("proj-1", "stage", "stage-1") == replacement
```

- [ ] **Step 7: Run storage tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_checkpoint_storage.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit Task 2**

Run:

```powershell
git add review_gate/storage_sqlite.py tests/test_checkpoint_storage.py
git commit -m "feat: persist graph projection records"
```

---

### Task 3: Add KnowledgeSignalGraphProjector

**Files:**
- Create: `review_gate/knowledge_graph_projector.py`
- Modify: `tests/test_knowledge_graph_projector.py`

- [ ] **Step 1: Add failing single-topic projection test**

Append this test:

```python
from review_gate.checkpoint_models import KnowledgeSignalRecord
from review_gate.knowledge_graph_projector import KnowledgeSignalGraphProjector


def test_graph_projector_groups_same_topic_signals_into_one_node() -> None:
    signals = [
        KnowledgeSignalRecord(
            signal_id="ks-1",
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
            payload={"description": "Answer still mixes proposal status with execution status."},
        ),
        KnowledgeSignalRecord(
            signal_id="ks-2",
            assessment_fact_batch_id="afb-1",
            assessment_fact_item_id="afi-2",
            source_evaluation_item_id="ei-2",
            signal_type="weakness",
            topic_key="proposal-execution-separation",
            polarity="negative",
            summary="proposal/execution boundary",
            confidence=0.6,
            status="active",
            projector_version="fact-signal-v1",
            created_at="2026-04-09T12:03:30Z",
            payload={"description": "Needs a clearer boundary."},
        ),
    ]

    revision, nodes, pointer = KnowledgeSignalGraphProjector().project(
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        signals=signals,
        created_at="2026-04-09T12:04:00Z",
    )

    assert revision.graph_revision_id == "gr-proj-1-stage-stage-1-20260409120400"
    assert revision.node_count == 1
    assert revision.relation_count == 0
    assert revision.source_fact_batch_ids == ["afb-1"]
    assert revision.source_signal_ids == ["ks-1", "ks-2"]
    assert len(nodes) == 1
    assert nodes[0].topic_key == "proposal-execution-separation"
    assert nodes[0].label == "proposal execution separation"
    assert nodes[0].node_type == "weakness_topic"
    assert nodes[0].source_signal_ids == ["ks-1", "ks-2"]
    assert nodes[0].supporting_fact_ids == ["afi-1", "afi-2"]
    assert nodes[0].confidence == 0.8
    assert pointer.active_graph_revision_id == revision.graph_revision_id
```

- [ ] **Step 2: Run single-topic test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py::test_graph_projector_groups_same_topic_signals_into_one_node -q
```

Expected: FAIL because `review_gate.knowledge_graph_projector` does not exist.

- [ ] **Step 3: Implement the projector**

Create `review_gate/knowledge_graph_projector.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass

from review_gate.checkpoint_models import (
    ActiveGraphRevisionPointerRecord,
    GraphRevisionRecord,
    KnowledgeNodeRecord,
    KnowledgeSignalRecord,
)


@dataclass(slots=True)
class KnowledgeSignalGraphProjector:
    projector_version: str = "signal-graph-v1"
    created_by: str = "knowledge_signal_graph_projector"

    def project(
        self,
        *,
        project_id: str,
        scope_type: str,
        scope_ref: str,
        signals: list[KnowledgeSignalRecord],
        created_at: str,
        based_on_revision_id: str | None = None,
    ) -> tuple[GraphRevisionRecord, list[KnowledgeNodeRecord], ActiveGraphRevisionPointerRecord]:
        graph_revision_id = self._revision_id(
            project_id=project_id,
            scope_type=scope_type,
            scope_ref=scope_ref,
            created_at=created_at,
        )
        nodes = self._project_nodes(
            graph_revision_id=graph_revision_id,
            signals=signals,
            created_at=created_at,
        )
        source_signal_ids = sorted({signal.signal_id for signal in signals})
        source_fact_batch_ids = sorted({signal.assessment_fact_batch_id for signal in signals})
        revision = GraphRevisionRecord(
            graph_revision_id=graph_revision_id,
            project_id=project_id,
            scope_type=scope_type,
            scope_ref=scope_ref,
            revision_type="deterministic_signal_projection",
            based_on_revision_id=based_on_revision_id,
            source_fact_batch_ids=source_fact_batch_ids,
            source_signal_ids=source_signal_ids,
            status="active",
            revision_summary=f"{len(source_signal_ids)} signals projected into {len(nodes)} nodes",
            node_count=len(nodes),
            relation_count=0,
            created_by=self.created_by,
            created_at=created_at,
            activated_at=created_at,
            payload={"projector_version": self.projector_version},
        )
        pointer = ActiveGraphRevisionPointerRecord(
            project_id=project_id,
            scope_type=scope_type,
            scope_ref=scope_ref,
            active_graph_revision_id=graph_revision_id,
            updated_at=created_at,
            updated_by=self.created_by,
            payload={"projector_version": self.projector_version},
        )
        return revision, nodes, pointer

    def _project_nodes(
        self,
        *,
        graph_revision_id: str,
        signals: list[KnowledgeSignalRecord],
        created_at: str,
    ) -> list[KnowledgeNodeRecord]:
        grouped: dict[str, list[KnowledgeSignalRecord]] = {}
        for signal in signals:
            grouped.setdefault(signal.topic_key or "untagged", []).append(signal)

        nodes: list[KnowledgeNodeRecord] = []
        for topic_key in sorted(grouped):
            group = sorted(grouped[topic_key], key=lambda item: (-item.confidence, item.signal_id))
            primary = group[0]
            signal_types = sorted({signal.signal_type for signal in group})
            nodes.append(
                KnowledgeNodeRecord(
                    knowledge_node_id=f"kn-{graph_revision_id}-{self._safe_key(topic_key)}",
                    graph_revision_id=graph_revision_id,
                    topic_key=topic_key,
                    label=primary.summary or topic_key,
                    node_type=self._node_type(signal_types),
                    description=str(primary.payload.get("description", "")),
                    source_signal_ids=sorted({signal.signal_id for signal in group}),
                    supporting_fact_ids=sorted({signal.assessment_fact_item_id for signal in group}),
                    confidence=primary.confidence,
                    status="active",
                    created_by=self.created_by,
                    created_at=created_at,
                    updated_at=created_at,
                    payload={
                        "projector_version": self.projector_version,
                        "signal_types": signal_types,
                        "polarity_counts": self._polarity_counts(group),
                    },
                )
            )
        return nodes

    def _node_type(self, signal_types: list[str]) -> str:
        if "weakness" in signal_types:
            return "weakness_topic"
        if signal_types == ["strength"]:
            return "strength_topic"
        return "evidence_topic"

    def _polarity_counts(self, signals: list[KnowledgeSignalRecord]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for signal in signals:
            counts[signal.polarity] = counts.get(signal.polarity, 0) + 1
        return counts

    def _revision_id(self, *, project_id: str, scope_type: str, scope_ref: str, created_at: str) -> str:
        timestamp = re.sub(r"[^0-9]", "", created_at)[:14]
        return f"gr-{self._safe_key(project_id)}-{self._safe_key(scope_type)}-{self._safe_key(scope_ref)}-{timestamp}"

    def _safe_key(self, value: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
        return safe or "untagged"
```

- [ ] **Step 4: Run single-topic test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py::test_graph_projector_groups_same_topic_signals_into_one_node -q
```

Expected: PASS.

- [ ] **Step 5: Add multi-topic projection test**

Append this test:

```python
def test_graph_projector_creates_one_node_per_topic() -> None:
    signals = [
        KnowledgeSignalRecord(
            signal_id="ks-gap",
            assessment_fact_batch_id="afb-1",
            assessment_fact_item_id="afi-gap",
            source_evaluation_item_id="ei-1",
            signal_type="weakness",
            topic_key="state-boundary",
            polarity="negative",
            summary="state boundary",
            confidence=0.7,
            status="active",
            projector_version="fact-signal-v1",
            created_at="2026-04-09T12:03:00Z",
            payload={"description": "state boundary is unclear"},
        ),
        KnowledgeSignalRecord(
            signal_id="ks-strength",
            assessment_fact_batch_id="afb-1",
            assessment_fact_item_id="afi-strength",
            source_evaluation_item_id="ei-2",
            signal_type="strength",
            topic_key="test-discipline",
            polarity="positive",
            summary="test discipline",
            confidence=0.9,
            status="active",
            projector_version="fact-signal-v1",
            created_at="2026-04-09T12:03:30Z",
            payload={"description": "tests are concrete"},
        ),
    ]

    revision, nodes, pointer = KnowledgeSignalGraphProjector().project(
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        signals=signals,
        created_at="2026-04-09T12:04:00Z",
    )

    assert revision.node_count == 2
    assert revision.relation_count == 0
    assert pointer.active_graph_revision_id == revision.graph_revision_id
    assert [node.topic_key for node in nodes] == ["state-boundary", "test-discipline"]
    assert [node.node_type for node in nodes] == ["weakness_topic", "strength_topic"]
```

- [ ] **Step 6: Run projector tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

Run:

```powershell
git add review_gate/knowledge_graph_projector.py tests/test_knowledge_graph_projector.py
git commit -m "feat: project knowledge signals into graph revisions"
```

---

### Task 4: Guard Graph Projection Boundaries

**Files:**
- Modify: `tests/test_checkpoint_storage.py`
- Modify: `docs/superpowers/plans/2026-04-19-knowledge-signal-to-graph-revision-implementation.md`

- [ ] **Step 1: Add legacy graph isolation test**

Append this test:

```python
def test_graph_projection_records_do_not_write_legacy_graph_tables(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "checkpoint.db")
    store.initialize()
    revision = GraphRevisionRecord(
        graph_revision_id="gr-1",
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        revision_type="deterministic_signal_projection",
        based_on_revision_id=None,
        source_fact_batch_ids=["afb-1"],
        source_signal_ids=["ks-1"],
        status="active",
        revision_summary="1 signal projected into 1 node",
        node_count=1,
        relation_count=0,
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-09T12:04:00Z",
        activated_at="2026-04-09T12:04:00Z",
        payload={},
    )
    node = KnowledgeNodeRecord(
        knowledge_node_id="kn-gr-1-state-boundary",
        graph_revision_id="gr-1",
        topic_key="state-boundary",
        label="state boundary",
        node_type="weakness_topic",
        description="state boundary is unclear",
        source_signal_ids=["ks-1"],
        supporting_fact_ids=["afi-1"],
        confidence=0.7,
        status="active",
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-09T12:04:00Z",
        updated_at="2026-04-09T12:04:00Z",
        payload={},
    )

    store.insert_graph_revision(revision)
    store.insert_graph_nodes([node])

    assert store.list_knowledge_nodes() == []
    assert store.list_knowledge_relations() == []
```

- [ ] **Step 2: Run legacy graph isolation test**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_checkpoint_storage.py::test_graph_projection_records_do_not_write_legacy_graph_tables -q
```

Expected: PASS.

- [ ] **Step 3: Run focused graph projection tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py tests/test_checkpoint_storage.py::test_checkpoint_storage_round_trips_graph_projection_records tests/test_checkpoint_storage.py::test_active_graph_revision_pointer_replaces_previous_revision tests/test_checkpoint_storage.py::test_graph_projection_records_do_not_write_legacy_graph_tables -q
```

Expected: PASS.

- [ ] **Step 4: Run related regression tests**

Run:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_signal_projector.py tests/test_checkpoint_storage.py tests/test_assessment_synthesizer.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

Run:

```powershell
git add tests/test_checkpoint_storage.py docs/superpowers/plans/2026-04-19-knowledge-signal-to-graph-revision-implementation.md
git commit -m "test: guard graph projection storage boundaries"
```

---

## Final Verification

- [ ] Run focused tests:

```powershell
$env:PYTHONPATH='.'; pytest tests/test_knowledge_graph_projector.py tests/test_knowledge_signal_projector.py tests/test_checkpoint_storage.py tests/test_assessment_synthesizer.py -q
```

Expected: PASS.

- [ ] Check changed files:

```powershell
git status --short --branch
```

Expected: only intentional tracked changes remain, plus pre-existing untracked `.env/`, `eval-live-smoke-*`, and `tmp_review_check*` directories if they still exist.

- [ ] Push if the implementation commits are complete:

```powershell
git push
```

Expected: branch updates successfully.

---

## Self-Review

Spec coverage:

1. `GraphRevisionRecord` is covered by Task 1 and Task 2.
2. `KnowledgeNodeRecord` is covered by Task 1, Task 2, and Task 3.
3. `ActiveGraphRevisionPointerRecord` is covered by Task 1 and Task 2.
4. Deterministic `KnowledgeSignalRecord -> GraphRevisionRecord + KnowledgeNodeRecord[] + ActiveGraphRevisionPointerRecord` projection is covered by Task 3.
5. Legacy graph store isolation is covered by Task 4.
6. `KnowledgeRelationRecord`, API/UI read integration, Maintenance Agent, LLM calls, user node state, focus clusters, and graph rewrite history are intentionally excluded.

Type consistency:

1. `GraphRevisionRecord.source_signal_ids` and `KnowledgeNodeRecord.source_signal_ids` use `list[str]` and `_coerce_str_list`.
2. Storage methods read records back from each row's JSON payload, matching existing checkpoint storage style.
3. The projector returns records but does not persist them.
4. Method names avoid colliding with legacy graph APIs: new revision nodes use `insert_graph_nodes` / `list_graph_nodes`, while old profile graph still uses `upsert_knowledge_node` / `list_knowledge_nodes`.

Implementation boundary:

1. Do not modify `ProfileSpaceService`.
2. Do not write to `knowledge_map_node_store` or `knowledge_relation_store`.
3. Do not add `KnowledgeRelationRecord` in this batch.
4. Do not add HTTP/UI read surface in this batch.
5. Do not call LLM from graph projection.
