from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import ReviewMode, ReviewPassState, ReviewRequest
from .workflow import ReviewWorkflowResult, run_review_workflow


@dataclass(slots=True)
class JointTrialScenario:
    user_request: str
    main_skill_stage: str
    main_skill_goal: str
    main_skill_deliverable: str
    main_skill_exit: str
    review_reason: str
    review_stage_id: str
    review_stage_summary: str
    candidate_answer: str
    answer: str
    review_mode: ReviewMode = ReviewMode.DEEP


@dataclass(slots=True)
class JointTrialResult:
    workflow_result: ReviewWorkflowResult
    summary: dict[str, object]
    visualization: str
    html: str
    snapshot_path: Path
    html_path: Path
    summary_path: Path
    visualization_path: Path


def run_joint_main_skill_trial(*, scenario: JointTrialScenario, artifact_dir: Path) -> JointTrialResult:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = artifact_dir / 'joint-trial-snapshot.json'
    html_path = artifact_dir / 'joint-trial-report.html'
    summary_path = artifact_dir / 'joint-trial-summary.json'
    visualization_path = artifact_dir / 'joint-trial-visualization.md'

    workflow_result = run_review_workflow(
        request=ReviewRequest(
            stage_id=scenario.review_stage_id,
            stage_summary=scenario.review_stage_summary,
            candidate_answer=scenario.candidate_answer,
            mode=scenario.review_mode,
            trigger_reason='joint_main_skill_trial',
        ),
        answer=scenario.answer,
        snapshot_target=snapshot_path,
    )

    html_path.write_text(workflow_result.html, encoding='utf-8')
    summary = _build_summary(scenario=scenario, workflow_result=workflow_result, snapshot_path=snapshot_path, html_path=html_path, visualization_path=visualization_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    visualization = _build_visualization(scenario=scenario, summary=summary)
    visualization_path.write_text(visualization, encoding='utf-8')

    return JointTrialResult(
        workflow_result=workflow_result,
        summary=summary,
        visualization=visualization,
        html=workflow_result.html,
        snapshot_path=snapshot_path,
        html_path=html_path,
        summary_path=summary_path,
        visualization_path=visualization_path,
    )


def _build_summary(
    *,
    scenario: JointTrialScenario,
    workflow_result: ReviewWorkflowResult,
    snapshot_path: Path,
    html_path: Path,
    visualization_path: Path,
) -> dict[str, object]:
    assessment = workflow_result.session.assessment
    pass_state = assessment.pass_state.value if assessment.pass_state else None
    status = workflow_result.session.status.value
    return {
        'scenario': '主 skill 在阶段内建议进入 review_gate，随后把结果回流主流程。',
        'user_request': scenario.user_request,
        'main_skill_stage': scenario.main_skill_stage,
        'main_skill_goal': scenario.main_skill_goal,
        'main_skill_deliverable': scenario.main_skill_deliverable,
        'main_skill_exit': scenario.main_skill_exit,
        'review_reason': scenario.review_reason,
        'review_mode': scenario.review_mode.value,
        'main_flow_decision': _main_flow_decision(assessment.pass_state),
        'review_result': {
            'status': status,
            'pass_state': pass_state,
            'allow_next_stage': assessment.allow_next_stage,
            'recommend_learning': assessment.recommend_learning,
            'question_count': len(workflow_result.session.questions),
            'knowledge_entry_count': len(workflow_result.knowledge_entries),
            'human_summary': workflow_result.snapshot['human_summary'],
        },
        'artifacts': {
            'snapshot': str(snapshot_path.resolve()),
            'html': str(html_path.resolve()),
            'visualization': str(visualization_path.resolve()),
        },
    }


def _build_visualization(*, scenario: JointTrialScenario, summary: dict[str, object]) -> str:
    review_result = summary['review_result']
    return """# 联合试跑可视化

## 场景

- 用户请求：{user_request}
- 当前主阶段：{main_skill_stage}
- 当前主阶段目标：{main_skill_goal}
- 当前主阶段产物：{main_skill_deliverable}
- 当前主阶段退出条件：{main_skill_exit}
- 建议复盘原因：{review_reason}
- 复盘模式：{review_mode}

## 主流程判断树

```text
主阶段：{main_skill_stage}
└─ 用户担心自己只是看懂，还没真的掌握
   └─ 主 skill 建议进入 review_gate
      └─ 用户选择：{review_mode}
         └─ review_gate 返回：{pass_state}
            └─ 主流程回流：{main_flow_decision}
```

## 流程图

```mermaid
flowchart TD
    A[主阶段：{main_skill_stage}] --> B[用户表达理解可能不稳]
    B --> C[主 skill 给出复盘建议]
    C --> D[用户选择：{review_mode}]
    D --> E[review_gate 结果：{pass_state}]
    E --> F[主流程回流：{main_flow_decision}]
```

## 复盘结果

- review status：`{status}`
- pass state：`{pass_state}`
- allow next stage：`{allow_next_stage}`
- recommend learning：`{recommend_learning}`
- question count：`{question_count}`
- knowledge entry count：`{knowledge_entry_count}`
- human summary：{human_summary}

## 本次回答样本

> {answer}
""".format(
        user_request=scenario.user_request,
        main_skill_stage=scenario.main_skill_stage,
        main_skill_goal=scenario.main_skill_goal,
        main_skill_deliverable=scenario.main_skill_deliverable,
        main_skill_exit=scenario.main_skill_exit,
        review_reason=scenario.review_reason,
        review_mode=_mode_label(scenario.review_mode),
        pass_state=_pass_state_label(summary['review_result']['pass_state']),
        main_flow_decision=summary['main_flow_decision'],
        status=review_result['status'],
        allow_next_stage=review_result['allow_next_stage'],
        recommend_learning=review_result['recommend_learning'],
        question_count=review_result['question_count'],
        knowledge_entry_count=review_result['knowledge_entry_count'],
        human_summary=review_result['human_summary'],
        answer=scenario.answer,
    )


def _main_flow_decision(pass_state: ReviewPassState | None) -> str:
    if pass_state is ReviewPassState.PASS:
        return '允许建议进入下一阶段'
    if pass_state is ReviewPassState.REDIRECT_TO_LEARNING:
        return '留在当前阶段，优先转学习建议'
    if pass_state is ReviewPassState.CONTINUE_PROBING:
        return '留在当前阶段，继续追问或纠偏'
    return '留在当前阶段，等待进一步判断'


def _pass_state_label(pass_state: str | None) -> str:
    if pass_state == ReviewPassState.PASS.value:
        return '通过（pass）'
    if pass_state == ReviewPassState.REDIRECT_TO_LEARNING.value:
        return '转学习建议（redirect_to_learning）'
    if pass_state == ReviewPassState.CONTINUE_PROBING.value:
        return '继续追问（continue_probing）'
    return '未知（unknown）'


def _mode_label(mode: ReviewMode) -> str:
    if mode is ReviewMode.DEEP:
        return '深入复盘'
    return '简单复盘'
