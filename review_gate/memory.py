from __future__ import annotations

from .models import (
    KnowledgeEntry,
    KnowledgeEntryType,
    ReviewAssessment,
    ReviewPassState,
    new_entry_id,
)


def extract_entries(
    *, stage_id: str, assessment: ReviewAssessment, last_answer: str
) -> list[KnowledgeEntry]:
    gaps = '、'.join(assessment.core_gaps) if assessment.core_gaps else '没有显式记录缺口'
    reason = assessment.failure_reason or '没有显式失败原因'
    learning_recommendations = _unique_recommendations(assessment.learning_recommendations)

    error_pattern = KnowledgeEntry(
        entry_id=new_entry_id('err'),
        entry_type=KnowledgeEntryType.ERROR_PATTERN,
        stage_id=stage_id,
        summary=gaps,
        root_cause=reason,
        avoidance=_build_avoidance(stage_id, assessment),
        evidence=[last_answer],
        learning_recommendations=list(learning_recommendations),
        source_assessment=assessment,
    )
    capability_profile = KnowledgeEntry(
        entry_id=new_entry_id('cap'),
        entry_type=KnowledgeEntryType.CAPABILITY_PROFILE,
        stage_id=stage_id,
        summary=_build_capability_summary(assessment),
        root_cause=reason,
        avoidance='进入下一步前，先重新核对阶段输出结构、状态语义和退出条件。',
        evidence=[last_answer],
        learning_recommendations=list(learning_recommendations),
        source_assessment=assessment,
    )
    return [error_pattern, capability_profile]


def _build_avoidance(stage_id: str, assessment: ReviewAssessment) -> str:
    if assessment.pass_state is ReviewPassState.REDIRECT_TO_LEARNING:
        return f'先暂停 {stage_id} 的推进，补齐缺失概念后再回来复盘。'
    return f'继续留在 {stage_id}，强制把阶段目标、边界和退出条件讲清楚后再放行。'


def _build_capability_summary(assessment: ReviewAssessment) -> str:
    if assessment.pass_state is ReviewPassState.PASS:
        return '当前阶段解释在追问下仍然稳定。'
    if assessment.pass_state is ReviewPassState.REDIRECT_TO_LEARNING:
        return '当前阶段解释在高压下坍塌，需先补学习。'
    return '当前阶段理解仍然局部化，还需要继续追问。'


def _unique_recommendations(recommendations: list[str]) -> list[str]:
    unique: list[str] = []
    for item in recommendations:
        if item not in unique:
            unique.append(item)
    return unique
