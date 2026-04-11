from __future__ import annotations

from pathlib import Path

import pytest

from review_gate.checkpoint_models import (
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)
from review_gate.question_checkpoint_writer import (
    PersistedQuestionGeneration,
    QuestionCheckpointWriter,
)
from review_gate.storage_sqlite import SQLiteStore


def test_question_checkpoint_writer_persists_generation_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = QuestionCheckpointWriter(store=store)

    result = writer.write(
        request={
            "request_id": "req-qgen-1",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_goal": "freeze submit boundary",
            "created_at": "2026-04-11T09:00:00Z",
        },
        response={
            "questions": [
                {
                    "question_id": "q-1",
                    "question_level": "core",
                    "prompt": "Explain the boundary.",
                    "intent": "Check understanding.",
                    "expected_signals": ["Question, Assessment, Decision split"],
                    "source_context": [],
                },
                {
                    "question_id": "q-2",
                    "question_level": "why",
                    "prompt": "Why this boundary?",
                    "intent": "Check reasoning.",
                    "expected_signals": ["module vs interface"],
                    "source_context": [],
                },
            ]
        },
        question_set_id="set-1",
    )

    assert result == PersistedQuestionGeneration(
        workflow_run_id="run-req-qgen-1",
        question_batch_id="qb-req-qgen-1",
        question_item_ids=["req-qgen-1-q-1", "req-qgen-1-q-2"],
        question_set_id="set-1",
    )
    assert store.get_workflow_request("req-qgen-1") == WorkflowRequestRecord(
        request_id="req-qgen-1",
        request_type="question_cycle",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="question_generation_client",
        source="review_flow_service",
        status="completed",
        created_at="2026-04-11T09:00:00Z",
        payload={
            "request": {
                "request_id": "req-qgen-1",
                "project_id": "proj-1",
                "stage_id": "stage-1",
                "stage_goal": "freeze submit boundary",
                "created_at": "2026-04-11T09:00:00Z",
            }
        },
    )
    assert store.get_workflow_run("run-req-qgen-1") == WorkflowRunRecord(
        run_id="run-req-qgen-1",
        request_id="req-qgen-1",
        run_type="question_cycle",
        status="completed",
        started_at="2026-04-11T09:00:00Z",
        finished_at="2026-04-11T09:00:00Z",
        supersedes_run_id=None,
        payload={"question_count": 2, "request_id": "req-qgen-1"},
    )
    assert store.get_question_batch("qb-req-qgen-1") == QuestionBatchRecord(
        question_batch_id="qb-req-qgen-1",
        workflow_run_id="run-req-qgen-1",
        project_id="proj-1",
        stage_id="stage-1",
        generated_by="question_generation_client",
        source="review_flow_service",
        batch_goal="freeze submit boundary",
        entry_question_id="req-qgen-1-q-1",
        status="active",
        created_at="2026-04-11T09:00:00Z",
        payload={"question_count": 2, "request_id": "req-qgen-1"},
    )
    assert store.list_question_items("qb-req-qgen-1") == [
        QuestionItemRecord(
            question_id="req-qgen-1-q-1",
            question_batch_id="qb-req-qgen-1",
            question_type="core",
            prompt="Explain the boundary.",
            intent="Check understanding.",
            difficulty_level="core",
            order_index=0,
            status="ready",
            created_at="2026-04-11T09:00:00Z",
            payload={
                "expected_signals": ["Question, Assessment, Decision split"],
                "source_context": [],
                "transport_question_id": "set-1-q-1",
            },
        ),
        QuestionItemRecord(
            question_id="req-qgen-1-q-2",
            question_batch_id="qb-req-qgen-1",
            question_type="why",
            prompt="Why this boundary?",
            intent="Check reasoning.",
            difficulty_level="why",
            order_index=1,
            status="ready",
            created_at="2026-04-11T09:00:00Z",
            payload={
                "expected_signals": ["module vs interface"],
                "source_context": [],
                "transport_question_id": "set-1-q-2",
            },
        ),
    ]


def test_question_checkpoint_writer_keeps_existing_transport_question_ids(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = QuestionCheckpointWriter(store=store)

    result = writer.write(
        request={
            "request_id": "req-qgen-2",
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_goal": "freeze submit boundary",
            "created_at": "2026-04-11T09:05:00Z",
        },
        response={
            "questions": [
                {
                    "question_id": "set-1-q-1",
                    "question_level": "core",
                    "prompt": "Explain the boundary.",
                    "intent": "Check understanding.",
                    "expected_signals": [],
                    "source_context": [],
                }
            ]
        },
        question_set_id="set-1",
    )

    assert result.question_item_ids == ["req-qgen-2-set-1-q-1"]
    assert store.list_question_items("qb-req-qgen-2")[0].payload["transport_question_id"] == "set-1-q-1"


def test_question_checkpoint_writer_leaves_in_progress_when_batch_write_fails(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = QuestionCheckpointWriter(store=store)

    def raise_after_workflow_checkpoint(_record: QuestionBatchRecord) -> None:
        raise RuntimeError("boom")

    store.insert_question_batch = raise_after_workflow_checkpoint  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="boom"):
        writer.write(
            request={
                "request_id": "req-qgen-3",
                "project_id": "proj-1",
                "stage_id": "stage-1",
                "stage_goal": "freeze submit boundary",
                "created_at": "2026-04-11T09:10:00Z",
            },
            response={
                "questions": [
                    {
                        "question_id": "q-1",
                        "question_level": "core",
                        "prompt": "Explain the boundary.",
                        "intent": "Check understanding.",
                        "expected_signals": [],
                        "source_context": [],
                    }
                ]
            },
            question_set_id="set-1",
        )

    assert store.get_workflow_request("req-qgen-3") == WorkflowRequestRecord(
        request_id="req-qgen-3",
        request_type="question_cycle",
        project_id="proj-1",
        stage_id="stage-1",
        requested_by="question_generation_client",
        source="review_flow_service",
        status="in_progress",
        created_at="2026-04-11T09:10:00Z",
        payload={
            "request": {
                "request_id": "req-qgen-3",
                "project_id": "proj-1",
                "stage_id": "stage-1",
                "stage_goal": "freeze submit boundary",
                "created_at": "2026-04-11T09:10:00Z",
            }
        },
    )
    assert store.get_workflow_run("run-req-qgen-3") == WorkflowRunRecord(
        run_id="run-req-qgen-3",
        request_id="req-qgen-3",
        run_type="question_cycle",
        status="in_progress",
        started_at="2026-04-11T09:10:00Z",
        finished_at="2026-04-11T09:10:00Z",
        supersedes_run_id=None,
        payload={"question_count": 1, "request_id": "req-qgen-3"},
    )
    assert store.get_question_batch("qb-req-qgen-3") is None
    assert store.list_question_items("qb-req-qgen-3") == []


def test_question_checkpoint_writer_rejects_empty_questions_before_finalizing(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    writer = QuestionCheckpointWriter(store=store)

    with pytest.raises(ValueError, match="questions"):
        writer.write(
            request={
                "request_id": "req-qgen-4",
                "project_id": "proj-1",
                "stage_id": "stage-1",
                "stage_goal": "freeze submit boundary",
                "created_at": "2026-04-11T09:15:00Z",
            },
            response={"questions": []},
            question_set_id="set-1",
        )

    assert store.get_workflow_request("req-qgen-4") is None
    assert store.get_workflow_run("run-req-qgen-4") is None
    assert store.get_question_batch("qb-req-qgen-4") is None
