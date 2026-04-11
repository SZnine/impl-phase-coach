from __future__ import annotations

from dataclasses import dataclass

from review_gate.domain import WorkspaceEvent
from review_gate.storage_sqlite import SQLiteStore


@dataclass(slots=True)
class PublishedQuestionSetGeneration:
    generation_index: int
    event: WorkspaceEvent


class QuestionSetGenerationPublisher:
    def __init__(self, *, store: SQLiteStore) -> None:
        self._store = store

    def publish(
        self,
        *,
        request_id: str,
        project_id: str,
        stage_id: str,
        question_set_id: str,
        question_batch_id: str,
        workflow_run_id: str,
        question_item_ids: list[str],
        created_at: str,
    ) -> PublishedQuestionSetGeneration:
        generation_index = self._next_question_set_generation_index(
            project_id=project_id,
            stage_id=stage_id,
            question_set_id=question_set_id,
        )
        event = WorkspaceEvent(
            event_id=f"evt-question-set-generated-{generation_index:08d}-{request_id}",
            project_id=project_id,
            event_type="question_set_generated",
            created_at=created_at,
            payload={
                "generation_index": generation_index,
                "stage_id": stage_id,
                "question_set_id": question_set_id,
                "question_batch_id": question_batch_id,
                "workflow_run_id": workflow_run_id,
                "question_item_ids": list(question_item_ids),
            },
        )
        self._store.append_event(event)
        return PublishedQuestionSetGeneration(generation_index=generation_index, event=event)

    def _next_question_set_generation_index(self, *, project_id: str, stage_id: str, question_set_id: str) -> int:
        latest_generation_index = 0
        for event in self._store.list_events(project_id=project_id):
            if event.event_type != "question_set_generated":
                continue
            if str(event.payload.get("stage_id", "")) != stage_id:
                continue
            if str(event.payload.get("question_set_id", "")) != question_set_id:
                continue
            if "generation_index" not in event.payload:
                continue
            latest_generation_index = max(
                latest_generation_index,
                self._coerce_generation_index(event.payload.get("generation_index")),
            )
        return latest_generation_index + 1

    def _coerce_generation_index(self, raw_value: object) -> int:
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return 0
