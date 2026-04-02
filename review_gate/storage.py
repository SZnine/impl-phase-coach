from __future__ import annotations

import json
from pathlib import Path

from .models import KnowledgeEntry, ReviewReport


def build_review_snapshot(
    *, session_record: dict[str, object], report: ReviewReport, entries: list[KnowledgeEntry]
) -> dict[str, object]:
    return {
        'schema_version': 1,
        'human_summary': _build_human_summary(session_record, entries),
        'session': dict(session_record),
        'report': {
            'summary_card': {
                'stage_id': report.summary_card.stage_id,
                'pass_state': report.summary_card.pass_state.value,
                'headline': report.summary_card.headline,
                'next_step': report.summary_card.next_step,
            },
            'expanded_report': report.expanded_report,
        },
        'knowledge_entries': [
            {
                'entry_id': entry.entry_id,
                'entry_type': entry.entry_type.value,
                'stage_id': entry.stage_id,
                'summary': entry.summary,
                'root_cause': entry.root_cause,
                'avoidance': entry.avoidance,
                'evidence': list(entry.evidence),
                'learning_recommendations': list(entry.learning_recommendations),
            }
            for entry in entries
        ],
    }


def write_review_snapshot(*, target: Path, snapshot: dict[str, object]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def _build_human_summary(
    session_record: dict[str, object], entries: list[KnowledgeEntry]
) -> str:
    stage_id = str(session_record.get('stage_id', 'unknown-stage'))
    status = str(session_record.get('status', 'unknown-status'))
    questions = session_record.get('questions', [])
    question_count = len(questions) if isinstance(questions, list) else 0
    entry_count = len(entries)
    return (
        f'{stage_id} 当前状态为 {status}，包含 {question_count} 个追问问题，'
        f'沉淀了 {entry_count} 个知识条目。'
    )
