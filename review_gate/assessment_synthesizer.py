from __future__ import annotations

import re
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
                topic_key = self._topic_key(str(gap))
                fact_items.append(
                    AssessmentFactItemRecord(
                        assessment_fact_item_id=f"afi-{item.evaluation_item_id}-{topic_key}",
                        assessment_fact_batch_id=assessment_fact_batch_id,
                        source_evaluation_item_id=item.evaluation_item_id,
                        fact_type="gap",
                        topic_key=topic_key,
                        title=str(gap).replace("-", " "),
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
            for support_signal in item.payload.get("support_signals", []):
                if not isinstance(support_signal, dict):
                    continue
                source_label = str(support_signal.get("source_label", "")).strip()
                target_label = str(support_signal.get("target_label", "")).strip()
                source_node_type = str(support_signal.get("source_node_type", "")).strip()
                target_node_type = str(support_signal.get("target_node_type", "")).strip()
                basis_type = str(support_signal.get("basis_type", "")).strip()
                basis_key = str(support_signal.get("basis_key", "")).strip()
                if not (source_label and target_label and source_node_type and target_node_type and basis_type and basis_key):
                    continue
                source_topic_key = self._topic_key(source_label)
                target_topic_key = self._topic_key(target_label)
                fact_items.append(
                    AssessmentFactItemRecord(
                        assessment_fact_item_id=self._support_relation_fact_id(
                            evaluation_item_id=item.evaluation_item_id,
                            source_topic_key=source_topic_key,
                            target_topic_key=target_topic_key,
                        ),
                        assessment_fact_batch_id=assessment_fact_batch_id,
                        source_evaluation_item_id=item.evaluation_item_id,
                        fact_type="support_relation",
                        topic_key=source_topic_key,
                        title=f"{source_label} supports {target_label}",
                        confidence=item.confidence,
                        status="active",
                        created_at=item.evaluated_at,
                        payload={
                            "relation_type": "supports",
                            "directionality": "directed",
                            "source_label": source_label,
                            "source_node_type": source_node_type,
                            "source_topic_key": source_topic_key,
                            "target_label": target_label,
                            "target_node_type": target_node_type,
                            "target_topic_key": target_topic_key,
                            "basis_type": basis_type,
                            "basis_key": basis_key,
                            "description": f"{source_label} supports {target_label}.",
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

    def _topic_key(self, value: str) -> str:
        key = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
        return key or "untagged"

    def _support_relation_fact_id(self, *, evaluation_item_id: str, source_topic_key: str, target_topic_key: str) -> str:
        return f"afi-{evaluation_item_id}-supports-{source_topic_key}-{target_topic_key}"
