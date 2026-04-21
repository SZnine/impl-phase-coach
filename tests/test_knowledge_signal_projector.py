from review_gate.checkpoint_models import (
    AssessmentFactBatchRecord,
    AssessmentFactItemRecord,
    KnowledgeSignalRecord,
)
from review_gate.knowledge_signal_projector import AssessmentFactSignalProjector


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
