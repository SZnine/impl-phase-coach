from __future__ import annotations

from dataclasses import dataclass

from review_gate.checkpoint_models import QuestionBatchRecord, QuestionItemRecord
from review_gate.domain import WorkspaceEvent
from review_gate.storage_sqlite import SQLiteStore


@dataclass(slots=True)
class ResolvedQuestionChain:
    workflow_run_id: str
    question_batch_id: str
    question_item_id: str
    transport_question_id: str
    resolution_mode: str
    generated_batch: QuestionBatchRecord | None = None
    generated_item: QuestionItemRecord | None = None


class GeneratedChainResolver:
    def __init__(self, *, store: SQLiteStore) -> None:
        self._store = store

    def resolve(
        self,
        *,
        project_id: str,
        stage_id: str,
        question_set_id: str,
        transport_question_id: str,
        request_id: str,
        created_at: str,
    ) -> ResolvedQuestionChain:
        latest_event = self._find_latest_generated_question_set_event(
            project_id=project_id,
            stage_id=stage_id,
            question_set_id=question_set_id,
        )
        if latest_event is None:
            return self._fallback_chain(request_id=request_id, transport_question_id=transport_question_id)

        question_batch_id = str(latest_event.payload.get("question_batch_id", "")).strip()
        workflow_run_id = str(latest_event.payload.get("workflow_run_id", "")).strip()
        generated_batch = self._store.get_question_batch(question_batch_id) if question_batch_id else None
        if generated_batch is None:
            return self._fallback_chain(request_id=request_id, transport_question_id=transport_question_id)

        generated_item = self._find_generated_item(
            question_batch_id=generated_batch.question_batch_id,
            transport_question_id=transport_question_id,
        )
        if generated_item is None or not workflow_run_id:
            return self._fallback_chain(request_id=request_id, transport_question_id=transport_question_id)

        return ResolvedQuestionChain(
            workflow_run_id=workflow_run_id,
            question_batch_id=generated_batch.question_batch_id,
            question_item_id=generated_item.question_id,
            transport_question_id=transport_question_id,
            resolution_mode="reused",
            generated_batch=generated_batch,
            generated_item=generated_item,
        )

    def _find_latest_generated_question_set_event(
        self,
        *,
        project_id: str,
        stage_id: str,
        question_set_id: str,
    ) -> WorkspaceEvent | None:
        latest_event: WorkspaceEvent | None = None
        for event in self._store.list_events(project_id=project_id):
            if event.event_type != "question_set_generated":
                continue
            if str(event.payload.get("stage_id", "")).strip() != stage_id:
                continue
            if str(event.payload.get("question_set_id", "")).strip() != question_set_id:
                continue
            latest_event = event
        return latest_event

    def _find_generated_item(
        self,
        *,
        question_batch_id: str,
        transport_question_id: str,
    ) -> QuestionItemRecord | None:
        for item in self._store.list_question_items(question_batch_id):
            item_transport_question_id = str(item.payload.get("transport_question_id", item.question_id))
            if item_transport_question_id == transport_question_id:
                return item
        return None

    def _fallback_chain(self, *, request_id: str, transport_question_id: str) -> ResolvedQuestionChain:
        return ResolvedQuestionChain(
            workflow_run_id=f"run-{request_id}",
            question_batch_id=f"qb-{request_id}",
            question_item_id=f"{request_id}-{transport_question_id}",
            transport_question_id=transport_question_id,
            resolution_mode="fallback",
        )
