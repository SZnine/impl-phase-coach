from pathlib import Path

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
from review_gate.storage_sqlite import SQLiteStore


def test_sqlite_store_round_trips_first_checkpoint_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()

    workflow_request = WorkflowRequestRecord(
        request_id="wr-1",
        request_type="question_cycle",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="local-user",
        source="frontend_manual",
        status="pending",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    workflow_run = WorkflowRunRecord(
        run_id="run-1",
        request_id="wr-1",
        run_type="question_cycle",
        status="running",
        started_at="2026-04-09T12:00:00Z",
        payload={},
    )
    question_batch = QuestionBatchRecord(
        question_batch_id="qb-1",
        workflow_run_id="run-1",
        project_id="proj-1",
        stage_id="stage-1",
        generated_by="project_agent_adapter",
        source="review_flow_service",
        batch_goal="freeze module-interface boundary",
        entry_question_id="set-1-q-1",
        status="active",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    question_item = QuestionItemRecord(
        question_id="set-1-q-1",
        question_batch_id="qb-1",
        question_type="diagnostic",
        prompt="Explain the current-stage boundary.",
        intent="Check current-stage understanding.",
        difficulty_level="standard",
        order_index=0,
        status="pending",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    answer_batch = AnswerBatchRecord(
        answer_batch_id="ab-1",
        question_batch_id="qb-1",
        workflow_run_id="run-1",
        submitted_by="local-user",
        submission_mode="single_submit",
        completion_status="complete",
        submitted_at="2026-04-09T12:01:00Z",
        status="submitted",
        payload={},
    )
    answer_item = AnswerItemRecord(
        answer_item_id="ai-1",
        answer_batch_id="ab-1",
        question_id="set-1-q-1",
        answered_by="local-user",
        answer_text="We split state and scoring.",
        answer_format="plain_text",
        order_index=0,
        answered_at="2026-04-09T12:01:00Z",
        status="answered",
        payload={},
    )
    evaluation_batch = EvaluationBatchRecord(
        evaluation_batch_id="eb-1",
        answer_batch_id="ab-1",
        workflow_run_id="run-1",
        project_id="proj-1",
        stage_id="stage-1",
        evaluated_by="evaluator_agent",
        evaluator_version="test-v1",
        confidence=0.8,
        status="completed",
        evaluated_at="2026-04-09T12:02:00Z",
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
        evaluated_at="2026-04-09T12:02:00Z",
        payload={"diagnosed_gaps": ["proposal-execution-separation"]},
    )
    evidence_span = EvidenceSpanRecord(
        evidence_span_id="es-1",
        evaluation_item_id="ei-1",
        answer_item_id="ai-1",
        span_type="quoted_text",
        supports_dimension="causality",
        content="state and scoring",
        start_offset=14,
        end_offset=31,
        created_at="2026-04-09T12:02:00Z",
        payload={"why_it_matters": "boundary anchor"},
    )
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
        payload={"description": "still mixed"},
    )

    store.insert_workflow_request(workflow_request)
    store.insert_workflow_run(workflow_run)
    store.insert_question_batch(question_batch)
    store.insert_question_items([question_item])
    store.insert_answer_batch(answer_batch)
    store.insert_answer_items([answer_item])
    store.insert_evaluation_batch(evaluation_batch)
    store.insert_evaluation_items([evaluation_item])
    store.insert_evidence_spans([evidence_span])
    store.insert_assessment_fact_batch(fact_batch)
    store.insert_assessment_fact_items([fact_item])

    assert store.get_workflow_request("wr-1") == workflow_request
    assert store.get_workflow_run("run-1") == workflow_run
    assert store.get_question_batch("qb-1") == question_batch
    assert store.list_question_items("qb-1") == [question_item]
    assert store.get_answer_batch("ab-1") == answer_batch
    assert store.list_answer_items("ab-1") == [answer_item]
    assert store.get_evaluation_batch("eb-1") == evaluation_batch
    assert store.list_evaluation_items("eb-1") == [evaluation_item]
    assert store.list_evidence_spans("ei-1") == [evidence_span]
    assert store.get_latest_assessment_fact_batch("proj-1", "stage-1") == fact_batch
    assert store.list_assessment_fact_items("afb-1") == [fact_item]
