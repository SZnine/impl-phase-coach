from pathlib import Path

from review_gate.http_api import create_default_workspace_api
from scripts.seed_demo_data import seed_demo_workspace


def test_seed_demo_workspace_creates_summary_visible_demo_data(tmp_path: Path) -> None:
    db_path = tmp_path / "demo" / "review-workbench-demo.sqlite3"
    session_path = tmp_path / "demo" / "workspace-session-demo.json"

    seed_demo_workspace(db_path=db_path, session_path=session_path)

    api = create_default_workspace_api(db_path=db_path, session_path=session_path)
    summary_view = api.get_knowledge_map_summary_view("proj-1", "stage-1")
    graph_view = api.get_knowledge_graph_main_view(
        "proj-1",
        "stage-1",
        cluster_id="proj-1:stage-1:focus:demo-support-showcase",
    )

    assert db_path.exists()
    assert session_path.exists()
    assert summary_view.focus_clusters
    assert any(item.title == "Support relationships hotspot" for item in summary_view.focus_clusters)
    assert graph_view.selected_cluster is not None
    assert graph_view.nodes
    assert any(item["relation_type"] == "supports" for item in graph_view.relations)


def test_seed_demo_workspace_prioritizes_support_showcase_and_deduplicates_weak_spots(tmp_path: Path) -> None:
    db_path = tmp_path / "demo" / "review-workbench-demo.sqlite3"
    session_path = tmp_path / "demo" / "workspace-session-demo.json"

    seed_demo_workspace(db_path=db_path, session_path=session_path)

    api = create_default_workspace_api(db_path=db_path, session_path=session_path)
    summary_view = api.get_knowledge_map_summary_view("proj-1", "stage-1")

    assert summary_view.focus_clusters[0].title == "Support relationships hotspot"
    assert summary_view.current_weak_spots == ["Needs deeper boundary explanation."]
