from review_gate.action_dtos import SubmitAnswerRequest
from review_gate.review_flow_service import ReviewFlowService
from review_gate.storage_sqlite import SQLiteStore
from pathlib import Path


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



