import json

from review_gate.gate import ReviewGate
from review_gate.memory import extract_entries
from review_gate.models import ReviewAssessment, ReviewMode, ReviewPassState, ReviewRequest
from review_gate.report import build_review_report, render_review_html
from review_gate.storage import build_review_snapshot, write_review_snapshot


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



def test_build_review_snapshot_returns_stable_local_schema() -> None:
    gate = ReviewGate()
    session = gate.start_session(
        ReviewRequest(
            stage_id="stage-6",
            stage_summary="Connect interactive report and local review archive",
            candidate_answer="I think I understand it.",
            mode=ReviewMode.DEEP,
            trigger_reason="auto_review_suggestion",
        )
    )
    session = gate.record_answer(
        session,
        "I don't know. I cannot explain the stage boundary or the state semantics clearly.",
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

    snapshot = build_review_snapshot(
        session_record=gate.export_session_record(session),
        report=report,
        entries=entries,
    )

    assert snapshot["schema_version"] == 1
    assert snapshot["session"]["stage_id"] == "stage-6"
    assert snapshot["report"]["summary_card"]["pass_state"] == "redirect_to_learning"
    assert snapshot["session"]["learning_recommendations"]
    assert snapshot["knowledge_entries"][0]["learning_recommendations"]



def test_build_review_snapshot_includes_human_summary() -> None:
    gate = ReviewGate()
    session = gate.start_session(
        ReviewRequest(
            stage_id="stage-7",
            stage_summary="Make the recap output easier for humans to scan",
            candidate_answer="Need review",
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

    snapshot = build_review_snapshot(
        session_record=gate.export_session_record(session),
        report=report,
        entries=entries,
    )

    assert snapshot["human_summary"]
    assert "stage-7" in snapshot["human_summary"].lower()
    assert "needs_follow_up" in snapshot["human_summary"]
    assert "1 个追问问题" in snapshot["human_summary"]



def test_write_review_snapshot_writes_json_file(tmp_path) -> None:
    payload = {
        "schema_version": 1,
        "human_summary": "stage-6 当前需要继续处理",
        "session": {"session_id": "review-1", "learning_recommendations": ["学习状态语义"]},
        "report": {"summary_card": {"stage_id": "stage-6"}, "expanded_report": "ok"},
        "knowledge_entries": [{"entry_id": "err-1", "learning_recommendations": ["学习状态语义"]}],
    }

    target = tmp_path / "review-session.json"
    write_review_snapshot(target=target, snapshot=payload)

    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == payload
