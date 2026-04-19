from __future__ import annotations

import re
from dataclasses import dataclass

from review_gate.checkpoint_models import (
    ActiveGraphRevisionPointerRecord,
    GraphRevisionRecord,
    KnowledgeNodeRecord,
    KnowledgeSignalRecord,
)


@dataclass(slots=True)
class KnowledgeSignalGraphProjector:
    projector_version: str = "signal-graph-v1"
    created_by: str = "knowledge_signal_graph_projector"

    def project(
        self,
        *,
        project_id: str,
        scope_type: str,
        scope_ref: str,
        signals: list[KnowledgeSignalRecord],
        created_at: str,
        based_on_revision_id: str | None = None,
    ) -> tuple[GraphRevisionRecord, list[KnowledgeNodeRecord], ActiveGraphRevisionPointerRecord]:
        graph_revision_id = self._revision_id(
            project_id=project_id,
            scope_type=scope_type,
            scope_ref=scope_ref,
            created_at=created_at,
        )
        nodes = self._project_nodes(
            graph_revision_id=graph_revision_id,
            signals=signals,
            created_at=created_at,
        )
        source_signal_ids = sorted({signal.signal_id for signal in signals})
        source_fact_batch_ids = sorted({signal.assessment_fact_batch_id for signal in signals})
        revision = GraphRevisionRecord(
            graph_revision_id=graph_revision_id,
            project_id=project_id,
            scope_type=scope_type,
            scope_ref=scope_ref,
            revision_type="deterministic_signal_projection",
            based_on_revision_id=based_on_revision_id,
            source_fact_batch_ids=source_fact_batch_ids,
            source_signal_ids=source_signal_ids,
            status="active",
            revision_summary=f"{len(source_signal_ids)} signals projected into {len(nodes)} nodes",
            node_count=len(nodes),
            relation_count=0,
            created_by=self.created_by,
            created_at=created_at,
            activated_at=created_at,
            payload={"projector_version": self.projector_version},
        )
        pointer = ActiveGraphRevisionPointerRecord(
            project_id=project_id,
            scope_type=scope_type,
            scope_ref=scope_ref,
            active_graph_revision_id=graph_revision_id,
            updated_at=created_at,
            updated_by=self.created_by,
            payload={"projector_version": self.projector_version},
        )
        return revision, nodes, pointer

    def _project_nodes(
        self,
        *,
        graph_revision_id: str,
        signals: list[KnowledgeSignalRecord],
        created_at: str,
    ) -> list[KnowledgeNodeRecord]:
        grouped: dict[str, list[KnowledgeSignalRecord]] = {}
        for signal in signals:
            grouped.setdefault(signal.topic_key or "untagged", []).append(signal)

        nodes: list[KnowledgeNodeRecord] = []
        for topic_key in sorted(grouped):
            group = sorted(grouped[topic_key], key=lambda item: (-item.confidence, item.signal_id))
            primary = group[0]
            signal_types = sorted({signal.signal_type for signal in group})
            nodes.append(
                KnowledgeNodeRecord(
                    knowledge_node_id=f"kn-{graph_revision_id}-{self._safe_key(topic_key)}",
                    graph_revision_id=graph_revision_id,
                    topic_key=topic_key,
                    label=primary.summary or topic_key,
                    node_type=self._node_type(signal_types),
                    description=str(primary.payload.get("description", "")),
                    source_signal_ids=sorted({signal.signal_id for signal in group}),
                    supporting_fact_ids=sorted({signal.assessment_fact_item_id for signal in group}),
                    confidence=primary.confidence,
                    status="active",
                    created_by=self.created_by,
                    created_at=created_at,
                    updated_at=created_at,
                    payload={
                        "projector_version": self.projector_version,
                        "signal_types": signal_types,
                        "polarity_counts": self._polarity_counts(group),
                    },
                )
            )
        return nodes

    def _node_type(self, signal_types: list[str]) -> str:
        if "weakness" in signal_types:
            return "weakness_topic"
        if signal_types == ["strength"]:
            return "strength_topic"
        return "evidence_topic"

    def _polarity_counts(self, signals: list[KnowledgeSignalRecord]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for signal in signals:
            counts[signal.polarity] = counts.get(signal.polarity, 0) + 1
        return counts

    def _revision_id(self, *, project_id: str, scope_type: str, scope_ref: str, created_at: str) -> str:
        timestamp = re.sub(r"[^0-9]", "", created_at)[:14]
        return f"gr-{self._safe_key(project_id)}-{self._safe_key(scope_type)}-{self._safe_key(scope_ref)}-{timestamp}"

    def _safe_key(self, value: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
        return safe or "untagged"
