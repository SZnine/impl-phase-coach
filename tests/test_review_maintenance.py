from review_gate.maintenance import create_maintenance_task, plan_compaction, run_maintenance_task
from review_gate.memory import extract_entries
from review_gate.models import (
    CompactionMode,
    MaintenanceTaskStatus,
    ReviewAssessment,
    ReviewPassState,
)


def _build_duplicate_entries():
    assessment = ReviewAssessment(
        pass_state=ReviewPassState.CONTINUE_PROBING,
        confidence=0.45,
        core_gaps=["stage boundary explanation is unstable"],
        failure_reason="answer stays at slogan level",
        allow_next_stage=False,
        recommend_learning=True,
        learning_recommendations=[
            "Restate the phase boundary once.",
            "Restate the phase boundary once.",
        ],
    )
    entries = extract_entries(
        stage_id="stage-5",
        assessment=assessment,
        last_answer="I get it, but I cannot defend why this stays in stage 5.",
    )
    return entries + entries


def test_create_maintenance_task_builds_pending_task() -> None:
    duplicates = _build_duplicate_entries()

    task = create_maintenance_task(mode=CompactionMode.LIGHT, entries=duplicates)

    assert task.mode is CompactionMode.LIGHT
    assert task.status is MaintenanceTaskStatus.PENDING
    assert task.source_entry_count == len(duplicates)



def test_plan_compaction_marks_duplicates_for_light_merge() -> None:
    duplicates = _build_duplicate_entries()

    plan = plan_compaction(duplicates, mode=CompactionMode.LIGHT)

    assert plan.mode is CompactionMode.LIGHT
    assert plan.candidate_entry_ids
    assert plan.requires_manual_review is False
    assert plan.strategy_summary == "light merge duplicate stage knowledge entries"



def test_run_maintenance_task_executes_light_compaction() -> None:
    duplicates = _build_duplicate_entries()

    execution = run_maintenance_task(duplicates, mode=CompactionMode.LIGHT)

    assert execution.task.status is MaintenanceTaskStatus.COMPLETED
    assert execution.plan.mode is CompactionMode.LIGHT
    assert len(execution.result.entries) == 2
    assert execution.result.compression_reason == "merged duplicate stage knowledge entries"
    assert execution.result.entries[0].learning_recommendations == ["Restate the phase boundary once."]
