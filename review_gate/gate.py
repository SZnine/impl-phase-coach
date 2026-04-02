from __future__ import annotations

from .models import (
    ReviewAssessment,
    ReviewMode,
    ReviewPassState,
    ReviewQuestion,
    ReviewRequest,
    ReviewSession,
    ReviewSessionStatus,
    new_question_id,
    new_session_id,
)


class ReviewGate:
    """Entry point for minimal review-mode sessions."""

    def start_session(self, request: ReviewRequest) -> ReviewSession:
        return ReviewSession(
            session_id=new_session_id(),
            stage_id=request.stage_id,
            mode=request.mode,
            status=ReviewSessionStatus.IN_PROGRESS,
            assessment=ReviewAssessment(
                pass_state=None,
                confidence=0.0,
                failure_reason=None,
                allow_next_stage=False,
                recommend_learning=False,
            ),
        )

    def record_answer(self, session: ReviewSession, answer: str) -> ReviewSession:
        session.answers.append(answer)
        normalized = answer.lower()

        if self._looks_missing_foundation(normalized):
            session.status = ReviewSessionStatus.REDIRECTED_TO_LEARNING
            session.assessment = ReviewAssessment(
                pass_state=ReviewPassState.REDIRECT_TO_LEARNING,
                confidence=0.2,
                core_gaps=['高压下无法稳定解释当前阶段内核', '状态语义（state semantics）边界不稳定'],
                failure_reason='无法清楚解释当前阶段内核或关键决策边界',
                allow_next_stage=False,
                recommend_learning=True,
                learning_recommendations=self._build_learning_recommendations(session.stage_id),
            )
            return session

        if self._looks_stable_enough(normalized, answer):
            session.status = ReviewSessionStatus.PASSED
            session.assessment = ReviewAssessment(
                pass_state=ReviewPassState.PASS,
                confidence=0.8,
                core_gaps=[],
                failure_reason=None,
                allow_next_stage=True,
                recommend_learning=False,
            )
            return session

        session.status = ReviewSessionStatus.NEEDS_FOLLOW_UP
        session.assessment = ReviewAssessment(
            pass_state=ReviewPassState.CONTINUE_PROBING,
            confidence=0.5,
            core_gaps=['解释还停留在口号层，没有稳定展开到阶段目标、边界和退出条件'],
            failure_reason='回答体现出局部识别，但还没有稳定输出能力',
            allow_next_stage=False,
            recommend_learning=False,
        )
        session.questions.append(self._build_follow_up_question(session))
        return session

    def export_session_record(self, session: ReviewSession) -> dict[str, object]:
        return {
            'session_id': session.session_id,
            'stage_id': session.stage_id,
            'mode': session.mode.value,
            'status': session.status.value,
            'pass_state': session.assessment.pass_state.value if session.assessment.pass_state else None,
            'confidence': session.assessment.confidence,
            'core_gaps': list(session.assessment.core_gaps),
            'failure_reason': session.assessment.failure_reason,
            'allow_next_stage': session.assessment.allow_next_stage,
            'recommend_learning': session.assessment.recommend_learning,
            'learning_recommendations': list(session.assessment.learning_recommendations),
            'questions': [
                {
                    'question_id': question.question_id,
                    'question_type': question.question_type,
                    'prompt': question.prompt,
                    'severity': question.severity,
                }
                for question in session.questions
            ],
            'answers': list(session.answers),
        }

    @staticmethod
    def _looks_missing_foundation(normalized: str) -> bool:
        markers = [
            "i don't know",
            'i do not know',
            'cannot explain',
            "can't explain",
            'not understand',
            '不知道',
            '讲不清',
            '说不清',
            '无法解释',
            '解释不清',
            '我也不懂',
        ]
        return any(marker in normalized for marker in markers)

    @staticmethod
    def _looks_stable_enough(normalized: str, raw: str) -> bool:
        unstable_markers = [
            'not sure',
            'still cannot',
            'cannot defend',
            'cannot explain',
            'sort of',
            '不确定',
            '说不清',
            '讲不清',
            '无法解释',
            '不能证明',
            '不太清楚',
            '还是不清楚',
            '有点懂',
        ]
        if any(marker in normalized for marker in unstable_markers):
            return False

        has_reasoning = any(token in normalized for token in ['because', 'why', '因为', '所以', '因此'])
        has_contrast = any(
            token in normalized
            for token in ['instead', 'rather than', 'not', '而不是', '而非', '不是新的', '不是单独', '不要把', '不应', '本质上']
        )
        return has_reasoning and has_contrast and len(raw.strip()) >= 40

    @staticmethod
    def _build_follow_up_question(session: ReviewSession) -> ReviewQuestion:
        if session.mode is ReviewMode.DEEP:
            return ReviewQuestion(
                question_id=new_question_id(),
                question_type='defend-stage-boundary',
                prompt=(
                    f'请直接论证为什么 {session.stage_id} 仍然应该留在当前阶段，'
                    '并说明那个最容易被误判的替代阶段为什么不成立。'
                ),
                severity='intense',
            )
        return ReviewQuestion(
            question_id=new_question_id(),
            question_type='restate-stage-core',
            prompt=(
                f'请不用口号，重新说明 {session.stage_id} 的阶段目标、阶段产物和退出条件。'
            ),
            severity='standard',
        )

    @staticmethod
    def _build_learning_recommendations(stage_id: str) -> list[str]:
        return [
            f'先重建 {stage_id} 相关的状态语义（state semantics），再回到返回分支或阶段判断。',
            '用两个具体例子比较 DENIED 和 FAILED，要求你能口头解释边界，而不是只会记结论。',
        ]
