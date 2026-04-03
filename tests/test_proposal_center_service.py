from pathlib import Path

from review_gate.proposal_center_service import ProposalCenterService
from review_gate.storage_sqlite import SQLiteStore


def test_proposal_center_service_records_user_action_and_execution() -> None:
    service = ProposalCenterService.for_testing()

    proposal = service.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
    )[0]
    action = service.record_user_action(
        proposal_id=proposal["proposal_id"],
        action_type="accept",
        selected_target_ids=["m-1", "m-2"],
    )
    execution = service.execute_proposal(
        proposal_id=proposal["proposal_id"],
        action_id=action["action_id"],
    )

    assert proposal["proposal_type"] == "compress_mistake_entries"
    assert action["action_type"] == "accept"
    assert execution["status"] == "succeeded"
    assert execution["proposal_id"] == proposal["proposal_id"]
    assert execution["action_id"] == action["action_id"]


def test_proposal_center_service_lists_created_proposals() -> None:
    service = ProposalCenterService.for_testing()
    service.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
    )

    proposals = service.list_proposals()

    assert len(proposals) == 1
    assert proposals[0]["proposal_type"] == "compress_mistake_entries"
    assert proposals[0]["target_ids"] == ["m-1", "m-2"]
    assert proposals[0]["status"] == "pending_review"


def test_proposal_center_service_updates_proposal_status_after_accept() -> None:
    service = ProposalCenterService.for_testing()
    proposal = service.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
    )[0]
    action = service.record_user_action(
        proposal_id=proposal["proposal_id"],
        action_type="accept",
        selected_target_ids=[],
    )

    execution = service.execute_proposal(proposal["proposal_id"], action["action_id"])
    refreshed = service.get_proposal(proposal["proposal_id"])

    assert execution["proposal_status"] == "accepted"
    assert refreshed["status"] == "accepted"
    assert refreshed["latest_execution_status"] == "succeeded"
    assert refreshed["latest_execution_summary"] == "accept on proposal-1 => succeeded"


def test_proposal_center_service_reject_keeps_applied_targets_empty() -> None:
    service = ProposalCenterService.for_testing()

    proposal = service.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
    )[0]
    action = service.record_user_action(
        proposal_id=proposal["proposal_id"],
        action_type="reject",
        selected_target_ids=["m-1", "m-2"],
    )
    execution = service.execute_proposal(
        proposal_id=proposal["proposal_id"],
        action_id=action["action_id"],
    )

    assert execution["status"] == "cancelled"
    assert execution["proposal_status"] == "rejected"
    assert execution["applied_target_ids"] == []
    assert execution["unchanged_target_ids"] == ["m-1", "m-2"]


def test_proposal_center_service_rejects_mismatched_action_proposal_pair() -> None:
    service = ProposalCenterService.for_testing()

    proposal_one = service.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1"],
    )[0]
    proposal_two = service.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-2"],
    )[0]
    action = service.record_user_action(
        proposal_id=proposal_one["proposal_id"],
        action_type="accept",
        selected_target_ids=["m-1"],
    )

    execution = service.execute_proposal(
        proposal_id=proposal_two["proposal_id"],
        action_id=action["action_id"],
    )

    assert execution["status"] == "failed"
    assert execution["applied_target_ids"] == []
    assert execution["error_message"] == "Action does not belong to the proposal."


def test_proposal_center_service_with_store_round_trips_records_between_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "proposal-center.sqlite3"
    store = SQLiteStore(db_path)
    store.initialize()

    writer = ProposalCenterService.with_store(store)
    proposal = writer.create_compression_proposals(
        target_type="mistake_entries",
        target_ids=["m-1", "m-2"],
        project_id="proj-1",
        stage_id="stage-1",
    )[0]
    action = writer.record_user_action(
        proposal_id=proposal["proposal_id"],
        action_type="defer",
        selected_target_ids=[],
    )
    execution = writer.execute_proposal(proposal["proposal_id"], action["action_id"])

    reader = ProposalCenterService.with_store(store)
    proposals = reader.list_proposals(project_id="proj-1", stage_id="stage-1")
    refreshed = reader.get_proposal(proposal["proposal_id"])

    assert execution["status"] == "cancelled"
    assert execution["proposal_status"] == "deferred"
    assert proposals[0]["proposal_id"] == proposal["proposal_id"]
    assert refreshed["status"] == "deferred"
    assert refreshed["latest_execution_status"] == "cancelled"
    assert refreshed["latest_execution_summary"] == "defer on proposal-1 => cancelled"
