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
