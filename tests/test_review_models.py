from review_gate.models import (
    KnowledgeEntry,
    KnowledgeEntryType,
    ReviewAssessment,
    ReviewPassState,
    ReviewReport,
    ReviewSummaryCard,
)
from review_gate.report import build_review_report



def test_knowledge_entry_captures_error_pattern_payload() -> None:
    assessment = ReviewAssessment(
        pass_state=ReviewPassState.REDIRECT_TO_LEARNING,
        confidence=0.35,
        core_gaps=["state semantics"],
        failure_reason="cannot explain denied vs failed under pressure",
        allow_next_stage=False,
        recommend_learning=True,
        learning_recommendations=["先重建 state semantics，再回到返回分支设计。"],
    )

    entry = KnowledgeEntry(
        entry_id="entry-1",
        entry_type=KnowledgeEntryType.ERROR_PATTERN,
        stage_id="stage-2",
        summary="Confuses DENIED with FAILED",
        root_cause="State semantics not internalized",
        avoidance="Explain state boundary before coding return values",
        evidence=["expected DENIED, actual FAILED"],
        source_assessment=assessment,
    )

    assert entry.entry_type is KnowledgeEntryType.ERROR_PATTERN
    assert entry.source_assessment.failure_reason == (
        "cannot explain denied vs failed under pressure"
    )



def test_build_review_report_returns_summary_card_and_expanded_report() -> None:
    assessment = ReviewAssessment(
        pass_state=ReviewPassState.CONTINUE_PROBING,
        confidence=0.55,
        core_gaps=["cannot compare denied vs failed clearly"],
        failure_reason="answer stays at slogan level",
        allow_next_stage=False,
        recommend_learning=False,
    )

    report = build_review_report(
        stage_id="stage-2",
        assessment=assessment,
        last_answer="They are different but I cannot explain the boundary clearly.",
    )

    assert isinstance(report, ReviewReport)
    assert isinstance(report.summary_card, ReviewSummaryCard)
    assert report.summary_card.pass_state is ReviewPassState.CONTINUE_PROBING
    assert "核心缺口：cannot compare denied vs failed clearly" in report.expanded_report



def test_build_review_report_includes_learning_recommendations() -> None:
    assessment = ReviewAssessment(
        pass_state=ReviewPassState.REDIRECT_TO_LEARNING,
        confidence=0.25,
        core_gaps=["state semantics"],
        failure_reason="cannot explain denied vs failed under pressure",
        allow_next_stage=False,
        recommend_learning=True,
        learning_recommendations=[
            "先重建 state semantics，再回到返回分支设计。",
            "用两个具体例子比较 DENIED 和 FAILED。",
        ],
    )

    report = build_review_report(
        stage_id="stage-2",
        assessment=assessment,
        last_answer="I cannot defend the state boundary under pressure.",
    )

    assert "学习建议：" in report.expanded_report
    assert "先重建 state semantics，再回到返回分支设计。" in report.expanded_report
