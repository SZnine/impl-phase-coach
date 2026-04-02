from review_gate.gate import ReviewGate
from review_gate.models import (
    ReviewMode,
    ReviewPassState,
    ReviewRequest,
    ReviewSessionStatus,
)


def test_start_session_creates_pending_review_session() -> None:
    gate = ReviewGate()
    request = ReviewRequest(
        stage_id="stage-1",
        stage_summary="Freeze review module boundaries",
        candidate_answer="I think I understand the stage goals.",
        mode=ReviewMode.SIMPLE,
        trigger_reason="looks_understood_but_cannot_output",
    )

    session = gate.start_session(request)

    assert session.stage_id == "stage-1"
    assert session.mode is ReviewMode.SIMPLE
    assert session.status is ReviewSessionStatus.IN_PROGRESS
    assert session.questions == []
    assert session.answers == []
    assert session.assessment.pass_state is None



def test_record_answer_adds_simple_follow_up_question_for_partial_answer() -> None:
    gate = ReviewGate()
    session = gate.start_session(
        ReviewRequest(
            stage_id="stage-2",
            stage_summary="Explain why denied differs from failed",
            candidate_answer="I sort of get it.",
            mode=ReviewMode.SIMPLE,
            trigger_reason="looks_understood_but_cannot_output",
        )
    )

    updated = gate.record_answer(
        session,
        "DENIED and FAILED are different, but I am not sure how to explain why.",
    )

    assert updated.status is ReviewSessionStatus.NEEDS_FOLLOW_UP
    assert updated.assessment.pass_state is ReviewPassState.CONTINUE_PROBING
    assert updated.assessment.allow_next_stage is False
    assert updated.answers[-1].startswith("DENIED and FAILED")
    assert updated.questions[-1].severity == "standard"
    assert updated.questions[-1].question_type == "restate-stage-core"



def test_record_answer_adds_deep_follow_up_question_for_partial_answer() -> None:
    gate = ReviewGate()
    session = gate.start_session(
        ReviewRequest(
            stage_id="stage-2",
            stage_summary="Defend why denied should not collapse into failed",
            candidate_answer="Need deeper review",
            mode=ReviewMode.DEEP,
            trigger_reason="review_requested",
        )
    )

    updated = gate.record_answer(
        session,
        "They are not the same, but I still cannot defend the boundary in detail.",
    )

    assert updated.status is ReviewSessionStatus.NEEDS_FOLLOW_UP
    assert updated.assessment.pass_state is ReviewPassState.CONTINUE_PROBING
    assert updated.questions[-1].severity == "intense"
    assert updated.questions[-1].question_type == "defend-stage-boundary"



def test_record_answer_redirects_to_learning_with_explicit_recommendations() -> None:
    gate = ReviewGate()
    session = gate.start_session(
        ReviewRequest(
            stage_id="stage-2",
            stage_summary="Explain stage boundary and state semantics",
            candidate_answer="Need review",
            mode=ReviewMode.DEEP,
            trigger_reason="review_requested",
        )
    )

    updated = gate.record_answer(
        session,
        "I don't know. I cannot explain the difference or why the stage is designed this way.",
    )

    assert updated.status is ReviewSessionStatus.REDIRECTED_TO_LEARNING
    assert updated.assessment.pass_state is ReviewPassState.REDIRECT_TO_LEARNING
    assert updated.assessment.recommend_learning is True
    assert updated.assessment.allow_next_stage is False
    assert updated.assessment.learning_recommendations
    assert "state semantics" in updated.assessment.learning_recommendations[0].lower()



def test_record_answer_passes_for_real_chinese_boundary_explanation() -> None:
    gate = ReviewGate()
    session = gate.start_session(
        ReviewRequest(
            stage_id="stage-2",
            stage_summary="Explain why stage-internal feedback should remain a subphase",
            candidate_answer="需要中文试跑",
            mode=ReviewMode.DEEP,
            trigger_reason="chinese_live_trial",
        )
    )

    updated = gate.record_answer(
        session,
        "我发现有时候容易把阶段内的子反馈测试，调试优化当作一个新的阶段，使得阶段这个概念边界不稳，因此，要明确阶段的边界，如果用户给出了当前阶段的疑惑或者测试反馈想要得到建议或者帮助，不要把这一项列为单独的项目阶段，因为他本质上更像是阶段内的衍生子阶段。",
    )

    assert updated.status is ReviewSessionStatus.PASSED
    assert updated.assessment.pass_state is ReviewPassState.PASS
    assert updated.assessment.allow_next_stage is True
