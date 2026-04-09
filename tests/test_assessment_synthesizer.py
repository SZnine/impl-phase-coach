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
