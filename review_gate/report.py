from __future__ import annotations

from html import escape
from pathlib import Path

from .models import KnowledgeEntry, ReviewAssessment, ReviewPassState, ReviewReport, ReviewSummaryCard

_TEMPLATE_PATH = Path(__file__).with_name('ui').joinpath('review_result.html')


def build_review_report(
    *, stage_id: str, assessment: ReviewAssessment, last_answer: str
) -> ReviewReport:
    pass_state = assessment.pass_state or ReviewPassState.CONTINUE_PROBING
    headline = _build_headline(pass_state)
    next_step = _build_next_step(pass_state)

    summary_card = ReviewSummaryCard(
        stage_id=stage_id,
        pass_state=pass_state,
        headline=headline,
        next_step=next_step,
    )
    expanded_report = _build_expanded_report(assessment, last_answer)
    return ReviewReport(summary_card=summary_card, expanded_report=expanded_report)


def render_review_html(
    report: ReviewReport,
    *,
    session_record: dict[str, object] | None = None,
    knowledge_entries: list[KnowledgeEntry] | None = None,
) -> str:
    template = _TEMPLATE_PATH.read_text(encoding='utf-8-sig')
    summary_html = (
        f'<h1>{escape(report.summary_card.headline)}</h1>'
        f'<p><strong>当前阶段：</strong> {escape(report.summary_card.stage_id)}</p>'
        f'<p><strong>当前判定：</strong> {escape(_pass_state_label(report.summary_card.pass_state))}</p>'
        f'<p>{escape(report.summary_card.next_step)}</p>'
    )
    expanded_html = ''.join(
        f'<p>{escape(line)}</p>' for line in report.expanded_report.splitlines() if line.strip()
    )
    follow_up_html = _build_follow_up_html(session_record)
    learning_html = _build_learning_html(session_record)
    knowledge_html = _build_knowledge_html(knowledge_entries or [])
    return (
        template.replace('{{SUMMARY_CARD}}', summary_html)
        .replace('{{EXPANDED_REPORT}}', expanded_html)
        .replace('{{FOLLOW_UP_SECTION}}', follow_up_html)
        .replace('{{LEARNING_SECTION}}', learning_html)
        .replace('{{KNOWLEDGE_SECTION}}', knowledge_html)
    )


def _build_headline(pass_state: ReviewPassState) -> str:
    if pass_state is ReviewPassState.PASS:
        return '当前阶段理解已经稳定，可以进入下一步。'
    if pass_state is ReviewPassState.REDIRECT_TO_LEARNING:
        return '当前存在核心理解缺口，暂时不能继续推进。'
    return '当前阶段理解还不稳定，需要继续追问。'


def _build_next_step(pass_state: ReviewPassState) -> str:
    if pass_state is ReviewPassState.PASS:
        return '可以进入下一阶段。'
    if pass_state is ReviewPassState.REDIRECT_TO_LEARNING:
        return '先暂停推进，先补学习建议里指出的缺口。'
    return '继续在当前阶段内追问。'


def _build_expanded_report(assessment: ReviewAssessment, last_answer: str) -> str:
    gaps = '、'.join(assessment.core_gaps) if assessment.core_gaps else '无'
    reason = assessment.failure_reason or '无'
    lines = [
        f'最近一次回答：{last_answer}',
        f'当前判定：{_pass_state_label(assessment.pass_state)}',
        f'核心缺口：{gaps}',
        f'失败原因：{reason}',
        f'是否建议补学习：{_bool_label(assessment.recommend_learning)}',
    ]
    if assessment.learning_recommendations:
        lines.append('学习建议：')
        lines.extend(f'- {item}' for item in assessment.learning_recommendations)
    return '\n'.join(lines)


def _build_follow_up_html(session_record: dict[str, object] | None) -> str:
    questions = [] if not session_record else session_record.get('questions', [])
    items = []
    for question in questions:
        if isinstance(question, dict):
            qtype = escape(str(question.get('question_type', 'unknown')))
            prompt = escape(str(question.get('prompt', '')))
            severity = _severity_label(str(question.get('severity', 'unknown')))
            items.append(f'<li><strong>{qtype}</strong>（{escape(severity)}）<br />{prompt}</li>')
    body = '<p>当前没有记录到追问问题。</p>' if not items else f'<ul>{"".join(items)}</ul>'
    return f'<section id="follow-up-section"><h3>追问问题</h3>{body}</section>'


def _build_learning_html(session_record: dict[str, object] | None) -> str:
    recommendations = [] if not session_record else session_record.get('learning_recommendations', [])
    items = [f'<li>{escape(str(item))}</li>' for item in recommendations]
    body = '<p>当前没有记录到学习建议。</p>' if not items else f'<ul>{"".join(items)}</ul>'
    return f'<section id="learning-section"><h3>学习建议</h3>{body}</section>'


def _build_knowledge_html(entries: list[KnowledgeEntry]) -> str:
    items = [
        f'<li><strong>{escape(entry.entry_type.value)}</strong>：{escape(entry.summary)}</li>'
        for entry in entries
    ]
    body = '<p>当前没有记录到知识沉淀条目。</p>' if not items else f'<ul>{"".join(items)}</ul>'
    return f'<section id="knowledge-section"><h3>知识沉淀摘要</h3>{body}</section>'


def _pass_state_label(pass_state: ReviewPassState | None) -> str:
    if pass_state is ReviewPassState.PASS:
        return '通过（pass）'
    if pass_state is ReviewPassState.REDIRECT_TO_LEARNING:
        return '转学习建议（redirect_to_learning）'
    if pass_state is ReviewPassState.CONTINUE_PROBING:
        return '继续追问（continue_probing）'
    return '未知（unknown）'


def _bool_label(flag: bool) -> str:
    return '是' if flag else '否'


def _severity_label(value: str) -> str:
    if value == 'intense':
        return '高压'
    if value == 'standard':
        return '标准'
    return value
