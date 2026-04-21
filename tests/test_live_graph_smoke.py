from review_gate.live_graph_smoke import (
    build_live_graph_smoke_artifact,
    classify_live_graph_smoke_issues,
    format_live_graph_smoke_report,
)


def test_classify_live_graph_smoke_issues_requires_graph_node_and_cluster() -> None:
    issues = classify_live_graph_smoke_issues(
        submit_response={"success": True},
        graph_revision={
            "has_active_revision": True,
            "revision": {"node_count": 1, "relation_count": 0},
            "nodes": [{"knowledge_node_id": "kn-1"}],
            "relations": [],
        },
        graph_main={
            "nodes": [{"node_id": "kn-1"}],
            "relations": [],
            "selected_cluster": {"center_node_id": "kn-1"},
        },
        strict=False,
    )

    assert issues == []


def test_classify_live_graph_smoke_issues_treats_missing_relation_as_strict_only() -> None:
    base_kwargs = {
        "submit_response": {"success": True},
        "graph_revision": {
            "has_active_revision": True,
            "revision": {"node_count": 1, "relation_count": 0},
            "nodes": [{"knowledge_node_id": "kn-1"}],
            "relations": [],
        },
        "graph_main": {
            "nodes": [{"node_id": "kn-1"}],
            "relations": [],
            "selected_cluster": {"center_node_id": "kn-1"},
        },
    }

    assert classify_live_graph_smoke_issues(**base_kwargs, strict=False) == []
    assert classify_live_graph_smoke_issues(**base_kwargs, strict=True) == ["missing_relation_in_strict_mode"]


def test_build_live_graph_smoke_artifact_omits_sensitive_provider_config() -> None:
    artifact = build_live_graph_smoke_artifact(
        submit_response={"success": True},
        graph_revision={"has_active_revision": True},
        graph_main={"nodes": []},
        issues=[],
        db_path="C:/tmp/smoke.sqlite3",
        model="gpt-5.4-mini",
    )

    assert artifact["model"] == "gpt-5.4-mini"
    assert artifact["db_path"] == "C:/tmp/smoke.sqlite3"
    assert "api_key" not in str(artifact).lower()
    assert "authorization" not in str(artifact).lower()


def test_format_live_graph_smoke_report_surfaces_graph_counts_and_cluster() -> None:
    report = format_live_graph_smoke_report(
        {
            "model": "gpt-5.4-mini",
            "issues": [],
            "submit_response": {"success": True},
            "graph_revision": {
                "revision": {"node_count": 2, "relation_count": 1},
            },
            "graph_main": {
                "selected_cluster": {
                    "center_node_id": "kn-target",
                    "neighbor_node_ids": ["kn-source"],
                    "focus_reason_codes": ["weak_signal_active", "relation_connected"],
                }
            },
        }
    )

    assert "model: gpt-5.4-mini" in report
    assert "node_count: 2" in report
    assert "relation_count: 1" in report
    assert "issues: none" in report
    assert "center_node_id: kn-target" in report
