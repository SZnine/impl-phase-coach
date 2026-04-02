import json

from review_gate import ReviewMode
from review_gate.joint_trial import JointTrialScenario, run_joint_main_skill_trial


def test_run_joint_main_skill_trial_writes_utf8_artifacts(tmp_path) -> None:
    scenario = JointTrialScenario(
        user_request="我觉得已经理解了，但担心自己只是跟着走，还没有真的掌握。",
        main_skill_stage="阶段 5 / 验收与阶段复盘",
        main_skill_goal="验证当前阶段是否真的可以放行，而不是只会重复结论。",
        main_skill_deliverable="复盘建议与主流程回流结论。",
        main_skill_exit="只有复盘通过时才建议进入下一阶段。",
        review_reason="用户准备进入下一阶段，但主动表达了理解不稳。",
        review_stage_id="stage-5-acceptance-freeze",
        review_stage_summary="验证当前阶段冻结是否成立，并确认理解是否能承受追问。",
        candidate_answer="使用联合模拟验证主 skill 和 review_gate 的回流关系。",
        answer=(
            "当前阶段之所以可以冻结，是因为阶段边界、模块边界和退出条件已经成立；"
            "如果复盘发现我只能重复结论而不能解释为什么不是别的阶段，就不应该放行，"
            "所以这里要先验证理解是否能在追问下保持稳定，而不是直接跳到下一阶段。"
        ),
        review_mode=ReviewMode.DEEP,
    )

    result = run_joint_main_skill_trial(scenario=scenario, artifact_dir=tmp_path)

    assert result.summary["review_result"]["pass_state"] == "pass"
    assert result.summary["main_flow_decision"] == "允许建议进入下一阶段"
    assert result.visualization_path.exists()
    assert result.html_path.exists()
    assert result.snapshot_path.exists()
    assert "联合试跑可视化" in result.visualization
    assert "阶段 5 / 验收与阶段复盘" in result.visualization
    assert "当前阶段之所以可以冻结" in result.html

    loaded_summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert loaded_summary["main_skill_stage"] == "阶段 5 / 验收与阶段复盘"
    assert loaded_summary["review_result"]["human_summary"]
