from review_gate.gate import ReviewGate
from review_gate.memory import extract_entries
from review_gate.models import (
    ReviewAssessment,
    ReviewMode,
    ReviewPassState,
    ReviewRequest,
)
from review_gate.report import build_review_report, render_review_html



def test_render_review_html_includes_summary_and_expand_toggle() -> None:
    report = build_review_report(
        stage_id="stage-2",
        assessment=ReviewAssessment(
            pass_state=ReviewPassState.CONTINUE_PROBING,
            confidence=0.55,
            core_gaps=["cannot compare denied vs failed clearly"],
            failure_reason="answer stays at slogan level",
            allow_next_stage=False,
            recommend_learning=False,
        ),
        last_answer="They are different but I cannot explain the boundary clearly.",
    )

    html = render_review_html(report)

    assert '<section id="summary-card">' in html
    assert '继续在当前阶段内追问。' in html
    assert 'id="toggle-report"' in html
    assert 'aria-controls="coach-report"' in html
    assert '<section id="coach-report" hidden>' in html
    assert '当前阶段理解还不稳定，需要继续追问。' in html



def test_render_review_html_embeds_toggle_script() -> None:
    report = build_review_report(
        stage_id="stage-4",
        assessment=ReviewAssessment(
            pass_state=ReviewPassState.REDIRECT_TO_LEARNING,
            confidence=0.2,
            core_gaps=["cannot defend core state boundary"],
            failure_reason="answer collapses under reframing",
            allow_next_stage=False,
            recommend_learning=True,
        ),
        last_answer="I understand it, but I cannot explain why under pressure.",
    )

    html = render_review_html(report)

    assert 'function toggleCoachReport()' in html
    assert '展开完整复盘' in html
    assert '收起完整复盘' in html



def test_render_review_html_groups_followup_learning_and_knowledge_sections() -> None:
    gate = ReviewGate()
    session = gate.start_session(
        ReviewRequest(
            stage_id="stage-7",
            stage_summary="Probe whether the user can defend the phase boundary under pressure",
            candidate_answer="Need deeper review",
            mode=ReviewMode.DEEP,
            trigger_reason="review_requested",
        )
    )
    session = gate.record_answer(
        session,
        "They are not the same, but I still cannot defend the boundary in detail.",
    )
    report = build_review_report(
        stage_id=session.stage_id,
        assessment=session.assessment,
        last_answer=session.answers[-1],
    )
    entries = extract_entries(
        stage_id=session.stage_id,
        assessment=session.assessment,
        last_answer=session.answers[-1],
    )

    html = render_review_html(
        report,
        session_record=gate.export_session_record(session),
        knowledge_entries=entries,
    )

    assert '追问问题' in html
    assert '学习建议' in html
    assert '知识沉淀摘要' in html
    assert 'defend-stage-boundary' in html
    assert '当前阶段理解仍然局部化，还需要继续追问。' in html



def test_export_session_record_returns_minimal_local_trace_payload() -> None:
    gate = ReviewGate()
    session = gate.start_session(
        ReviewRequest(
            stage_id="stage-5",
            stage_summary="Freeze whether the current phase can be released",
            candidate_answer="I think it is ready.",
            mode=ReviewMode.SIMPLE,
            trigger_reason="post_stage_review",
        )
    )
    session = gate.record_answer(
        session,
        "Because the current phase has explicit exit criteria and stable boundaries, it should stay here instead of dropping to another phase.",
    )

    payload = gate.export_session_record(session)

    assert payload["session_id"].startswith("review-")
    assert payload["stage_id"] == "stage-5"
    assert payload["status"] == "passed"
    assert payload["pass_state"] == "pass"
    assert payload["answers"]
    assert isinstance(payload["core_gaps"], list)
