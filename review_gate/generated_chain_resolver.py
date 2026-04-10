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
        for event in self._iter_matching_generated_question_set_events(
            project_id=project_id,
            stage_id=stage_id,
            question_set_id=question_set_id,
        ):
            resolved = self._resolve_generated_event(
                event=event,
                transport_question_id=transport_question_id,
            )
            if resolved is not None:
                return resolved

        return self._fallback_chain(request_id=request_id, transport_question_id=transport_question_id)

    def _iter_matching_generated_question_set_events(
        self,
        *,
        project_id: str,
        stage_id: str,
        question_set_id: str,
    ) -> list[WorkspaceEvent]:
        matching_events: list[WorkspaceEvent] = []
        for event in self._store.list_events(project_id=project_id):
            if event.event_type != "question_set_generated":
                continue
            if str(event.payload.get("stage_id", "")).strip() != stage_id:
                continue
            if str(event.payload.get("question_set_id", "")).strip() != question_set_id:
                continue
            matching_events.append(event)
        return list(reversed(matching_events))

    def _resolve_generated_event(
        self,
        *,
        event: WorkspaceEvent,
        transport_question_id: str,
    ) -> ResolvedQuestionChain | None:
        question_batch_id = str(event.payload.get("question_batch_id", "")).strip()
        workflow_run_id = str(event.payload.get("workflow_run_id", "")).strip()
        if not question_batch_id or not workflow_run_id:
            return None

        generated_batch = self._store.get_question_batch(question_batch_id)
        if generated_batch is None:
            return None

        generated_item = self._find_generated_item(
            question_batch_id=generated_batch.question_batch_id,
            transport_question_id=transport_question_id,
        )
        if generated_item is None:
            return None

        return ResolvedQuestionChain(
            workflow_run_id=workflow_run_id,
            question_batch_id=generated_batch.question_batch_id,
            question_item_id=generated_item.question_id,
            transport_question_id=transport_question_id,
            resolution_mode="reused",
            generated_batch=generated_batch,
            generated_item=generated_item,
        )

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
