from pathlib import Path

from review_gate.checkpoint_models import (
    ActiveGraphRevisionPointerRecord,
    AnswerBatchRecord,
    AnswerItemRecord,
    AssessmentFactBatchRecord,
    AssessmentFactItemRecord,
    EvaluationBatchRecord,
    EvaluationItemRecord,
    EvidenceSpanRecord,
    GraphRevisionRecord,
    KnowledgeNodeRecord,
    KnowledgeRelationRecord,
    KnowledgeSignalRecord,
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


def test_checkpoint_storage_round_trips_knowledge_signals(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "checkpoint.db")
    store.initialize()
    _seed_minimal_assessment_fact(store)

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

    store.insert_knowledge_signals([signal])

    assert store.list_knowledge_signals_for_fact_batch("afb-1") == [signal]
    assert store.list_knowledge_signals_for_fact_item("afi-1") == [signal]

    replacement = KnowledgeSignalRecord(
        signal_id="ks-afi-1-weakness-proposal-execution-separation",
        assessment_fact_batch_id="afb-1",
        assessment_fact_item_id="afi-1",
        source_evaluation_item_id="ei-1",
        signal_type="weakness",
        topic_key="proposal-execution-separation",
        polarity="negative",
        summary="updated proposal execution separation",
        confidence=0.85,
        status="active",
        projector_version="fact-signal-v1",
        created_at="2026-04-09T12:03:30Z",
        payload={"source_fact_type": "gap", "description": "updated"},
    )

    store.insert_knowledge_signals([replacement])

    assert store.list_knowledge_signals_for_fact_batch("afb-1") == [replacement]


def test_knowledge_signal_storage_does_not_write_legacy_graph_tables(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "checkpoint.db")
    store.initialize()
    _seed_minimal_assessment_fact(store)

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

    store.insert_knowledge_signals([signal])

    assert store.list_knowledge_nodes() == []
    assert store.list_knowledge_relations() == []


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
    target_node = KnowledgeNodeRecord(
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
    store.insert_graph_nodes([source_node, target_node])
    store.insert_graph_relations([relation])
    store.upsert_active_graph_revision_pointer(pointer)

    assert store.get_graph_revision("gr-proj-1-stage-1-20260409120400") == revision
    assert store.list_graph_nodes("gr-proj-1-stage-1-20260409120400") == [source_node, target_node]
    assert store.list_graph_relations("gr-proj-1-stage-1-20260409120400") == [relation]
    assert store.get_active_graph_revision_pointer("proj-1", "stage", "stage-1") == pointer


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


def _seed_minimal_assessment_fact(store: SQLiteStore) -> None:
    workflow_request = WorkflowRequestRecord(
        request_id="wr-1",
        request_type="review",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="user",
        source="test",
        status="accepted",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    workflow_run = WorkflowRunRecord(
        run_id="run-1",
        request_id="wr-1",
        run_type="review",
        status="completed",
        started_at="2026-04-09T12:00:00Z",
        finished_at="2026-04-09T12:04:00Z",
        payload={},
    )
    question_batch = QuestionBatchRecord(
        question_batch_id="qb-1",
        workflow_run_id="run-1",
        project_id="proj-1",
        stage_id="stage-1",
        generated_by="project_agent",
        source="test",
        batch_goal="checkpoint",
        entry_question_id="q-1",
        status="completed",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    question_item = QuestionItemRecord(
        question_id="q-1",
        question_batch_id="qb-1",
        question_type="conceptual",
        prompt="Explain proposal and execution separation.",
        intent="diagnose gap",
        difficulty_level="medium",
        order_index=0,
        status="active",
        created_at="2026-04-09T12:00:00Z",
        payload={},
    )
    answer_batch = AnswerBatchRecord(
        answer_batch_id="ab-1",
        question_batch_id="qb-1",
        workflow_run_id="run-1",
        submitted_by="user",
        submission_mode="batch",
        completion_status="completed",
        submitted_at="2026-04-09T12:01:00Z",
        status="submitted",
        payload={},
    )
    answer_item = AnswerItemRecord(
        answer_item_id="ai-1",
        answer_batch_id="ab-1",
        question_id="q-1",
        answered_by="user",
        answer_text="They are the same thing.",
        answer_format="plain_text",
        order_index=0,
        answered_at="2026-04-09T12:01:00Z",
        status="submitted",
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
        payload={},
    )
    evaluation_item = EvaluationItemRecord(
        evaluation_item_id="ei-1",
        evaluation_batch_id="eb-1",
        question_id="q-1",
        answer_item_id="ai-1",
        local_verdict="partial",
        confidence=0.8,
        status="completed",
        evaluated_at="2026-04-09T12:02:00Z",
        payload={"diagnosed_gaps": ["proposal-execution-separation"]},
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
    store.insert_assessment_fact_batch(fact_batch)
    store.insert_assessment_fact_items([fact_item])
