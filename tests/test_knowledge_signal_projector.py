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
