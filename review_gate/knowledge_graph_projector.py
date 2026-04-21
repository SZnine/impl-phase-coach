from __future__ import annotations

import re
from dataclasses import dataclass

from review_gate.checkpoint_models import (
    ActiveGraphRevisionPointerRecord,
    GraphRevisionRecord,
    KnowledgeNodeRecord,
    KnowledgeRelationRecord,
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
    ) -> tuple[
        GraphRevisionRecord,
        list[KnowledgeNodeRecord],
        list[KnowledgeRelationRecord],
        ActiveGraphRevisionPointerRecord,
    ]:
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
        relations = self._project_relations(
            graph_revision_id=graph_revision_id,
            signals=signals,
            nodes=nodes,
            created_at=created_at,
        )
        source_signal_ids = sorted({signal.signal_id for signal in signals})
        source_fact_batch_ids = sorted({signal.assessment_fact_batch_id for signal in signals})
        revision_summary = f"{len(source_signal_ids)} signals projected into {len(nodes)} nodes"
        if relations:
            revision_summary = f"{revision_summary} and {len(relations)} relations"
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
            revision_summary=revision_summary,
            node_count=len(nodes),
            relation_count=len(relations),
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
        return revision, nodes, relations, pointer

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

    def _project_relations(
        self,
        *,
        graph_revision_id: str,
        signals: list[KnowledgeSignalRecord],
        nodes: list[KnowledgeNodeRecord],
        created_at: str,
    ) -> list[KnowledgeRelationRecord]:
        node_by_topic = {node.topic_key: node for node in nodes}
        relations: list[KnowledgeRelationRecord] = []
        for signal in sorted(signals, key=lambda item: item.signal_id):
            if signal.signal_type != "support_relation":
                continue
            relation_type = str(signal.payload.get("relation_type", "")).strip()
            source_topic_key = str(signal.payload.get("source_topic_key", signal.topic_key)).strip()
            target_topic_key = str(signal.payload.get("target_topic_key", "")).strip()
            if relation_type != "supports" or not source_topic_key or not target_topic_key:
                continue
            source_node = node_by_topic.get(source_topic_key)
            target_node = node_by_topic.get(target_topic_key)
            if source_node is None or target_node is None:
                continue
            relation_id = (
                f"kr-{graph_revision_id}-"
                f"{self._safe_key(source_topic_key)}-supports-{self._safe_key(target_topic_key)}"
            )
            relations.append(
                KnowledgeRelationRecord(
                    knowledge_relation_id=relation_id,
                    graph_revision_id=graph_revision_id,
                    from_node_id=source_node.knowledge_node_id,
                    to_node_id=target_node.knowledge_node_id,
                    relation_type="supports",
                    directionality=str(signal.payload.get("directionality", "directed")),
                    description=str(signal.payload.get("description", signal.summary)),
                    source_signal_ids=[signal.signal_id],
                    supporting_fact_ids=[signal.assessment_fact_item_id],
                    confidence=signal.confidence,
                    status=signal.status,
                    created_by=self.created_by,
                    created_at=created_at,
                    updated_at=created_at,
                    payload={
                        "projector_version": self.projector_version,
                        "basis_type": str(signal.payload.get("basis_type", "")),
                        "basis_key": str(signal.payload.get("basis_key", "")),
                    },
                )
            )
        return relations

    def _node_type(self, signal_types: list[str]) -> str:
        if "weakness" in signal_types:
            return "weakness_topic"
        if signal_types == ["strength"]:
            return "strength_topic"
        if "support_relation" in signal_types:
            return "evidence_topic"
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
