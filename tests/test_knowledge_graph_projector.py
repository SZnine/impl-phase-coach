from review_gate.checkpoint_models import (
    ActiveGraphRevisionPointerRecord,
    GraphRevisionRecord,
    KnowledgeNodeRecord,
    KnowledgeRelationRecord,
    KnowledgeSignalRecord,
)
from review_gate.knowledge_graph_projector import KnowledgeSignalGraphProjector


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

    revision, nodes, relations, pointer = KnowledgeSignalGraphProjector().project(
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
    assert relations == []
    assert nodes[0].topic_key == "proposal-execution-separation"
    assert nodes[0].label == "proposal execution separation"
    assert nodes[0].node_type == "weakness_topic"
    assert nodes[0].source_signal_ids == ["ks-1", "ks-2"]
    assert nodes[0].supporting_fact_ids == ["afi-1", "afi-2"]
    assert nodes[0].confidence == 0.8
    assert pointer.active_graph_revision_id == revision.graph_revision_id


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

    revision, nodes, relations, pointer = KnowledgeSignalGraphProjector().project(
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        signals=signals,
        created_at="2026-04-09T12:04:00Z",
    )

    assert revision.node_count == 2
    assert revision.relation_count == 0
    assert pointer.active_graph_revision_id == revision.graph_revision_id
    assert relations == []
    assert [node.topic_key for node in nodes] == ["state-boundary", "test-discipline"]
    assert [node.node_type for node in nodes] == ["weakness_topic", "strength_topic"]


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
    assert revision.revision_summary == "2 signals projected into 2 nodes and 1 relations"
    assert [node.topic_key for node in nodes] == ["api-boundary-discipline", "boundary-discipline"]
    assert len(relations) == 1
    assert relations[0].relation_type == "supports"
    assert relations[0].directionality == "directed"
    assert relations[0].from_node_id.endswith("-boundary-discipline")
    assert relations[0].to_node_id.endswith("-api-boundary-discipline")
    assert relations[0].source_signal_ids == ["ks-support"]
    assert relations[0].supporting_fact_ids == ["afi-support"]
    assert pointer.active_graph_revision_id == revision.graph_revision_id
