from __future__ import annotations

from review_gate.domain import (
    EvidenceRef,
    FocusCluster,
    FocusExplanation,
    KnowledgeNode,
    KnowledgeRelation,
    ProfileSpace,
    UserNodeState,
    current_utc_timestamp,
)
from review_gate.explanation_generators import DeterministicFocusExplanationGenerator, FocusExplanationGenerator
from review_gate.storage_sqlite import SQLiteStore


class ProfileSpaceService:
    def __init__(
        self,
        store: SQLiteStore | None = None,
        generator: FocusExplanationGenerator | None = None,
    ) -> None:
        self._store = store
        self._focus_explanation_generator = generator or DeterministicFocusExplanationGenerator()
        self._stage_summaries: dict[tuple[str, str], dict] = {}
        self._mistakes: dict[str, dict] = {}
        self._index_entries: dict[str, dict] = {}
        self._knowledge_nodes: dict[str, dict] = {}
        self._map_nodes: dict[str, dict] = {}
        self._evidence_refs: dict[str, dict] = {}
        self._user_node_states: dict[tuple[str, str], dict] = {}
        self._knowledge_relations: dict[str, dict] = {}
        self._focus_clusters: dict[str, dict] = {}
        self._focus_explanations: dict[tuple[str, str], dict] = {}

    @classmethod
    def for_testing(cls, generator: FocusExplanationGenerator | None = None) -> "ProfileSpaceService":
        return cls(generator=generator)

    @classmethod
    def with_store(cls, store: SQLiteStore, generator: FocusExplanationGenerator | None = None) -> "ProfileSpaceService":
        return cls(store=store, generator=generator)

    def sync_from_assessment(self, project_id: str, stage_id: str, assessment: dict) -> dict:
        assessment_id = str(assessment.get("assessment_id", "assessment-unknown"))
        verdict = str(assessment.get("verdict", "unknown"))
        core_gaps = [str(item).strip() for item in assessment.get("core_gaps", []) if str(item).strip()]
        misconceptions = [str(item).strip() for item in assessment.get("misconceptions", []) if str(item).strip()]
        has_meaningful_signal = bool(core_gaps or misconceptions)
        confidence = float(assessment.get("confidence", 0.0) or 0.0)
        profile_space_id = self._profile_space_id(project_id)

        mistake_ids: list[str] = []
        mistake_entries: list[dict] = []
        if core_gaps or misconceptions:
            mistake_id = f"{project_id}:{stage_id}:{assessment_id}:mistake-1"
            root_cause = core_gaps[0] if core_gaps else misconceptions[0]
            avoidance = f"Review the stage boundary and revisit: {root_cause}"
            mistake_type = "reasoning_gap" if core_gaps else "boundary_confusion"
            mistake_entry = {
                "mistake_id": mistake_id,
                "label": root_cause,
                "mistake_type": mistake_type,
                "project_id": project_id,
                "stage_id": stage_id,
                "root_cause_summary": root_cause,
                "avoidance_summary": avoidance,
                "status": "active",
            }
            mistake_entries.append(mistake_entry)
            mistake_ids.append(mistake_id)

        index_entry_ids: list[str] = []
        index_entries: list[dict] = []
        if core_gaps:
            entry_id = f"{project_id}:{stage_id}:{assessment_id}:index-1"
            summary = f"Revisit why this stage needs: {core_gaps[0]}"
            index_entry = {
                "entry_id": entry_id,
                "title": core_gaps[0],
                "entry_type": "mistake_avoidance",
                "summary": summary,
                "project_id": project_id,
                "stage_id": stage_id,
                "linked_mistake_ids": list(mistake_ids),
                "status": "active",
            }
            index_entries.append(index_entry)
            index_entry_ids.append(entry_id)

        knowledge_node_ids: list[str] = []
        knowledge_nodes: list[dict] = []
        map_nodes: list[dict] = []
        evidence_ids: list[str] = []
        evidence_refs: list[dict] = []
        user_node_state_ids: list[str] = []
        user_node_states: list[dict] = []
        relation_ids: list[str] = []
        relations: list[dict] = []
        focus_cluster_ids: list[str] = []
        focus_clusters: list[dict] = []
        focus_explanations: list[dict] = []
        if has_meaningful_signal:
            node_label = core_gaps[0] if core_gaps else (misconceptions[0] if misconceptions else verdict)
            node_id = f"{project_id}:{stage_id}:{assessment_id}:node-1"
            knowledge_node = {
                "node_id": node_id,
                "label": node_label,
                "node_type": "decision" if core_gaps else "concept",
                "project_id": project_id,
                "stage_id": stage_id,
                "strength": 1 if verdict == "weak" else 2,
                "linked_mistake_ids": list(mistake_ids),
                "summary": f"Derived from {verdict} assessment in {stage_id}.",
                "status": "active",
            }
            knowledge_nodes.append(knowledge_node)
            knowledge_node_ids.append(node_id)
            map_node = KnowledgeNode(
                node_id=node_id,
                profile_space_id=profile_space_id,
                label=node_label,
                node_type="decision" if core_gaps else "concept",
                abstract_level="L1",
                scope="project-bound",
                canonical_summary=f"Derived from {verdict} assessment in {stage_id}.",
                source_refs=[assessment_id],
                seed_or_generated="generated",
                status="active",
            ).to_dict()
            map_nodes.append(map_node)
            knowledge_node_ids.append(node_id)

            evidence_id = f"{project_id}:{stage_id}:{assessment_id}:evidence-1"
            evidence_ref = {
                "evidence_id": evidence_id,
                "profile_space_id": profile_space_id,
                "node_id": node_id,
                "evidence_type": "assessment",
                "ref_id": assessment_id,
                "project_id": project_id,
                "stage_id": stage_id,
                "summary": f"{verdict} assessment highlighted {node_label}.",
            }
            evidence_refs.append(evidence_ref)
            evidence_ids.append(evidence_id)

            user_node_state = {
                "profile_space_id": profile_space_id,
                "node_id": node_id,
                "activation_status": "active",
                "mastery_status": verdict,
                "review_needed": verdict != "strong",
                "weak_signal_count": len(core_gaps) + len(misconceptions),
                "linked_project_count": 1,
                "last_seen_at": current_utc_timestamp(),
                "confidence": confidence,
            }
            user_node_states.append(user_node_state)
            user_node_state_ids.append(f"{profile_space_id}:{node_id}")

            stable_center_node_id = node_id
            if core_gaps:
                stable_center_node_id = self._stable_node_id(profile_space_id, "knowledge", core_gaps[0])
                stable_node = KnowledgeNode(
                    node_id=stable_center_node_id,
                    profile_space_id=profile_space_id,
                    label=core_gaps[0],
                    node_type="decision",
                    abstract_level="L2",
                    scope="project-bound",
                    canonical_summary=f"Stable knowledge area for {core_gaps[0]}.",
                    source_refs=[assessment_id],
                    seed_or_generated="generated",
                    status="active",
                ).to_dict()
                map_nodes.append(stable_node)
                knowledge_node_ids.append(stable_center_node_id)

                stable_evidence_id = f"{project_id}:{stage_id}:{assessment_id}:evidence-2"
                evidence_refs.append(
                    {
                        "evidence_id": stable_evidence_id,
                        "profile_space_id": profile_space_id,
                        "node_id": stable_center_node_id,
                        "evidence_type": "assessment",
                        "ref_id": assessment_id,
                        "project_id": project_id,
                        "stage_id": stage_id,
                        "summary": f"{verdict} assessment reinforced {core_gaps[0]}.",
                    }
                )
                evidence_ids.append(stable_evidence_id)

                stable_state = {
                    "profile_space_id": profile_space_id,
                    "node_id": stable_center_node_id,
                    "activation_status": "active",
                    "mastery_status": verdict,
                    "review_needed": verdict != "strong",
                    "weak_signal_count": len(core_gaps) + len(misconceptions),
                    "linked_project_count": 1,
                    "last_seen_at": current_utc_timestamp(),
                    "confidence": confidence,
                }
                user_node_states.append(stable_state)
                user_node_state_ids.append(f"{profile_space_id}:{stable_center_node_id}")

                abstracts_relation_id = f"{project_id}:{stage_id}:{self._slugify(core_gaps[0])}:abstracts:{assessment_id}"
                relations.append(
                    {
                        "relation_id": abstracts_relation_id,
                        "profile_space_id": profile_space_id,
                        "source_node_id": stable_center_node_id,
                        "target_node_id": node_id,
                        "relation_type": "abstracts",
                        "strength": 2,
                        "evidence_ids": [stable_evidence_id],
                        "status": "active",
                    }
                )
                relation_ids.append(abstracts_relation_id)

            focus_neighbor_node_ids: list[str] = []
            if misconceptions:
                misconception_label = misconceptions[0]
                mistake_node_id = self._stable_node_id(profile_space_id, "mistake", misconception_label)
                mistake_node = KnowledgeNode(
                    node_id=mistake_node_id,
                    profile_space_id=profile_space_id,
                    label=misconception_label,
                    node_type="mistake",
                    abstract_level="L1",
                    scope="personal",
                    canonical_summary=f"Repeated misconception: {misconception_label}.",
                    source_refs=[assessment_id],
                    seed_or_generated="generated",
                    status="active",
                ).to_dict()
                map_nodes.append(mistake_node)
                knowledge_node_ids.append(mistake_node_id)
                focus_neighbor_node_ids.append(mistake_node_id)

                misconception_evidence_id = f"{project_id}:{stage_id}:{assessment_id}:evidence-3"
                evidence_refs.append(
                    {
                        "evidence_id": misconception_evidence_id,
                        "profile_space_id": profile_space_id,
                        "node_id": mistake_node_id,
                        "evidence_type": "assessment",
                        "ref_id": assessment_id,
                        "project_id": project_id,
                        "stage_id": stage_id,
                        "summary": f"{verdict} assessment exposed misconception: {misconception_label}.",
                    }
                )
                evidence_ids.append(misconception_evidence_id)

                misconception_state = {
                    "profile_space_id": profile_space_id,
                    "node_id": mistake_node_id,
                    "activation_status": "active",
                    "mastery_status": verdict,
                    "review_needed": True,
                    "weak_signal_count": len(core_gaps) + len(misconceptions),
                    "linked_project_count": 1,
                    "last_seen_at": current_utc_timestamp(),
                    "confidence": confidence,
                }
                user_node_states.append(misconception_state)
                user_node_state_ids.append(f"{profile_space_id}:{mistake_node_id}")

                causes_relation_id = (
                    f"{project_id}:{stage_id}:{self._slugify(node_label)}:causes_mistake:{self._slugify(misconception_label)}"
                )
                relations.append(
                    {
                        "relation_id": causes_relation_id,
                        "profile_space_id": profile_space_id,
                        "source_node_id": stable_center_node_id,
                        "target_node_id": mistake_node_id,
                        "relation_type": "causes_mistake",
                        "strength": 2,
                        "evidence_ids": [misconception_evidence_id],
                        "status": "active",
                    }
                )
                relation_ids.append(causes_relation_id)

            focus_cluster_id = f"{project_id}:{stage_id}:focus:{self._slugify(node_label)}"
            focus_reason_codes = ["current_project_hit"]
            if verdict != "strong":
                focus_reason_codes.append("weak_signal_active")
            focus_cluster = self._merge_focus_cluster(
                project_id=project_id,
                stage_id=stage_id,
                cluster_id=focus_cluster_id,
                profile_space_id=profile_space_id,
                title=f"{node_label} hotspot",
                center_node_id=stable_center_node_id,
                neighbor_node_ids=focus_neighbor_node_ids,
                focus_reason_codes=focus_reason_codes,
                focus_reason_summary=f"This area is active because the current stage exposed {node_label}.",
                confidence=confidence,
            )
            focus_clusters.append(focus_cluster)
            focus_cluster_ids.append(focus_cluster_id)
            focus_explanations.append(
                self._build_focus_explanation(
                    profile_space_id=profile_space_id,
                    cluster=focus_cluster,
                )
            )

        latest_summary = (
            f"synced {verdict} assessment with {len(index_entry_ids)} knowledge entries and {len(mistake_ids)} mistakes"
            if (index_entry_ids or mistake_ids)
            else f"synced {verdict} assessment without durable knowledge additions"
        )

        if self._store is None:
            for item in mistake_entries:
                self._mistakes[item["mistake_id"]] = dict(item)
            for item in index_entries:
                self._index_entries[item["entry_id"]] = dict(item)
            for item in knowledge_nodes:
                self._knowledge_nodes[item["node_id"]] = dict(item)
            for item in map_nodes:
                self._map_nodes[item["node_id"]] = dict(item)
            for item in evidence_refs:
                self._evidence_refs[item["evidence_id"]] = dict(item)
            for item in user_node_states:
                self._user_node_states[(item["profile_space_id"], item["node_id"])] = dict(item)
            for item in relations:
                self._knowledge_relations[item["relation_id"]] = dict(item)
            for item in focus_clusters:
                self._focus_clusters[item["cluster_id"]] = dict(item)
            for item in focus_explanations:
                self._focus_explanations[(item["subject_type"], item["subject_id"])] = dict(item)

            self._stage_summaries[(project_id, stage_id)] = self._build_stage_summary(project_id, stage_id, latest_summary)
        else:
            for item in mistake_entries:
                self._store.upsert_profile_mistake(profile_space_id, item)
            for item in index_entries:
                self._store.upsert_profile_index_entry(profile_space_id, item)
            for item in knowledge_nodes:
                self._store.upsert_profile_knowledge_node(profile_space_id, item)
            for item in map_nodes:
                self._store.upsert_knowledge_node(KnowledgeNode.from_dict(item))
            for item in evidence_refs:
                self._store.upsert_evidence_ref(EvidenceRef.from_dict(item))
            for item in user_node_states:
                self._store.upsert_user_node_state(UserNodeState.from_dict(item))
            for item in relations:
                self._store.upsert_knowledge_relation(KnowledgeRelation.from_dict(item))
            for item in focus_clusters:
                self._store.upsert_focus_cluster(FocusCluster.from_dict(item))
            for item in focus_explanations:
                self._store.upsert_focus_explanation(FocusExplanation.from_dict(item))

            summary = self._build_stage_summary(project_id, stage_id, latest_summary)
            self._store.upsert_profile_stage_summary(profile_space_id, project_id, stage_id, summary)
            self._store.upsert_profile_space(self._build_profile_space(project_id, latest_summary))

        return {
            "profile_space_id": profile_space_id,
            "project_id": project_id,
            "stage_id": stage_id,
            "assessment_id": assessment_id,
            "mistake_ids": mistake_ids,
            "index_entry_ids": index_entry_ids,
            "knowledge_node_ids": knowledge_node_ids,
            "evidence_ids": evidence_ids,
            "user_node_state_ids": user_node_state_ids,
            "relation_ids": relation_ids,
            "focus_cluster_ids": focus_cluster_ids,
            "summary": f"synced {verdict} assessment for {project_id}/{stage_id}",
        }

    def get_stage_knowledge_summary(self, project_id: str, stage_id: str) -> dict:
        if self._store is not None:
            summary = self._store.get_profile_stage_summary(self._profile_space_id(project_id), project_id, stage_id)
            if summary is None:
                return self._empty_summary()
            return dict(summary)

        summary = self._stage_summaries.get((project_id, stage_id))
        if summary is None:
            return self._empty_summary()
        return dict(summary)

    def get_project_knowledge_summary(self, project_id: str) -> dict:
        if self._store is not None:
            summaries = self._store.list_profile_stage_summaries(
                profile_space_id=self._profile_space_id(project_id),
                project_id=project_id,
            )
        else:
            summaries = [summary for (current_project_id, _), summary in self._stage_summaries.items() if current_project_id == project_id]

        if not summaries:
            return self._empty_summary()
        return {
            "knowledge_entry_count": sum(int(summary.get("knowledge_entry_count", 0)) for summary in summaries),
            "mistake_count": sum(int(summary.get("mistake_count", 0)) for summary in summaries),
            "latest_summary": str(summaries[-1].get("latest_summary", "No knowledge extracted yet.")),
        }

    def list_mistakes(self, project_id: str | None = None, stage_id: str | None = None) -> list[dict]:
        if self._store is not None:
            profile_space_id = self._profile_space_id(project_id) if project_id is not None else None
            return self._store.list_profile_mistakes(profile_space_id=profile_space_id, project_id=project_id, stage_id=stage_id)

        mistakes = list(self._mistakes.values())
        if project_id is not None:
            mistakes = [item for item in mistakes if item["project_id"] == project_id]
        if stage_id is not None:
            mistakes = [item for item in mistakes if item["stage_id"] == stage_id]
        return [dict(item) for item in mistakes]

    def list_index_entries(self, project_id: str | None = None, stage_id: str | None = None) -> list[dict]:
        if self._store is not None:
            profile_space_id = self._profile_space_id(project_id) if project_id is not None else None
            return self._store.list_profile_index_entries(profile_space_id=profile_space_id, project_id=project_id, stage_id=stage_id)

        entries = list(self._index_entries.values())
        if project_id is not None:
            entries = [item for item in entries if item["project_id"] == project_id]
        if stage_id is not None:
            entries = [item for item in entries if item["stage_id"] == stage_id]
        return [dict(item) for item in entries]

    def list_knowledge_nodes(self, project_id: str | None = None, stage_id: str | None = None) -> list[dict]:
        if self._store is not None:
            profile_space_id = self._profile_space_id(project_id) if project_id is not None else None
            return self._store.list_profile_knowledge_nodes(profile_space_id=profile_space_id, project_id=project_id, stage_id=stage_id)

        nodes = list(self._knowledge_nodes.values())
        if project_id is not None:
            nodes = [item for item in nodes if item["project_id"] == project_id]
        if stage_id is not None:
            nodes = [item for item in nodes if item["stage_id"] == stage_id]
        return [dict(item) for item in nodes]

    def list_evidence_refs(self, project_id: str | None = None, stage_id: str | None = None) -> list[dict]:
        if self._store is not None:
            profile_space_id = self._profile_space_id(project_id) if project_id is not None else None
            return [
                item.to_dict()
                for item in self._store.list_evidence_refs(
                    profile_space_id=profile_space_id,
                    project_id=project_id,
                    stage_id=stage_id,
                )
            ]

        items = list(self._evidence_refs.values())
        if project_id is not None:
            items = [item for item in items if item["project_id"] == project_id]
        if stage_id is not None:
            items = [item for item in items if item["stage_id"] == stage_id]
        return [dict(item) for item in items]

    def list_map_nodes(self, project_id: str | None = None, stage_id: str | None = None) -> list[dict]:
        if self._store is not None:
            profile_space_id = self._profile_space_id(project_id) if project_id is not None else None
            items = [item.to_dict() for item in self._store.list_knowledge_nodes(profile_space_id=profile_space_id)]
        else:
            items = [dict(item) for item in self._map_nodes.values()]

        if project_id is None and stage_id is None:
            return items

        matching_node_ids = {
            item["node_id"]
            for item in self.list_evidence_refs(project_id=project_id, stage_id=stage_id)
        }
        return [item for item in items if item["node_id"] in matching_node_ids]

    def list_user_node_states(self, project_id: str | None = None, stage_id: str | None = None) -> list[dict]:
        if self._store is not None:
            profile_space_id = self._profile_space_id(project_id) if project_id is not None else None
            items = [item.to_dict() for item in self._store.list_user_node_states(profile_space_id=profile_space_id)]
        else:
            items = [dict(item) for item in self._user_node_states.values()]

        if project_id is None and stage_id is None:
            return items

        matching_node_ids = {
            item["node_id"]
            for item in self.list_evidence_refs(project_id=project_id, stage_id=stage_id)
        }
        return [item for item in items if item["node_id"] in matching_node_ids]

    def list_knowledge_relations(self, project_id: str | None = None, stage_id: str | None = None) -> list[dict]:
        if self._store is not None:
            profile_space_id = self._profile_space_id(project_id) if project_id is not None else None
            items = [item.to_dict() for item in self._store.list_knowledge_relations(profile_space_id=profile_space_id)]
        else:
            items = [dict(item) for item in self._knowledge_relations.values()]

        if project_id is None and stage_id is None:
            return items

        matching_node_ids = {item["node_id"] for item in self.list_map_nodes(project_id=project_id, stage_id=stage_id)}
        return [
            item
            for item in items
            if item["source_node_id"] in matching_node_ids and item["target_node_id"] in matching_node_ids
        ]

    def list_focus_clusters(self, project_id: str | None = None, stage_id: str | None = None) -> list[dict]:
        if self._store is not None:
            profile_space_id = self._profile_space_id(project_id) if project_id is not None else None
            items = [item.to_dict() for item in self._store.list_focus_clusters(profile_space_id=profile_space_id)]
        else:
            items = [dict(item) for item in self._focus_clusters.values()]

        if project_id is None and stage_id is None:
            return items

        matching_node_ids = {item["node_id"] for item in self.list_map_nodes(project_id=project_id, stage_id=stage_id)}
        return [item for item in items if item["center_node_id"] in matching_node_ids]

    def get_focus_explanation(self, subject_type: str, subject_id: str, project_id: str | None = None) -> dict | None:
        if self._store is not None:
            profile_space_id = self._profile_space_id(project_id) if project_id is not None else None
            item = self._store.get_focus_explanation(
                subject_type=subject_type,
                subject_id=subject_id,
                profile_space_id=profile_space_id,
            )
            return item.to_dict() if item is not None else None

        item = self._focus_explanations.get((subject_type, subject_id))
        return dict(item) if item is not None else None

    def _build_stage_summary(self, project_id: str, stage_id: str, latest_summary: str) -> dict:
        return {
            "knowledge_entry_count": len(self.list_index_entries(project_id=project_id, stage_id=stage_id)),
            "mistake_count": len(self.list_mistakes(project_id=project_id, stage_id=stage_id)),
            "latest_summary": latest_summary,
        }

    def _build_profile_space(self, project_id: str, latest_summary: str) -> ProfileSpace:
        return ProfileSpace(
            profile_space_id=self._profile_space_id(project_id),
            project_id=project_id,
            label="default",
            summary=latest_summary,
            mistake_ids=[item["mistake_id"] for item in self.list_mistakes(project_id=project_id)],
            index_entry_ids=[item["entry_id"] for item in self.list_index_entries(project_id=project_id)],
            knowledge_node_ids=[item["node_id"] for item in self.list_knowledge_nodes(project_id=project_id)],
            proposal_ids=[],
        )

    def _profile_space_id(self, project_id: str) -> str:
        return f"profile-space:{project_id}"

    def _empty_summary(self) -> dict:
        return {
            "knowledge_entry_count": 0,
            "mistake_count": 0,
            "latest_summary": "No knowledge extracted yet.",
        }

    def _stable_node_id(self, profile_space_id: str, prefix: str, label: str) -> str:
        return f"{profile_space_id}:{prefix}:{self._slugify(label)}"

    def _slugify(self, value: str) -> str:
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
        while "--" in slug:
            slug = slug.replace("--", "-")
        return slug or "unknown"

    def _merge_focus_cluster(
        self,
        *,
        project_id: str,
        stage_id: str,
        cluster_id: str,
        profile_space_id: str,
        title: str,
        center_node_id: str,
        neighbor_node_ids: list[str],
        focus_reason_codes: list[str],
        focus_reason_summary: str,
        confidence: float,
    ) -> dict:
        existing = next(
            (item for item in self.list_focus_clusters(project_id=project_id, stage_id=stage_id) if item["cluster_id"] == cluster_id),
            None,
        )
        merged_neighbor_node_ids: list[str] = []
        for node_id in [*(existing.get("neighbor_node_ids", []) if existing is not None else []), *neighbor_node_ids]:
            if node_id not in merged_neighbor_node_ids:
                merged_neighbor_node_ids.append(node_id)

        merged_reason_codes: list[str] = []
        for code in [*(existing.get("focus_reason_codes", []) if existing is not None else []), *focus_reason_codes]:
            if code not in merged_reason_codes:
                merged_reason_codes.append(code)

        return {
            "cluster_id": cluster_id,
            "profile_space_id": profile_space_id,
            "title": title if existing is None else existing.get("title", title),
            "center_node_id": center_node_id if existing is None else existing.get("center_node_id", center_node_id),
            "neighbor_node_ids": merged_neighbor_node_ids,
            "focus_reason_codes": merged_reason_codes,
            "focus_reason_summary": focus_reason_summary if existing is None else existing.get("focus_reason_summary", focus_reason_summary),
            "generated_from": "current_project",
            "confidence": max(confidence, float(existing.get("confidence", 0.0))) if existing is not None else confidence,
            "last_generated_at": current_utc_timestamp(),
            "is_pinned": bool(existing.get("is_pinned", False)) if existing is not None else False,
            "status": "active",
        }

    def _build_focus_explanation(self, *, profile_space_id: str, cluster: dict) -> dict:
        return self._focus_explanation_generator.build_focus_cluster_explanation(
            profile_space_id=profile_space_id,
            cluster=cluster,
        ).to_dict()
