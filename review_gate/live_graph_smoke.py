from __future__ import annotations

from typing import Any


def classify_live_graph_smoke_issues(
    *,
    submit_response: dict[str, Any],
    graph_revision: dict[str, Any],
    graph_main: dict[str, Any],
    strict: bool,
) -> list[str]:
    issues: list[str] = []
    if submit_response.get("success") is not True:
        issues.append("submit_failed")
    if graph_revision.get("has_active_revision") is not True:
        issues.append("missing_active_graph_revision")

    revision = graph_revision.get("revision")
    if not isinstance(revision, dict) or _coerce_int(revision.get("node_count")) < 1:
        issues.append("missing_graph_nodes")

    if not graph_main.get("nodes"):
        issues.append("missing_graph_main_nodes")
    if graph_main.get("selected_cluster") is None:
        issues.append("missing_selected_cluster")

    relation_count = _coerce_int(revision.get("relation_count")) if isinstance(revision, dict) else 0
    if strict and relation_count < 1:
        issues.append("missing_relation_in_strict_mode")
    return issues


def build_live_graph_smoke_artifact(
    *,
    submit_response: dict[str, Any],
    graph_revision: dict[str, Any],
    graph_main: dict[str, Any],
    issues: list[str],
    db_path: str,
    model: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "db_path": db_path,
        "issues": list(issues),
        "submit_response": submit_response,
        "graph_revision": graph_revision,
        "graph_main": graph_main,
    }


def format_live_graph_smoke_report(artifact: dict[str, Any]) -> str:
    graph_revision = artifact.get("graph_revision", {})
    revision = graph_revision.get("revision", {}) if isinstance(graph_revision, dict) else {}
    graph_main = artifact.get("graph_main", {})
    selected_cluster = graph_main.get("selected_cluster", {}) if isinstance(graph_main, dict) else {}
    issues = artifact.get("issues") or []
    lines = [
        "# Live Graph Smoke Report",
        "",
        f"model: {artifact.get('model', '')}",
        f"db_path: {artifact.get('db_path', '')}",
        f"issues: {', '.join(issues) if issues else 'none'}",
        "",
        "## Graph Revision",
        f"node_count: {revision.get('node_count', 0)}",
        f"relation_count: {revision.get('relation_count', 0)}",
        "",
        "## Selected Cluster",
        f"center_node_id: {selected_cluster.get('center_node_id', '')}",
        f"neighbor_node_ids: {selected_cluster.get('neighbor_node_ids', [])}",
        f"focus_reason_codes: {selected_cluster.get('focus_reason_codes', [])}",
    ]
    return "\n".join(lines)


def _coerce_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
