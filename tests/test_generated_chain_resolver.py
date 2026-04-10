from __future__ import annotations

from pathlib import Path

from review_gate.checkpoint_models import (
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)
from review_gate.domain import WorkspaceEvent
from review_gate.generated_chain_resolver import GeneratedChainResolver
from review_gate.storage_sqlite import SQLiteStore


def _seed_generated_chain(
    store: SQLiteStore,
    *,
    request_id: str,
    created_at: str,
    transport_question_id: str,
) -> None:
    workflow_run_id = f"run-{request_id}"
    question_batch_id = f"qb-{request_id}"

    store.insert_workflow_request(
        WorkflowRequestRecord(
            request_id=request_id,
            request_type="question_cycle",
            project_id="proj-1",
            stage_id="stage-1",
            requested_by="question_generation_client",
            source="review_flow_service",
            status="completed",
            created_at=created_at,
            payload={"request_id": request_id},
        )
    )
    store.insert_workflow_run(
        WorkflowRunRecord(
            run_id=workflow_run_id,
            request_id=request_id,
            run_type="question_cycle",
            status="completed",
            started_at=created_at,
            finished_at=created_at,
            supersedes_run_id=None,
            payload={"request_id": request_id},
        )
    )
    store.insert_question_batch(
        QuestionBatchRecord(
            question_batch_id=question_batch_id,
            workflow_run_id=workflow_run_id,
            project_id="proj-1",
            stage_id="stage-1",
            generated_by="question_generation_client",
            source="review_flow_service",
            batch_goal="freeze boundary",
            entry_question_id=f"{request_id}-q-1",
            status="active",
            created_at=created_at,
            payload={"request_id": request_id},
        )
    )
    store.insert_question_items(
        [
            QuestionItemRecord(
                question_id=f"{request_id}-q-1",
                question_batch_id=question_batch_id,
                question_type="core",
                prompt="Explain the boundary.",
                intent="Check understanding.",
                difficulty_level="core",
                order_index=0,
                status="ready",
                created_at=created_at,
                payload={"transport_question_id": transport_question_id},
            )
        ]
    )


def test_generated_chain_resolver_reuses_latest_generated_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    resolver = GeneratedChainResolver(store=store)

    _seed_generated_chain(
        store,
        request_id="req-qgen-1",
        created_at="2026-04-10T10:00:00Z",
        transport_question_id="set-1-q-1",
    )
    _seed_generated_chain(
        store,
        request_id="req-qgen-2",
        created_at="2026-04-10T10:05:00Z",
        transport_question_id="set-1-q-1",
    )
    store.append_event(
        WorkspaceEvent(
            event_id="evt-question-set-generated-00000001-req-qgen-1",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="2026-04-10T10:00:00Z",
            payload={
                "stage_id": "stage-1",
                "question_set_id": "set-1",
                "question_batch_id": "qb-req-qgen-1",
                "workflow_run_id": "run-req-qgen-1",
                "question_item_ids": ["req-qgen-1-q-1"],
            },
        )
    )
    store.append_event(
        WorkspaceEvent(
            event_id="evt-question-set-generated-00000002-req-qgen-2",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="2026-04-10T10:05:00Z",
            payload={
                "stage_id": "stage-1",
                "question_set_id": "set-1",
                "question_batch_id": "qb-req-qgen-2",
                "workflow_run_id": "run-req-qgen-2",
                "question_item_ids": ["req-qgen-2-q-1"],
            },
        )
    )

    resolved = resolver.resolve(
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        transport_question_id="set-1-q-1",
        request_id="req-submit-1",
        created_at="2026-04-10T10:10:00Z",
    )

    assert resolved.resolution_mode == "reused"
    assert resolved.workflow_run_id == "run-req-qgen-2"
    assert resolved.question_batch_id == "qb-req-qgen-2"
    assert resolved.question_item_id == "req-qgen-2-q-1"
    assert resolved.transport_question_id == "set-1-q-1"
    assert resolved.generated_batch is not None
    assert resolved.generated_batch.question_batch_id == "qb-req-qgen-2"
    assert resolved.generated_item is not None
    assert resolved.generated_item.question_id == "req-qgen-2-q-1"


def test_generated_chain_resolver_skips_corrupt_latest_event_and_uses_earlier_valid_chain(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    resolver = GeneratedChainResolver(store=store)

    _seed_generated_chain(
        store,
        request_id="req-qgen-1",
        created_at="2026-04-10T10:00:00Z",
        transport_question_id="set-1-q-1",
    )
    store.append_event(
        WorkspaceEvent(
            event_id="evt-question-set-generated-00000001-req-qgen-1",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="2026-04-10T10:00:00Z",
            payload={
                "stage_id": "stage-1",
                "question_set_id": "set-1",
                "question_batch_id": "qb-req-qgen-1",
                "workflow_run_id": "run-req-qgen-1",
                "question_item_ids": ["req-qgen-1-q-1"],
            },
        )
    )
    store.append_event(
        WorkspaceEvent(
            event_id="evt-question-set-generated-00000002-req-qgen-2",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="2026-04-10T10:05:00Z",
            payload={
                "stage_id": "stage-1",
                "question_set_id": "set-1",
                "question_batch_id": "qb-req-qgen-2",
                "workflow_run_id": "run-req-qgen-2",
                "question_item_ids": ["req-qgen-2-q-1"],
            },
        )
    )
    _seed_generated_chain(
        store,
        request_id="req-qgen-2",
        created_at="2026-04-10T10:05:00Z",
        transport_question_id="different-transport-question",
    )

    resolved = resolver.resolve(
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        transport_question_id="set-1-q-1",
        request_id="req-submit-1",
        created_at="2026-04-10T10:10:00Z",
    )

    assert resolved.resolution_mode == "reused"
    assert resolved.workflow_run_id == "run-req-qgen-1"
    assert resolved.question_batch_id == "qb-req-qgen-1"
    assert resolved.question_item_id == "req-qgen-1-q-1"


def test_generated_chain_resolver_uses_event_id_to_pick_newest_same_created_at_event(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    resolver = GeneratedChainResolver(store=store)

    _seed_generated_chain(
        store,
        request_id="req-qgen-1",
        created_at="2026-04-10T10:00:00Z",
        transport_question_id="set-1-q-1",
    )
    _seed_generated_chain(
        store,
        request_id="req-qgen-2",
        created_at="2026-04-10T10:00:00Z",
        transport_question_id="set-1-q-1",
    )
    store.append_event(
        WorkspaceEvent(
            event_id="evt-question-set-generated-00000001-req-qgen-1",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="2026-04-10T10:00:00Z",
            payload={
                "stage_id": "stage-1",
                "question_set_id": "set-1",
                "question_batch_id": "qb-req-qgen-1",
                "workflow_run_id": "run-req-qgen-1",
                "question_item_ids": ["req-qgen-1-q-1"],
            },
        )
    )
    store.append_event(
        WorkspaceEvent(
            event_id="evt-question-set-generated-00000002-req-qgen-2",
            project_id="proj-1",
            event_type="question_set_generated",
            created_at="2026-04-10T10:00:00Z",
            payload={
                "stage_id": "stage-1",
                "question_set_id": "set-1",
                "question_batch_id": "qb-req-qgen-2",
                "workflow_run_id": "run-req-qgen-2",
                "question_item_ids": ["req-qgen-2-q-1"],
            },
        )
    )

    resolved = resolver.resolve(
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        transport_question_id="set-1-q-1",
        request_id="req-submit-1",
        created_at="2026-04-10T10:10:00Z",
    )

    assert resolved.resolution_mode == "reused"
    assert resolved.workflow_run_id == "run-req-qgen-2"
    assert resolved.question_batch_id == "qb-req-qgen-2"
    assert resolved.question_item_id == "req-qgen-2-q-1"


def test_generated_chain_resolver_falls_back_without_generated_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    resolver = GeneratedChainResolver(store=store)

    resolved = resolver.resolve(
        project_id="proj-1",
        stage_id="stage-1",
        question_set_id="set-1",
        transport_question_id="set-1-q-1",
        request_id="req-submit-1",
        created_at="2026-04-10T10:10:00Z",
    )

    assert resolved.resolution_mode == "fallback"
    assert resolved.workflow_run_id == "run-req-submit-1"
    assert resolved.question_batch_id == "qb-req-submit-1"
    assert resolved.question_item_id == "req-submit-1-set-1-q-1"
    assert resolved.transport_question_id == "set-1-q-1"
    assert resolved.generated_batch is None
    assert resolved.generated_item is None
