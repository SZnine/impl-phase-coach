from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from review_gate.domain import (
    ProfileSpace,
    ProjectReview,
    ProposalCenter,
    QuestionSet,
    StageReview,
    WorkspaceEvent,
    WorkspaceSession,
)
from review_gate.storage_sqlite import SQLiteStore
from review_gate.workspace_state_store import JsonWorkspaceStateStore


def test_domain_objects_round_trip_via_json() -> None:
    question_set = QuestionSet(
        question_set_id="set-1",
        stage_review_id="stage-review-1",
        title="core questions",
        question_ids=["q-1", "q-2"],
        active_question_id="q-1",
    )
    stage_review = StageReview(
        stage_review_id="stage-review-1",
        project_id="proj-1",
        stage_id="stage-1",
        stage_label="module interface freeze",
        stage_goal="keep the boundary stable",
        status="in_progress",
        question_set_ids=[question_set.question_set_id],
        active_question_set_id=question_set.question_set_id,
        related_mistake_ids=["mistake-1"],
        related_knowledge_node_ids=["node-1"],
        related_index_entry_ids=["index-1"],
        related_proposal_ids=["proposal-1"],
    )
    project = ProjectReview(
        project_id="proj-1",
        project_label="impl-phase-coach",
        project_summary="review workbench MVP",
        stage_reviews=[stage_review],
        knowledge_index_id="index-space-1",
        knowledge_graph_id="graph-1",
        profile_space_id="profile-1",
        proposal_center_id="proposal-center-1",
    )
    profile_space = ProfileSpace(
        profile_space_id="profile-1",
        project_id="proj-1",
        label="default",
        mistake_ids=["mistake-1"],
        index_entry_ids=["index-1"],
        knowledge_node_ids=["node-1"],
        proposal_ids=["proposal-1"],
    )
    event = WorkspaceEvent(
        event_id="event-1",
        project_id="proj-1",
        event_type="project_created",
        created_at="2026-04-02T12:00:00Z",
        payload={"project_label": "impl-phase-coach"},
    )

    assert ProjectReview.from_json(project.to_json()) == project
    assert StageReview.from_json(stage_review.to_json()) == stage_review
    assert QuestionSet.from_json(question_set.to_json()) == question_set
    assert ProfileSpace.from_json(profile_space.to_json()) == profile_space
    assert WorkspaceEvent.from_json(event.to_json()) == event


def test_sqlite_store_initializes_and_round_trips_core_records(tmp_path: Path) -> None:
    db_path = tmp_path / "review.sqlite3"
    store = SQLiteStore(db_path)
    store.initialize()

    with sqlite3.connect(db_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        }

    assert {"event_store", "profile_store", "project_store"}.issubset(table_names)

    project = ProjectReview(
        project_id="proj-1",
        project_label="impl-phase-coach",
        project_summary="review workbench MVP",
        stage_reviews=[
            StageReview(
                stage_review_id="stage-review-1",
                project_id="proj-1",
                stage_id="stage-1",
                stage_label="module interface freeze",
                stage_goal="keep the boundary stable",
                status="in_progress",
                question_set_ids=["set-1"],
                active_question_set_id="set-1",
            )
        ],
        knowledge_index_id="index-space-1",
        knowledge_graph_id="graph-1",
        profile_space_id="profile-1",
        proposal_center_id="proposal-center-1",
    )
    profile_space = ProfileSpace(
        profile_space_id="profile-1",
        project_id="proj-1",
        label="default",
        summary="primary review profile",
        mistake_ids=["mistake-1"],
        index_entry_ids=["index-1"],
        knowledge_node_ids=["node-1"],
        proposal_ids=["proposal-1"],
    )
    event = WorkspaceEvent(
        event_id="event-1",
        project_id="proj-1",
        event_type="project_created",
        created_at="2026-04-02T12:00:00Z",
        payload={"project_label": "impl-phase-coach"},
    )

    store.upsert_project_review(project)
    store.upsert_profile_space(profile_space)
    store.append_event(event)

    loaded_project = store.get_project_review("proj-1")
    loaded_profile = store.get_profile_space("profile-1")
    loaded_event = store.get_event("event-1")
    project_events = store.list_events("proj-1")

    assert loaded_project == project
    assert loaded_project is not None
    assert loaded_project.stage_reviews[0].stage_label == "module interface freeze"
    assert loaded_profile == profile_space
    assert loaded_event == event
    assert project_events == [event]


def test_sqlite_store_rejects_duplicate_event_ids_without_overwriting(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "review.sqlite3"
    store = SQLiteStore(db_path)
    store.initialize()

    first_event = WorkspaceEvent(
        event_id="event-1",
        project_id="proj-1",
        event_type="project_created",
        created_at="2026-04-02T12:00:00Z",
        payload={"project_label": "first"},
    )
    duplicate_event = WorkspaceEvent(
        event_id="event-1",
        project_id="proj-2",
        event_type="project_updated",
        created_at="2026-04-02T12:01:00Z",
        payload={"project_label": "second"},
    )

    store.append_event(first_event)

    with pytest.raises(sqlite3.IntegrityError):
        store.append_event(duplicate_event)

    assert store.get_event("event-1") == first_event
    assert store.list_events("proj-1") == [first_event]


def test_sqlite_store_round_trips_profile_space_entries(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "review.sqlite3"
    store = SQLiteStore(db_path)
    store.initialize()

    summary = {
        "knowledge_entry_count": 1,
        "mistake_count": 1,
        "latest_summary": "synced partial assessment with 1 knowledge entries and 1 mistakes",
    }
    mistake = {
        "mistake_id": "mistake-1",
        "label": "Decision awareness",
        "mistake_type": "reasoning_gap",
        "project_id": "proj-1",
        "stage_id": "stage-1",
        "root_cause_summary": "Decision awareness",
        "avoidance_summary": "Review the stage boundary and revisit: Decision awareness",
        "status": "active",
    }
    index_entry = {
        "entry_id": "index-1",
        "title": "Decision awareness",
        "entry_type": "mistake_avoidance",
        "summary": "Revisit why this stage needs: Decision awareness",
        "project_id": "proj-1",
        "stage_id": "stage-1",
        "linked_mistake_ids": ["mistake-1"],
        "status": "active",
    }
    node = {
        "node_id": "node-1",
        "label": "Decision awareness",
        "node_type": "decision",
        "project_id": "proj-1",
        "stage_id": "stage-1",
        "strength": 2,
        "linked_mistake_ids": ["mistake-1"],
        "summary": "Derived from partial assessment in stage-1.",
        "status": "active",
    }

    store.upsert_profile_stage_summary("profile-1", "proj-1", "stage-1", summary)
    store.upsert_profile_mistake("profile-1", mistake)
    store.upsert_profile_index_entry("profile-1", index_entry)
    store.upsert_profile_knowledge_node("profile-1", node)

    assert store.get_profile_stage_summary("profile-1", "proj-1", "stage-1") == summary
    assert store.list_profile_mistakes(profile_space_id="profile-1", project_id="proj-1", stage_id="stage-1") == [mistake]
    assert store.list_profile_index_entries(profile_space_id="profile-1", project_id="proj-1", stage_id="stage-1") == [index_entry]
    assert store.list_profile_knowledge_nodes(profile_space_id="profile-1", project_id="proj-1", stage_id="stage-1") == [node]


def test_sqlite_store_round_trips_question_set_and_proposal_center(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "review.sqlite3"
    store = SQLiteStore(db_path)
    store.initialize()

    question_set = QuestionSet(
        question_set_id="set-1",
        stage_review_id="stage-review-1",
        title="core questions",
        question_ids=["q-1", "q-2"],
        active_question_id="q-1",
    )
    proposal_center = ProposalCenter(
        proposal_center_id="proposal-center-1",
        project_id="proj-1",
        proposal_ids=["proposal-1"],
        active_proposal_id="proposal-1",
    )

    store.upsert_question_set(question_set)
    store.upsert_proposal_center(proposal_center)

    assert store.get_question_set("set-1") == question_set
    assert store.get_proposal_center("proposal-center-1") == proposal_center


def test_sqlite_store_round_trips_proposal_action_and_execution_records(tmp_path: Path) -> None:
    db_path = tmp_path / "review.sqlite3"
    store = SQLiteStore(db_path)
    store.initialize()

    proposal = {
        "proposal_id": "proposal-1",
        "proposal_type": "compress_mistake_entries",
        "target_type": "mistake_entries",
        "target_ids": ["m-1", "m-2"],
        "project_id": "proj-1",
        "stage_id": "stage-1",
        "status": "accepted",
        "reason": "Compress 2 mistake_entries",
        "preview_summary": "Would compress 2 targets from mistake_entries.",
        "latest_execution_status": "succeeded",
        "latest_execution_summary": "accept on proposal-1 => succeeded",
        "risk_notes": [],
    }
    action = {
        "action_id": "action-1",
        "proposal_id": "proposal-1",
        "action_type": "accept",
        "selected_target_ids": ["m-1", "m-2"],
    }
    execution = {
        "execution_id": "execution-1",
        "proposal_id": "proposal-1",
        "action_id": "action-1",
        "proposal_type": "compress_mistake_entries",
        "proposal_status": "accepted",
        "status": "succeeded",
        "applied_target_ids": ["m-1", "m-2"],
        "unchanged_target_ids": [],
        "generated_target_ids": [],
        "summary": "accept on proposal-1 => succeeded",
        "risk_notes": [],
        "error_message": None,
    }

    store.upsert_proposal_record("proposal-center:proj-1", proposal)
    store.upsert_proposal_action_record("proposal-center:proj-1", action)
    store.upsert_execution_record("proposal-center:proj-1", execution)

    assert store.get_proposal_record("proposal-1") == proposal
    assert store.get_proposal_action_record("action-1") == action
    assert store.list_proposal_records(proposal_center_id="proposal-center:proj-1") == [proposal]
    assert store.list_proposal_action_records(proposal_center_id="proposal-center:proj-1", proposal_id="proposal-1") == [action]
    assert store.list_execution_records(proposal_center_id="proposal-center:proj-1", proposal_id="proposal-1") == [execution]


def test_domain_from_dict_handles_null_collections_and_stringifies_optional_ids() -> None:
    session = WorkspaceSession.from_json(
        json.dumps(
            {
                "workspace_session_id": 1,
                "active_project_id": None,
                "active_stage_id": 2,
                "active_panel": None,
                "active_question_set_id": 3,
                "active_question_id": None,
                "active_profile_space_id": 4,
                "active_proposal_center_id": None,
                "last_opened_at": None,
                "filters": None,
            }
        )
    )
    question_set = QuestionSet.from_dict(
        {
            "question_set_id": 5,
            "stage_review_id": 6,
            "title": None,
            "status": None,
            "question_ids": None,
            "active_question_id": 7,
        }
    )
    stage_review = StageReview.from_dict(
        {
            "stage_review_id": 8,
            "project_id": 9,
            "stage_id": 10,
            "stage_label": None,
            "stage_goal": None,
            "status": None,
            "question_set_ids": None,
            "active_question_set_id": 11,
            "history_count": None,
            "retention_status": None,
            "related_mistake_ids": None,
            "related_knowledge_node_ids": None,
            "related_index_entry_ids": None,
            "related_proposal_ids": None,
            "mastery_status": None,
        }
    )
    proposal_center = ProposalCenter.from_dict(
        {
            "proposal_center_id": 12,
            "project_id": 13,
            "proposal_ids": None,
            "active_proposal_id": 14,
            "status": None,
        }
    )
    event = WorkspaceEvent.from_json(
        json.dumps(
            {
                "event_id": 15,
                "project_id": None,
                "event_type": "workspace_opened",
                "created_at": "2026-04-02T12:00:00Z",
                "payload": None,
            }
        )
    )
    project = ProjectReview.from_dict(
        {
            "project_id": 16,
            "project_label": None,
            "project_summary": None,
            "stage_reviews": None,
            "knowledge_index_id": None,
            "knowledge_graph_id": None,
            "profile_space_id": None,
            "proposal_center_id": None,
        }
    )

    assert session.workspace_session_id == "1"
    assert session.active_stage_id == "2"
    assert session.active_question_set_id == "3"
    assert session.filters == {}
    assert question_set.question_set_id == "5"
    assert question_set.stage_review_id == "6"
    assert question_set.question_ids == []
    assert question_set.active_question_id == "7"
    assert stage_review.stage_review_id == "8"
    assert stage_review.project_id == "9"
    assert stage_review.stage_id == "10"
    assert stage_review.question_set_ids == []
    assert stage_review.active_question_set_id == "11"
    assert proposal_center.proposal_center_id == "12"
    assert proposal_center.project_id == "13"
    assert proposal_center.proposal_ids == []
    assert proposal_center.active_proposal_id == "14"
    assert event.event_id == "15"
    assert event.payload == {}
    assert project.project_id == "16"
    assert project.stage_reviews == []


def test_workspace_state_store_round_trips_session(tmp_path: Path) -> None:
    path = tmp_path / "workspace-state.json"
    store = JsonWorkspaceStateStore(path)

    session = WorkspaceSession(
        workspace_session_id="ws-1",
        active_project_id="proj-1",
        active_stage_id="stage-1",
        active_panel="questions",
        active_question_set_id="set-1",
        active_question_id="q-1",
        active_profile_space_id="profile-1",
        active_proposal_center_id="proposal-center-1",
        last_opened_at="2026-04-02T12:00:00Z",
        filters={"status": "in_progress"},
    )

    store.save(session)
    loaded = store.load()

    assert loaded == session
    assert loaded is not None
    assert loaded.active_project_id == "proj-1"
    assert loaded.active_question_id == "q-1"
    assert loaded.filters == {"status": "in_progress"}
