from __future__ import annotations

from dataclasses import dataclass

from review_gate.checkpoint_models import (
    AssessmentFactBatchRecord,
    AssessmentFactItemRecord,
    EvaluationBatchRecord,
    EvaluationItemRecord,
    EvidenceSpanRecord,
)


@dataclass(slots=True)
class AssessmentSynthesizer:
    synthesizer_version: str = "first-checkpoint-v1"

    def synthesize(
        self,
        *,
        workflow_run_id: str,
        evaluation_batch: EvaluationBatchRecord,
        evaluation_items: list[EvaluationItemRecord],
        evidence_spans: list[EvidenceSpanRecord],
    ) -> tuple[AssessmentFactBatchRecord, list[AssessmentFactItemRecord]]:
        assessment_fact_batch_id = f"afb-{evaluation_batch.evaluation_batch_id}"
        fact_items: list[AssessmentFactItemRecord] = []
        for item in evaluation_items:
            diagnosed_gaps = list(item.payload.get("diagnosed_gaps", []))
            reasoned_summary = str(item.payload.get("reasoned_summary", ""))
            for gap in diagnosed_gaps:
                fact_items.append(
                    AssessmentFactItemRecord(
                        assessment_fact_item_id=f"afi-{item.evaluation_item_id}-{gap}",
                        assessment_fact_batch_id=assessment_fact_batch_id,
                        source_evaluation_item_id=item.evaluation_item_id,
                        fact_type="gap",
                        topic_key=gap,
                        title=gap.replace("-", " "),
                        confidence=item.confidence,
                        status="active",
                        created_at=item.evaluated_at,
                        payload={
                            "description": reasoned_summary,
                            "dimension_refs": item.payload.get("dimension_refs", []),
                            "evidence_span_ids": [
                                span.evidence_span_id
                                for span in evidence_spans
                                if span.evaluation_item_id == item.evaluation_item_id
                            ],
                        },
                    )
                )
        fact_batch = AssessmentFactBatchRecord(
            assessment_fact_batch_id=assessment_fact_batch_id,
            evaluation_batch_id=evaluation_batch.evaluation_batch_id,
            workflow_run_id=workflow_run_id,
            synthesized_by="assessment_synthesizer",
            synthesizer_version=self.synthesizer_version,
            status="completed",
            synthesized_at=evaluation_batch.evaluated_at,
            payload={"item_count": len(fact_items)},
        )
        return fact_batch, fact_items
