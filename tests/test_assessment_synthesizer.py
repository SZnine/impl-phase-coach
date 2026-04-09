from review_gate.assessment_synthesizer import AssessmentSynthesizer
from review_gate.checkpoint_models import (
    AnswerBatchRecord,
    AnswerItemRecord,
    AssessmentFactBatchRecord,
    AssessmentFactItemRecord,
    EvaluationBatchRecord,
    EvaluationItemRecord,
    EvidenceSpanRecord,
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
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


def test_checkpoint_records_round_trip_json() -> None:
    records = [
        WorkflowRequestRecord(
            request_id="wr-1",
            request_type="assessment",
            project_id="proj-1",
            stage_id="stage-1",
            requested_by="agent-1",
            source="api",
            status="open",
            created_at="2026-04-09T12:00:00Z",
            payload={"priority": "normal"},
        ),
        WorkflowRunRecord(
            run_id="run-1",
            request_id="wr-1",
            run_type="assessment",
            status="running",
            started_at="2026-04-09T12:00:00Z",
            finished_at=None,
            supersedes_run_id=None,
            payload={"step": 1},
        ),
        QuestionBatchRecord(
            question_batch_id="qb-1",
            workflow_run_id="run-1",
            project_id="proj-1",
            stage_id="stage-1",
            generated_by="generator",
            source="review_gate",
            batch_goal="identify gaps",
            entry_question_id="q-1",
            status="active",
            created_at="2026-04-09T12:00:00Z",
            payload={"item_count": 1},
        ),
        QuestionItemRecord(
            question_id="q-1",
            question_batch_id="qb-1",
            question_type="gap_probe",
            prompt="What is missing?",
            intent="diagnose",
            difficulty_level="medium",
            order_index=0,
            status="active",
            created_at="2026-04-09T12:00:00Z",
            payload={"dimension_refs": ["causality"]},
        ),
        AnswerBatchRecord(
            answer_batch_id="ab-1",
            question_batch_id="qb-1",
            workflow_run_id="run-1",
            submitted_by="agent-2",
            submission_mode="manual",
            completion_status="complete",
            submitted_at="2026-04-09T12:00:00Z",
            status="completed",
            payload={"answer_count": 1},
        ),
        AnswerItemRecord(
            answer_item_id="ai-1",
            answer_batch_id="ab-1",
            question_id="q-1",
            answered_by="agent-2",
            answer_text="It is not executed yet.",
            answer_format="text",
            order_index=0,
            answered_at="2026-04-09T12:00:00Z",
            status="completed",
            revision_of_answer_item_id=None,
            payload={"confidence_basis": "direct"},
        ),
        EvaluationBatchRecord(
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
        ),
        EvaluationItemRecord(
            evaluation_item_id="ei-1",
            evaluation_batch_id="eb-1",
            question_id="q-1",
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
        ),
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
        ),
        AssessmentFactBatchRecord(
            assessment_fact_batch_id="afb-1",
            evaluation_batch_id="eb-1",
            workflow_run_id="run-1",
            synthesized_by="assessment_synthesizer",
            synthesizer_version="first-checkpoint-v1",
            status="completed",
            synthesized_at="2026-04-09T12:00:00Z",
            supersedes_assessment_fact_batch_id=None,
            payload={"item_count": 1},
        ),
        AssessmentFactItemRecord(
            assessment_fact_item_id="afi-1",
            assessment_fact_batch_id="afb-1",
            source_evaluation_item_id="ei-1",
            fact_type="gap",
            topic_key="proposal-execution-separation",
            title="proposal execution separation",
            confidence=0.8,
            status="active",
            created_at="2026-04-09T12:00:00Z",
            supersedes_assessment_fact_item_id=None,
            payload={"description": "Answer still mixes proposal status with execution status."},
        ),
    ]

    for record in records:
        restored = type(record).from_json(record.to_json())
        assert restored == record
