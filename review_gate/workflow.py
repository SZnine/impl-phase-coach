from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .gate import ReviewGate
from .memory import extract_entries
from .models import KnowledgeEntry, ReviewReport, ReviewRequest, ReviewSession
from .report import build_review_report, render_review_html
from .storage import build_review_snapshot, write_review_snapshot


@dataclass(slots=True)
class ReviewWorkflowResult:
    session: ReviewSession
    report: ReviewReport
    knowledge_entries: list[KnowledgeEntry]
    html: str
    snapshot: dict[str, object]
    snapshot_target: Path | None


def run_review_workflow(
    *, request: ReviewRequest, answer: str, snapshot_target: Path | None = None
) -> ReviewWorkflowResult:
    gate = ReviewGate()
    session = gate.start_session(request)
    session = gate.record_answer(session, answer)
    session_record = gate.export_session_record(session)
    report = build_review_report(
        stage_id=session.stage_id,
        assessment=session.assessment,
        last_answer=session.answers[-1],
    )
    knowledge_entries = extract_entries(
        stage_id=session.stage_id,
        assessment=session.assessment,
        last_answer=session.answers[-1],
    )
    html = render_review_html(
        report,
        session_record=session_record,
        knowledge_entries=knowledge_entries,
    )
    snapshot = build_review_snapshot(
        session_record=session_record,
        report=report,
        entries=knowledge_entries,
    )
    if snapshot_target is not None:
        write_review_snapshot(target=snapshot_target, snapshot=snapshot)

    return ReviewWorkflowResult(
        session=session,
        report=report,
        knowledge_entries=knowledge_entries,
        html=html,
        snapshot=snapshot,
        snapshot_target=snapshot_target,
    )
