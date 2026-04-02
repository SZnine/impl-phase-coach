from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from review_gate import ReviewMode, ReviewRequest, run_review_workflow


answer = (
    "我发现有时候容易把阶段内的子反馈测试，调试优化当作一个新的阶段，使得阶段这个概念边界不稳，因此，要明确阶段的边界，如果用户给出了当前阶段的疑惑或者测试反馈想要得到建议或者帮助，不要把这一项列为单独的项目阶段，因为他本质上更像是阶段内的衍生子阶段。"
)

request = ReviewRequest(
    stage_id="stage-boundary-review",
    stage_summary="论证为什么阶段内反馈应留在当前阶段内处理，而不是升格成新的主阶段。",
    candidate_answer="使用当前对话做中文真实试跑。",
    mode=ReviewMode.DEEP,
    trigger_reason="live_project_trial_from_current_conversation",
)

artifact_dir = ROOT / "artifacts" / "review-gate-live-trial-cn"
artifact_dir.mkdir(parents=True, exist_ok=True)
snapshot_target = artifact_dir / "current-dialogue-snapshot.json"
html_target = artifact_dir / "current-dialogue-report.html"

result = run_review_workflow(
    request=request,
    answer=answer,
    snapshot_target=snapshot_target,
)
html_target.write_text(result.html, encoding="utf-8")

print("SNAPSHOT=" + str(snapshot_target.resolve()))
print("HTML=" + str(html_target.resolve()))
print("STATUS=" + result.session.status.value)
print("PASS_STATE=" + str(result.session.assessment.pass_state.value if result.session.assessment.pass_state else None))
print("ALLOW_NEXT_STAGE=" + str(result.session.assessment.allow_next_stage))
print("RECOMMEND_LEARNING=" + str(result.session.assessment.recommend_learning))
print("QUESTIONS=" + str(len(result.session.questions)))
print("KNOWLEDGE_ENTRIES=" + str(len(result.knowledge_entries)))
print("HUMAN_SUMMARY=" + result.snapshot["human_summary"])
if result.session.questions:
    q = result.session.questions[-1]
    print("FOLLOW_UP_TYPE=" + q.question_type)
    print("FOLLOW_UP_SEVERITY=" + q.severity)
    print("FOLLOW_UP_PROMPT=" + q.prompt)
