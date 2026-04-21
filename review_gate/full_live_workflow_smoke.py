from __future__ import annotations

from typing import Any


def resolve_first_generated_transport_question_id(
    *,
    generation_response: dict[str, Any],
    question_set_id: str,
) -> str:
    questions = generation_response.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("generation_response must contain at least one question")
    first_question = questions[0]
    if not isinstance(first_question, dict):
        raise ValueError("generation_response question item must be an object")
    raw_question_id = str(first_question.get("question_id") or first_question.get("id") or "").strip()
    if not raw_question_id:
        raise ValueError("generation_response first question missing question_id")
    if raw_question_id.startswith(f"{question_set_id}-"):
        return raw_question_id
    return f"{question_set_id}-{raw_question_id}"


def classify_full_live_workflow_smoke_issues(
    *,
    generation_response: dict[str, Any],
    submit_response: dict[str, Any],
    graph_revision: dict[str, Any],
    graph_main: dict[str, Any],
    strict: bool,
) -> list[str]:
    issues: list[str] = []
    questions = generation_response.get("questions")
    if not isinstance(questions, list) or not questions:
        issues.append("missing_generated_questions")
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


def build_full_live_workflow_smoke_artifact(
    *,
    generation_response: dict[str, Any],
    selected_question_id: str,
    submit_response: dict[str, Any],
    graph_revision: dict[str, Any],
    graph_main: dict[str, Any],
    issues: list[str],
    db_path: str,
    project_model: str,
    evaluator_model: str,
) -> dict[str, Any]:
    return {
        "project_model": project_model,
        "evaluator_model": evaluator_model,
        "db_path": db_path,
        "selected_question_id": selected_question_id,
        "issues": list(issues),
        "generation_response": generation_response,
        "submit_response": submit_response,
        "graph_revision": graph_revision,
        "graph_main": graph_main,
    }


def format_full_live_workflow_smoke_report(artifact: dict[str, Any]) -> str:
    generation_response = artifact.get("generation_response", {})
    questions = generation_response.get("questions", []) if isinstance(generation_response, dict) else []
    generated_question_count = len(questions) if isinstance(questions, list) else 0
    graph_revision = artifact.get("graph_revision", {})
    revision = graph_revision.get("revision", {}) if isinstance(graph_revision, dict) else {}
    graph_main = artifact.get("graph_main", {})
    selected_cluster = graph_main.get("selected_cluster", {}) if isinstance(graph_main, dict) else {}
    issues = artifact.get("issues") or []
    lines = [
        "# Full Live Workflow Smoke Report",
        "",
        f"project_model: {artifact.get('project_model', '')}",
        f"evaluator_model: {artifact.get('evaluator_model', '')}",
        f"db_path: {artifact.get('db_path', '')}",
        f"issues: {', '.join(issues) if issues else 'none'}",
        "",
        "## Generation",
        f"generated_question_count: {generated_question_count}",
        f"selected_question_id: {artifact.get('selected_question_id', '')}",
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
