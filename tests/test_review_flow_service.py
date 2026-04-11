import pytest

from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.answer_checkpoint_writer import CheckpointWriteResult
from review_gate.generated_chain_resolver import ResolvedQuestionChain
from review_gate.domain import QuestionSet, WorkspaceEvent
from review_gate.project_agent_response_normalizer import ProjectAgentResponseNormalizer
from review_gate.review_flow_service import ReviewFlowService
from review_gate.storage_sqlite import SQLiteStore
from pathlib import Path

from review_gate.checkpoint_models import (
    AnswerBatchRecord,
    AnswerItemRecord,
    AssessmentFactBatchRecord,
    EvidenceSpanRecord,
    EvaluationBatchRecord,
    EvaluationItemRecord,
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)


class CapturingAssessmentClient:
    def __init__(
        self,
        *,
        assessment_override: dict | None = None,
        confidence: float = 0.8,
    ) -> None:
        self.requests: list[dict] = []
        self.assessment_override = assessment_override or {}
        self.confidence = confidence

    @classmethod
    def for_testing(cls) -> "CapturingAssessmentClient":
        return cls()

    def assess(self, request: dict) -> dict:
        self.requests.append(request)
        assessment = {
            "score_total": 0.72,
            "dimension_scores": {
                "correctness": 3,
                "reasoning": 3,
                "decision_awareness": 2,
                "boundary_awareness": 3,
                "stability": 2,
            },
            "verdict": "partial",
            "core_gaps": [],
            "misconceptions": [],
            "evidence": ["assessment evidence: verdict=partial"],
        }
        assessment.update(self.assessment_override)
        return {
            "request_id": request["request_id"],
            "assessment": assessment,
            "recommended_action": "continue_answering",
            "recommended_follow_up_questions": [],
            "learning_recommendations": [],
            "warnings": [],
            "confidence": self.confidence,
        }


class WeakAssessmentClient:
    @classmethod
    def for_testing(cls) -> "WeakAssessmentClient":
        return cls()

    def assess(self, request: dict) -> dict:
        return {
            "request_id": request["request_id"],
            "assessment": {
                "score_total": 0.35,
                "dimension_scores": {
                    "correctness": 1,
                    "reasoning": 1,
                    "decision_awareness": 1,
                    "boundary_awareness": 1,
                    "stability": 1,
                },
                "verdict": "weak",
                "core_gaps": ["Needs deeper boundary explanation."],
                "misconceptions": [],
                "evidence": ["assessment evidence: verdict=weak"],
            },
            "recommended_action": "redirect_to_learning",
            "recommended_follow_up_questions": [],
            "learning_recommendations": ["Revisit the stage boundary."],
            "warnings": [],
            "confidence": 0.7,
        }


class RawProjectAgentQuestionGenerationClient:
    def __init__(self, *, raw_content: str) -> None:
        self.raw_content = raw_content
        self.requests: list[dict] = []

    def generate(self, request: dict) -> dict:
        self.requests.append(request)
        return {
            "request_id": request["request_id"],
            "provider": "openai_compatible",
            "model": "gpt-5.4",
            "raw_content": self.raw_content,
            "raw_response": {"choices": [{"message": {"content": self.raw_content}}]},
            "output_contract": {
                "questions": [
                    {
                        "id": "q-1",
                        "prompt": "string",
                        "type": "open",
                        "intent": "string",
                        "difficulty": "basic|intermediate|advanced",
                    }
                ]
            },
        }


class CapturingGeneratedChainResolver:
    def __init__(self, resolved_chain: ResolvedQuestionChain) -> None:
        self.resolved_chain = resolved_chain
        self.calls: list[dict] = []

    def resolve(self, **kwargs) -> ResolvedQuestionChain:
        self.calls.append(dict(kwargs))
        return self.resolved_chain


class CapturingAnswerCheckpointWriter:
    def __init__(self, *, store: SQLiteStore | None = None) -> None:
        self.calls: list[dict] = []
        self._store = store

    def write(self, **kwargs) -> CheckpointWriteResult:
        self.calls.append(dict(kwargs))
        request: SubmitAnswerRequest = kwargs["request"]
        resolved_chain: ResolvedQuestionChain = kwargs["resolved_chain"]
        if self._store is not None:
            workflow_run_id = f"run-{request.request_id}"
            answer_batch_id = f"ab-{request.request_id}"
            evaluation_batch_id = f"eb-{request.request_id}"
            answer_item_id = f"ai-{request.request_id}-0"
            evaluation_item_id = f"ei-{request.request_id}-0"
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
                    run_id=workflow_run_id,
                    request_id=request.request_id,
                    run_type="assessment",
                    status="completed",
                    started_at=request.created_at,
                    finished_at=request.created_at,
                    supersedes_run_id=None,
                    payload={"request_id": request.request_id},
                )
            )
            self._store.insert_answer_batch(
                AnswerBatchRecord(
                    answer_batch_id=answer_batch_id,
                    question_batch_id=resolved_chain.question_batch_id,
                    workflow_run_id=workflow_run_id,
                    submitted_by=request.actor_id,
                    submission_mode="single_submit",
                    completion_status="complete",
                    submitted_at=request.created_at,
                    status="submitted",
                    payload={"request_id": request.request_id},
                )
            )
            self._store.insert_answer_items(
                [
                    AnswerItemRecord(
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
                        payload={"answer_excerpt": request.answer_text.strip()[:120]},
                    )
                ]
            )
            self._store.insert_evaluation_batch(
                EvaluationBatchRecord(
                    evaluation_batch_id=evaluation_batch_id,
                    answer_batch_id=answer_batch_id,
                    workflow_run_id=workflow_run_id,
                    project_id=request.project_id,
                    stage_id=request.stage_id,
                    evaluated_by="assessment_agent",
                    evaluator_version="test-writer",
                    confidence=0.8,
                    status="completed",
                    evaluated_at=request.created_at,
                    supersedes_evaluation_batch_id=None,
                    payload={"request_id": request.request_id},
                )
            )
            self._store.insert_evaluation_items(
                [
                    EvaluationItemRecord(
                        evaluation_item_id=evaluation_item_id,
                        evaluation_batch_id=evaluation_batch_id,
                        question_id=resolved_chain.question_item_id,
                        answer_item_id=answer_item_id,
                        local_verdict=str(kwargs["assessment"].get("verdict", "")),
                        confidence=float(kwargs["assessment"].get("score", 0.0)),
                        status="completed",
                        evaluated_at=request.created_at,
                        payload={"reasoned_summary": str(kwargs["assessment"].get("summary", ""))},
                    )
                ]
            )
        return CheckpointWriteResult(
            workflow_run_id=f"run-{request.request_id}",
            question_batch_id=resolved_chain.question_batch_id,
            answer_batch_id=f"ab-{request.request_id}",
            evaluation_batch_id=f"eb-{request.request_id}",
            assessment_fact_batch_id=f"afb-eb-{request.request_id}",
        )


def _semantic_question_set() -> QuestionSet:
    return QuestionSet(
        question_set_id="set-1",
        stage_review_id="proj-1:stage-1",
        title="Question set set-1",
        status="active",
        question_ids=["set-1-q-1", "set-1-q-2"],
        active_question_id="set-1-q-1",
    )


def _insert_legacy_generated_chain(
    *,
    store: SQLiteStore,
    request_id: str,
    created_at: str,
) -> None:
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
            payload={"request": {"request_id": request_id}},
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
            payload={"question_count": 2, "request_id": request_id},
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
            batch_goal="freeze the minimal Question / Assessment / Decision boundary",
            entry_question_id=f"{request_id}-q-1",
            status="active",
            created_at=created_at,
            payload={"question_count": 2, "request_id": request_id},
        )
    )
    store.insert_question_items(
        [
            QuestionItemRecord(
                question_id=f"{request_id}-q-1",
                question_batch_id=question_batch_id,
                question_type="core",
                prompt="Explain the current-stage boundary.",
                intent="Check current-stage understanding.",
                difficulty_level="core",
                order_index=0,
                status="ready",
                created_at=created_at,
                payload={
                    "expected_signals": ["Question, Assessment, Decision split"],
                    "source_context": [],
                    "transport_question_id": "set-1-q-1",
                },
            ),
            QuestionItemRecord(
                question_id=f"{request_id}-q-2",
                question_batch_id=question_batch_id,
                question_type="why",
                prompt="Why did we choose this boundary?",
                intent="Check reasoning about trade-offs.",
                difficulty_level="why",
                order_index=1,
                status="ready",
                created_at=created_at,
                payload={
                    "expected_signals": ["module vs interface"],
                    "source_context": [],
                    "transport_question_id": "set-1-q-2",
                },
            ),
        ]
    )
    store.append_event(
        WorkspaceEvent(
            event_id=f"evt-question-set-generated-{request_id}",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at=created_at,
            payload={
                "stage_id": "stage-1",
                "question_set_id": "set-1",
                "question_batch_id": question_batch_id,
                "workflow_run_id": workflow_run_id,
                "question_item_ids": [f"{request_id}-q-1", f"{request_id}-q-2"],
            },
        )
    )


def test_generate_question_set_returns_structured_questions() -> None:
    service = ReviewFlowService.for_testing()

    response = service.generate_question_set(
        {
            "request_id": "req-qgen-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
            "stage_summary": "Task 4 adapter shell",
            "stage_artifacts": [],
            "stage_exit_criteria": [],
            "current_decisions": ["Question, Assessment, Decision split"],
            "key_logic_points": ["structured DTOs"],
            "known_weak_points": [],
            "boundary_focus": ["module vs interface"],
            "question_strategy": "core_and_why",
            "max_questions": 2,
            "source_refs": [],
        }
    )

    assert response["request_id"] == "req-qgen-1"
    assert response["questions"]
    assert response["questions"][0]["question_level"] == "core"
    assert response["questions"][1]["question_level"] == "why"


def test_generate_question_set_persists_first_checkpoint_question_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    question_set = _semantic_question_set()
    store.upsert_question_set(question_set)
    service = ReviewFlowService.with_store(store)

    response = service.generate_question_set(
        {
            "request_id": "req-qgen-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
            "stage_summary": "Task 4 adapter shell",
            "stage_artifacts": [],
            "stage_exit_criteria": [],
            "current_decisions": ["Question, Assessment, Decision split"],
            "key_logic_points": ["structured DTOs"],
            "known_weak_points": [],
            "boundary_focus": ["module vs interface"],
            "question_strategy": "core_and_why",
            "max_questions": 2,
            "source_refs": [],
        }
    )

    assert response["request_id"] == "req-qgen-1"
    assert response["questions"]
    assert response["questions"][0]["question_level"] == "core"
    assert response["questions"][1]["question_level"] == "why"

    assert store.get_workflow_request("req-qgen-1") == WorkflowRequestRecord(
        request_id="req-qgen-1",
        request_type="question_cycle",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="question_generation_client",
        source="review_flow_service",
        status="completed",
        created_at="",
        payload={
            "request": {
                "boundary_focus": ["module vs interface"],
                "current_decisions": ["Question, Assessment, Decision split"],
                "key_logic_points": ["structured DTOs"],
                "known_weak_points": [],
                "max_questions": 2,
                "project_id": "proj-1",
                "question_strategy": "core_and_why",
                "request_id": "req-qgen-1",
                "source_refs": [],
                "stage_artifacts": [],
                "stage_exit_criteria": [],
                "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
                "stage_id": "stage-1",
                "stage_label": "module-interface-boundary",
                "stage_summary": "Task 4 adapter shell",
            }
        },
    )
    assert store.get_workflow_run("run-req-qgen-1") == WorkflowRunRecord(
        run_id="run-req-qgen-1",
        request_id="req-qgen-1",
        run_type="question_cycle",
        status="completed",
        started_at="",
        finished_at="",
        supersedes_run_id=None,
        payload={"question_count": 2, "request_id": "req-qgen-1"},
    )
    assert store.get_question_set("set-1") == question_set
    assert store.get_question_batch("qb-req-qgen-1") == QuestionBatchRecord(
        question_batch_id="qb-req-qgen-1",
        workflow_run_id="run-req-qgen-1",
        project_id="proj-1",
        stage_id="stage-1",
        generated_by="question_generation_client",
        source="review_flow_service",
        batch_goal="freeze the minimal Question / Assessment / Decision boundary",
        entry_question_id="req-qgen-1-q-1",
        status="active",
        created_at="",
        payload={"question_count": 2, "request_id": "req-qgen-1"},
    )
    assert store.list_question_items("qb-req-qgen-1") == [
        QuestionItemRecord(
            question_id="req-qgen-1-q-1",
            question_batch_id="qb-req-qgen-1",
            question_type="core",
            prompt="Explain the current-stage boundary.",
            intent="Check current-stage understanding.",
            difficulty_level="core",
            order_index=0,
            status="ready",
            created_at="",
            payload={
                "expected_signals": ["Question, Assessment, Decision split"],
                "source_context": [],
                "transport_question_id": "set-1-q-1",
            },
        ),
        QuestionItemRecord(
            question_id="req-qgen-1-q-2",
            question_batch_id="qb-req-qgen-1",
            question_type="why",
            prompt="Why did we choose this boundary?",
            intent="Check reasoning about trade-offs.",
            difficulty_level="why",
            order_index=1,
            status="ready",
            created_at="",
            payload={
                "expected_signals": ["module vs interface"],
                "source_context": [],
                "transport_question_id": "set-1-q-2",
            },
        ),
    ]

    assert store.list_events(project_id="proj-1") == [
        WorkspaceEvent(
            event_id="evt-question-set-generated-00000001-req-qgen-1",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="",
            payload={
                "generation_index": 1,
                "stage_id": "stage-1",
                "question_set_id": "set-1",
                "question_batch_id": "qb-req-qgen-1",
                "workflow_run_id": "run-req-qgen-1",
                "question_item_ids": ["req-qgen-1-q-1", "req-qgen-1-q-2"],
            },
        )
    ]


def test_generate_question_set_skips_event_without_active_question_set(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    service = ReviewFlowService.with_store(store)
    original_get_stage_review = service._get_stage_review
    original_get_stage_definition = service._get_stage_definition
    service._get_stage_review = lambda project_id, stage_id: None  # type: ignore[method-assign]
    service._get_stage_definition = (  # type: ignore[method-assign]
        lambda project_id, stage_id: {
            **original_get_stage_definition(project_id, stage_id),
            "active_question_set_id": "",
        }
    )

    try:
        response = service.generate_question_set(
            {
                "request_id": "req-qgen-empty-set",
                "project_id": "proj-1",
                "stage_id": "stage-1",
                "stage_label": "module-interface-boundary",
                "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
                "stage_summary": "Task 4 adapter shell",
                "stage_artifacts": [],
                "stage_exit_criteria": [],
                "current_decisions": ["Question, Assessment, Decision split"],
                "key_logic_points": ["structured DTOs"],
                "known_weak_points": [],
                "boundary_focus": ["module vs interface"],
                "question_strategy": "core_and_why",
                "max_questions": 2,
                "source_refs": [],
            }
        )

        assert response["request_id"] == "req-qgen-empty-set"
        assert response["questions"]
        assert store.get_question_batch("qb-req-qgen-empty-set") is not None
        assert all(event.event_type != "question_set_generated" for event in store.list_events(project_id="proj-1"))
        assert store.list_question_items("qb-req-qgen-empty-set")[0].payload["transport_question_id"] == "q-1"
    finally:
        service._get_stage_review = original_get_stage_review  # type: ignore[method-assign]
        service._get_stage_definition = original_get_stage_definition  # type: ignore[method-assign]


def test_submit_answer_uses_current_question_context_and_user_excerpt() -> None:
    assessment_client = CapturingAssessmentClient.for_testing()
    service = ReviewFlowService(assessment_client=assessment_client)

    response = service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-02T12:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-2",
            answer_text="We split the boundary to keep state and scoring separate.",
            draft_id=None,
        )
    )

    assert response.success is True
    assert response.result_type == "assessment_created"
    assert response.assessment_summary is not None
    assert response.assessment_summary.answer_excerpt == "We split the boundary to keep state and scoring separate."
    assert response.message == "Assessment created with verdict partial."
    assert assessment_client.requests[0]["question_id"] == "set-1-q-2"
    assert assessment_client.requests[0]["question_set_id"] == "set-1"
    assert assessment_client.requests[0]["question_level"] == "why"
    assert assessment_client.requests[0]["question_prompt"] == "Why do we use this boundary for question set-1-q-2?"
    assert assessment_client.requests[0]["question_intent"] == "Check the reasoning behind the decision."
    assert assessment_client.requests[0]["expected_signals"] == ["stage-1", "set-1", "set-1-q-2", "why"]


def test_submit_answer_delegates_checkpoint_resolution_and_writes_but_keeps_legacy_facts(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    question_set = _semantic_question_set()
    store.upsert_question_set(question_set)
    assessment_client = CapturingAssessmentClient(
        assessment_override={
            "core_gaps": ["Need clearer boundary wording."],
            "dimension_scores": {
                "correctness": 3,
                "reasoning": 3,
                "decision_awareness": 2,
                "boundary_awareness": 1,
                "stability": 2,
            },
        }
    )
    service = ReviewFlowService(assessment_client=assessment_client, store=store)
    _insert_legacy_generated_chain(
        store=store,
        request_id="qgen-1",
        created_at="2026-04-10T11:00:00Z",
    )
    resolver = CapturingGeneratedChainResolver(
        ResolvedQuestionChain(
            workflow_run_id="run-qgen-1",
            question_batch_id="qb-qgen-1",
            question_item_id="qgen-1-q-1",
            transport_question_id="set-1-q-1",
            resolution_mode="reused",
        )
    )
    writer = CapturingAnswerCheckpointWriter(store=store)
    service._generated_chain_resolver = resolver
    service._answer_checkpoint_writer = writer

    response = service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-delegate-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-10T12:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="We split the boundary to keep state and scoring separate.",
            draft_id=None,
        )
    )

    assert response.success is True
    assert resolver.calls == [
        {
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "question_set_id": "set-1",
            "transport_question_id": "set-1-q-1",
            "request_id": "req-delegate-1",
            "created_at": "2026-04-10T12:00:00Z",
        }
    ]
    assert len(writer.calls) == 1
    assert writer.calls[0]["resolved_chain"] == resolver.resolved_chain
    assert writer.calls[0]["assessment"] == {
        "verdict": "partial",
        "score": 0.8,
        "summary": "Assessment verdict partial for set-1-q-1.",
        "gaps": ["Need clearer boundary wording."],
        "dimensions": ["decision_awareness", "boundary_awareness"],
    }
    assert store.get_workflow_request("req-delegate-1") == WorkflowRequestRecord(
        request_id="req-delegate-1",
        request_type="assessment",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="local-user",
        source="question_detail",
        status="completed",
        created_at="2026-04-10T12:00:00Z",
        payload={"request_id": "req-delegate-1"},
    )
    assert store.list_evidence_spans("ei-req-delegate-1-0") == [
        EvidenceSpanRecord(
            evidence_span_id="es-req-delegate-1-0",
            evaluation_item_id="ei-req-delegate-1-0",
            answer_item_id="ai-req-delegate-1-0",
            span_type="quoted_text",
            supports_dimension="assessment",
            content="assessment evidence: verdict=partial",
            start_offset=0,
            end_offset=len("assessment evidence: verdict=partial"),
            created_at="2026-04-10T12:00:00Z",
            payload={"evidence_index": 0},
        )
    ]
    answer_fact = store.get_answer_fact("answer-req-delegate-1")
    assessment_fact = store.get_assessment_fact("assessment-req-delegate-1")
    assert answer_fact is not None
    assert assessment_fact is not None


def test_submit_answer_reuses_existing_generated_question_batch(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    question_set = _semantic_question_set()
    store.upsert_question_set(question_set)
    service = ReviewFlowService(assessment_client=CapturingAssessmentClient.for_testing(), store=store)

    service.generate_question_set(
        {
            "request_id": "req-qgen-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
            "stage_summary": "Task 4 adapter shell",
            "stage_artifacts": [],
            "stage_exit_criteria": [],
            "current_decisions": ["Question, Assessment, Decision split"],
            "key_logic_points": ["structured DTOs"],
            "known_weak_points": [],
            "boundary_focus": ["module vs interface"],
            "question_strategy": "core_and_why",
            "max_questions": 2,
            "source_refs": [],
        }
    )

    response = service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-chain-existing-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-09T12:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="We split the boundary to keep state and scoring separate.",
            draft_id=None,
        )
    )

    assert response.success is True
    assert store.get_question_set("set-1") == question_set
    assert store.get_question_batch("qb-req-qgen-1") == QuestionBatchRecord(
        question_batch_id="qb-req-qgen-1",
        workflow_run_id="run-req-qgen-1",
        project_id="proj-1",
        stage_id="stage-1",
        generated_by="question_generation_client",
        source="review_flow_service",
        batch_goal="freeze the minimal Question / Assessment / Decision boundary",
        entry_question_id="req-qgen-1-q-1",
        status="active",
        created_at="",
        payload={"question_count": 2, "request_id": "req-qgen-1"},
    )
    assert store.get_workflow_request("req-chain-existing-1") == WorkflowRequestRecord(
        request_id="req-chain-existing-1",
        request_type="assessment",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="local-user",
        source="question_detail",
        status="completed",
        created_at="2026-04-09T12:00:00Z",
        payload={"request_id": "req-chain-existing-1"},
    )
    assert store.get_workflow_run("run-req-chain-existing-1") == WorkflowRunRecord(
        run_id="run-req-chain-existing-1",
        request_id="req-chain-existing-1",
        run_type="assessment",
        status="completed",
        started_at="2026-04-09T12:00:00Z",
        finished_at="2026-04-09T12:00:00Z",
        supersedes_run_id=None,
        payload={"request_id": "req-chain-existing-1"},
    )
    assert store.get_question_batch("qb-req-chain-existing-1") is None
    assert store.get_answer_batch("ab-req-chain-existing-1") == AnswerBatchRecord(
        answer_batch_id="ab-req-chain-existing-1",
        question_batch_id="qb-req-qgen-1",
        workflow_run_id="run-req-chain-existing-1",
        submitted_by="local-user",
        submission_mode="single_submit",
        completion_status="complete",
        submitted_at="2026-04-09T12:00:00Z",
        status="submitted",
        payload={
            "request_id": "req-chain-existing-1",
            "resolution_mode": "reused",
            "transport_question_id": "set-1-q-1",
        },
    )


def test_generate_question_set_normalizes_project_agent_output_and_persists_checkpoint(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    question_set = _semantic_question_set()
    store.upsert_question_set(question_set)
    service = ReviewFlowService(
        question_generation_client=RawProjectAgentQuestionGenerationClient(
            raw_content="""
            {
              "questions": [
                {
                  "id": "llm-q-1",
                  "prompt": "Why is the generation-side orchestration split valuable now?",
                  "intent": "Check migration reasoning.",
                  "difficulty": "intermediate",
                  "expected_signals": ["generation-side split"],
                  "source_context": ["project-agent"]
                }
              ],
              "generation_summary": "Generated 1 llm-backed question.",
              "coverage_notes": ["project-grounded", "interview-style"],
              "warnings": [],
              "confidence": 0.91
            }
            """
        ),
        project_agent_response_normalizer=ProjectAgentResponseNormalizer(),
        store=store,
    )

    response = service.generate_question_set(
        {
            "request_id": "req-qgen-llm-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "project-agent-llm-integration",
            "stage_goal": "switch generation to a real llm-backed project agent",
            "stage_summary": "first stable llm-backed generation path",
            "current_decisions": ["split generation-side orchestration"],
            "key_logic_points": ["checkpoint continuity"],
            "known_weak_points": ["output normalization"],
            "boundary_focus": ["project + interview question mix"],
            "question_strategy": "full_depth",
            "max_questions": 1,
            "source_refs": ["docs/spec.md"],
        }
    )

    assert response["request_id"] == "req-qgen-llm-1"
    assert response["generation_summary"] == "Generated 1 llm-backed question."
    assert response["questions"] == [
        {
            "question_id": "q-1",
            "question_level": "why",
            "prompt": "Why is the generation-side orchestration split valuable now?",
            "intent": "Check migration reasoning.",
            "expected_signals": ["generation-side split"],
            "source_context": ["project-agent"],
        }
    ]
    assert store.get_question_batch("qb-req-qgen-llm-1") is not None
    assert store.list_question_items("qb-req-qgen-llm-1")[0].payload["transport_question_id"] == "set-1-q-1"


def test_generate_question_set_preserves_mixed_levels_from_project_agent_quality_signals(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    question_set = _semantic_question_set()
    store.upsert_question_set(question_set)
    service = ReviewFlowService(
        question_generation_client=RawProjectAgentQuestionGenerationClient(
            raw_content="""
            {
              "questions": [
                {
                  "id": "fundamentals-1",
                  "category": "interview_fundamentals",
                  "difficulty": "basic",
                  "prompt": "What is the difference between append-only records and mutable current state?"
                },
                {
                  "id": "design-1",
                  "difficulty": "basic",
                  "prompt": "Why do we keep transport ids separate from durable ids in the checkpoint path?"
                },
                {
                  "id": "risk-1",
                  "category": "failure_mode",
                  "difficulty": "basic",
                  "prompt": "What migration risk appears if malformed LLM output reaches persisted checkpoint records?"
                }
              ],
              "generation_summary": "Generated 3 mixed questions.",
              "coverage_notes": ["project-grounded", "fundamentals", "failure-mode"],
              "warnings": [],
              "confidence": 0.93
            }
            """
        ),
        project_agent_response_normalizer=ProjectAgentResponseNormalizer(),
        store=store,
    )

    response = service.generate_question_set(
        {
            "request_id": "req-qgen-llm-quality-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "project-agent-quality-tuning",
            "stage_goal": "improve project grounding and level spread",
            "stage_summary": "quality regression for project agent output shaping",
            "current_decisions": ["keep checkpoint chain stable"],
            "key_logic_points": ["normalization before persistence"],
            "known_weak_points": ["level collapse"],
            "boundary_focus": ["project-grounded vs interview fundamentals", "risk escalation"],
            "question_strategy": "full_depth",
            "max_questions": 3,
            "source_refs": ["docs/spec.md"],
        }
    )

    assert [item["question_level"] for item in response["questions"]] == ["core", "why", "abstract"]
    assert [item.question_type for item in store.list_question_items("qb-req-qgen-llm-quality-1")] == [
        "core",
        "why",
        "abstract",
    ]


def test_generate_question_set_rejects_invalid_project_agent_output_before_checkpoint_write(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    store.upsert_question_set(_semantic_question_set())
    service = ReviewFlowService(
        question_generation_client=RawProjectAgentQuestionGenerationClient(raw_content="not-json"),
        project_agent_response_normalizer=ProjectAgentResponseNormalizer(),
        store=store,
    )

    with pytest.raises(ValueError, match="not valid JSON"):
        service.generate_question_set(
            {
                "request_id": "req-qgen-llm-bad",
                "project_id": "proj-1",
                "stage_id": "stage-1",
                "stage_label": "project-agent-llm-integration",
                "stage_goal": "switch generation to a real llm-backed project agent",
                "stage_summary": "first stable llm-backed generation path",
                "current_decisions": ["split generation-side orchestration"],
                "key_logic_points": ["checkpoint continuity"],
                "known_weak_points": ["output normalization"],
                "boundary_focus": ["project + interview question mix"],
                "question_strategy": "full_depth",
                "max_questions": 1,
                "source_refs": ["docs/spec.md"],
            }
        )

    assert store.get_workflow_request("req-qgen-llm-bad") is None
    assert store.get_question_batch("qb-req-qgen-llm-bad") is None


def test_submit_answer_reuses_newest_generated_question_batch_for_same_question_set(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    question_set = _semantic_question_set()
    store.upsert_question_set(question_set)
    service = ReviewFlowService(assessment_client=CapturingAssessmentClient.for_testing(), store=store)

    service.generate_question_set(
        {
            "request_id": "req-qgen-9",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
            "stage_summary": "Task 4 adapter shell",
            "stage_artifacts": [],
            "stage_exit_criteria": [],
            "current_decisions": ["Question, Assessment, Decision split"],
            "key_logic_points": ["structured DTOs"],
            "known_weak_points": [],
            "boundary_focus": ["module vs interface"],
            "question_strategy": "core_and_why",
            "max_questions": 2,
            "source_refs": [],
        }
    )
    service.generate_question_set(
        {
            "request_id": "req-qgen-10",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
            "stage_summary": "Task 4 adapter shell",
            "stage_artifacts": [],
            "stage_exit_criteria": [],
            "current_decisions": ["Question, Assessment, Decision split"],
            "key_logic_points": ["structured DTOs"],
            "known_weak_points": [],
            "boundary_focus": ["module vs interface"],
            "question_strategy": "core_and_why",
            "max_questions": 2,
            "source_refs": [],
        }
    )

    response = service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-chain-existing-2",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-09T13:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="We split the boundary to keep state and scoring separate.",
            draft_id=None,
        )
    )

    assert response.success is True
    assert store.get_question_set("set-1") == question_set
    assert store.get_answer_batch("ab-req-chain-existing-2") == AnswerBatchRecord(
        answer_batch_id="ab-req-chain-existing-2",
        question_batch_id="qb-req-qgen-10",
        workflow_run_id="run-req-chain-existing-2",
        submitted_by="local-user",
        submission_mode="single_submit",
        completion_status="complete",
        submitted_at="2026-04-09T13:00:00Z",
        status="submitted",
        payload={
            "request_id": "req-chain-existing-2",
            "resolution_mode": "reused",
            "transport_question_id": "set-1-q-1",
        },
    )
    assert store.list_answer_items("ab-req-chain-existing-2") == [
        AnswerItemRecord(
            answer_item_id="ai-req-chain-existing-2-0",
            answer_batch_id="ab-req-chain-existing-2",
            question_id="req-qgen-10-q-1",
            answered_by="local-user",
            answer_text="We split the boundary to keep state and scoring separate.",
            answer_format="plain_text",
            order_index=0,
            answered_at="2026-04-09T13:00:00Z",
            status="answered",
            revision_of_answer_item_id=None,
            payload={
                "request_id": "req-chain-existing-2",
                "transport_question_id": "set-1-q-1",
                "answer_excerpt": "We split the boundary to keep state and scoring separate.",
            },
        )
    ]
    assert store.get_evaluation_batch("eb-req-chain-existing-2") == EvaluationBatchRecord(
        evaluation_batch_id="eb-req-chain-existing-2",
        answer_batch_id="ab-req-chain-existing-2",
        workflow_run_id="run-req-chain-existing-2",
        project_id="proj-1",
        stage_id="stage-1",
        evaluated_by="assessment_agent",
        evaluator_version="review_flow_service:first-checkpoint",
        confidence=0.8,
        status="completed",
        evaluated_at="2026-04-09T13:00:00Z",
        supersedes_evaluation_batch_id=None,
        payload={
            "request_id": "req-chain-existing-2",
            "verdict": "partial",
            "score": 0.8,
            "summary": "Assessment verdict partial for set-1-q-1.",
        },
    )


def test_submit_answer_reuses_later_legacy_generated_batch_for_same_question_set(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    question_set = _semantic_question_set()
    store.upsert_question_set(question_set)
    service = ReviewFlowService(assessment_client=CapturingAssessmentClient.for_testing(), store=store)

    _insert_legacy_generated_chain(
        store=store,
        request_id="req-qgen-9",
        created_at="2026-04-09T12:00:00Z",
    )
    _insert_legacy_generated_chain(
        store=store,
        request_id="req-qgen-10",
        created_at="2026-04-09T12:05:00Z",
    )

    response = service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-chain-existing-legacy-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-09T13:30:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="We split the boundary to keep state and scoring separate.",
            draft_id=None,
        )
    )

    assert response.success is True
    assert store.get_question_set("set-1") == question_set
    assert store.get_answer_batch("ab-req-chain-existing-legacy-1") == AnswerBatchRecord(
        answer_batch_id="ab-req-chain-existing-legacy-1",
        question_batch_id="qb-req-qgen-10",
        workflow_run_id="run-req-chain-existing-legacy-1",
        submitted_by="local-user",
        submission_mode="single_submit",
        completion_status="complete",
        submitted_at="2026-04-09T13:30:00Z",
        status="submitted",
        payload={
            "request_id": "req-chain-existing-legacy-1",
            "resolution_mode": "reused",
            "transport_question_id": "set-1-q-1",
        },
    )
    assert store.list_answer_items("ab-req-chain-existing-legacy-1") == [
        AnswerItemRecord(
            answer_item_id="ai-req-chain-existing-legacy-1-0",
            answer_batch_id="ab-req-chain-existing-legacy-1",
            question_id="req-qgen-10-q-1",
            answered_by="local-user",
            answer_text="We split the boundary to keep state and scoring separate.",
            answer_format="plain_text",
            order_index=0,
            answered_at="2026-04-09T13:30:00Z",
            status="answered",
            revision_of_answer_item_id=None,
            payload={
                "request_id": "req-chain-existing-legacy-1",
                "transport_question_id": "set-1-q-1",
                "answer_excerpt": "We split the boundary to keep state and scoring separate.",
            },
        )
    ]
    assert store.get_evaluation_batch("eb-req-chain-existing-legacy-1") == EvaluationBatchRecord(
        evaluation_batch_id="eb-req-chain-existing-legacy-1",
        answer_batch_id="ab-req-chain-existing-legacy-1",
        workflow_run_id="run-req-chain-existing-legacy-1",
        project_id="proj-1",
        stage_id="stage-1",
        evaluated_by="assessment_agent",
        evaluator_version="review_flow_service:first-checkpoint",
        confidence=0.8,
        status="completed",
        evaluated_at="2026-04-09T13:30:00Z",
        supersedes_evaluation_batch_id=None,
        payload={
            "request_id": "req-chain-existing-legacy-1",
            "verdict": "partial",
            "score": 0.8,
            "summary": "Assessment verdict partial for set-1-q-1.",
        },
    )


def test_submit_answer_reuses_later_legacy_batch_over_older_indexed_batch(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    question_set = _semantic_question_set()
    store.upsert_question_set(question_set)
    service = ReviewFlowService(assessment_client=CapturingAssessmentClient.for_testing(), store=store)

    service.generate_question_set(
        {
            "request_id": "req-qgen-indexed-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "module-interface-boundary",
            "stage_goal": "freeze the minimal Question / Assessment / Decision boundary",
            "stage_summary": "Task 4 adapter shell",
            "stage_artifacts": [],
            "stage_exit_criteria": [],
            "current_decisions": ["Question, Assessment, Decision split"],
            "key_logic_points": ["structured DTOs"],
            "known_weak_points": [],
            "boundary_focus": ["module vs interface"],
            "question_strategy": "core_and_why",
            "max_questions": 2,
            "source_refs": [],
        }
    )
    _insert_legacy_generated_chain(
        store=store,
        request_id="req-qgen-legacy-later-1",
        created_at="2026-04-10T10:00:00Z",
    )

    response = service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-chain-mixed-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-10T10:30:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="We split the boundary to keep state and scoring separate.",
            draft_id=None,
        )
    )

    assert response.success is True
    assert store.get_question_set("set-1") == question_set
    assert store.get_answer_batch("ab-req-chain-mixed-1") == AnswerBatchRecord(
        answer_batch_id="ab-req-chain-mixed-1",
        question_batch_id="qb-req-qgen-legacy-later-1",
        workflow_run_id="run-req-chain-mixed-1",
        submitted_by="local-user",
        submission_mode="single_submit",
        completion_status="complete",
        submitted_at="2026-04-10T10:30:00Z",
        status="submitted",
        payload={
            "request_id": "req-chain-mixed-1",
            "resolution_mode": "reused",
            "transport_question_id": "set-1-q-1",
        },
    )
    assert store.list_answer_items("ab-req-chain-mixed-1") == [
        AnswerItemRecord(
            answer_item_id="ai-req-chain-mixed-1-0",
            answer_batch_id="ab-req-chain-mixed-1",
            question_id="req-qgen-legacy-later-1-q-1",
            answered_by="local-user",
            answer_text="We split the boundary to keep state and scoring separate.",
            answer_format="plain_text",
            order_index=0,
            answered_at="2026-04-10T10:30:00Z",
            status="answered",
            revision_of_answer_item_id=None,
            payload={
                "request_id": "req-chain-mixed-1",
                "transport_question_id": "set-1-q-1",
                "answer_excerpt": "We split the boundary to keep state and scoring separate.",
            },
        )
    ]
    assert store.get_evaluation_batch("eb-req-chain-mixed-1") == EvaluationBatchRecord(
        evaluation_batch_id="eb-req-chain-mixed-1",
        answer_batch_id="ab-req-chain-mixed-1",
        workflow_run_id="run-req-chain-mixed-1",
        project_id="proj-1",
        stage_id="stage-1",
        evaluated_by="assessment_agent",
        evaluator_version="review_flow_service:first-checkpoint",
        confidence=0.8,
        status="completed",
        evaluated_at="2026-04-10T10:30:00Z",
        supersedes_evaluation_batch_id=None,
        payload={
            "request_id": "req-chain-mixed-1",
            "verdict": "partial",
            "score": 0.8,
            "summary": "Assessment verdict partial for set-1-q-1.",
        },
    )


def test_submit_answer_persists_first_checkpoint_chain_without_prior_generation(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    question_set = _semantic_question_set()
    store.upsert_question_set(question_set)
    service = ReviewFlowService(assessment_client=CapturingAssessmentClient.for_testing(), store=store)

    response = service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-chain-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-09T12:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="We split the boundary to keep state and scoring separate.",
            draft_id=None,
        )
    )

    assert response.success is True
    assert store.get_question_set("set-1") == question_set
    assert store.get_workflow_request("req-chain-1") == WorkflowRequestRecord(
        request_id="req-chain-1",
        request_type="assessment",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="local-user",
        source="question_detail",
        status="completed",
        created_at="2026-04-09T12:00:00Z",
        payload={"request_id": "req-chain-1"},
    )
    assert store.get_workflow_run("run-req-chain-1") == WorkflowRunRecord(
        run_id="run-req-chain-1",
        request_id="req-chain-1",
        run_type="assessment",
        status="completed",
        started_at="2026-04-09T12:00:00Z",
        finished_at="2026-04-09T12:00:00Z",
        supersedes_run_id=None,
        payload={"request_id": "req-chain-1"},
    )
    assert store.get_question_batch("qb-req-chain-1") == QuestionBatchRecord(
        question_batch_id="qb-req-chain-1",
        workflow_run_id="run-req-chain-1",
        project_id="proj-1",
        stage_id="stage-1",
        generated_by="answer_checkpoint_writer",
        source="question_detail",
        batch_goal="materialize fallback submit-side question chain",
        entry_question_id="req-chain-1-set-1-q-1",
        status="active",
        created_at="2026-04-09T12:00:00Z",
        payload={
            "request_id": "req-chain-1",
            "resolution_mode": "fallback",
            "transport_question_id": "set-1-q-1",
        },
    )
    assert store.list_question_items("qb-req-chain-1") == [
        QuestionItemRecord(
            question_id="req-chain-1-set-1-q-1",
            question_batch_id="qb-req-chain-1",
            question_type="core",
            prompt="Fallback question for set-1-q-1.",
            intent="Preserve submit-side checkpoint continuity.",
            difficulty_level="core",
            order_index=0,
            status="ready",
            created_at="2026-04-09T12:00:00Z",
            payload={
                "request_id": "req-chain-1",
                "resolution_mode": "fallback",
                "transport_question_id": "set-1-q-1",
            },
        )
    ]
    assert store.get_answer_batch("ab-req-chain-1") == AnswerBatchRecord(
        answer_batch_id="ab-req-chain-1",
        question_batch_id="qb-req-chain-1",
        workflow_run_id="run-req-chain-1",
        submitted_by="local-user",
        submission_mode="single_submit",
        completion_status="complete",
        submitted_at="2026-04-09T12:00:00Z",
        status="submitted",
        payload={
            "request_id": "req-chain-1",
            "resolution_mode": "fallback",
            "transport_question_id": "set-1-q-1",
        },
    )
    assert store.list_answer_items("ab-req-chain-1") == [
        AnswerItemRecord(
            answer_item_id="ai-req-chain-1-0",
            answer_batch_id="ab-req-chain-1",
            question_id="req-chain-1-set-1-q-1",
            answered_by="local-user",
            answer_text="We split the boundary to keep state and scoring separate.",
            answer_format="plain_text",
            order_index=0,
            answered_at="2026-04-09T12:00:00Z",
            status="answered",
            revision_of_answer_item_id=None,
            payload={
                "request_id": "req-chain-1",
                "transport_question_id": "set-1-q-1",
                "answer_excerpt": "We split the boundary to keep state and scoring separate.",
            },
        )
    ]
    assert store.get_evaluation_batch("eb-req-chain-1") == EvaluationBatchRecord(
        evaluation_batch_id="eb-req-chain-1",
        answer_batch_id="ab-req-chain-1",
        workflow_run_id="run-req-chain-1",
        project_id="proj-1",
        stage_id="stage-1",
        evaluated_by="assessment_agent",
        evaluator_version="review_flow_service:first-checkpoint",
        confidence=0.8,
        status="completed",
        evaluated_at="2026-04-09T12:00:00Z",
        supersedes_evaluation_batch_id=None,
        payload={
            "request_id": "req-chain-1",
            "verdict": "partial",
            "score": 0.8,
            "summary": "Assessment verdict partial for set-1-q-1.",
        },
    )
    assert store.get_latest_assessment_fact_batch("proj-1", "stage-1") == AssessmentFactBatchRecord(
        assessment_fact_batch_id="afb-eb-req-chain-1",
        evaluation_batch_id="eb-req-chain-1",
        workflow_run_id="run-req-chain-1",
        synthesized_by="assessment_synthesizer",
        synthesizer_version="first-checkpoint-v1",
        status="completed",
        synthesized_at="2026-04-09T12:00:00Z",
        supersedes_assessment_fact_batch_id=None,
        payload={"item_count": 0},
    )
    assert store.list_assessment_fact_items("afb-eb-req-chain-1") == []
    assert store.list_evidence_spans("ei-req-chain-1-0") == [
        EvidenceSpanRecord(
            evidence_span_id="es-req-chain-1-0",
            evaluation_item_id="ei-req-chain-1-0",
            answer_item_id="ai-req-chain-1-0",
            span_type="quoted_text",
            supports_dimension="assessment",
            content="assessment evidence: verdict=partial",
            start_offset=0,
            end_offset=len("assessment evidence: verdict=partial"),
            created_at="2026-04-09T12:00:00Z",
            payload={"evidence_index": 0},
        )
    ]


def test_submit_answer_does_not_promote_mastery_on_weak_assessment() -> None:
    service = ReviewFlowService(assessment_client=WeakAssessmentClient.for_testing())

    response = service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-weak",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-02T12:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="short answer",
            draft_id=None,
        )
    )

    assert response.success is True
    assert response.result_type == "assessment_created"
    assert service.get_stage_view("proj-1", "stage-1").mastery_status == "unverified"



def test_submit_answer_persists_facts_and_recovers_mastery_after_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "review.sqlite3"
    store = SQLiteStore(db_path)
    store.initialize()
    first_service = ReviewFlowService(assessment_client=CapturingAssessmentClient.for_testing(), store=store)

    submit_response = first_service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-persist-1",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-08T12:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="This answer is long enough to avoid the weak fallback verdict.",
            draft_id=None,
        )
    )

    assert submit_response.success is True
    assert first_service.get_latest_assessment_snapshot("proj-1", "stage-1") is not None

    second_service = ReviewFlowService.with_store(SQLiteStore(db_path))
    stage_view = second_service.get_stage_view("proj-1", "stage-1")

    assert stage_view.mastery_status == "partially_verified"
    assert second_service.get_latest_assessment_snapshot("proj-1", "stage-1") is not None
def test_submit_answer_rejects_blank_answer_text() -> None:
    service = ReviewFlowService.for_testing()

    response = service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-blank",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-02T12:00:00Z",
            question_set_id="set-1",
            question_id="q-1",
            answer_text="   ",
            draft_id=None,
        )
    )

    assert response.success is False
    assert response.result_type == "invalid_input"
    assert response.assessment_summary is None


def test_submit_answer_derives_support_signals_from_support_basis_tags() -> None:
    service = ReviewFlowService(
        assessment_client=CapturingAssessmentClient(
            assessment_override={
                "core_gaps": ["Review flow control"],
                "support_basis_tags": [
                    {
                        "basis_key": "state_modeling",
                        "source_label": "State machine",
                        "source_node_type": "foundation",
                        "target_label": "Review flow control",
                        "target_node_type": "concept",
                    }
                ],
            }
        )
    )

    service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-support-basis",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-09T10:00:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="This answer is long enough to produce a structured assessment.",
            draft_id=None,
        )
    )

    snapshot = service.get_latest_assessment_snapshot("proj-1", "stage-1")

    assert snapshot is not None
    assert snapshot["support_basis_tags"][0]["basis_key"] == "state_modeling"
    assert snapshot["support_signals"] == [
        {
            "source_label": "State machine",
            "source_node_type": "foundation",
            "target_label": "Review flow control",
            "target_node_type": "concept",
            "basis_type": "support_basis_tag",
            "basis_key": "state_modeling",
        }
    ]


def test_submit_answer_derives_support_signals_from_dimension_hits_and_core_gaps() -> None:
    service = ReviewFlowService(
        assessment_client=CapturingAssessmentClient(
            assessment_override={
                "core_gaps": ["API boundary discipline"],
                "dimension_scores": {
                    "correctness": 3,
                    "reasoning": 3,
                    "decision_awareness": 3,
                    "boundary_awareness": 1,
                    "stability": 2,
                },
            }
        )
    )

    service.submit_answer(
        SubmitAnswerRequest(
            request_id="req-dimension-support",
            project_id="proj-1",
            stage_id="stage-1",
            source_page="question_detail",
            actor_id="local-user",
            created_at="2026-04-09T10:05:00Z",
            question_set_id="set-1",
            question_id="set-1-q-1",
            answer_text="This answer is long enough to produce a structured assessment.",
            draft_id=None,
        )
    )

    snapshot = service.get_latest_assessment_snapshot("proj-1", "stage-1")

    assert snapshot is not None
    assert "boundary_awareness" in snapshot["dimension_hits"]
    assert snapshot["support_signals"] == [
        {
            "source_label": "Boundary discipline",
            "source_node_type": "foundation",
            "target_label": "API boundary discipline",
            "target_node_type": "method",
            "basis_type": "dimension_hit",
            "basis_key": "boundary_awareness",
        }
    ]



