from __future__ import annotations

from pathlib import Path

import pytest

from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.answer_checkpoint_writer import AnswerCheckpointWriter, CheckpointWriteResult
from review_gate.assessment_synthesizer import AssessmentSynthesizer
from review_gate.checkpoint_models import (
    ActiveGraphRevisionPointerRecord,
    AnswerBatchRecord,
    AnswerItemRecord,
    AssessmentFactBatchRecord,
    AssessmentFactItemRecord,
    EvaluationBatchRecord,
    EvaluationItemRecord,
    GraphRevisionRecord,
    KnowledgeNodeRecord,
    KnowledgeSignalRecord,
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)
from review_gate.generated_chain_resolver import ResolvedQuestionChain
from review_gate.storage_sqlite import SQLiteStore


def _writer_request(*, request_id: str, answer_text: str, created_at: str) -> SubmitAnswerRequest:
    return SubmitAnswerRequest(
        request_id=request_id,
        project_id="proj-1",
        stage_id="stage-1",
        source_page="question_detail",
        actor_id="local-user",
        created_at=created_at,
        question_set_id="set-1",
        question_id="set-1-q-1",
        answer_text=answer_text,
        draft_id=None,
    )


def _resolved_chain() -> ResolvedQuestionChain:
    return ResolvedQuestionChain(
        workflow_run_id="run-req-qgen-1",
        question_batch_id="qb-req-qgen-1",
        question_item_id="req-qgen-1-q-1",
        transport_question_id="set-1-q-1",
        resolution_mode="reused",
    )


def _seed_generated_question_chain(store: SQLiteStore, *, request_id: str, created_at: str) -> None:
    workflow_run_id = f"run-{request_id}"
    question_batch_id = f"qb-{request_id}"

    store.insert_workflow_request(
        WorkflowRequestRecord(
            request_id=request_id,
            request_type="question_cycle",
            project_id="proj-1",
            stage_id="stage-1",
            requested_by="question_generation_client",
            source="review_flow_service",
            status="completed",
            created_at=created_at,
            payload={"request_id": request_id},
        )
    )
    store.insert_workflow_run(
        WorkflowRunRecord(
            run_id=workflow_run_id,
            request_id=request_id,
            run_type="question_cycle",
            status="completed",
            started_at=created_at,
            finished_at=created_at,
            supersedes_run_id=None,
            payload={"request_id": request_id},
        )
    )
    store.insert_question_batch(
        QuestionBatchRecord(
            question_batch_id=question_batch_id,
            workflow_run_id=workflow_run_id,
            project_id="proj-1",
            stage_id="stage-1",
            generated_by="question_generation_client",
            source="review_flow_service",
            batch_goal="freeze boundary",
            entry_question_id=f"{request_id}-q-1",
            status="active",
            created_at=created_at,
            payload={"request_id": request_id},
        )
    )
    store.insert_question_items(
        [
            QuestionItemRecord(
                question_id=f"{request_id}-q-1",
                question_batch_id=question_batch_id,
                question_type="core",
                prompt="Explain the boundary.",
                intent="Check understanding.",
                difficulty_level="core",
                order_index=0,
                status="ready",
                created_at=created_at,
                payload={"transport_question_id": "set-1-q-1"},
            )
        ]
    )


class FailingGraphProjector:
    def project(self, **_: object) -> object:
        raise RuntimeError("graph projection failed")


def test_answer_checkpoint_writer_persists_submit_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = AnswerCheckpointWriter(store=store, synthesizer=AssessmentSynthesizer())
    _seed_generated_question_chain(store, request_id="req-qgen-1", created_at="2026-04-10T10:05:00Z")

    result = writer.write(
        request=_writer_request(
            request_id="req-submit-1",
            answer_text="We split state and scoring boundaries.",
            created_at="2026-04-10T11:00:00Z",
        ),
        resolved_chain=_resolved_chain(),
        assessment={
            "verdict": "partial",
            "score": 0.8,
            "summary": "Still mixes proposal and execution.",
            "gaps": ["proposal-execution-separation"],
            "dimensions": ["understanding", "causality"],
        },
    )

    assert result == CheckpointWriteResult(
        workflow_run_id="run-req-submit-1",
        question_batch_id="qb-req-qgen-1",
        answer_batch_id="ab-req-submit-1",
        evaluation_batch_id="eb-req-submit-1",
        assessment_fact_batch_id="afb-eb-req-submit-1",
        assessment_fact_item_count=1,
        knowledge_signal_count=1,
        graph_revision_id="gr-proj-1-stage-stage-1-20260410110000",
        graph_node_count=1,
    )
    assert store.get_workflow_request("req-submit-1") == WorkflowRequestRecord(
        request_id="req-submit-1",
        request_type="assessment",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="local-user",
        source="question_detail",
        status="completed",
        created_at="2026-04-10T11:00:00Z",
        payload={"request_id": "req-submit-1"},
    )
    assert store.get_workflow_run("run-req-submit-1") == WorkflowRunRecord(
        run_id="run-req-submit-1",
        request_id="req-submit-1",
        run_type="assessment",
        status="completed",
        started_at="2026-04-10T11:00:00Z",
        finished_at="2026-04-10T11:00:00Z",
        supersedes_run_id=None,
        payload={"request_id": "req-submit-1"},
    )
    assert store.get_answer_batch("ab-req-submit-1") == AnswerBatchRecord(
        answer_batch_id="ab-req-submit-1",
        question_batch_id="qb-req-qgen-1",
        workflow_run_id="run-req-submit-1",
        submitted_by="local-user",
        submission_mode="single_submit",
        completion_status="complete",
        submitted_at="2026-04-10T11:00:00Z",
        status="submitted",
        payload={
            "request_id": "req-submit-1",
            "resolution_mode": "reused",
            "transport_question_id": "set-1-q-1",
        },
    )
    assert store.list_answer_items("ab-req-submit-1") == [
        AnswerItemRecord(
            answer_item_id="ai-req-submit-1-0",
            answer_batch_id="ab-req-submit-1",
            question_id="req-qgen-1-q-1",
            answered_by="local-user",
            answer_text="We split state and scoring boundaries.",
            answer_format="plain_text",
            order_index=0,
            answered_at="2026-04-10T11:00:00Z",
            status="answered",
            revision_of_answer_item_id=None,
            payload={
                "request_id": "req-submit-1",
                "transport_question_id": "set-1-q-1",
                "answer_excerpt": "We split state and scoring boundaries.",
            },
        )
    ]
    signal_id = (
        "ks-afi-ei-req-submit-1-0-proposal-execution-separation"
        "-weakness-proposal-execution-separation"
    )
    assert store.list_knowledge_signals_for_fact_batch("afb-eb-req-submit-1") == [
        KnowledgeSignalRecord(
            signal_id=signal_id,
            assessment_fact_batch_id="afb-eb-req-submit-1",
            assessment_fact_item_id="afi-ei-req-submit-1-0-proposal-execution-separation",
            source_evaluation_item_id="ei-req-submit-1-0",
            signal_type="weakness",
            topic_key="proposal-execution-separation",
            polarity="negative",
            summary="proposal execution separation",
            confidence=0.8,
            status="active",
            projector_version="fact-signal-v1",
            created_at="2026-04-10T11:00:00Z",
            payload={
                "source_fact_type": "gap",
                "source_title": "proposal execution separation",
                "description": "Still mixes proposal and execution.",
                "source_payload": {
                    "description": "Still mixes proposal and execution.",
                    "dimension_refs": ["understanding", "causality"],
                    "evidence_span_ids": [],
                },
                "fact_batch_synthesizer_version": "first-checkpoint-v1",
            },
        )
    ]
    assert store.get_graph_revision("gr-proj-1-stage-stage-1-20260410110000") == GraphRevisionRecord(
        graph_revision_id="gr-proj-1-stage-stage-1-20260410110000",
        project_id="proj-1",
        scope_type="stage",
        scope_ref="stage-1",
        revision_type="deterministic_signal_projection",
        based_on_revision_id=None,
        source_fact_batch_ids=["afb-eb-req-submit-1"],
        source_signal_ids=[signal_id],
        status="active",
        revision_summary="1 signals projected into 1 nodes",
        node_count=1,
        relation_count=0,
        created_by="knowledge_signal_graph_projector",
        created_at="2026-04-10T11:00:00Z",
        activated_at="2026-04-10T11:00:00Z",
        payload={"projector_version": "signal-graph-v1"},
    )
    assert store.list_graph_nodes("gr-proj-1-stage-stage-1-20260410110000") == [
        KnowledgeNodeRecord(
            knowledge_node_id=(
                "kn-gr-proj-1-stage-stage-1-20260410110000"
                "-proposal-execution-separation"
            ),
            graph_revision_id="gr-proj-1-stage-stage-1-20260410110000",
            topic_key="proposal-execution-separation",
            label="proposal execution separation",
            node_type="weakness_topic",
            description="Still mixes proposal and execution.",
            source_signal_ids=[signal_id],
            supporting_fact_ids=["afi-ei-req-submit-1-0-proposal-execution-separation"],
            confidence=0.8,
            status="active",
            created_by="knowledge_signal_graph_projector",
            created_at="2026-04-10T11:00:00Z",
            updated_at="2026-04-10T11:00:00Z",
            payload={
                "projector_version": "signal-graph-v1",
                "signal_types": ["weakness"],
                "polarity_counts": {"negative": 1},
            },
        )
    ]
    assert store.get_active_graph_revision_pointer("proj-1", "stage", "stage-1") == (
        ActiveGraphRevisionPointerRecord(
            project_id="proj-1",
            scope_type="stage",
            scope_ref="stage-1",
            active_graph_revision_id="gr-proj-1-stage-stage-1-20260410110000",
            updated_at="2026-04-10T11:00:00Z",
            updated_by="knowledge_signal_graph_projector",
            payload={"projector_version": "signal-graph-v1"},
        )
    )
    assert store.list_knowledge_nodes() == []
    assert store.list_knowledge_relations() == []
    assert store.get_evaluation_batch("eb-req-submit-1") == EvaluationBatchRecord(
        evaluation_batch_id="eb-req-submit-1",
        answer_batch_id="ab-req-submit-1",
        workflow_run_id="run-req-submit-1",
        project_id="proj-1",
        stage_id="stage-1",
        evaluated_by="assessment_agent",
        evaluator_version="review_flow_service:first-checkpoint",
        confidence=0.8,
        status="completed",
        evaluated_at="2026-04-10T11:00:00Z",
        supersedes_evaluation_batch_id=None,
        payload={
            "request_id": "req-submit-1",
            "verdict": "partial",
            "score": 0.8,
            "summary": "Still mixes proposal and execution.",
        },
    )
    assert store.list_evaluation_items("eb-req-submit-1") == [
        EvaluationItemRecord(
            evaluation_item_id="ei-req-submit-1-0",
            evaluation_batch_id="eb-req-submit-1",
            question_id="req-qgen-1-q-1",
            answer_item_id="ai-req-submit-1-0",
            local_verdict="partial",
            confidence=0.8,
            status="completed",
            evaluated_at="2026-04-10T11:00:00Z",
            payload={
                "reasoned_summary": "Still mixes proposal and execution.",
                "diagnosed_gaps": ["proposal-execution-separation"],
                "dimension_refs": ["understanding", "causality"],
            },
        )
    ]
    assert store.get_latest_assessment_fact_batch("proj-1", "stage-1") == AssessmentFactBatchRecord(
        assessment_fact_batch_id="afb-eb-req-submit-1",
        evaluation_batch_id="eb-req-submit-1",
        workflow_run_id="run-req-submit-1",
        synthesized_by="assessment_synthesizer",
        synthesizer_version="first-checkpoint-v1",
        status="completed",
        synthesized_at="2026-04-10T11:00:00Z",
        supersedes_assessment_fact_batch_id=None,
        payload={"item_count": 1},
    )
    assert store.list_assessment_fact_items("afb-eb-req-submit-1") == [
        AssessmentFactItemRecord(
            assessment_fact_item_id="afi-ei-req-submit-1-0-proposal-execution-separation",
            assessment_fact_batch_id="afb-eb-req-submit-1",
            source_evaluation_item_id="ei-req-submit-1-0",
            fact_type="gap",
            topic_key="proposal-execution-separation",
            title="proposal execution separation",
            confidence=0.8,
            status="active",
            created_at="2026-04-10T11:00:00Z",
            supersedes_assessment_fact_item_id=None,
            payload={
                "description": "Still mixes proposal and execution.",
                "dimension_refs": ["understanding", "causality"],
                "evidence_span_ids": [],
            },
        )
    ]


def test_answer_checkpoint_writer_uses_assessment_synthesizer_for_multiple_gaps(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = AnswerCheckpointWriter(store=store, synthesizer=AssessmentSynthesizer())
    _seed_generated_question_chain(store, request_id="req-qgen-1", created_at="2026-04-10T10:05:00Z")

    result = writer.write(
        request=_writer_request(
            request_id="req-submit-2",
            answer_text="We split state and scoring boundaries.",
            created_at="2026-04-10T11:05:00Z",
        ),
        resolved_chain=_resolved_chain(),
        assessment={
            "verdict": "partial",
            "score": 0.72,
            "summary": "Two boundary gaps remain.",
            "gaps": [
                "proposal-execution-separation",
                "scope-boundary-separation",
            ],
            "dimensions": ["understanding", "causality"],
        },
    )

    assert result.assessment_fact_batch_id == "afb-eb-req-submit-2"
    assert store.get_workflow_request("req-submit-2") == WorkflowRequestRecord(
        request_id="req-submit-2",
        request_type="assessment",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="local-user",
        source="question_detail",
        status="completed",
        created_at="2026-04-10T11:05:00Z",
        payload={"request_id": "req-submit-2"},
    )
    assert store.get_workflow_run("run-req-submit-2") == WorkflowRunRecord(
        run_id="run-req-submit-2",
        request_id="req-submit-2",
        run_type="assessment",
        status="completed",
        started_at="2026-04-10T11:05:00Z",
        finished_at="2026-04-10T11:05:00Z",
        supersedes_run_id=None,
        payload={"request_id": "req-submit-2"},
    )
    assert store.list_assessment_fact_items("afb-eb-req-submit-2") == [
        AssessmentFactItemRecord(
            assessment_fact_item_id="afi-ei-req-submit-2-0-proposal-execution-separation",
            assessment_fact_batch_id="afb-eb-req-submit-2",
            source_evaluation_item_id="ei-req-submit-2-0",
            fact_type="gap",
            topic_key="proposal-execution-separation",
            title="proposal execution separation",
            confidence=0.72,
            status="active",
            created_at="2026-04-10T11:05:00Z",
            supersedes_assessment_fact_item_id=None,
            payload={
                "description": "Two boundary gaps remain.",
                "dimension_refs": ["understanding", "causality"],
                "evidence_span_ids": [],
            },
        ),
        AssessmentFactItemRecord(
            assessment_fact_item_id="afi-ei-req-submit-2-0-scope-boundary-separation",
            assessment_fact_batch_id="afb-eb-req-submit-2",
            source_evaluation_item_id="ei-req-submit-2-0",
            fact_type="gap",
            topic_key="scope-boundary-separation",
            title="scope boundary separation",
            confidence=0.72,
            status="active",
            created_at="2026-04-10T11:05:00Z",
            supersedes_assessment_fact_item_id=None,
            payload={
                "description": "Two boundary gaps remain.",
                "dimension_refs": ["understanding", "causality"],
                "evidence_span_ids": [],
            },
        ),
    ]


def test_answer_checkpoint_writer_skips_graph_revision_when_assessment_has_no_signals(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = AnswerCheckpointWriter(store=store, synthesizer=AssessmentSynthesizer())
    _seed_generated_question_chain(store, request_id="req-qgen-1", created_at="2026-04-10T10:05:00Z")

    result = writer.write(
        request=_writer_request(
            request_id="req-submit-no-signal",
            answer_text="No diagnosed gaps in this answer.",
            created_at="2026-04-10T11:20:00Z",
        ),
        resolved_chain=_resolved_chain(),
        assessment={
            "verdict": "pass",
            "score": 0.95,
            "summary": "No durable gaps detected.",
            "gaps": [],
            "dimensions": ["understanding"],
        },
    )

    assert result.assessment_fact_batch_id == "afb-eb-req-submit-no-signal"
    assert result.assessment_fact_item_count == 0
    assert result.knowledge_signal_count == 0
    assert result.graph_revision_id is None
    assert result.graph_node_count == 0
    assert store.list_assessment_fact_items("afb-eb-req-submit-no-signal") == []
    assert store.list_knowledge_signals_for_fact_batch("afb-eb-req-submit-no-signal") == []
    assert store.get_active_graph_revision_pointer("proj-1", "stage", "stage-1") is None


def test_answer_checkpoint_writer_materializes_fallback_question_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = AnswerCheckpointWriter(store=store, synthesizer=AssessmentSynthesizer())

    result = writer.write(
        request=_writer_request(
            request_id="req-submit-3",
            answer_text="We split state and scoring boundaries.",
            created_at="2026-04-10T11:10:00Z",
        ),
        resolved_chain=ResolvedQuestionChain(
            workflow_run_id="run-req-submit-3",
            question_batch_id="qb-req-submit-3",
            question_item_id="req-submit-3-set-1-q-1",
            transport_question_id="set-1-q-1",
            resolution_mode="fallback",
        ),
        assessment={
            "verdict": "partial",
            "score": 0.55,
            "summary": "Fallback chain still writes checkpoint records.",
            "gaps": ["proposal-execution-separation"],
            "dimensions": ["understanding"],
        },
    )

    assert result.workflow_run_id == "run-req-submit-3"
    assert store.get_workflow_request("req-submit-3") == WorkflowRequestRecord(
        request_id="req-submit-3",
        request_type="assessment",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="local-user",
        source="question_detail",
        status="completed",
        created_at="2026-04-10T11:10:00Z",
        payload={"request_id": "req-submit-3"},
    )
    assert store.get_workflow_run("run-req-submit-3") == WorkflowRunRecord(
        run_id="run-req-submit-3",
        request_id="req-submit-3",
        run_type="assessment",
        status="completed",
        started_at="2026-04-10T11:10:00Z",
        finished_at="2026-04-10T11:10:00Z",
        supersedes_run_id=None,
        payload={"request_id": "req-submit-3"},
    )
    assert store.get_question_batch("qb-req-submit-3") == QuestionBatchRecord(
        question_batch_id="qb-req-submit-3",
        workflow_run_id="run-req-submit-3",
        project_id="proj-1",
        stage_id="stage-1",
        generated_by="answer_checkpoint_writer",
        source="question_detail",
        batch_goal="materialize fallback submit-side question chain",
        entry_question_id="req-submit-3-set-1-q-1",
        status="active",
        created_at="2026-04-10T11:10:00Z",
        payload={
            "request_id": "req-submit-3",
            "resolution_mode": "fallback",
            "transport_question_id": "set-1-q-1",
        },
    )
    assert store.list_question_items("qb-req-submit-3") == [
        QuestionItemRecord(
            question_id="req-submit-3-set-1-q-1",
            question_batch_id="qb-req-submit-3",
            question_type="core",
            prompt="Fallback question for set-1-q-1.",
            intent="Preserve submit-side checkpoint continuity.",
            difficulty_level="core",
            order_index=0,
            status="ready",
            created_at="2026-04-10T11:10:00Z",
            payload={
                "request_id": "req-submit-3",
                "resolution_mode": "fallback",
                "transport_question_id": "set-1-q-1",
            },
        )
    ]


def test_answer_checkpoint_writer_leaves_submit_workflow_in_progress_on_downstream_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = AnswerCheckpointWriter(store=store, synthesizer=AssessmentSynthesizer())

    def fail_insert_answer_batch(_: AnswerBatchRecord) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(store, "insert_answer_batch", fail_insert_answer_batch)

    with pytest.raises(RuntimeError, match="boom"):
        writer.write(
            request=_writer_request(
                request_id="req-submit-4",
                answer_text="We split state and scoring boundaries.",
                created_at="2026-04-10T11:15:00Z",
            ),
            resolved_chain=ResolvedQuestionChain(
                workflow_run_id="run-req-submit-4",
                question_batch_id="qb-req-submit-4",
                question_item_id="req-submit-4-set-1-q-1",
                transport_question_id="set-1-q-1",
                resolution_mode="fallback",
            ),
            assessment={
                "verdict": "partial",
                "score": 0.4,
                "summary": "Downstream failure should not finalize workflow.",
                "gaps": ["proposal-execution-separation"],
                "dimensions": ["understanding"],
            },
        )

    assert store.get_workflow_request("req-submit-4") == WorkflowRequestRecord(
        request_id="req-submit-4",
        request_type="assessment",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="local-user",
        source="question_detail",
        status="in_progress",
        created_at="2026-04-10T11:15:00Z",
        payload={"request_id": "req-submit-4"},
    )
    assert store.get_workflow_run("run-req-submit-4") == WorkflowRunRecord(
        run_id="run-req-submit-4",
        request_id="req-submit-4",
        run_type="assessment",
        status="in_progress",
        started_at="2026-04-10T11:15:00Z",
        finished_at="2026-04-10T11:15:00Z",
        supersedes_run_id=None,
        payload={"request_id": "req-submit-4"},
    )


def test_answer_checkpoint_writer_leaves_submit_workflow_in_progress_on_graph_projection_failure(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = AnswerCheckpointWriter(
        store=store,
        synthesizer=AssessmentSynthesizer(),
        graph_projector=FailingGraphProjector(),  # type: ignore[arg-type]
    )
    _seed_generated_question_chain(store, request_id="req-qgen-1", created_at="2026-04-10T10:05:00Z")

    with pytest.raises(RuntimeError, match="graph projection failed"):
        writer.write(
            request=_writer_request(
                request_id="req-submit-graph-fail",
                answer_text="We split state and scoring boundaries.",
                created_at="2026-04-10T11:25:00Z",
            ),
            resolved_chain=_resolved_chain(),
            assessment={
                "verdict": "partial",
                "score": 0.6,
                "summary": "Graph projection failure should not finalize workflow.",
                "gaps": ["proposal-execution-separation"],
                "dimensions": ["understanding"],
            },
        )

    assert store.get_workflow_request("req-submit-graph-fail") == WorkflowRequestRecord(
        request_id="req-submit-graph-fail",
        request_type="assessment",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="local-user",
        source="question_detail",
        status="in_progress",
        created_at="2026-04-10T11:25:00Z",
        payload={"request_id": "req-submit-graph-fail"},
    )
    assert store.get_workflow_run("run-req-submit-graph-fail") == WorkflowRunRecord(
        run_id="run-req-submit-graph-fail",
        request_id="req-submit-graph-fail",
        run_type="assessment",
        status="in_progress",
        started_at="2026-04-10T11:25:00Z",
        finished_at="2026-04-10T11:25:00Z",
        supersedes_run_id=None,
        payload={"request_id": "req-submit-graph-fail"},
    )
    assert store.list_knowledge_signals_for_fact_batch("afb-eb-req-submit-graph-fail") != []
    assert store.get_active_graph_revision_pointer("proj-1", "stage", "stage-1") is None
