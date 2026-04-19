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
