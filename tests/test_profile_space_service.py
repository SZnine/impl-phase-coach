from pathlib import Path

from review_gate.profile_space_service import ProfileSpaceService
from review_gate.storage_sqlite import SQLiteStore


def test_profile_space_service_syncs_mistake_and_index_entries() -> None:
    service = ProfileSpaceService.for_testing()

    result = service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-1",
            "verdict": "partial",
            "misconceptions": ["Boundary confusion"],
            "core_gaps": ["Decision awareness"],
        },
    )

    assert result["project_id"] == "proj-1"
    assert result["stage_id"] == "stage-1"
    assert result["mistake_ids"]
    assert result["index_entry_ids"]
    assert result["knowledge_node_ids"]
    assert result["summary"].startswith("synced partial assessment")

    summary = service.get_stage_knowledge_summary("proj-1", "stage-1")
    assert summary["knowledge_entry_count"] == 1
    assert summary["mistake_count"] == 1
    assert "synced partial assessment" in summary["latest_summary"]


def test_profile_space_service_lists_durable_mistake_entries() -> None:
    service = ProfileSpaceService.for_testing()
    service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-1",
            "verdict": "partial",
            "misconceptions": ["Boundary confusion"],
            "core_gaps": ["Decision awareness"],
        },
    )

    mistakes = service.list_mistakes(project_id="proj-1", stage_id="stage-1")

    assert len(mistakes) == 1
    assert mistakes[0]["project_id"] == "proj-1"
    assert mistakes[0]["stage_id"] == "stage-1"
    assert mistakes[0]["root_cause_summary"] == "Decision awareness"
    assert mistakes[0]["avoidance_summary"].startswith("Review the stage boundary")


def test_profile_space_service_lists_durable_index_entries() -> None:
    service = ProfileSpaceService.for_testing()
    service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-4",
            "verdict": "partial",
            "misconceptions": [],
            "core_gaps": ["Decision awareness"],
        },
    )

    entries = service.list_index_entries(project_id="proj-1", stage_id="stage-1")

    assert len(entries) == 1
    assert entries[0]["project_id"] == "proj-1"
    assert entries[0]["stage_id"] == "stage-1"
    assert entries[0]["title"] == "Decision awareness"
    assert entries[0]["entry_type"] == "mistake_avoidance"


def test_profile_space_service_lists_durable_knowledge_nodes() -> None:
    service = ProfileSpaceService.for_testing()
    service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-5",
            "verdict": "partial",
            "misconceptions": ["Boundary confusion"],
            "core_gaps": ["Decision awareness"],
        },
    )

    nodes = service.list_knowledge_nodes(project_id="proj-1", stage_id="stage-1")

    assert len(nodes) == 1
    assert nodes[0]["project_id"] == "proj-1"
    assert nodes[0]["stage_id"] == "stage-1"
    assert nodes[0]["label"] == "Decision awareness"
    assert nodes[0]["node_type"] == "decision"
    assert nodes[0]["linked_mistake_ids"]


def test_profile_space_service_skips_knowledge_nodes_without_meaningful_signals() -> None:
    service = ProfileSpaceService.for_testing()

    result = service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-2",
            "verdict": "unknown",
            "misconceptions": [],
            "core_gaps": [],
        },
    )

    assert result["mistake_ids"] == []
    assert result["index_entry_ids"] == []
    assert result["knowledge_node_ids"] == []


def test_profile_space_service_persists_entries_across_service_instances(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()

    writer = ProfileSpaceService.with_store(store)
    writer.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-persist-1",
            "verdict": "partial",
            "misconceptions": ["Boundary confusion"],
            "core_gaps": ["Decision awareness"],
        },
    )

    reader = ProfileSpaceService.with_store(store)
    summary = reader.get_stage_knowledge_summary("proj-1", "stage-1")

    assert summary["knowledge_entry_count"] == 1
    assert summary["mistake_count"] == 1
    assert reader.list_mistakes(project_id="proj-1", stage_id="stage-1")[0]["label"] == "Decision awareness"
    assert reader.list_index_entries(project_id="proj-1", stage_id="stage-1")[0]["title"] == "Decision awareness"
    assert reader.list_knowledge_nodes(project_id="proj-1", stage_id="stage-1")[0]["label"] == "Decision awareness"
    assert store.get_profile_space("profile-space:proj-1") is not None


def test_profile_space_service_keeps_zero_summary_for_weak_assessment_without_gaps() -> None:
    service = ProfileSpaceService.for_testing()

    service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-3",
            "verdict": "weak",
            "misconceptions": [],
            "core_gaps": [],
        },
    )

    summary = service.get_stage_knowledge_summary("proj-1", "stage-1")
    assert summary["knowledge_entry_count"] == 0
    assert summary["mistake_count"] == 0
    assert summary["latest_summary"] == "synced weak assessment without durable knowledge additions"
    assert service.list_mistakes(project_id="proj-1", stage_id="stage-1") == []
    assert service.list_index_entries(project_id="proj-1", stage_id="stage-1") == []
    assert service.list_knowledge_nodes(project_id="proj-1", stage_id="stage-1") == []


def test_profile_space_service_skips_knowledge_nodes_for_strong_assessment_without_gaps() -> None:
    service = ProfileSpaceService.for_testing()

    result = service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "a-6",
            "verdict": "strong",
            "misconceptions": [],
            "core_gaps": [],
        },
    )

    summary = service.get_stage_knowledge_summary("proj-1", "stage-1")
    assert result["knowledge_node_ids"] == []
    assert summary["knowledge_entry_count"] == 0
    assert summary["mistake_count"] == 0
    assert summary["latest_summary"] == "synced strong assessment without durable knowledge additions"
    assert service.list_knowledge_nodes(project_id="proj-1", stage_id="stage-1") == []


def test_sync_from_assessment_creates_node_evidence_and_user_state(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    service = ProfileSpaceService.with_store(store)

    result = service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "assessment-1",
            "verdict": "partial",
            "core_gaps": ["State and return value separation"],
            "misconceptions": ["Boundary confusion"],
            "confidence": 0.78,
        },
    )

    assert result["knowledge_node_ids"]
    assert result["evidence_ids"]
    assert result["user_node_state_ids"]

    nodes = service.list_knowledge_nodes(project_id="proj-1", stage_id="stage-1")
    assert nodes[0]["label"] == "State and return value separation"

    evidence_refs = service.list_evidence_refs(project_id="proj-1", stage_id="stage-1")
    assert any(item["node_id"] == result["knowledge_node_ids"][0] for item in evidence_refs)
    assert all(item["evidence_type"] == "assessment" for item in evidence_refs)

    states = service.list_user_node_states(project_id="proj-1", stage_id="stage-1")
    matching_state = next(item for item in states if item["node_id"] == result["knowledge_node_ids"][0])
    assert matching_state["mastery_status"] == "partial"
    assert matching_state["review_needed"] is True


def test_sync_from_assessment_generates_minimal_relations_and_stable_focus_cluster() -> None:
    service = ProfileSpaceService.for_testing()

    result = service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "assessment-2",
            "verdict": "partial",
            "core_gaps": ["State and return value separation"],
            "misconceptions": ["Boundary confusion"],
            "confidence": 0.81,
        },
    )

    relations = service.list_knowledge_relations(project_id="proj-1", stage_id="stage-1")
    relation_types = {item["relation_type"] for item in relations}
    assert relation_types == {"abstracts", "causes_mistake"}

    clusters = service.list_focus_clusters(project_id="proj-1", stage_id="stage-1")
    assert len(clusters) == 1
    assert clusters[0]["cluster_id"] == result["focus_cluster_ids"][0]
    assert clusters[0]["center_node_id"] != result["knowledge_node_ids"][0]
    assert "weak_signal_active" in clusters[0]["focus_reason_codes"]


def test_sync_from_assessment_reuses_focus_cluster_for_same_stage_hotspot() -> None:
    service = ProfileSpaceService.for_testing()

    first = service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "assessment-3",
            "verdict": "partial",
            "core_gaps": ["Decision awareness"],
            "misconceptions": ["Boundary confusion"],
            "confidence": 0.74,
        },
    )
    second = service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "assessment-4",
            "verdict": "partial",
            "core_gaps": ["Decision awareness"],
            "misconceptions": ["Boundary confusion"],
            "confidence": 0.88,
        },
    )

    clusters = service.list_focus_clusters(project_id="proj-1", stage_id="stage-1")
    assert len(clusters) == 1
    assert first["focus_cluster_ids"] == second["focus_cluster_ids"]
    assert clusters[0]["focus_reason_codes"] == ["current_project_hit", "weak_signal_active"]


def test_sync_from_assessment_writes_focus_explanation_cache() -> None:
    service = ProfileSpaceService.for_testing()

    result = service.sync_from_assessment(
        project_id="proj-1",
        stage_id="stage-1",
        assessment={
            "assessment_id": "assessment-5",
            "verdict": "partial",
            "core_gaps": ["Decision awareness"],
            "misconceptions": [],
            "confidence": 0.76,
        },
    )

    explanation = service.get_focus_explanation("focus_cluster", result["focus_cluster_ids"][0], project_id="proj-1")

    assert explanation is not None
    assert explanation["subject_type"] == "focus_cluster"
    assert explanation["subject_id"] == result["focus_cluster_ids"][0]
    assert explanation["generated_by"] == "deterministic"
    assert "Decision awareness" in explanation["summary"]
