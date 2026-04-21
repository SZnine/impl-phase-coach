from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.assessment_synthesizer import AssessmentSynthesizer
from review_gate.checkpoint_models import (
    AnswerBatchRecord,
    AnswerItemRecord,
    EvaluationBatchRecord,
    EvaluationItemRecord,
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)
from review_gate.generated_chain_resolver import ResolvedQuestionChain
from review_gate.knowledge_graph_projector import KnowledgeSignalGraphProjector
from review_gate.knowledge_signal_projector import AssessmentFactSignalProjector
from review_gate.storage_sqlite import SQLiteStore


@dataclass(slots=True)
class CheckpointWriteResult:
    workflow_run_id: str
    question_batch_id: str
    answer_batch_id: str
    evaluation_batch_id: str
    assessment_fact_batch_id: str
    assessment_fact_item_count: int = 0
    knowledge_signal_count: int = 0
    graph_revision_id: str | None = None
    graph_node_count: int = 0
    graph_relation_count: int = 0


class AnswerCheckpointWriter:
    def __init__(
        self,
        *,
        store: SQLiteStore,
        synthesizer: AssessmentSynthesizer,
        signal_projector: AssessmentFactSignalProjector | None = None,
        graph_projector: KnowledgeSignalGraphProjector | None = None,
    ) -> None:
        self._store = store
        self._synthesizer = synthesizer
        self._signal_projector = signal_projector or AssessmentFactSignalProjector()
        self._graph_projector = graph_projector or KnowledgeSignalGraphProjector()

    def write(
        self,
        *,
        request: SubmitAnswerRequest,
        resolved_chain: ResolvedQuestionChain,
        assessment: dict[str, Any],
    ) -> CheckpointWriteResult:
        confidence = float(assessment.get("score", 0.0))
        submit_workflow_request = WorkflowRequestRecord(
            request_id=request.request_id,
            request_type="assessment",
            project_id=request.project_id,
            stage_id=request.stage_id,
            requested_by=request.actor_id,
            source=request.source_page,
            status="in_progress",
            created_at=request.created_at,
            payload={"request_id": request.request_id},
        )
        submit_workflow_run_id = f"run-{request.request_id}"
        submit_workflow_run = WorkflowRunRecord(
            run_id=submit_workflow_run_id,
            request_id=request.request_id,
            run_type="assessment",
            status="in_progress",
            started_at=request.created_at,
            finished_at=request.created_at,
            supersedes_run_id=None,
            payload={"request_id": request.request_id},
        )
        answer_batch_id = f"ab-{request.request_id}"
        answer_item_id = f"ai-{request.request_id}-0"
        evaluation_batch_id = f"eb-{request.request_id}"
        evaluation_item_id = f"ei-{request.request_id}-0"

        self._store.insert_workflow_request(submit_workflow_request)
        self._store.insert_workflow_run(submit_workflow_run)

        if resolved_chain.resolution_mode == "fallback":
            self._materialize_fallback_question_chain(
                request=request,
                resolved_chain=resolved_chain,
                workflow_run_id=submit_workflow_run_id,
            )

        answer_batch = AnswerBatchRecord(
            answer_batch_id=answer_batch_id,
            question_batch_id=resolved_chain.question_batch_id,
            workflow_run_id=submit_workflow_run_id,
            submitted_by=request.actor_id,
            submission_mode="single_submit",
            completion_status="complete",
            submitted_at=request.created_at,
            status="submitted",
            payload={
                "request_id": request.request_id,
                "resolution_mode": resolved_chain.resolution_mode,
                "transport_question_id": resolved_chain.transport_question_id,
            },
        )
        answer_item = AnswerItemRecord(
            answer_item_id=answer_item_id,
            answer_batch_id=answer_batch_id,
            question_id=resolved_chain.question_item_id,
            answered_by=request.actor_id,
            answer_text=request.answer_text,
            answer_format="plain_text",
            order_index=0,
            answered_at=request.created_at,
            status="answered",
            revision_of_answer_item_id=None,
            payload={
                "request_id": request.request_id,
                "transport_question_id": request.question_id,
                "answer_excerpt": request.answer_text.strip()[:120],
            },
        )
        evaluation_batch = EvaluationBatchRecord(
            evaluation_batch_id=evaluation_batch_id,
            answer_batch_id=answer_batch_id,
            workflow_run_id=submit_workflow_run_id,
            project_id=request.project_id,
            stage_id=request.stage_id,
            evaluated_by="assessment_agent",
            evaluator_version="review_flow_service:first-checkpoint",
            confidence=confidence,
            status="completed",
            evaluated_at=request.created_at,
            supersedes_evaluation_batch_id=None,
            payload={
                "request_id": request.request_id,
                "verdict": str(assessment.get("verdict", "")),
                "score": confidence,
                "summary": str(assessment.get("summary", "")),
            },
        )
        evaluation_payload: dict[str, Any] = {
            "reasoned_summary": str(assessment.get("summary", "")),
            "diagnosed_gaps": self._coerce_str_list(assessment.get("gaps")),
            "dimension_refs": self._coerce_str_list(assessment.get("dimensions")),
        }
        support_signals = self._coerce_dict_list(assessment.get("support_signals"))
        if support_signals:
            evaluation_payload["support_signals"] = support_signals

        evaluation_item = EvaluationItemRecord(
            evaluation_item_id=evaluation_item_id,
            evaluation_batch_id=evaluation_batch_id,
            question_id=resolved_chain.question_item_id,
            answer_item_id=answer_item_id,
            local_verdict=str(assessment.get("verdict", "")),
            confidence=confidence,
            status="completed",
            evaluated_at=request.created_at,
            payload=evaluation_payload,
        )

        self._store.insert_answer_batch(answer_batch)
        self._store.insert_answer_items([answer_item])
        self._store.insert_evaluation_batch(evaluation_batch)
        self._store.insert_evaluation_items([evaluation_item])

        fact_batch, fact_items = self._synthesizer.synthesize(
            workflow_run_id=submit_workflow_run_id,
            evaluation_batch=evaluation_batch,
            evaluation_items=[evaluation_item],
            evidence_spans=[],
        )
        self._store.insert_assessment_fact_batch(fact_batch)
        self._store.insert_assessment_fact_items(fact_items)

        knowledge_signals = self._signal_projector.project(
            fact_batch=fact_batch,
            fact_items=fact_items,
        )
        self._store.insert_knowledge_signals(knowledge_signals)

        graph_revision_id: str | None = None
        graph_node_count = 0
        graph_relation_count = 0
        if knowledge_signals:
            graph_revision, graph_nodes, graph_relations, active_pointer = self._graph_projector.project(
                project_id=request.project_id,
                scope_type="stage",
                scope_ref=request.stage_id,
                signals=knowledge_signals,
                created_at=request.created_at,
            )
            self._store.insert_graph_revision(graph_revision)
            self._store.insert_graph_nodes(graph_nodes)
            self._store.insert_graph_relations(graph_relations)
            self._store.upsert_active_graph_revision_pointer(active_pointer)
            graph_revision_id = graph_revision.graph_revision_id
            graph_node_count = len(graph_nodes)
            graph_relation_count = len(graph_relations)

        self._store.insert_workflow_request(
            WorkflowRequestRecord(
                request_id=request.request_id,
                request_type="assessment",
                project_id=request.project_id,
                stage_id=request.stage_id,
                requested_by=request.actor_id,
                source=request.source_page,
                status="completed",
                created_at=request.created_at,
                payload={"request_id": request.request_id},
            )
        )
        self._store.insert_workflow_run(
            WorkflowRunRecord(
                run_id=submit_workflow_run_id,
                request_id=request.request_id,
                run_type="assessment",
                status="completed",
                started_at=request.created_at,
                finished_at=request.created_at,
                supersedes_run_id=None,
                payload={"request_id": request.request_id},
            )
        )

        return CheckpointWriteResult(
            workflow_run_id=submit_workflow_run_id,
            question_batch_id=resolved_chain.question_batch_id,
            answer_batch_id=answer_batch_id,
            evaluation_batch_id=evaluation_batch_id,
            assessment_fact_batch_id=fact_batch.assessment_fact_batch_id,
            assessment_fact_item_count=len(fact_items),
            knowledge_signal_count=len(knowledge_signals),
            graph_revision_id=graph_revision_id,
            graph_node_count=graph_node_count,
            graph_relation_count=graph_relation_count,
        )

    def _materialize_fallback_question_chain(
        self,
        *,
        request: SubmitAnswerRequest,
        resolved_chain: ResolvedQuestionChain,
        workflow_run_id: str,
    ) -> None:
        if self._store.get_question_batch(resolved_chain.question_batch_id) is None:
            self._store.insert_question_batch(
                QuestionBatchRecord(
                    question_batch_id=resolved_chain.question_batch_id,
                    workflow_run_id=workflow_run_id,
                    project_id=request.project_id,
                    stage_id=request.stage_id,
                    generated_by="answer_checkpoint_writer",
                    source=request.source_page,
                    batch_goal="materialize fallback submit-side question chain",
                    entry_question_id=resolved_chain.question_item_id,
                    status="active",
                    created_at=request.created_at,
                    payload={
                        "request_id": request.request_id,
                        "resolution_mode": resolved_chain.resolution_mode,
                        "transport_question_id": resolved_chain.transport_question_id,
                    },
                )
            )

        if not self._store.list_question_items(resolved_chain.question_batch_id):
            self._store.insert_question_items(
                [
                    QuestionItemRecord(
                        question_id=resolved_chain.question_item_id,
                        question_batch_id=resolved_chain.question_batch_id,
                        question_type="core",
                        prompt=f"Fallback question for {resolved_chain.transport_question_id}.",
                        intent="Preserve submit-side checkpoint continuity.",
                        difficulty_level="core",
                        order_index=0,
                        status="ready",
                        created_at=request.created_at,
                        payload={
                            "request_id": request.request_id,
                            "resolution_mode": resolved_chain.resolution_mode,
                            "transport_question_id": resolved_chain.transport_question_id,
                        },
                    )
                ]
            )

    @staticmethod
    def _coerce_str_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            items = value
        elif isinstance(value, tuple):
            items = list(value)
        elif isinstance(value, dict):
            items = list(value.keys())
        else:
            items = [value]
        return [str(item) for item in items]

    @staticmethod
    def _coerce_dict_list(value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]
