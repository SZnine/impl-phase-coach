import json

from review_gate.models import ReviewMode, ReviewRequest
from review_gate.workflow import run_review_workflow



def test_run_review_workflow_returns_all_primary_artifacts(tmp_path) -> None:
    request = ReviewRequest(
        stage_id="stage-10",
        stage_summary="Expose a single project-facing review entrypoint",
        candidate_answer="Need review",
        mode=ReviewMode.DEEP,
        trigger_reason="project_entrypoint",
    )

    result = run_review_workflow(
        request=request,
        answer="They are not the same, but I still cannot defend the boundary in detail.",
        snapshot_target=tmp_path / "review-output.json",
    )

    assert result.session.stage_id == "stage-10"
    assert result.report.summary_card.stage_id == "stage-10"
    assert result.html
    assert result.snapshot["human_summary"]
    assert len(result.knowledge_entries) == 2
    assert result.snapshot_target == tmp_path / "review-output.json"
    assert result.snapshot_target.exists()



def test_run_review_workflow_writes_snapshot_payload_to_target(tmp_path) -> None:
    target = tmp_path / "review-output.json"
    request = ReviewRequest(
        stage_id="stage-10",
        stage_summary="Expose a single project-facing review entrypoint",
        candidate_answer="Need review",
        mode=ReviewMode.DEEP,
        trigger_reason="project_entrypoint",
    )

    result = run_review_workflow(
        request=request,
        answer="I don't know. I cannot explain the stage boundary or the state semantics clearly.",
        snapshot_target=target,
    )

    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == result.snapshot
    assert loaded["session"]["stage_id"] == "stage-10"
    assert loaded["report"]["summary_card"]["pass_state"] == "redirect_to_learning"
