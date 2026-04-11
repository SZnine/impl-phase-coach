from __future__ import annotations

from pathlib import Path

from review_gate.domain import WorkspaceEvent
from review_gate.question_set_generation_publisher import QuestionSetGenerationPublisher
from review_gate.storage_sqlite import SQLiteStore


def _seed_question_set_generated_event(
    store: SQLiteStore,
    *,
    event_id: str,
    created_at: str,
    payload: dict[str, object],
) -> None:
    store.append_event(
        WorkspaceEvent(
            event_id=event_id,
            project_id="proj-1",
            event_type="question_set_generated",
            created_at=created_at,
            payload=payload,
        )
    )


def test_question_set_generation_publisher_increments_generation_index_from_prior_events(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    publisher = QuestionSetGenerationPublisher(store=store)
    _seed_question_set_generated_event(
        store,
        event_id="evt-question-set-generated-00000002-req-old",
        created_at="2026-04-10T10:00:00Z",
        payload={
            "generation_index": 2,
            "stage_id": "stage-1",
            "question_set_id": "set-1",
            "question_batch_id": "qb-req-old",
            "workflow_run_id": "run-req-old",
            "question_item_ids": ["req-old-q-1"],
        },
    )

    published = publisher.publish(
        request_id="req-new",
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        question_batch_id="qb-req-new",
        workflow_run_id="run-req-new",
        question_item_ids=["req-new-q-1", "req-new-q-2"],
        created_at="2026-04-10T10:10:00Z",
    )

    assert published.generation_index == 3
    assert published.event.event_id == "evt-question-set-generated-00000003-req-new"
    assert store.get_event("evt-question-set-generated-00000003-req-new") == published.event


def test_question_set_generation_publisher_ignores_legacy_and_missing_generation_index(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    publisher = QuestionSetGenerationPublisher(store=store)
    _seed_question_set_generated_event(
        store,
        event_id="evt-question-set-generated-00000001-req-legacy",
        created_at="2026-04-10T10:00:00Z",
        payload={
            "stage_id": "stage-1",
            "question_set_id": "set-1",
            "question_batch_id": "qb-req-legacy",
            "workflow_run_id": "run-req-legacy",
            "question_item_ids": ["req-legacy-q-1"],
        },
    )
    _seed_question_set_generated_event(
        store,
        event_id="evt-question-set-generated-00000002-req-modern",
        created_at="2026-04-10T10:05:00Z",
        payload={
            "generation_index": "2",
            "stage_id": "stage-1",
            "question_set_id": "set-1",
            "question_batch_id": "qb-req-modern",
            "workflow_run_id": "run-req-modern",
            "question_item_ids": ["req-modern-q-1"],
        },
    )

    published = publisher.publish(
        request_id="req-new",
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        question_batch_id="qb-req-new",
        workflow_run_id="run-req-new",
        question_item_ids=["req-new-q-1"],
        created_at="2026-04-10T10:10:00Z",
    )

    assert published.generation_index == 3
    assert published.event.payload["generation_index"] == 3


def test_question_set_generation_publisher_preserves_event_shape_and_key_fields(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    publisher = QuestionSetGenerationPublisher(store=store)

    published = publisher.publish(
        request_id="req-qgen-1",
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        question_batch_id="qb-req-qgen-1",
        workflow_run_id="run-req-qgen-1",
        question_item_ids=["req-qgen-1-q-1", "req-qgen-1-q-2"],
        created_at="2026-04-10T10:10:00Z",
    )

    assert published.event.event_type == "question_set_generated"
    assert published.event.project_id == "proj-1"
    assert published.event.created_at == "2026-04-10T10:10:00Z"
    assert published.event.payload == {
        "generation_index": 1,
        "stage_id": "stage-1",
        "question_set_id": "set-1",
        "question_batch_id": "qb-req-qgen-1",
        "workflow_run_id": "run-req-qgen-1",
        "question_item_ids": ["req-qgen-1-q-1", "req-qgen-1-q-2"],
    }
    assert store.get_event("evt-question-set-generated-00000001-req-qgen-1") == published.event
