from __future__ import annotations

from dataclasses import dataclass

from review_gate.checkpoint_models import (
    AssessmentFactBatchRecord,
    AssessmentFactItemRecord,
    KnowledgeSignalRecord,
)


@dataclass(slots=True)
class AssessmentFactSignalProjector:
    projector_version: str = "fact-signal-v1"

    def project(
        self,
        *,
        fact_batch: AssessmentFactBatchRecord,
        fact_items: list[AssessmentFactItemRecord],
    ) -> list[KnowledgeSignalRecord]:
        signals: list[KnowledgeSignalRecord] = []
        for fact_item in fact_items:
            signals.append(self._project_item(fact_batch=fact_batch, fact_item=fact_item))
        return signals

    def _project_item(
        self,
        *,
        fact_batch: AssessmentFactBatchRecord,
        fact_item: AssessmentFactItemRecord,
    ) -> KnowledgeSignalRecord:
        signal_type, polarity = self._classify_fact(fact_item.fact_type)
        return KnowledgeSignalRecord(
            signal_id=self._signal_id(fact_item=fact_item, signal_type=signal_type),
            assessment_fact_batch_id=fact_batch.assessment_fact_batch_id,
            assessment_fact_item_id=fact_item.assessment_fact_item_id,
            source_evaluation_item_id=fact_item.source_evaluation_item_id,
            signal_type=signal_type,
            topic_key=fact_item.topic_key,
            polarity=polarity,
            summary=fact_item.title or fact_item.topic_key,
            confidence=fact_item.confidence,
            status=fact_item.status,
            projector_version=self.projector_version,
            created_at=fact_item.created_at,
            payload={
                "source_fact_type": fact_item.fact_type,
                "source_title": fact_item.title,
                "description": str(fact_item.payload.get("description", "")),
                "source_payload": fact_item.payload,
                "fact_batch_synthesizer_version": fact_batch.synthesizer_version,
            },
        )

    def _classify_fact(self, fact_type: str) -> tuple[str, str]:
        normalized = fact_type.strip().lower()
        if normalized in {"gap", "weakness", "misconception"}:
            return "weakness", "negative"
        if normalized in {"strength", "mastery"}:
            return "strength", "positive"
        return "evidence", "neutral"

    def _signal_id(self, *, fact_item: AssessmentFactItemRecord, signal_type: str) -> str:
        topic_key = fact_item.topic_key or "untagged"
        return f"ks-{fact_item.assessment_fact_item_id}-{signal_type}-{topic_key}"
