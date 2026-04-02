from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from review_gate import ReviewMode
from review_gate.joint_trial import JointTrialScenario, run_joint_main_skill_trial


scenario = JointTrialScenario(
    user_request="可以，模拟一次吧，并将模拟过程结果可视化呈现给我。",
    main_skill_stage="阶段 5 / 验收与阶段复盘",
    main_skill_goal="判断当前是否真的可以从验收阶段进入下一阶段，而不是只会复述结论。",
    main_skill_deliverable="复盘建议、复盘结果，以及复盘结果回流主流程后的结论。",
    main_skill_exit="只有复盘结果为 pass 时，主流程才会建议进入下一阶段。",
    review_reason="用户准备前进，但明确担心自己可能只是看懂，还没有真正掌握。",
    review_stage_id="stage-5-acceptance-freeze",
    review_stage_summary="验证当前阶段冻结是否成立，并检查理解是否能承受深入追问。",
    candidate_answer="使用联合模拟验证主 skill 与 review_gate 的回流关系。",
    answer=(
        "当前阶段之所以可以冻结，是因为阶段边界、模块边界和退出条件已经成立；"
        "如果复盘发现我只能重复结论而不能解释为什么不是别的阶段，就不应该放行，"
        "所以这里要先验证理解是否能在追问下保持稳定，而不是直接跳到下一阶段。"
    ),
    review_mode=ReviewMode.DEEP,
)

artifact_dir = ROOT / "artifacts" / "joint-main-skill-trial"
result = run_joint_main_skill_trial(scenario=scenario, artifact_dir=artifact_dir)

print("SNAPSHOT=" + str(result.snapshot_path.resolve()))
print("HTML=" + str(result.html_path.resolve()))
print("SUMMARY=" + str(result.summary_path.resolve()))
print("VISUALIZATION=" + str(result.visualization_path.resolve()))
print("STATUS=" + result.workflow_result.session.status.value)
print(
    "PASS_STATE="
    + str(
        result.workflow_result.session.assessment.pass_state.value
        if result.workflow_result.session.assessment.pass_state
        else None
    )
)
print("MAIN_FLOW_DECISION=" + str(result.summary["main_flow_decision"]))
print("QUESTION_COUNT=" + str(len(result.workflow_result.session.questions)))
print("KNOWLEDGE_ENTRIES=" + str(len(result.workflow_result.knowledge_entries)))
print("HUMAN_SUMMARY=" + str(result.summary["review_result"]["human_summary"]))
