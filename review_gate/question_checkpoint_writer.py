from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from review_gate.checkpoint_models import (
    QuestionBatchRecord,
    QuestionItemRecord,
    WorkflowRequestRecord,
    WorkflowRunRecord,
)
from review_gate.storage_sqlite import SQLiteStore


@dataclass(slots=True)
class PersistedQuestionGeneration:
    workflow_run_id: str
    question_batch_id: str
    question_item_ids: list[str]
    question_set_id: str


class QuestionCheckpointWriter:
    def __init__(self, *, store: SQLiteStore) -> None:
        self._store = store

    def write(
        self,
        *,
        request: dict[str, Any],
        response: dict[str, Any],
        question_set_id: str,
    ) -> PersistedQuestionGeneration:
        request_id = str(request["request_id"])
        created_at = str(request.get("created_at", ""))
        workflow_run_id = f"run-{request_id}"
        question_batch_id = f"qb-{request_id}"
        questions = response.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError("response['questions'] must contain at least one question")

        self._store.insert_workflow_request(
            WorkflowRequestRecord(
                request_id=request_id,
                request_type="question_cycle",
                project_id=str(request["project_id"]),
                stage_id=str(request["stage_id"]),
                requested_by="question_generation_client",
                source="review_flow_service",
                status="in_progress",
                created_at=created_at,
                payload={"request": dict(request)},
            )
        )
        self._store.insert_workflow_run(
            WorkflowRunRecord(
                run_id=workflow_run_id,
                request_id=request_id,
                run_type="question_cycle",
                status="in_progress",
                started_at=created_at,
                finished_at=created_at,
                supersedes_run_id=None,
                payload={"question_count": len(questions), "request_id": request_id},
            )
        )

        question_items: list[QuestionItemRecord] = []
        for index, item in enumerate(questions):
            raw_question_id = str(item.get("question_id", f"q-{index + 1}"))
            persisted_question_id = f"{request_id}-{raw_question_id}"
            transport_question_id = self._build_transport_question_id(
                question_set_id=question_set_id,
                raw_question_id=raw_question_id,
            )
            question_items.append(
                QuestionItemRecord(
                    question_id=persisted_question_id,
                    question_batch_id=question_batch_id,
                    question_type=str(item.get("question_level", "core")),
                    prompt=str(item.get("prompt", "")),
                    intent=str(item.get("intent", "")),
                    difficulty_level=str(item.get("question_level", "core")),
                    order_index=index,
                    status="ready",
                    created_at=created_at,
                    payload={
                        "expected_signals": self._coerce_str_list(item.get("expected_signals")),
                        "source_context": self._coerce_str_list(item.get("source_context")),
                        "transport_question_id": transport_question_id,
                    },
                )
            )

        self._store.insert_question_batch(
            QuestionBatchRecord(
                question_batch_id=question_batch_id,
                workflow_run_id=workflow_run_id,
                project_id=str(request["project_id"]),
                stage_id=str(request["stage_id"]),
                generated_by="question_generation_client",
                source="review_flow_service",
                batch_goal=str(request.get("stage_goal", "")),
                entry_question_id=(question_items[0].question_id if question_items else ""),
                status="active",
                created_at=created_at,
                payload={"question_count": len(question_items), "request_id": request_id},
            )
        )
        self._store.insert_question_items(question_items)

        self._store.insert_workflow_request(
            WorkflowRequestRecord(
                request_id=request_id,
                request_type="question_cycle",
                project_id=str(request["project_id"]),
                stage_id=str(request["stage_id"]),
                requested_by="question_generation_client",
                source="review_flow_service",
                status="completed",
                created_at=created_at,
                payload={"request": dict(request)},
            )
        )
        self._store.insert_workflow_run(
            WorkflowRunRecord(
                run_id=workflow_run_id,
                request_id=request_id,
                run_type="question_cycle",
                status="completed",
                started_at=created_at,
                finished_at=created_at,
                supersedes_run_id=None,
                payload={"question_count": len(question_items), "request_id": request_id},
            )
        )

        return PersistedQuestionGeneration(
            workflow_run_id=workflow_run_id,
            question_batch_id=question_batch_id,
            question_item_ids=[item.question_id for item in question_items],
            question_set_id=question_set_id,
        )

    def _build_transport_question_id(self, *, question_set_id: str, raw_question_id: str) -> str:
        if not question_set_id:
            return raw_question_id
        if raw_question_id.startswith(f"{question_set_id}-"):
            return raw_question_id
        return f"{question_set_id}-{raw_question_id}"

    @staticmethod
    def _coerce_str_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            items = value
        elif isinstance(value, tuple):
            items = list(value)
        elif isinstance(value, dict):
            items = list(value.keys())
        else:
            items = [value]
        return [str(item) for item in items]
